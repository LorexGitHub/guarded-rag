"""One VectorStore contract. Unit tests run it on InMemoryVectorStore, e2e on OpenSearchStore."""

import pytest

from guarded_rag.seams import Chunk

DIM = 3


def chunk(doc_id: str, i: int, text: str = "t") -> Chunk:
    return Chunk(doc_id, f"{doc_id}.txt", i, text)


class VectorStoreContract:
    @pytest.fixture
    def ready(self, store):
        store.ensure_index(DIM)
        return store

    def test_ensure_index_is_idempotent(self, store):
        store.ensure_index(DIM)
        store.ensure_index(DIM)

    def test_identical_vector_scores_one_and_opposite_scores_zero(self, ready):
        ready.replace_document("a", [chunk("a", 0), chunk("a", 1)], [[1, 0, 0], [-1, 0, 0]])
        hits = ready.search([1, 0, 0], k=5, min_score=0.7)
        assert [h.chunk.chunk_index for h in hits] == [0, 1]
        assert hits[0].score == pytest.approx(1.0)
        assert hits[1].score == pytest.approx(0.0)

    def test_passed_flag_follows_min_score(self, ready):
        ready.replace_document("a", [chunk("a", 0), chunk("a", 1)], [[1, 0, 0], [0, 1, 0]])
        hits = ready.search([1, 0, 0], k=5, min_score=0.7)
        assert [(h.chunk.chunk_index, h.passed) for h in hits] == [(0, True), (1, False)]

    def test_search_returns_at_most_k_best_first(self, ready):
        vectors = [[1, 0, 0], [0.9, 0.1, 0], [0.5, 0.5, 0]]
        ready.replace_document("a", [chunk("a", i) for i in range(3)], vectors)
        hits = ready.search([1, 0, 0], k=2, min_score=0.0)
        assert [h.chunk.chunk_index for h in hits] == [0, 1]

    def test_replace_document_drops_the_old_chunks_only(self, ready):
        ready.replace_document("a", [chunk("a", 0, "old")], [[1, 0, 0]])
        ready.replace_document("b", [chunk("b", 0, "other")], [[1, 0, 0]])
        ready.replace_document("a", [chunk("a", 0, "new")], [[1, 0, 0]])
        texts = sorted(h.chunk.text for h in ready.search([1, 0, 0], k=5, min_score=0.0))
        assert texts == ["new", "other"]
