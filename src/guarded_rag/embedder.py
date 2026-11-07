"""Embedder over Ollama's /api/embed (ADR 0002). Task prefixes live here, not in callers."""

import httpx

BATCH_SIZE = 32
DOCUMENT_PREFIX = "search_document: "
QUERY_PREFIX = "search_query: "


class OllamaEmbedder:
    def __init__(self, client: httpx.Client, model: str, dim: int):
        self._client = client
        self._model = model
        self.dim = dim

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        prefixed = [DOCUMENT_PREFIX + t for t in texts]
        vectors: list[list[float]] = []
        for start in range(0, len(prefixed), BATCH_SIZE):
            vectors += self._embed(prefixed[start : start + BATCH_SIZE])
        return vectors

    def embed_query(self, text: str) -> list[float]:
        return self._embed([QUERY_PREFIX + text])[0]

    def _embed(self, inputs: list[str]) -> list[list[float]]:
        response = self._client.post("/api/embed", json={"model": self._model, "input": inputs})
        response.raise_for_status()
        vectors = response.json()["embeddings"]
        for vector in vectors:
            if len(vector) != self.dim:
                raise ValueError(f"embedding dimension {len(vector)} != expected {self.dim}")
        return vectors
