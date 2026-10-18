"""Load local models lazily; imports and help do not download model weights."""
from functools import lru_cache
from contextlib import closing
import hashlib
import sqlite3

import numpy as np
from langchain_core.embeddings import Embeddings

from .settings import DATA, EMBEDDING_MODEL, EMBEDDING_REVISION, RERANKER_MODEL, RERANKER_REVISION


@lru_cache(maxsize=1)
def embedding_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(EMBEDDING_MODEL, revision=EMBEDDING_REVISION)


@lru_cache(maxsize=1)
def reranker_model():
    from sentence_transformers import CrossEncoder
    return CrossEncoder(RERANKER_MODEL, revision=RERANKER_REVISION, max_length=512)


def encode_documents(texts: list[str]):
    model = embedding_model()
    revision = getattr(model[0].auto_model.config, "_commit_hash", None) or EMBEDDING_REVISION
    keys = [hashlib.sha256(f"{EMBEDDING_MODEL}:{revision}:{text}".encode()).hexdigest() for text in texts]
    cache_path = DATA / "indexes" / "embedding-cache.sqlite3"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(cache_path)) as cache:
        cache.execute("CREATE TABLE IF NOT EXISTS vectors (key TEXT PRIMARY KEY, vector BLOB NOT NULL)")
        found = {}
        for key in dict.fromkeys(keys):
            row = cache.execute("SELECT vector FROM vectors WHERE key = ?", (key,)).fetchone()
            if row:
                found[key] = np.frombuffer(row[0], dtype=np.float32).copy()
        missing = list(dict.fromkeys(key for key in keys if key not in found))
        text_by_key = dict(zip(keys, texts))
        if missing:
            vectors = model.encode([text_by_key[key] for key in missing], normalize_embeddings=True,
                                   batch_size=16, show_progress_bar=False)
            for key, vector in zip(missing, vectors):
                value = np.asarray(vector, dtype=np.float32)
                cache.execute("INSERT OR REPLACE INTO vectors VALUES (?, ?)", (key, value.tobytes()))
                found[key] = value
        cache.commit()
    return np.stack([found[key] for key in keys])


def encode_query(text: str):
    # BGE's recommended retrieval instruction is for queries, not documents.
    return embedding_model().encode(["Represent this sentence for searching relevant passages: " + text],
                                    normalize_embeddings=True, show_progress_bar=False)[0]


class CachedBGEEmbeddings(Embeddings):
    """LangChain embedding integration preserving our model, cache and query instruction."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return encode_documents(texts).tolist() if texts else []

    def embed_query(self, text: str) -> list[float]:
        return encode_query(text).tolist()
