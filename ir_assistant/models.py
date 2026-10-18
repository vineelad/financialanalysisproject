from typing import Literal

from pydantic import BaseModel, Field


class Source(BaseModel):
    document_id: str
    bank: str
    title: str
    url: str
    format: Literal["html", "pdf"]
    periods: list[str]
    publication_date: str


class Block(BaseModel):
    block_id: str
    document_id: str
    bank: str
    kind: Literal["narrative", "table"]
    text: str
    location: str
    url: str
    periods: list[str]
    # Source row IDs survive all chunking strategies for evaluation.
    evidence_ids: list[str]


class Chunk(BaseModel):
    chunk_id: str
    document_id: str
    bank: str
    strategy: str
    text: str
    location: str
    url: str
    periods: list[str]
    evidence_ids: list[str]
    token_count: int


class Hit(BaseModel):
    chunk: Chunk
    score: float


class Scope(BaseModel):
    banks: list[str] = Field(default_factory=list)
    periods: list[str] = Field(default_factory=list)
    clarification: str | None = None
    unsupported: str | None = None


class Claim(BaseModel):
    text: str
    citations: list[str] = Field(min_length=1)


class GeneratedAnswer(BaseModel):
    status: Literal["answered", "insufficient_evidence"]
    claims: list[Claim] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class Answer(BaseModel):
    question: str
    status: str
    mode: str
    text: str
    hits: list[Hit] = Field(default_factory=list)
    elapsed_seconds: float = 0
    usage: dict = Field(default_factory=dict)
