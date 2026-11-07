"""Names shared by uploads, ingest and documents (ADR 0006): doc ids, S3 keys, allowed files."""

import re

ALLOWED_SUFFIXES = (".txt", ".md")
UPLOAD_PREFIX = "uploads/"
DOC_ID_PATTERN = re.compile(r"[A-Za-z0-9_-]+")


def doc_id_for(filename: str) -> str:
    """handbook.md becomes handbook-md, so a re-upload replaces the document."""
    return re.sub(r"[^A-Za-z0-9_-]", "-", filename)


def status_key(doc_id: str) -> str:
    return f"status/{doc_id}.json"


def is_allowed_filename(filename: str) -> bool:
    suffix = next((s for s in ALLOWED_SUFFIXES if filename.lower().endswith(s)), None)
    return suffix is not None and len(filename) > len(suffix) and "/" not in filename
