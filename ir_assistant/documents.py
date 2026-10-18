"""Lossless bridge between validated financial chunks and LangChain documents."""
import json

from langchain_core.documents import Document

from .models import Chunk


def to_document(chunk: Chunk, score: float | None = None) -> Document:
    metadata = chunk.model_dump(exclude={"text", "periods", "evidence_ids"})
    # Chroma metadata is scalar-valued. JSON preserves list order and IDs.
    metadata["periods_json"] = json.dumps(chunk.periods)
    metadata["evidence_ids_json"] = json.dumps(chunk.evidence_ids)
    metadata["source"] = chunk.url
    if score is not None:
        metadata["retrieval_score"] = score
    return Document(id=chunk.chunk_id, page_content=chunk.text, metadata=metadata)


def from_document(document: Document) -> Chunk:
    metadata = dict(document.metadata)
    metadata["periods"] = json.loads(metadata.pop("periods_json"))
    metadata["evidence_ids"] = json.loads(metadata.pop("evidence_ids_json"))
    metadata["text"] = document.page_content
    metadata.pop("source", None)
    metadata.pop("retrieval_score", None)
    return Chunk.model_validate(metadata)
