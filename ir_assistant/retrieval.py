import hashlib
import json
import re
from typing import Any

from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_chroma import Chroma
from pydantic import Field

from .embedding import CachedBGEEmbeddings, reranker_model
from .documents import to_document
from .models import Block, Chunk, Hit
from .metric_registry import matches_metric_label
from .metric_registry import metric_definition
from .banks import bank_registry, named_banks
from .settings import CANDIDATE_K, CONTEXT_TOKENS, DATA, EMBEDDING_MODEL, EMBEDDING_REVISION, FINAL_K
from .scope import consumer_only, header_periods, matches_quarter_context
from .storage import read_jsonl, write_json, write_jsonl

RETRIEVAL_POLICY = "v6-source-segment-alias-coverage"


def retrieval_budget(question: str, banks: list[str]) -> dict:
    count = max(1, len(banks))
    metrics = max(1, len(required_peer_metrics(question)))
    return {"candidate_k": max(CANDIDATE_K, 10 * count),
            "final_k": max(FINAL_K, metrics * count),
            "context_tokens": CONTEXT_TOKENS if count <= 2 else (CONTEXT_TOKENS // 2) * count}


def revenue_build_question(question: str) -> bool:
    """Separate a segment's revenue construction from a peer gap calculation."""
    if re.search(r"\b(gap|difference|ratio|larger|smaller)\b", question, re.I) and not re.search(
            r"\b(build(?:s|ing)?|built|breakdown|components?|composition|reconcile)\b", question, re.I):
        return False
    return bool(re.search(r"\brevenue\b", question, re.I) and re.search(
        r"\b(build(?:s|ing)?|built|breakdown|components?|compose[ds]?|composition|made up|reconcile)\b"
        r"|how\b.*\brevenue\b.*\b(calculated|constructed|derived)\b", question, re.I))


def narrative_question(question: str) -> bool:
    return bool(re.search(r"\b(why|drove|driven|drivers?|explain|explanation)\b|management (?:say|attribute)", question, re.I))


def row_label(text: str) -> str:
    if "\nRow " not in text:
        return ""
    label = text.rsplit("\nRow ", 1)[1].split("|", 1)[0].split("=", 1)[-1]
    return re.sub(r"\s*\([a-z]\)\s*$", "", label, flags=re.I).strip().casefold()


def search_text(chunk: Chunk) -> str:
    # Repeated table headers should not outrank a matching numeric row.
    label = row_label(chunk.text)
    return (label + " ") * 5 + chunk.text if label else chunk.text


def scope_matches(chunk: Chunk, question: str) -> bool:
    if consumer_only(question) and "Table header context:\n" in chunk.text:
        # Inspect actual headings/row labels, not a preceding CEO paragraph
        # which may mention every business in the bank.
        header = chunk.text.split("Table header context:\n", 1)[1].split("\nRow ", 1)[0]
        values = [value.strip() for line in header.splitlines()
                  for value in (re.findall(r"\bc\d+(?:-\d+)?=([^|]+)", line) or [line])]
        values.append(row_label(chunk.text))
        markers = bank_registry().get(chunk.bank, {}).get("consumer_table_markers", ["Consumer", "CCB", "USPB"])
        if not any(value.casefold().startswith(marker.casefold()) for value in values for marker in markers):
            return False
    if not re.search(r"\bconsolidated\b|company.wide|firm.wide|group.level", question, re.I):
        return True
    header = chunk.text.split("\nRow ", 1)[0]
    return not re.search(r"business segment|segment results|consumer.*banking|commercial.*bank|wealth.*management|global markets", header, re.I)


def required_peer_metrics(question: str) -> list[str]:
    text = question.lower()
    if revenue_build_question(question):
        return ["revenue", "net_interest_income", "noninterest_income"]
    if narrative_question(question):
        return []
    if re.search(r"\broa\b|return on (?:average )?assets", text):
        return ["roa"]
    if re.search(r"\bassets?\b", text):
        return ["assets"]
    if "operating leverage" in text:
        return ["revenue", "expense"]
    if "revenue" in text and not any(term in text for term in ("noninterest revenue", "interest income", "rate", "yield")):
        return ["revenue"]
    if "expense" in text:
        return ["expense"]
    return []


def numeric_metric_row(chunk: Chunk, metric: str) -> bool:
    if "\nRow " not in chunk.text:
        return False
    row = chunk.text.rsplit("\nRow ", 1)[1]
    if not re.search(r"\bc\d+(?:-\d+)?=\(?\d", row):
        return False
    label = row_label(chunk.text)
    return matches_metric_label(label, "noninterest_expense" if metric == "expense" else metric)


def peer_metric_hits(ranked: list[Hit], banks: list[str], question: str, periods: list[str] | None = None) -> list[Hit]:
    required = []
    for bank in banks:
        for metric in required_peer_metrics(question):
            matching = [h for h in ranked if h.chunk.bank == bank and numeric_metric_row(h.chunk, metric)
                        and scope_matches(h.chunk, question)]
            if metric == "assets" and "average" in question.lower():
                matching = [h for h in matching if re.search(r"average balances|average balance sheets", h.chunk.text, re.I)]
            if metric == "assets" and re.search(r"period.end|balance sheet|asset balances", question, re.I) and "average" not in question.lower():
                matching = [h for h in matching if not re.search(r"average balances|average balance sheets", h.chunk.text, re.I)]
            # A row spanning both requested quarters is preferable to a row
            # containing just one, independently of its gold/fact annotation.
            matching.sort(key=lambda h: -len(header_periods(h.chunk.text).intersection(periods or [])))
            if matching:
                required.append(matching[0])
    return required


def explanation_hits(ranked: list[Hit], banks: list[str], question: str) -> list[Hit]:
    if not narrative_question(question):
        return []
    metric = "expense" if "expense" in question.lower() and "revenue" not in question.lower() else "revenue"
    result = []
    for bank in banks:
        matches = [h for h in ranked if h.chunk.bank == bank and "\nRow " not in h.chunk.text
                   and re.search(metric + r"[^\n]{0,160}\b(driven|due to|reflect|primarily|because)", h.chunk.text, re.I)
                   and not re.search(r"forward.looking|risk factors", h.chunk.text, re.I)]
        if matches:
            result.append(matches[0])
    return result


def segment_structure_question(question: str) -> bool:
    text = question.lower()
    return bool(re.search(r"\bsegments?\b", text)) and bool(
        re.search(r"\b(names?|structure|scope|organized|organisation|organization)\b", text)
        or re.search(r"\bwhich\b.*\bsegments?\b.*\breport", text))


def segment_overview(text: str) -> bool:
    # Select the document's own organization, without a list of bank-specific
    # segment names or source IDs. Detailed business-line tables do not qualify.
    return bool(re.search(r"table of contents|(?:by|across) business segments?|reportable segments?", text, re.I))


def prefer_segment_overviews(chunks: list[Chunk], question: str) -> list[Chunk]:
    if not segment_structure_question(question):
        return chunks
    preferred = [c for c in chunks if segment_overview(c.text)]
    covered_banks = {c.bank for c in preferred}
    # Preserve ordinary retrieval for a bank with no identified overview.
    return preferred + [c for c in chunks if c.bank not in covered_banks]


def select_final_hits(ranked: list[Hit], banks: list[str], question: str = "", periods: list[str] | None = None) -> list[Hit]:
    final, used = [], 0
    budget = retrieval_budget(question, banks)
    limit = budget["final_k"]

    def add(hit: Hit) -> None:
        nonlocal used
        if (len(final) < limit and hit.chunk.chunk_id not in {h.chunk.chunk_id for h in final}
                and used + hit.chunk.token_count <= budget["context_tokens"]):
            final.append(hit)
            used += hit.chunk.token_count

    for hit in peer_metric_hits(ranked, banks, question, periods) + explanation_hits(ranked, banks, question):
        add(hit)
    if len(banks) > 1:
        for bank in banks:
            if any(h.chunk.bank == bank for h in final):
                continue
            for hit in ranked:
                if hit.chunk.bank == bank and used + hit.chunk.token_count <= budget["context_tokens"]:
                    add(hit)
                    break
    for hit in ranked:
        add(hit)
    return final


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _base_retrieval_queries(question: str) -> list[str]:
    question = re.sub(r"\broa\b", "return on assets", question, flags=re.I)
    question = re.sub(r"\basset\b", "assets", question, flags=re.I)
    if revenue_build_question(question):
        return [question + " " + metric for metric in
                ("total net revenue", "net interest income", "total noninterest income noninterest revenue")]
    if segment_structure_question(question):
        queries = [question, "reported business segments table of contents quarterly results by business segment"]
        if re.search(r"\bcorporate\b", question, re.I):
            queries.append("commercial investment bank business segment reporting structure")
        return queries
    if re.search(r"operating\s+leverage", question, flags=re.I):
        # Retrieve both required metrics instead of relying on the model to
        # associate this analytical term with its underlying source rows.
        return [re.sub(r"operating\s+leverage", metric, question, flags=re.I)
                for metric in ("total net revenue", "total noninterest expense")]
    return [question]


def retrieval_queries(question: str, banks: list[str] | None = None) -> list[str]:
    queries = _base_retrieval_queries(question)
    if consumer_only(question):
        for bank in (banks if banks is not None else named_banks(question)):
            terms = bank_registry().get(bank, {}).get("consumer_query_terms", [])
            if not terms:
                continue
            labels = [label for metric in required_peer_metrics(question)
                      for label in metric_definition("noninterest_expense" if metric == "expense" else metric).retrieval_labels.get(bank, ())]
            queries.extend(query + " " + " ".join([*terms, *labels]) for query in _base_retrieval_queries(question))
    return list(dict.fromkeys(queries))


def fuse(rankings: list[list[str]], k: int = 60) -> list[tuple[str, float]]:
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, item_id in enumerate(dict.fromkeys(ranking), 1):
            scores[item_id] = scores.get(item_id, 0) + 1 / (k + rank)
    return sorted(scores.items(), key=lambda item: (-item[1], item[0]))


def client():
    import chromadb
    from chromadb.config import Settings
    return chromadb.PersistentClient(path=str(DATA / "indexes" / "chroma"),
                                    settings=Settings(anonymized_telemetry=False))


def vector_store(collection_name: str) -> Chroma:
    return Chroma(client=client(), collection_name=collection_name,
                  embedding_function=CachedBGEEmbeddings(), create_collection_if_not_exists=False)


class HybridCandidateRetriever(BaseRetriever):
    """A LangChain retriever returning the fused candidate pool before reranking."""

    engine: Any = Field(exclude=True)
    banks: list[str] = Field(default_factory=list)
    periods: list[str] = Field(default_factory=list)

    def _get_relevant_documents(self, query: str, *, run_manager: CallbackManagerForRetrieverRun) -> list[Document]:
        return self.engine.candidate_documents(query, self.banks, self.periods)


def build_index(strategy: str) -> dict:
    from .chunking import chunk_blocks
    blocks_path = DATA / "processed" / "blocks.jsonl"
    blocks = read_jsonl(blocks_path, Block)
    if not blocks:
        raise ValueError("The prepared corpus is empty")
    chunks = chunk_blocks(blocks, strategy)
    # Build a new collection, then publish its name. Failed rebuilds leave the
    # previous published index usable. Old collections can be cleaned manually.
    fingerprint = hashlib.sha256(blocks_path.read_bytes() + EMBEDDING_MODEL.encode() +
                                 json.dumps([c.model_dump() for c in chunks], sort_keys=True).encode()).hexdigest()
    collection_name = f"ir-{strategy}-{fingerprint[:16]}"
    chroma_client = client()
    chroma_client.get_or_create_collection(collection_name, metadata={"hnsw:space": "cosine"})
    store = Chroma(client=chroma_client, collection_name=collection_name,
                   embedding_function=CachedBGEEmbeddings())
    print(f"Indexing {strategy}: {len(chunks)} chunks with {EMBEDDING_MODEL}", flush=True)
    for start in range(0, len(chunks), 32):
        batch = chunks[start:start + 32]
        store.add_documents([to_document(item) for item in batch], ids=[item.chunk_id for item in batch])
        if start == 0 or (start + len(batch)) % 320 == 0 or start + len(batch) == len(chunks):
            print(f"  {strategy}: {start + len(batch)}/{len(chunks)} indexed", flush=True)
    write_jsonl(DATA / "processed" / f"chunks-{strategy}.jsonl", chunks)
    from .embedding import embedding_model
    summary = {"collection": collection_name, "strategy": strategy, "chunks": len(chunks),
               "embedding_model": EMBEDDING_MODEL, "corpus_hash": hashlib.sha256(blocks_path.read_bytes()).hexdigest()}
    summary["model_revision"] = getattr(embedding_model()[0].auto_model.config, "_commit_hash", None) or EMBEDDING_REVISION
    write_json(DATA / "processed" / f"index-{strategy}.json", summary)
    return summary


class Retriever:
    def __init__(self, strategy: str):
        self.chunks = read_jsonl(DATA / "processed" / f"chunks-{strategy}.jsonl", Chunk)
        summary = json.loads((DATA / "processed" / f"index-{strategy}.json").read_text(encoding="utf-8"))
        if summary["embedding_model"] != EMBEDDING_MODEL or summary.get("model_revision") not in (None, EMBEDDING_REVISION):
            raise ValueError("Embedding model changed after indexing; rebuild both indexes")
        current_hash = hashlib.sha256((DATA / "processed" / "blocks.jsonl").read_bytes()).hexdigest()
        if summary["corpus_hash"] != current_hash:
            raise ValueError("Corpus changed after indexing; rebuild both indexes")
        self.store = vector_store(summary["collection"])
        self.by_id = {chunk.chunk_id: chunk for chunk in self.chunks}

    def candidate_documents(self, question: str, banks: list[str], periods: list[str]) -> list[Document]:
        from rank_bm25 import BM25Okapi
        available = [c for c in self.chunks if (not banks or c.bank in banks)
                     and (not periods or any(p in c.periods for p in periods))
                     and matches_quarter_context(c.text, periods, question) and scope_matches(c, question)]
        consumer_terms = ["Consumer", "CONSUMER", "consumer", "CCB", "USPB", "Personal Banking"] if consumer_only(question) else []
        if consumer_terms:
            available = [c for c in available if any(term in c.text for term in consumer_terms)]
        available = prefer_segment_overviews(available, question)
        if not available:
            return []
        lookup = {chunk.chunk_id: chunk for chunk in available}
        # Separate bank searches prevent a comparison from retrieving only one
        # bank. The same quotas apply in every experimental condition.
        rankings = []
        queries = retrieval_queries(question, banks)
        query_vectors = [self.store.embeddings.embed_query(query) for query in queries]
        for bank in (banks or sorted({c.bank for c in available})):
            bank_chunks = [c for c in available if c.bank == bank]
            if not bank_chunks:
                continue
            eligible_documents = sorted({c.document_id for c in bank_chunks})
            where = {"$and": [{"bank": bank}, {"document_id": {"$in": eligible_documents}}]}
            document_filter = {"where_document": {"$or": [{"$contains": term} for term in consumer_terms]}} if consumer_terms else {}
            bm25 = BM25Okapi([tokenize(search_text(c)) for c in bank_chunks])
            for query, query_vector in zip(queries, query_vectors):
                documents = self.store.similarity_search_by_vector(query_vector, k=min(len(bank_chunks), CANDIDATE_K),
                                                                  filter=where, **document_filter)
                dense = [doc.id for doc in documents if doc.id in lookup]
                scores = bm25.get_scores(tokenize(query))
                sparse = [bank_chunks[i].chunk_id for i in sorted(range(len(scores)), key=lambda i: -scores[i])[:CANDIDATE_K]
                          if scores[i] > 0]
                rankings.extend([dense, sparse])
        fused = fuse(rankings)
        # Reserve candidate slots per requested bank, then fill globally.
        fused_hits = [Hit(chunk=lookup[cid], score=score) for cid, score in fused]
        chosen_ids = [h.chunk.chunk_id for h in peer_metric_hits(fused_hits, banks, question, periods)
                      + explanation_hits(fused_hits, banks, question)]
        if banks:
            quota = max(1, retrieval_budget(question, banks)["candidate_k"] // len(banks))
            for bank in banks:
                reserved = sum(lookup[cid].bank == bank for cid in chosen_ids)
                chosen_ids.extend([cid for cid, _ in fused if lookup[cid].bank == bank and cid not in chosen_ids][:max(0, quota-reserved)])
        chosen_ids = list(dict.fromkeys(chosen_ids + [cid for cid, _ in fused]))[:retrieval_budget(question, banks)["candidate_k"]]
        score_lookup = dict(fused)
        return [to_document(lookup[cid], score_lookup[cid]) for cid in chosen_ids]

    def search(self, question: str, banks: list[str], periods: list[str], rerank: bool = False) -> tuple[list[Hit], list[Hit]]:
        documents = HybridCandidateRetriever(engine=self, banks=banks, periods=periods).invoke(question)
        candidates = [Hit(chunk=self.by_id[doc.id], score=doc.metadata["retrieval_score"]) for doc in documents]
        ranked = candidates[:]
        if rerank and ranked:
            ranking_question = question
            if segment_structure_question(question):
                # Rank the resolved structural intent, rather than letting
                # corporate/business-line wording favor an umbrella heading.
                ranking_question = retrieval_queries(question)[-1]
            if re.search(r"operating\s+leverage", question, flags=re.I):
                ranking_question += " Retrieve total net revenue and total noninterest expense for both quarters."
            scores = reranker_model().predict([(ranking_question, hit.chunk.text) for hit in ranked])
            ranked = [Hit(chunk=hit.chunk, score=float(score)) for hit, score in zip(ranked, scores)]
        ranked.sort(key=lambda hit: (-hit.score, hit.chunk.chunk_id))
        return select_final_hits(ranked, banks, question, periods), candidates
