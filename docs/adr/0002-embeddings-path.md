# 0002. Embeddings path

Status: proposed. Issue: LorexGitHub/guarded-rag#9. Covers handoff decision #11. Builds on ADR 0001.

## Decision

1. **Embeddings call Ollama `nomic-embed-text` directly over HTTP**, from the Lambda code, behind an `Embedder` protocol with one `OllamaEmbedder` implementation. Floci stubs embeddings, so no AWS route exists.
2. **The vector dimension is pinned to 768.** `Embedder` exposes `dim`, the OpenSearch `knn_vector` mapping is created from it, and ingest asserts that every returned vector has length `dim`. A model swap fails loudly instead of corrupting the index. Changing models means reindexing.
3. **Ingest batches through `/api/embed`**, sending `input: [...]` in batches of about 32 chunks. The query path sends a single-item `input`.
4. **Apply nomic's task prefixes inside `OllamaEmbedder`**: `search_document: ` for chunks and `search_query: ` for questions. Callers never see them. Omitting them lowers retrieval quality, and putting them in the caller would leak the model choice.

## Alternatives rejected

- **Embed inside the Lambda** (bundled ONNX or sentence-transformers). Removes the non-AWS call, but bloats the Lambda image and memory (ADR 0001 already has Lambda size unmeasured), and adds a second model runtime next to Ollama.
- **Route through Floci's Bedrock emulation.** Floci stubs `InvokeModel` and embeddings. It would need an upstream change.

## README credibility cost

The project claim is "AWS-shaped code against local backends". This is the one call that breaks it. The README must say so in one sentence: embeddings go straight to Ollama, because Floci can't emulate them. On real AWS the `Embedder` implementation would be swapped for a Bedrock Titan or Cohere one, and the dimension and mapping would change with it. The `Embedder` seam is what keeps that swap contained.

## Triggers to revisit

- Floci adds embedding proxying: add a Bedrock-backed `Embedder` and drop the exception.
- Ingest on the demo corpus takes too long on CPU: raise the batch size or shrink the corpus before changing models.
- The eval shows retrieval is the weak link: try a larger embedder, which means a new dimension and a reindex.

## Still open

- Checked on 2026-11-07 against a local Ollama: `/api/embed` with two inputs returns 2 vectors of 768 dims. Whether the Lambda containers can reach Ollama by name is still unchecked.
- Measure `nomic-embed-text` resident memory alongside `llama3.2:3b` (ADR 0001 estimates about 0.3 GiB).
