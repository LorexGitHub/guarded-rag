from dataclasses import replace

import pytest

from guarded_rag.handlers import deps as deps_module
from tests.fakes import RegexGuardrail


class PerRequest(RegexGuardrail):
    def for_request(self):
        return PerRequest()


@pytest.fixture(autouse=True)
def clear_cache():
    deps_module.build_deps.cache_clear()
    yield
    deps_module.build_deps.cache_clear()


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("OLLAMA_URL", "http://ollama.test:11434")
    monkeypatch.setenv("OPENSEARCH_URL", "http://search.test:9200")
    monkeypatch.setenv("BEDROCK_MODEL_ID", "model-x")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    monkeypatch.setattr(deps_module, "build_presidio_guardrail", lambda: PerRequest())


def test_build_deps_reads_env_for_every_seam(env):
    deps = deps_module.build_deps()
    assert deps.embedder._client.base_url == "http://ollama.test:11434"
    assert deps.embedder.dim == 768
    assert str(deps.store._client.base_url).rstrip("/") == "http://search.test:9200"
    assert deps.llm._model_id == "model-x"


def test_build_deps_is_cached(env):
    assert deps_module.build_deps() is deps_module.build_deps()


def test_each_request_gets_its_own_guardrail(env):
    first, second = deps_module.request_deps(), deps_module.request_deps()
    assert first.guardrail is not second.guardrail
    assert replace(first, guardrail=None) == replace(second, guardrail=None)
