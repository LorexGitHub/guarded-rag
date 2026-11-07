import json

import pytest

from guarded_rag.handlers.uploads import handler
from tests.fakes_aws import FakeObjects


def call(body, objects=None):
    event = {"body": json.dumps(body) if not isinstance(body, str) else body}
    response = handler(event, object(), objects=objects or FakeObjects())
    return response["statusCode"], json.loads(response["body"])


def test_returns_doc_id_and_presigned_put_url():
    status, body = call({"filename": "handbook.md"})
    assert status == 200
    assert body == {
        "doc_id": "handbook-md",
        "upload_url": "http://s3.test/uploads/handbook.md?signed",
        "method": "PUT",
    }


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"filename": 3},
        {"filename": ""},
        {"filename": "report.pdf"},
        {"filename": ".md"},
        {"filename": "a/b.md"},
        "not json",
    ],
)
def test_bad_requests(payload):
    status, body = call(payload)
    assert (status, body["error"]["code"]) == (400, "bad_request")


def test_txt_is_allowed_case_insensitively():
    assert call({"filename": "NOTES.TXT"})[0] == 200


def test_s3_failure_is_upstream():
    class Broken(FakeObjects):
        def presign_put(self, key):
            raise RuntimeError("down")

    status, body = call({"filename": "a.md"}, Broken())
    assert (status, body["error"]["code"]) == (502, "upstream_failed")
