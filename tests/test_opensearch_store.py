"""VectorStore contract against a real OpenSearch (the Compose stack's domain, host port 9400)."""

import os
import uuid

import httpx
import pytest

from guarded_rag.opensearch_store import OpenSearchStore
from tests.contract import DIM, VectorStoreContract

pytestmark = pytest.mark.e2e

URL = os.environ.get("OPENSEARCH_URL", "http://localhost:9400")


@pytest.fixture
def store():
    client = httpx.Client(base_url=URL, timeout=30)
    index = f"chunks-test-{uuid.uuid4().hex[:8]}"
    yield OpenSearchStore(client, index=index)
    client.delete(f"/{index}")
    client.close()


class TestOpenSearchStore(VectorStoreContract):
    def test_ensure_index_rejects_a_different_dimension(self, store):
        store.ensure_index(DIM)
        with pytest.raises(ValueError, match="dimension"):
            store.ensure_index(DIM + 1)
