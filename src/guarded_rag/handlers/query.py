"""POST /query (ADR 0006): runs answer_question and serializes the result and trace."""

from collections.abc import Callable

from guarded_rag.handlers.deps import request_deps
from guarded_rag.handlers.http import BadRequest, handle, json_body
from guarded_rag.pipeline import Deps, QueryResult, answer_question
from guarded_rag.seams import Finding, Hit


def handler(event, context, deps_factory: Callable[[], Deps] = request_deps) -> dict:
    return handle(lambda: _query(event, deps_factory), context)


def _query(event: dict, deps_factory: Callable[[], Deps]) -> dict:
    question = json_body(event).get("question")
    if not isinstance(question, str) or not question.strip():
        raise BadRequest
    return _serialize(answer_question(deps_factory(), question))


def _serialize(result: QueryResult) -> dict:
    return {
        "answer": result.answer,
        "refused": result.refused,
        "sources": [vars(s) for s in result.sources],
        "trace": {
            "hits": [_hit(h) for h in result.trace.hits],
            "findings_in": [_finding(f) for f in result.trace.findings_in],
            "findings_out": [_finding(f) for f in result.trace.findings_out],
        },
    }


def _hit(hit: Hit) -> dict:
    c = hit.chunk
    return {
        "doc_id": c.doc_id,
        "source": c.source,
        "chunk_index": c.chunk_index,
        "score": hit.score,
        "passed": hit.passed,
        "text": c.text,
    }


def _finding(finding: Finding) -> dict:
    return {"entity_type": finding.entity_type, "placeholder": finding.placeholder}
