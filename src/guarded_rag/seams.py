"""The four seams (ADR 0005): protocols over frozen dataclasses."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Finding:
    """One detected PII span. Never carries the raw value."""

    entity_type: str
    placeholder: str
    start: int
    end: int


@dataclass(frozen=True)
class Redaction:
    text: str
    findings: list[Finding]


@dataclass(frozen=True)
class Chunk:
    doc_id: str
    source: str
    chunk_index: int
    text: str


@dataclass(frozen=True)
class Hit:
    chunk: Chunk
    score: float
    passed: bool


class Guardrail(Protocol):
    def redact(self, text: str) -> Redaction: ...


class Embedder(Protocol):
    dim: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class VectorStore(Protocol):
    def ensure_index(self, dim: int) -> None: ...

    def replace_document(
        self, doc_id: str, chunks: list[Chunk], vectors: list[list[float]]
    ) -> None: ...

    def search(self, vector: list[float], k: int, min_score: float) -> list[Hit]: ...


class LLM(Protocol):
    def generate(self, system: str, user: str) -> str: ...
