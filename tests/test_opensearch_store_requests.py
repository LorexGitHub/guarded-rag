"""OpenSearchStore edge cases that need scripted responses, so no live OpenSearch."""

import httpx
import pytest

from guarded_rag.opensearch_store import OpenSearchStore
from tests.contract import chunk


def store_answering(*responses: httpx.Response) -> OpenSearchStore:
    queue = list(responses)
    client = httpx.Client(
        transport=httpx.MockTransport(lambda request: queue.pop(0)), base_url="http://os"
    )
    return OpenSearchStore(client)


def test_losing_a_concurrent_create_race_is_not_an_error():
    race = httpx.Response(400, text='{"error":{"type":"resource_already_exists_exception"}}')
    store_answering(httpx.Response(404), race).ensure_index(3)


def test_other_create_failures_raise():
    with pytest.raises(httpx.HTTPStatusError):
        store_answering(httpx.Response(404), httpx.Response(400, text="bad mapping")).ensure_index(
            3
        )


def test_a_hit_scoring_exactly_min_score_passes():
    found = {
        "hits": {
            "hits": [
                {
                    "_score": 0.7,
                    "_source": {"doc_id": "a", "source": "a.txt", "chunk_index": 0, "text": "t"},
                }
            ]
        }
    }
    [hit] = store_answering(httpx.Response(200, json=found)).search([1, 0, 0], k=5, min_score=0.7)
    assert hit.passed


def test_replace_document_rejects_mismatched_chunks_and_vectors():
    deleted = httpx.Response(200, json={})
    with pytest.raises(ValueError):
        store_answering(deleted).replace_document("a", [chunk("a", 0)], [[1, 0, 0], [0, 1, 0]])
