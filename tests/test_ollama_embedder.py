import json

import httpx
import pytest

from guarded_rag.embedder import BATCH_SIZE, OllamaEmbedder

DIM = 4


def embedder(requests: list[dict], dim: int = DIM, vector_len: int = DIM) -> OllamaEmbedder:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/embed"
        body = json.loads(request.content)
        requests.append(body)
        return httpx.Response(200, json={"embeddings": [[0.5] * vector_len for _ in body["input"]]})

    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="http://ollama")
    return OllamaEmbedder(client, model="nomic-embed-text", dim=dim)


def test_documents_get_the_search_document_prefix():
    sent: list[dict] = []
    embedder(sent).embed_documents(["a", "b"])
    assert sent == [
        {"model": "nomic-embed-text", "input": ["search_document: a", "search_document: b"]}
    ]


def test_query_is_one_input_with_the_search_query_prefix():
    sent: list[dict] = []
    vector = embedder(sent).embed_query("why")
    assert sent[0]["input"] == ["search_query: why"]
    assert vector == [0.5] * DIM


def test_documents_are_batched_and_order_is_kept():
    sent: list[dict] = []
    vectors = embedder(sent).embed_documents([str(i) for i in range(BATCH_SIZE * 2 + 1)])
    assert [len(r["input"]) for r in sent] == [BATCH_SIZE, BATCH_SIZE, 1]
    assert sent[2]["input"] == [f"search_document: {BATCH_SIZE * 2}"]
    assert len(vectors) == BATCH_SIZE * 2 + 1


def test_wrong_vector_length_fails_loudly():
    with pytest.raises(ValueError, match="dimension"):
        embedder([], vector_len=DIM + 1).embed_documents(["a"])
    with pytest.raises(ValueError, match="dimension"):
        embedder([], vector_len=DIM + 1).embed_query("a")


def test_http_error_raises():
    client = httpx.Client(
        transport=httpx.MockTransport(lambda r: httpx.Response(500)), base_url="http://ollama"
    )
    with pytest.raises(httpx.HTTPStatusError):
        OllamaEmbedder(client, model="m", dim=DIM).embed_query("a")


def test_empty_documents_make_no_request():
    sent: list[dict] = []
    assert embedder(sent).embed_documents([]) == []
    assert sent == []
