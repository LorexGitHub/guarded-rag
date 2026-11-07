import json

import pytest

from guarded_rag.handlers.documents import handler
from tests.fakes_aws import FakeObjects


def call(doc_id, objects):
    event = {"pathParameters": {"doc_id": doc_id}}
    response = handler(event, object(), objects=objects)
    return response["statusCode"], json.loads(response["body"])


def test_missing_marker_is_pending():
    assert call("handbook-md", FakeObjects()) == (
        200,
        {"doc_id": "handbook-md", "status": "pending", "chunks": None},
    )


def test_ready_marker_reports_chunk_count():
    objects = FakeObjects()
    objects.write("status/handbook-md.json", b'{"status": "ready", "chunks": 3}')
    assert call("handbook-md", objects)[1] == {
        "doc_id": "handbook-md",
        "status": "ready",
        "chunks": 3,
    }


def test_failed_marker():
    objects = FakeObjects()
    objects.write("status/a-md.json", b'{"status": "failed", "chunks": null}')
    assert call("a-md", objects)[1]["status"] == "failed"


@pytest.mark.parametrize("doc_id", ["", "../x", "a b", None])
def test_bad_doc_id(doc_id):
    status, body = call(doc_id, FakeObjects())
    assert (status, body["error"]["code"]) == (400, "bad_request")


def test_missing_path_parameters_is_bad_request():
    response = handler({}, object(), objects=FakeObjects())
    assert response["statusCode"] == 400


def test_s3_failure_is_upstream():
    class Broken(FakeObjects):
        def read(self, key):
            raise RuntimeError("down")

    assert call("a-md", Broken())[0] == 502
