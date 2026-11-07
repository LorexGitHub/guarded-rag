# 0006. HTTP API contract and trace shape

Status: proposed. Issue: LorexGitHub/guarded-rag#16. Builds on ADRs 0004 and 0005.

## Decision

1. **Routes** (API Gateway, JSON, one Lambda handler each):

| Route | Request | Success response |
|---|---|---|
| `POST /query` | `{"question": str}` | `200 {"answer", "refused", "sources", "trace"}` |
| `POST /uploads` | `{"filename": str}` | `200 {"doc_id", "upload_url", "method": "PUT"}` |
| `GET /documents/{doc_id}` | none | `200 {"doc_id", "status": "pending"\|"ready"\|"failed", "chunks": int\|null}` |

2. **Query.** No `k` or `min_score` overrides (ADR 0005 fixes them). `sources` is `[{doc_id, source, chunk_index}]` for passed hits only, deduplicated. The trace is always returned.
3. **Refusal is `200` with `refused: true`.** It is a designed outcome, not a client error.
4. **Errors.** Body is `{"error": {"code", "request_id"}}` and never contains the question, text or exception message.
   - `400 bad_request`: malformed JSON, missing field, or a filename that is not `.txt` or `.md`.
   - `500 guardrail_failed`: `Guardrail.redact` raised (fails closed, ADR 0005).
   - `502 upstream_failed`: `LLM`, `VectorStore` or `Embedder` raised.
   - `code` is a closed set of these three.
5. **Upload.** The browser PUTs the file to a presigned S3 URL; the S3 event starts ingest (ADR 0003). `doc_id` is the sanitized filename (`handbook.md` becomes `handbook-md`), so a re-upload replaces the document through `replace_document`. Only `.txt` and `.md` are accepted. The ingest handler enforces a 1 MB cap, because a presigned PUT cannot.
6. **Ingest completion.** The ingest handler writes `status/{doc_id}.json` (`ready` with a chunk count, or `failed` with no detail) after `replace_document`, so `ready` means searchable. `GET /documents/{doc_id}` reads it; a missing marker is `pending`. The UI polls about every second and gives up after a timeout. The API Lambda needs S3 read access.
7. **Trace.**
   - `hits[]`: `{doc_id, source, chunk_index, score, passed, text}`, all top-k, `text` redacted.
   - `findings_in[]` and `findings_out[]`: `{entity_type, placeholder}` only. **No spans.** The UI highlights placeholders by string match.
   - No timings, no raw values.
8. **CORS.** Terraform sets one exact allowed origin, the S3 website origin (no `*`). API Gateway allows `POST` and `GET` with `Content-Type`. The uploads bucket allows `PUT` with `Content-Type`. Handler error responses also carry `Access-Control-Allow-Origin`.

## Consequences

- `Finding` keeps `start` and `end` in Python (ADR 0005). The API serializer drops them.
- The e2e test includes a real cross-origin preflight against Floci. Floci's CORS support is unverified; if it fails, record that in `docs/spike.md` and revisit decision 8.

## Triggers to revisit

- The UI needs timings or per-stage detail: add them to the trace as new optional fields.
- Ingest status needs more than three states: move the marker to a status table.
