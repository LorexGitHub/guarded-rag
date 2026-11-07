import json

from guarded_rag.handlers.ingest import MAX_BYTES, handler
from guarded_rag.pipeline import Deps
from tests.fakes import FakeEmbedder, FakeLLM, InMemoryVectorStore, RegexGuardrail
from tests.fakes_aws import FakeObjects


def make_deps(store=None):
    return Deps(RegexGuardrail(), FakeEmbedder(), store or InMemoryVectorStore(), FakeLLM())


def event(key, size):
    return {"Records": [{"s3": {"object": {"key": key, "size": size}}}]}


def status(objects, doc_id):
    return json.loads(objects.blobs[f"status/{doc_id}.json"])


def run(ev, objects, deps):
    return handler(ev, object(), objects=objects, deps_factory=lambda: deps)


def test_ingests_and_marks_ready_with_chunk_count():
    objects, deps = FakeObjects(), make_deps()
    objects.write("uploads/handbook.md", b"Leave policy: 25 days.")
    run(event("uploads/handbook.md", 22), objects, deps)
    assert status(objects, "handbook-md") == {"status": "ready", "chunks": 1}
    hits = deps.store.search(deps.embedder.embed_query("Leave policy: 25 days."), 5, 0.7)
    assert [(h.chunk.doc_id, h.chunk.source, h.passed) for h in hits] == [
        ("handbook-md", "handbook.md", True)
    ]


def test_reupload_replaces_the_document():
    objects, deps = FakeObjects(), make_deps()
    objects.write("uploads/a.md", b"first version")
    run(event("uploads/a.md", 13), objects, deps)
    objects.write("uploads/a.md", b"second version")
    run(event("uploads/a.md", 14), objects, deps)
    texts = [h.chunk.text for h in deps.store.search(deps.embedder.embed_query("x"), 5, 0.0)]
    assert texts == ["second version"]


def test_url_encoded_keys_are_decoded():
    objects, deps = FakeObjects(), make_deps()
    objects.write("uploads/my notes.txt", b"hello")
    run(event("uploads/my+notes.txt", 5), objects, deps)
    assert status(objects, "my-notes-txt") == {"status": "ready", "chunks": 1}


def test_over_the_cap_fails_without_reading():
    objects, deps = FakeObjects(), make_deps()
    objects.write("uploads/big.md", b"x")
    run(event("uploads/big.md", MAX_BYTES + 1), objects, deps)
    assert status(objects, "big-md") == {"status": "failed", "chunks": None}
    assert deps.store.search(deps.embedder.embed_query("x"), 5, 0.0) == []


def test_exactly_the_cap_is_accepted():
    objects, deps = FakeObjects(), make_deps()
    objects.write("uploads/edge.md", b"x")
    run(event("uploads/edge.md", MAX_BYTES), objects, deps)
    assert status(objects, "edge-md")["status"] == "ready"


def test_missing_object_and_bad_encoding_fail():
    objects = FakeObjects()
    run(event("uploads/gone.md", 5), objects, make_deps())
    assert status(objects, "gone-md")["status"] == "failed"
    objects.write("uploads/bin.md", b"\xff\xfe\x00")
    run(event("uploads/bin.md", 3), objects, make_deps())
    assert status(objects, "bin-md")["status"] == "failed"


def test_disallowed_suffix_fails():
    objects = FakeObjects()
    objects.write("uploads/x.pdf", b"hi")
    run(event("uploads/x.pdf", 2), objects, make_deps())
    assert status(objects, "x-pdf")["status"] == "failed"


def test_pipeline_error_marks_failed_with_no_detail_and_does_not_raise():
    class Broken(InMemoryVectorStore):
        def replace_document(self, *args):
            raise RuntimeError("secret Jane Doe")

    objects = FakeObjects()
    objects.write("uploads/a.md", b"text")
    run(event("uploads/a.md", 4), objects, make_deps(Broken()))
    assert objects.blobs["status/a-md.json"] == b'{"status": "failed", "chunks": null}'


def test_every_record_is_processed_even_after_one_fails():
    objects, deps = FakeObjects(), make_deps()
    objects.write("uploads/b.md", b"fine")
    ev = event("uploads/a.pdf", 1)
    ev["Records"] += event("uploads/b.md", 4)["Records"]
    run(ev, objects, deps)
    assert status(objects, "a-pdf")["status"] == "failed"
    assert status(objects, "b-md")["status"] == "ready"
