# 0009. Guardrail engine, placement and placeholders

Status: proposed. Issue: LorexGitHub/guarded-rag#7 (decided there; recorded here by #19). Covers handoff decisions #10 and #16.

Three later ADRs change parts of this decision. They are marked **Superseded** below.

## Decision

1. **Engine:** Presidio with spaCy `en_core_web_md` plus custom regex recognizers. No GLiNER: it needs torch, which is too heavy for the Lambda image (ADR 0003).
2. **Entities:** `PERSON`, `PHONE_NUMBER`, `EMAIL_ADDRESS`, `EMPLOYEE_ID`, detected at score 0.5. Other Presidio entities are ignored.
3. **Registry.** Entities live in a registry. Regex and deny-list recognizers load from `guardrails/recognizers.yaml` (entity type, patterns, score, placeholder label). Complex ones are Python recognizer classes registered in code. `EMPLOYEE_ID` is the first YAML entry. A new entity needs only a registry entry and a seeded ground-truth value (ADR 0007).
4. **Placement:** redact the question and the answer.
5. **Retrieval:** embed the original question; send the redacted question to the LLM and the trace.
6. **Placeholders.** Per request, numbered per type in order of first appearance (`<PERSON_1>`, `<PHONE_NUMBER_1>`). One `value -> placeholder` map, case-insensitive and whitespace-normalized, is shared across the question and the answer. No de-anonymization. Partial names (Jane vs. Jane Doe) are out of scope and kept as a `known-weak` eval case.
7. **Finding:** an entity type, a placeholder and a span. It never holds the raw text.
8. **Failure:** fail closed. If Presidio errors or times out, the query returns an error, never an unredacted answer. This is unit-tested.
9. **No refusal logic in the guardrail.** The guardrail only redacts. Refusal comes from retrieval (ADR 0004).

## Superseded

- **Retrieved chunks go raw to the LLM, and the trace shows them with spans highlighted.** ADR 0005 keeps the first half. Chunk text in the trace is redacted, so the API never returns raw PII.
- **Finding fields** `{entity_type, placeholder, start, end, score, source}`. ADR 0006 keeps only `entity_type` and `placeholder` in the API, and the question/answer split is `findings_in` / `findings_out`. Spans stay in Python only.
- **Leak = a seeded value in the final `answer`.** ADR 0007 widens the scan to the whole serialized response.

## Alternatives rejected

- **GLiNER.** Better on names, but torch makes the image too big.
- **Redacting at ingest.** Cheaper at query time, but it hides the guardrail from the demo and loses the original text. Listed under the README's next steps.
- **Redacting retrieved chunks before the LLM.** More private, but slower and it degrades answers. Moved to next steps.

## Triggers to revisit

- Names miss too often in the eval: try a larger spaCy model or custom deny-lists before changing the engine.
- Per-request redaction is too slow on CPU: measure the redact call alone first.
- Chunk redaction before the LLM becomes a requirement: this decision and ADR 0005 both change.
