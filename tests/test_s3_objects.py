import io

import pytest
from botocore.response import StreamingBody
from botocore.stub import Stubber

from guarded_rag.handlers.objects import S3Objects


@pytest.fixture(autouse=True)
def aws_env(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")


def test_presigned_url_is_a_put_on_the_public_endpoint():
    objects = S3Objects("bucket", public_endpoint="http://localhost:4566")
    url = objects.presign_put("uploads/a.md")
    assert url.startswith("http://localhost:4566/")
    assert "uploads/a.md" in url
    assert "X-Amz-Signature=" in url


def test_read_returns_the_bytes():
    objects = S3Objects("bucket")
    body = StreamingBody(io.BytesIO(b"hello"), 5)
    with Stubber(objects._s3) as stub:
        stub.add_response("get_object", {"Body": body}, {"Bucket": "bucket", "Key": "k"})
        assert objects.read("k") == b"hello"


def test_read_of_a_missing_key_is_none():
    objects = S3Objects("bucket")
    with Stubber(objects._s3) as stub:
        stub.add_client_error("get_object", "NoSuchKey")
        assert objects.read("k") is None


def test_write_puts_json():
    objects = S3Objects("bucket")
    with Stubber(objects._s3) as stub:
        stub.add_response(
            "put_object",
            {},
            {"Bucket": "bucket", "Key": "k", "Body": b"{}", "ContentType": "application/json"},
        )
        objects.write("k", b"{}")
        stub.assert_no_pending_responses()
