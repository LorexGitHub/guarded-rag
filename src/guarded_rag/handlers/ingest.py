"""S3-triggered ingest (ADR 0003, 0006): enforce the size cap, ingest, write the status marker."""

import json
import logging
from collections.abc import Callable
from urllib.parse import unquote_plus

from guarded_rag.handlers.deps import request_deps
from guarded_rag.handlers.names import UPLOAD_PREFIX, doc_id_for, is_allowed_filename, status_key
from guarded_rag.handlers.objects import Objects, build_objects
from guarded_rag.pipeline import Deps, ingest_document

MAX_BYTES = 1_000_000

log = logging.getLogger(__name__)


class Rejected(Exception):
    """The upload cannot be ingested. Carries no detail, by design."""


def handler(
    event,
    context,
    objects: Objects | None = None,
    deps_factory: Callable[[], Deps] = request_deps,
) -> dict:
    objects = objects or build_objects()
    for record in event["Records"]:
        _ingest_record(record["s3"]["object"], objects, deps_factory)
    return {"processed": len(event["Records"])}


def _ingest_record(obj: dict, objects: Objects, deps_factory: Callable[[], Deps]) -> None:
    source = unquote_plus(obj["key"]).removeprefix(UPLOAD_PREFIX)
    doc_id = doc_id_for(source)
    try:
        chunks = _ingest(obj["key"], obj["size"], source, doc_id, objects, deps_factory)
        marker = {"status": "ready", "chunks": chunks}
    except Exception as e:
        # Log the type only: messages can echo document text. A failed marker has no detail.
        log.error("ingest of %s failed: %s", doc_id, type(e).__name__)
        marker = {"status": "failed", "chunks": None}
    objects.write(status_key(doc_id), json.dumps(marker).encode())


def _ingest(key, size, source, doc_id, objects, deps_factory) -> int:
    if size > MAX_BYTES or not is_allowed_filename(source):
        raise Rejected
    body = objects.read(unquote_plus(key))
    if body is None:
        raise Rejected
    return ingest_document(deps_factory(), doc_id, source, body.decode("utf-8"))
