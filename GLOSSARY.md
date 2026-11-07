# Glossary

**Seam**: a place where one implementation can be swapped for another without editing the code around it. In this repo a seam is a `typing.Protocol` (`Guardrail`, `Embedder`, `VectorStore`, `LLM`) with one real backend and one test fake. See ADR 0005.

**Finding**: one detected PII span, with its entity type and typed placeholder. It never holds the raw value.

**Hit**: one retrieved chunk with its score and whether it passed the score threshold.

**Refusal**: the fixed answer returned, without calling the `LLM`, when no hit passes the threshold (ADR 0004).
