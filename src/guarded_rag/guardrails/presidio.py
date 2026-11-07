"""Presidio guardrail (ADR 0009): redacts PII with per-request numbered placeholders."""

import re
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout

from guarded_rag.guardrails.registry import Registry, load_registry
from guarded_rag.seams import Finding, Redaction

SCORE_THRESHOLD = 0.5
TIMEOUT_SECONDS = 10.0
SPACY_MODEL = "en_core_web_md"


class GuardrailError(Exception):
    """Redaction failed. The query must error, never return unredacted text (fail closed)."""


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().lower()


def _non_overlapping(results: list) -> list:
    """Keep the higher score (then the longer span) wherever spans overlap."""
    ranked = sorted(results, key=lambda r: (-r.score, -(r.end - r.start), r.start))
    kept: list = []
    for r in ranked:
        if all(r.end <= k.start or r.start >= k.end for k in kept):
            kept.append(r)
    return sorted(kept, key=lambda r: r.start)


class PresidioGuardrail:
    """Holds the value -> placeholder map, so use one instance per request (see for_request)."""

    def __init__(self, analyzer, registry: Registry, timeout: float = TIMEOUT_SECONDS):
        self._analyzer = analyzer
        self._registry = registry
        self._timeout = timeout
        self._placeholders: dict[tuple[str, str], str] = {}

    def for_request(self) -> "PresidioGuardrail":
        return PresidioGuardrail(self._analyzer, self._registry, self._timeout)

    def redact(self, text: str) -> Redaction:
        spans = _non_overlapping(self._analyze(text))
        out, findings, pos = [], [], 0
        for r in spans:
            placeholder = self._placeholder(r.entity_type, text[r.start : r.end])
            out += [text[pos : r.start], placeholder]
            findings.append(Finding(r.entity_type, placeholder, r.start, r.end))
            pos = r.end
        out.append(text[pos:])
        return Redaction("".join(out), findings)

    def _analyze(self, text: str) -> list:
        entities = self._registry.entities
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(
                self._analyzer.analyze,
                text=text,
                language="en",
                entities=entities,
                score_threshold=SCORE_THRESHOLD,
            )
            try:
                results = future.result(timeout=self._timeout)
            except FutureTimeout as e:
                pool.shutdown(wait=False, cancel_futures=True)
                raise GuardrailError("redaction timed out") from e
            except Exception as e:
                raise GuardrailError("redaction failed") from e
        return [r for r in results if r.entity_type in entities]

    def _placeholder(self, entity_type: str, value: str) -> str:
        key = (entity_type, _normalize(value))
        if key not in self._placeholders:
            n = sum(1 for kind, _ in self._placeholders if kind == entity_type) + 1
            self._placeholders[key] = f"<{self._registry.label(entity_type)}_{n}>"
        return self._placeholders[key]


def build_presidio_guardrail(registry: Registry | None = None) -> PresidioGuardrail:
    """Loads spaCy and the YAML recognizers. Slow: build once and call for_request() per request."""
    from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer
    from presidio_analyzer.nlp_engine import NlpEngineProvider

    registry = registry or load_registry()
    nlp = NlpEngineProvider(
        nlp_configuration={
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "en", "model_name": SPACY_MODEL}],
        }
    ).create_engine()
    analyzer = AnalyzerEngine(nlp_engine=nlp, supported_languages=["en"])
    for e in registry.yaml_entities:
        patterns = [Pattern(p.name, p.regex, p.score) for p in e.patterns]
        analyzer.registry.add_recognizer(
            PatternRecognizer(supported_entity=e.entity_type, patterns=patterns)
        )
    return PresidioGuardrail(analyzer, registry)
