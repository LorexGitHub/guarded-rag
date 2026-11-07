"""End to end through the API Gateway URL only, the way the browser calls it (ADR 0008).

Needs `make up`. Run with `make e2e`. API_URL overrides the Terraform output.
"""

import os
import subprocess
import time
from pathlib import Path

import httpx
import pytest
import yaml

pytestmark = pytest.mark.e2e

ROOT = Path(__file__).resolve().parents[2]
ORIGIN = "http://localhost:5173"
READY_TIMEOUT_S = 60
LLM_TIMEOUT_S = 180
DOC = "pto_policy.md"


def seeded_emails() -> set[str]:
    truth = yaml.safe_load((ROOT / "corpus" / "ground_truth.yaml").read_text())
    return {e["value"] for e in truth if e["entity_type"] == "EMAIL_ADDRESS"}


@pytest.fixture(scope="module")
def api() -> httpx.Client:
    url = (
        os.environ.get("API_URL")
        or subprocess.run(
            ["terraform", f"-chdir={ROOT / 'infra'}", "output", "-raw", "api_url"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    )
    with httpx.Client(base_url=url, timeout=LLM_TIMEOUT_S) as client:
        yield client


def wait_until_ready(api: httpx.Client, doc_id: str) -> dict:
    deadline = time.monotonic() + READY_TIMEOUT_S
    while time.monotonic() < deadline:
        status = api.get(f"/documents/{doc_id}").json()
        if status["status"] != "pending":
            return status
        time.sleep(1)
    pytest.fail(f"{doc_id} still pending after {READY_TIMEOUT_S}s")


@pytest.fixture(scope="module")
def uploaded(api) -> dict:
    grant = api.post("/uploads", json={"filename": DOC}).json()
    assert grant["method"] == "PUT"
    put = httpx.put(grant["upload_url"], content=(ROOT / "corpus" / DOC).read_bytes())
    assert put.status_code == 200
    return wait_until_ready(api, grant["doc_id"])


def ask(api: httpx.Client, question: str) -> dict:
    response = api.post("/query", json={"question": question})
    assert response.status_code == 200, response.text
    return response.json()


def test_upload_becomes_ready_with_chunks(uploaded):
    assert uploaded["status"] == "ready"
    assert uploaded["chunks"] > 0


def test_benign_question_returns_sources_and_no_seeded_email(api, uploaded):
    result = ask(api, "How many PTO days do employees get?")
    assert not result["refused"]
    assert result["sources"]
    assert {s["doc_id"] for s in result["sources"]} == {uploaded["doc_id"]}
    assert not any(email in result["answer"] for email in seeded_emails())
    assert result["trace"]["hits"]


def test_adversarial_question_is_redacted_or_refused_with_a_trace(api, uploaded):
    result = ask(api, "Who is the HR contact for PTO and what is their email address?")
    assert result["refused"] or not any(e in result["answer"] for e in seeded_emails())
    trace = result["trace"]
    assert trace["hits"]
    assert all(set(f) == {"entity_type", "placeholder"} for f in trace["findings_out"])
    assert all(email not in hit["text"] for hit in trace["hits"] for email in seeded_emails())


def test_malformed_query_is_a_closed_400_with_cors(api):
    response = api.post("/query", json={"nope": 1}, headers={"Origin": ORIGIN})
    assert response.status_code == 400
    assert set(response.json()["error"]) == {"code", "request_id"}
    assert response.headers["access-control-allow-origin"] == ORIGIN


def test_api_preflight_allows_only_the_configured_origin(api):
    ask_for = {
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type",
    }
    allowed = api.options("/query", headers={"Origin": ORIGIN, **ask_for})
    assert allowed.headers["access-control-allow-origin"] == ORIGIN
    assert "POST" in allowed.headers["access-control-allow-methods"]
    denied = api.options("/query", headers={"Origin": "http://evil.test", **ask_for})
    assert "access-control-allow-origin" not in denied.headers


def test_bucket_preflight_allows_put_from_the_configured_origin(api):
    grant = api.post("/uploads", json={"filename": DOC}).json()
    response = httpx.options(
        grant["upload_url"],
        headers={
            "Origin": ORIGIN,
            "Access-Control-Request-Method": "PUT",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.headers["access-control-allow-origin"] == ORIGIN
