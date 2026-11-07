# 0005. Backend seams and interfaces

Status: proposed. Issue: LorexGitHub/guarded-rag#12. Covers handoff decision #15. Builds on ADRs 0001 to 0004.

## Decision

1. **Four seams:** `Guardrail`, `Embedder`, `VectorStore`, `LLM` (the Bedrock `converse` call). Chunking, prompt building and S3 reads are not seams. S3 reads stay in the thin ingest handler.
2. **Interfaces are `typing.Protocol`s over frozen dataclasses:**

```python
@dataclass(frozen=True)
class Finding:            # never carries the raw PII value
    entity_type: str      # "PERSON"
    placeholder: str      # "<PERSON_1>"
    start: int; end: int  # span in the original text
@dataclass(frozen=True)
class Redaction: text: str; findings: list[Finding]

class Guardrail(Protocol):
    def redact(self, text: str) -> Redaction: ...

class Embedder(Protocol):
    dim: int
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, text: str) -> list[float]: ...

@dataclass(frozen=True)
class Chunk: doc_id: str; source: str; chunk_index: int; text: str
@dataclass(frozen=True)
class Hit: chunk: Chunk; score: float; passed: bool   # passed = score >= min_score

class VectorStore(Protocol):
    def ensure_index(self, dim: int) -> None: ...
    def replace_document(self, doc_id: str, chunks: list[Chunk], vectors: list[list[float]]) -> None: ...
    def search(self, vector: list[float], k: int, min_score: float) -> list[Hit]: ...

class LLM(Protocol):
    def generate(self, system: str, user: str) -> str: ...
```

   `search` returns all top-k hits with a `passed` flag. This resolves ADR 0004 decision 4: the trace shows near-misses, and the pipeline uses only passed hits. `replace_document` makes delete-then-add one call.
3. **Wiring.** `pipeline.py` holds plain functions (`answer_question`, `ingest_document`) over a `Deps` dataclass (`guardrail`, `embedder`, `store`, `llm`). Each handler is thin and has one module-cached `build_deps()` that constructs the concrete classes from env. There is no backend factory and no env switch for backend kind: each seam has one real backend, so no unused backends exist.
4. **Config.** `K = 5` and `MIN_SCORE = 0.70` are constants in `config.py`. Endpoints and model names come from env and are read only in `build_deps()`. `pipeline.py` never reads env.
5. **Failures.** Seams raise; `pipeline.py` does not catch. Handlers map exceptions to a 5xx with no detail. The guardrail **fails closed**: if `redact` raises, the query errors and never returns unredacted text. `LLM` and `VectorStore` failures are errors, not refusals, so the eval can tell "refused" from "broke".
6. **Result shape.** `answer_question` returns a frozen `QueryResult(answer, sources, refused, trace)`. `trace` holds `hits` (all top-k), `findings_in` and `findings_out`. Chunk text in the trace is redacted through the `Guardrail`, so the API never returns raw PII.

## Fakes for unit tests

Hand-written in `tests/fakes.py`, with no mock library:

- `FakeEmbedder`: deterministic hash-based vectors with a small `dim`.
- `InMemoryVectorStore`: real cosine search with the same `(1+cos)/2` score as OpenSearch.
- `FakeLLM`: scripted answer that records the `system` and `user` it received, so tests can assert the redacted question reaches the prompt.
- Regex `Guardrail` stub (phone, email, a name list) for pipeline tests. Real Presidio runs only in `slow`-marked tests and the eval.
- One `VectorStore` contract suite runs against `InMemoryVectorStore` in unit tests and `OpenSearchStore` in e2e, so the fake cannot drift.

## Triggers to revisit

- A second real backend for a seam appears (Bedrock Guardrails, Titan): add it behind the existing protocol and a selection point in `build_deps()`. Do not add the selection point before then.
- The regex stub hides a bug that Presidio shows: widen the `slow` tests, not the stub.
- The trace's chunk redaction makes the query too slow: measure before changing the "no raw PII in the API" rule.

## Still open

- `Finding` spans refer to the original text, so they are not meaningful to the UI once the text is redacted. Check what the trace panel needs when the UI is built.
