# Glossary

**Seam**: a place where one implementation can be swapped for another without editing the code around it. In this repo a seam is a `typing.Protocol` (`Guardrail`, `Embedder`, `VectorStore`, `LLM`) with one real backend and one test fake. See ADR 0005.

**Finding**: one detected PII span, with its entity type and typed placeholder. It never holds the raw value.

**Hit**: one retrieved chunk with its score and whether it passed the score threshold.

**Refusal**: the fixed answer returned, without calling the `LLM`, when no hit passes the threshold (ADR 0004).

**Trace**: the part of a query response that shows the guardrail at work: all top-k hits (redacted text, score, `passed`) and the findings in the question and in the answer. Findings carry no spans. See ADR 0006.

**Ingest status**: `pending`, `ready` or `failed` for one uploaded document, read from the marker the ingest handler writes after `replace_document`. See ADR 0006.

**Seeded value**: a fake PII value (name, phone, email, `EMPLOYEE_ID`) the corpus generator planted in a document. Each one is recorded in `corpus/ground_truth.yaml`. See ADR 0006.

**Ground truth manifest**: `corpus/ground_truth.yaml`, the list of every seeded value with its entity type, document and normalized form. The eval's leak check reads it.

**Case**: one entry in `evals/cases.yaml`: a question, its category (benign, adversarial, out-of-corpus), expected sources, expected placeholder types and whether a refusal is expected.

**Leak**: a seeded value, or a generic email/phone match, found in the answer or anywhere else in the serialized response (`sources`, trace hits, chunk text) after normalization. Any leak fails CI. Refines the answer-only definition in #7 to match ADR 0005.

**Known-weak**: a case tag for inputs the guardrail is expected to miss (for example a partial name). It changes reporting only; the leak gate still applies.
