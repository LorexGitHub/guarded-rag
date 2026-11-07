"""POST /uploads: hands the browser a presigned PUT URL (ADR 0006 decision 5)."""

from guarded_rag.handlers.http import BadRequest, handle, json_body
from guarded_rag.handlers.names import UPLOAD_PREFIX, doc_id_for, is_allowed_filename
from guarded_rag.handlers.objects import Objects, build_objects


def handler(event, context, objects: Objects | None = None) -> dict:
    return handle(lambda: _upload(event, objects or build_objects()), context)


def _upload(event: dict, objects: Objects) -> dict:
    filename = json_body(event).get("filename")
    if not isinstance(filename, str) or not is_allowed_filename(filename):
        raise BadRequest
    return {
        "doc_id": doc_id_for(filename),
        "upload_url": objects.presign_put(UPLOAD_PREFIX + filename),
        "method": "PUT",
    }
