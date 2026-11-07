"""Chunking, prompt building, answer_question and ingest_document over Deps (ADR 0004, 0005, 0009).

Seams raise and nothing here catches, so a guardrail failure never yields text (fails closed).
"""

from dataclasses import dataclass

from guarded_rag.config import CHUNK_CHARS, MIN_SCORE, K
from guarded_rag.seams import (
    LLM,
    Chunk,
    Embedder,
    Finding,
    Guardrail,
    Hit,
    VectorStore,
)

REFUSAL = "I can't answer that from the documents I have."

SYSTEM_PROMPT = (
    "Answer the question using only the context. "
    "If the context does not contain the answer, say you don't know."
)


@dataclass(frozen=True)
class Deps:
    guardrail: Guardrail
    embedder: Embedder
    store: VectorStore
    llm: LLM


@dataclass(frozen=True)
class Source:
    doc_id: str
    source: str
    chunk_index: int


@dataclass(frozen=True)
class Trace:
    hits: list[Hit]  # all top-k, chunk text redacted
    findings_in: list[Finding]
    findings_out: list[Finding]


@dataclass(frozen=True)
class QueryResult:
    answer: str
    sources: list[Source]
    refused: bool
    trace: Trace


def chunk_text(text: str) -> list[str]:
    """Pack paragraphs into chunks of at most CHUNK_CHARS, splitting long ones on words."""
    chunks: list[str] = []
    current = ""
    for piece in _pieces(text):
        joined = f"{current}\n\n{piece}" if current else piece
        if current and len(joined) > CHUNK_CHARS:
            chunks.append(current)
            joined = piece
        current = joined
    return chunks + [current] if current else chunks


def _pieces(text: str) -> list[str]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    return [q for p in paragraphs for q in _split_words(p)]


def _split_words(paragraph: str) -> list[str]:
    parts: list[str] = []
    current = ""
    for word in paragraph.split():
        joined = f"{current} {word}" if current else word
        if current and len(joined) > CHUNK_CHARS:
            parts.append(current)
            joined = word
        current = joined
    return parts + [current]


def ingest_document(deps: Deps, doc_id: str, source: str, text: str) -> int:
    """Replace the document's chunks. Returns the chunk count."""
    texts = chunk_text(text)
    chunks = [Chunk(doc_id, source, i, t) for i, t in enumerate(texts)]
    deps.store.ensure_index(deps.embedder.dim)
    vectors = deps.embedder.embed_documents(texts) if texts else []
    deps.store.replace_document(doc_id, chunks, vectors)
    return len(chunks)


def build_prompt(question: str, chunks: list[Chunk]) -> str:
    context = "\n\n".join(c.text for c in chunks)
    return f"Context:\n{context}\n\nQuestion: {question}"


def answer_question(deps: Deps, question: str) -> QueryResult:
    redacted_question = deps.guardrail.redact(question)
    vector = deps.embedder.embed_query(question)
    hits = deps.store.search(vector, K, MIN_SCORE)
    passed = [h.chunk for h in hits if h.passed]

    if passed:
        raw = deps.llm.generate(SYSTEM_PROMPT, build_prompt(redacted_question.text, passed))
        answer = deps.guardrail.redact(raw)
        text, findings_out = answer.text, answer.findings
    else:
        text, findings_out = REFUSAL, []

    trace = Trace(
        hits=[_redact_hit(deps.guardrail, h) for h in hits],
        findings_in=redacted_question.findings,
        findings_out=findings_out,
    )
    sources = [Source(c.doc_id, c.source, c.chunk_index) for c in passed]
    return QueryResult(text, sources, refused=not passed, trace=trace)


def _redact_hit(guardrail: Guardrail, hit: Hit) -> Hit:
    c = hit.chunk
    redacted = Chunk(c.doc_id, c.source, c.chunk_index, guardrail.redact(c.text).text)
    return Hit(redacted, hit.score, hit.passed)
