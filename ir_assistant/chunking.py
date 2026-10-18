import hashlib
import re

import numpy as np

from .embedding import embedding_model, encode_documents
from .models import Block, Chunk
from .settings import CHUNK_SIZE, OVERLAP


def _make(block: Block, strategy: str, text: str, index: int, tokenizer) -> Chunk:
    digest = hashlib.sha256(f"{strategy}:{block.block_id}:{index}:{text}".encode()).hexdigest()[:20]
    # Oversized blocks are fragment-labelled. A fragment must not receive credit
    # for a whole table row it no longer contains.
    whole = text.strip() == block.text.strip()
    evidence = block.evidence_ids if whole else [f"{block.block_id}:fragment:{digest}"]
    return Chunk(chunk_id=digest, document_id=block.document_id, bank=block.bank,
                 strategy=strategy, text=text, location=block.location, url=block.url,
                 periods=block.periods, evidence_ids=evidence,
                 token_count=len(tokenizer.encode(text, add_special_tokens=False)))


def _fixed_parts(text: str, tokenizer, size: int, overlap: int) -> list[str]:
    # Character offsets preserve exact original numbers and punctuation; decoding
    # token IDs can insert spaces into a numeric value.
    encoded = tokenizer(text, add_special_tokens=False, return_offsets_mapping=True)
    offsets = encoded["offset_mapping"]
    result = []
    for start in range(0, len(offsets), size - overlap):
        end = min(start + size, len(offsets))
        result.append(text[offsets[start][0]:offsets[end - 1][1]])
        if end == len(offsets):
            break
    return result


def chunk_blocks(blocks: list[Block], strategy: str, threshold: float = 0.45) -> list[Chunk]:
    if strategy not in {"fixed", "semantic"}:
        raise ValueError("Unknown chunking strategy")
    tokenizer = embedding_model().tokenizer
    chunks = []
    # Pack short narrative paragraphs before comparing boundary strategies;
    # otherwise a corpus of short paragraphs would produce identical indexes.
    prepared, pending = [], []
    def flush():
        if not pending:
            return
        first = pending[0]
        prepared.append(first.model_copy(update={
            "block_id": first.block_id + f":through:{pending[-1].block_id}",
            "text": "\n".join(item.text for item in pending),
            "location": first.location + (f" through {pending[-1].location}" if len(pending) > 1 else ""),
            "evidence_ids": [eid for item in pending for eid in item.evidence_ids],
        }))
        pending.clear()
    for block in blocks:
        if block.kind == "table":
            flush()
            prepared.append(block)
            continue
        proposed = "\n".join([item.text for item in pending] + [block.text])
        if pending and (pending[0].document_id != block.document_id or
                        len(tokenizer.encode(proposed, add_special_tokens=False)) > 1200):
            flush()
        pending.append(block)
    flush()
    for block in prepared:
        tokens = tokenizer.encode(block.text, add_special_tokens=False)
        if len(tokens) <= CHUNK_SIZE:
            # Atomic table rows stay intact in both experiments.
            parts = [block.text]
        elif strategy == "fixed" or block.kind == "table":
            # Very large table rows are fragments, explicitly not auto-approved
            # financial facts. Header fidelity must be reviewed before use.
            parts = _fixed_parts(block.text, tokenizer, CHUNK_SIZE, OVERLAP)
        else:
            sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", block.text) if part.strip()]
            sentences = [fragment for sentence in sentences
                         for fragment in _fixed_parts(sentence, tokenizer, CHUNK_SIZE, 0)]
            vectors = encode_documents(sentences)
            parts, current = [], []
            for i, sentence in enumerate(sentences):
                proposed = " ".join(current + [sentence])
                too_long = len(tokenizer.encode(proposed, add_special_tokens=False)) > CHUNK_SIZE
                semantic_break = bool(current) and i > 0 and float(np.dot(vectors[i - 1], vectors[i])) < threshold
                large_enough = len(tokenizer.encode(" ".join(current), add_special_tokens=False)) >= 150
                if current and (too_long or (semantic_break and large_enough)):
                    parts.append(" ".join(current))
                    current = []
                current.append(sentence)
            if current:
                parts.append(" ".join(current))
        chunks.extend(_make(block, strategy, text, index, tokenizer) for index, text in enumerate(parts))
    return chunks
