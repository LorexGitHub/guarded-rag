"""VectorStore over OpenSearch k-NN (ADR 0004). Index creation is create-if-missing."""

import json

import httpx

from guarded_rag.seams import Chunk, Hit


def _mapping(dim: int) -> dict:
    return {
        "settings": {"index.knn": True},
        "mappings": {
            "properties": {
                "embedding": {
                    "type": "knn_vector",
                    "dimension": dim,
                    "method": {
                        "name": "hnsw",
                        "engine": "lucene",
                        "space_type": "cosinesimil",
                    },
                },
                "text": {"type": "text"},
                "doc_id": {"type": "keyword"},
                "source": {"type": "keyword"},
                "chunk_index": {"type": "integer"},
            }
        },
    }


class OpenSearchStore:
    def __init__(self, client: httpx.Client, index: str = "chunks"):
        self._client = client
        self._index = index

    def ensure_index(self, dim: int) -> None:
        response = self._client.get(f"/{self._index}")
        if response.status_code == 404:
            self._create(dim)
            return
        response.raise_for_status()
        existing = response.json()[self._index]["mappings"]["properties"]["embedding"]["dimension"]
        if int(existing) != dim:
            raise ValueError(f"index dimension {existing} != expected {dim}")

    def _create(self, dim: int) -> None:
        response = self._client.put(f"/{self._index}", json=_mapping(dim))
        # A concurrent ensure_index may have created it between our GET and PUT.
        if response.status_code == 400 and "resource_already_exists" in response.text:
            return
        response.raise_for_status()

    def replace_document(
        self, doc_id: str, chunks: list[Chunk], vectors: list[list[float]]
    ) -> None:
        self._client.post(
            f"/{self._index}/_delete_by_query",
            params={"refresh": "true"},
            json={"query": {"term": {"doc_id": doc_id}}},
        ).raise_for_status()
        if not chunks:
            return
        body = _bulk_body(chunks, vectors)
        response = self._client.post(
            f"/{self._index}/_bulk",
            params={"refresh": "true"},
            content=body,
            headers={"content-type": "application/x-ndjson"},
        )
        response.raise_for_status()
        if response.json()["errors"]:
            raise RuntimeError(f"bulk index failed: {response.text}")

    def search(self, vector: list[float], k: int, min_score: float) -> list[Hit]:
        response = self._client.post(
            f"/{self._index}/_search",
            json={"size": k, "query": {"knn": {"embedding": {"vector": vector, "k": k}}}},
        )
        response.raise_for_status()
        return [_hit(h, min_score) for h in response.json()["hits"]["hits"]]


def _hit(raw: dict, min_score: float) -> Hit:
    source = raw["_source"]
    chunk = Chunk(source["doc_id"], source["source"], source["chunk_index"], source["text"])
    return Hit(chunk, raw["_score"], raw["_score"] >= min_score)


def _bulk_body(chunks: list[Chunk], vectors: list[list[float]]) -> str:
    lines = []
    for chunk, vector in zip(chunks, vectors, strict=True):
        lines.append({"index": {"_id": f"{chunk.doc_id}:{chunk.chunk_index}"}})
        lines.append(
            {
                "embedding": vector,
                "text": chunk.text,
                "doc_id": chunk.doc_id,
                "source": chunk.source,
                "chunk_index": chunk.chunk_index,
            }
        )
    return "".join(json.dumps(line) + "\n" for line in lines)
