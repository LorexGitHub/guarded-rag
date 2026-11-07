"""Hand-written fakes for the four seams (ADR 0005). No mock library."""

import hashlib
import math
import re

from guarded_rag.seams import Chunk, Finding, Hit, Redaction


class FakeEmbedder:
    def __init__(self, dim: int = 8):
        self.dim = dim

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)

    def _vector(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode()).digest()
        raw = [digest[i % len(digest)] - 127.5 for i in range(self.dim)]
        norm = math.sqrt(sum(x * x for x in raw))
        return [x / norm for x in raw]


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    return dot / (math.hypot(*a) * math.hypot(*b))


class InMemoryVectorStore:
    """Real cosine search with OpenSearch's (1 + cos) / 2 score."""

    def __init__(self):
        self._rows: list[tuple[Chunk, list[float]]] = []

    def ensure_index(self, dim: int) -> None:
        pass

    def replace_document(
        self, doc_id: str, chunks: list[Chunk], vectors: list[list[float]]
    ) -> None:
        self._rows = [r for r in self._rows if r[0].doc_id != doc_id]
        self._rows += list(zip(chunks, vectors, strict=True))

    def search(self, vector: list[float], k: int, min_score: float) -> list[Hit]:
        scored = [(c, (1 + _cosine(vector, v)) / 2) for c, v in self._rows]
        best = sorted(scored, key=lambda cs: cs[1], reverse=True)[:k]
        return [Hit(c, s, s >= min_score) for c, s in best]


class FakeLLM:
    def __init__(self, answer: str = "fake answer"):
        self.answer = answer
        self.calls: list[tuple[str, str]] = []

    def generate(self, system: str, user: str) -> str:
        self.calls.append((system, user))
        return self.answer


_PATTERNS = {
    "EMAIL_ADDRESS": r"[\w.+-]+@[\w-]+\.[\w.]+",
    "PHONE_NUMBER": r"\d{3}-\d{3}-\d{4}",
}


class RegexGuardrail:
    """Stub for pipeline tests: phone, email and a name list. Real Presidio runs in slow tests."""

    def __init__(self, names: list[str] | None = None):
        self._patterns = dict(_PATTERNS)
        if names:
            self._patterns["PERSON"] = "|".join(re.escape(n) for n in names)

    def redact(self, text: str) -> Redaction:
        spans = sorted(
            (m.start(), m.end(), kind, m.group())
            for kind, pattern in self._patterns.items()
            for m in re.finditer(pattern, text)
        )
        seen: dict[tuple[str, str], str] = {}
        out, findings, pos = [], [], 0
        for start, end, kind, value in spans:
            n = sum(1 for k, _ in seen if k == kind)
            placeholder = seen.setdefault((kind, value), f"<{kind}_{n + 1}>")
            out += [text[pos:start], placeholder]
            findings.append(Finding(kind, placeholder, start, end))
            pos = end
        out.append(text[pos:])
        return Redaction("".join(out), findings)
