import json

import pytest

from guarded_rag.guardrails.presidio import GuardrailError
from guarded_rag.handlers.http import BadRequest, handle, json_body


class Ctx:
    aws_request_id = "req-1"


def call(fn, monkeypatch=None):
    return handle(fn, Ctx())


def body_of(response):
    return json.loads(response["body"])


def test_success_is_200_json_with_cors(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGIN", "http://site.test")
    response = call(lambda: {"ok": True})
    assert response["statusCode"] == 200
    assert body_of(response) == {"ok": True}
    assert response["headers"]["Content-Type"] == "application/json"
    assert response["headers"]["Access-Control-Allow-Origin"] == "http://site.test"


@pytest.mark.parametrize(
    ("exc", "status", "code"),
    [
        (BadRequest(), 400, "bad_request"),
        (GuardrailError("secret Jane Doe"), 500, "guardrail_failed"),
        (RuntimeError("secret Jane Doe"), 502, "upstream_failed"),
    ],
)
def test_errors_carry_only_code_and_request_id(exc, status, code):
    def boom():
        raise exc

    response = call(boom)
    assert response["statusCode"] == status
    assert body_of(response) == {"error": {"code": code, "request_id": "req-1"}}
    assert "Jane" not in response["body"]


def test_errors_also_carry_cors(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGIN", "http://site.test")

    def boom():
        raise BadRequest()

    assert call(boom)["headers"]["Access-Control-Allow-Origin"] == "http://site.test"


def test_missing_request_id_is_empty_string():
    def boom():
        raise BadRequest()

    response = handle(boom, object())
    assert body_of(response)["error"]["request_id"] == ""


def test_json_body_parses_an_object():
    assert json_body({"body": '{"a": 1}'}) == {"a": 1}


@pytest.mark.parametrize(
    "event", [{}, {"body": None}, {"body": "{"}, {"body": "[1]"}, {"body": '"x"'}]
)
def test_json_body_rejects_anything_but_an_object(event):
    with pytest.raises(BadRequest):
        json_body(event)
