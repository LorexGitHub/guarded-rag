"""HTTP plumbing shared by the API handlers (ADR 0006): JSON, CORS and the closed error set."""

import json
import os
from collections.abc import Callable

from guarded_rag.guardrails.presidio import GuardrailError


class BadRequest(Exception):
    """The request was malformed. Carries no detail, by design."""


def handle(run: Callable[[], dict], context) -> dict:
    """Runs one request. Errors become {"error": {"code", "request_id"}} and nothing else."""
    try:
        return _response(200, run())
    except BadRequest:
        return _error(400, "bad_request", context)
    except GuardrailError:
        return _error(500, "guardrail_failed", context)
    except Exception:
        return _error(502, "upstream_failed", context)


def json_body(event: dict) -> dict:
    try:
        parsed = json.loads(event.get("body") or "")
    except ValueError as e:
        raise BadRequest from e
    if not isinstance(parsed, dict):
        raise BadRequest
    return parsed


def _error(status: int, code: str, context) -> dict:
    request_id = getattr(context, "aws_request_id", "")
    return _response(status, {"error": {"code": code, "request_id": request_id}})


def _response(status: int, body: dict) -> dict:
    headers = {"Content-Type": "application/json"}
    origin = os.environ.get("ALLOWED_ORIGIN")
    if origin:
        headers["Access-Control-Allow-Origin"] = origin
    return {"statusCode": status, "headers": headers, "body": json.dumps(body)}
