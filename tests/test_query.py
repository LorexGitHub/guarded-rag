import json

import pytest

from guarded_rag.guardrails.presidio import GuardrailError
from guarded_rag.handlers.query import handler
from guarded_rag.pipeline import REFUSAL, Deps, ingest_document
from tests.fakes import FakeEmbedder, FakeLLM, InMemoryVectorStore, RegexGuardrail


def make_deps(llm=None):
    return Deps(
        guardrail=RegexGuardrail(names=["Jane Doe"]),
        embedder=FakeEmbedder(),
        store=InMemoryVectorStore(),
        llm=llm or FakeLLM("Call 555-123-4567."),
    )


def call(payload, deps):
    response = handler({"body": json.dumps(payload)}, object(), deps_factory=lambda: deps)
    return response["statusCode"], json.loads(response["body"])


def test_answered_response_shape_and_redaction():
    deps = make_deps()
    ingest_document(deps, "pto-md", "pto.md", "Leave policy: 25 days.")
    status, body = call({"question": "Leave policy: 25 days."}, deps)
    assert status == 200
    assert body["refused"] is False
    assert body["answer"] == "Call <PHONE_NUMBER_1>."
    assert body["sources"] == [{"doc_id": "pto-md", "source": "pto.md", "chunk_index": 0}]
    assert set(body) == {"answer", "refused", "sources", "trace"}


def test_trace_has_hits_and_findings_without_spans():
    deps = make_deps()
    ingest_document(deps, "pto-md", "pto.md", "Ask Jane Doe about leave.")
    _, body = call({"question": "Ask Jane Doe about leave."}, deps)
    hit = body["trace"]["hits"][0]
    assert hit == {
        "doc_id": "pto-md",
        "source": "pto.md",
        "chunk_index": 0,
        "score": hit["score"],
        "passed": True,
        "text": "Ask <PERSON_1> about leave.",
    }
    assert body["trace"]["findings_in"] == [{"entity_type": "PERSON", "placeholder": "<PERSON_1>"}]
    assert body["trace"]["findings_out"] == [
        {"entity_type": "PHONE_NUMBER", "placeholder": "<PHONE_NUMBER_1>"}
    ]
    assert "Jane Doe" not in json.dumps(body)


def test_refusal_is_a_200_with_refused_true():
    status, body = call({"question": "anything"}, make_deps())
    assert status == 200
    assert body["answer"] == REFUSAL
    assert body["refused"] is True
    assert body["sources"] == []


@pytest.mark.parametrize("payload", [{}, {"question": 5}, {"question": ""}, {"question": "  "}])
def test_bad_requests(payload):
    status, body = call(payload, make_deps())
    assert (status, body["error"]["code"]) == (400, "bad_request")


def test_malformed_json_is_bad_request():
    response = handler({"body": "{"}, object(), deps_factory=make_deps)
    assert response["statusCode"] == 400


def test_guardrail_failure_is_500_and_leaks_nothing():
    class Failing:
        def redact(self, text):
            raise GuardrailError(text)

    deps = make_deps()
    deps = Deps(Failing(), deps.embedder, deps.store, deps.llm)
    status, body = call({"question": "Jane Doe"}, deps)
    assert (status, body["error"]["code"]) == (500, "guardrail_failed")
    assert "Jane" not in json.dumps(body)


def test_upstream_failure_is_502():
    class Failing:
        def generate(self, system, user):
            raise RuntimeError("down")

    deps = make_deps(Failing())
    ingest_document(deps, "a-md", "a.md", "same text")
    status, body = call({"question": "same text"}, deps)
    assert (status, body["error"]["code"]) == (502, "upstream_failed")
