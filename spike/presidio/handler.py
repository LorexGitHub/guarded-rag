import json, os, resource, time

_t0 = time.time()
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine

_nlp = NlpEngineProvider(nlp_configuration={
    "nlp_engine_name": "spacy",
    "models": [{"lang_code": "en", "model_name": "en_core_web_md"}],
}).create_engine()
_analyzer = AnalyzerEngine(nlp_engine=_nlp, supported_languages=["en"])
_anonymizer = AnonymizerEngine()
INIT_S = time.time() - _t0


def redact(text):
    results = _analyzer.analyze(text=text, language="en")
    return _anonymizer.anonymize(text=text, analyzer_results=results).text


def _rss_mb():
    with open("/proc/self/status") as f:
        for line in f:
            if line.startswith("VmRSS"):
                return int(line.split()[1]) / 1024


def handler(event, context):
    body = event.get("body") or "{}"
    text = json.loads(body).get("text", "")
    t = time.time()
    out = redact(text)
    ms = (time.time() - t) * 1000
    return {
        "statusCode": 200,
        "headers": {"content-type": "application/json"},
        "body": json.dumps({"redacted": out, "redact_ms": round(ms, 1),
                            "init_s": round(INIT_S, 2), "rss_mb": round(_rss_mb(), 1)}),
    }
