"""build_deps(): the one place that reads env and constructs the concrete seams (ADR 0005)."""

import os
from dataclasses import replace
from functools import cache

import httpx

from guarded_rag.bedrock_llm import BedrockLLM
from guarded_rag.embedder import OllamaEmbedder
from guarded_rag.guardrails.presidio import build_presidio_guardrail
from guarded_rag.opensearch_store import OpenSearchStore
from guarded_rag.pipeline import Deps

EMBED_MODEL = "nomic-embed-text"
EMBED_DIM = 768
DEFAULT_MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"
HTTP_TIMEOUT = 120.0


@cache
def build_deps() -> Deps:
    """Cached per container. Loads spaCy, so the first call is slow."""
    import boto3

    ollama = httpx.Client(base_url=os.environ["OLLAMA_URL"], timeout=HTTP_TIMEOUT)
    opensearch = httpx.Client(base_url=os.environ["OPENSEARCH_URL"], timeout=HTTP_TIMEOUT)
    return Deps(
        guardrail=build_presidio_guardrail(),
        embedder=OllamaEmbedder(ollama, EMBED_MODEL, EMBED_DIM),
        store=OpenSearchStore(opensearch),
        # boto3 reads AWS_ENDPOINT_URL, which points it at Floci.
        llm=BedrockLLM(
            boto3.client("bedrock-runtime"), os.environ.get("BEDROCK_MODEL_ID", DEFAULT_MODEL_ID)
        ),
    )


def request_deps() -> Deps:
    """The cached deps with a fresh guardrail, because placeholders are numbered per request."""
    deps = build_deps()
    return replace(deps, guardrail=deps.guardrail.for_request())
