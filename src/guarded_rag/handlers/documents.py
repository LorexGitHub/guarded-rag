"""GET /documents/{doc_id}: reads the ingest marker (ADR 0006 decision 6)."""

import json

from guarded_rag.handlers.http import BadRequest, handle
from guarded_rag.handlers.names import DOC_ID_PATTERN, status_key
from guarded_rag.handlers.objects import Objects, build_objects


def handler(event, context, objects: Objects | None = None) -> dict:
    return handle(lambda: _status(event, objects or build_objects()), context)


def _status(event: dict, objects: Objects) -> dict:
    doc_id = (event.get("pathParameters") or {}).get("doc_id")
    if not isinstance(doc_id, str) or not DOC_ID_PATTERN.fullmatch(doc_id):
        raise BadRequest
    marker = objects.read(status_key(doc_id))
    if marker is None:
        return {"doc_id": doc_id, "status": "pending", "chunks": None}
    stored = json.loads(marker)
    return {"doc_id": doc_id, "status": stored["status"], "chunks": stored["chunks"]}
