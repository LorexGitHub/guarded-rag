# 0008. E2E tests and CI

Status: proposed. Issue: LorexGitHub/guarded-rag#17. Builds on ADR 0001 (memory budget), ADR 0003 (image cache), ADR 0006 (API contract) and ADR 0007 (eval runner).

## Decision

1. **The e2e test drives only the API Gateway URL on Floci**, the way the browser does:
   1. Request a presigned URL and PUT a corpus file to S3.
   2. Poll `GET /documents/{doc_id}` about once a second until `ready` (ADR 0006), with a timeout of about 60 s. No fixed sleeps.
   3. `POST` a benign question: sources come back and the answer has no seeded PII.
   4. `POST` an adversarial question: the answer is redacted or refused, and a trace is present.
   5. Send a cross-origin preflight to check Floci's CORS (unverified in ADR 0006).

   It also runs `evals/run.py --api-url` on about 5 cases as the smoke subset. It does not repeat the full in-process eval.
2. **Runner: start on free `ubuntu-latest` and measure.** The repo is private, so the free runner is 2 vCPU and 7 GB, not the 4 vCPU / 16 GB that ADR 0001 and the issue assumed. The first implementation ticket is a throwaway workflow that brings up Floci, OpenSearch and Ollama and records peak memory and per-case latency. If it fails, move to a paid larger runner or make the repo public. The choice is not made on paper.
3. **Caching:**
   - Ollama model blobs (about 2.3 GB) with `actions/cache`, keyed on a hash of the pulled model names.
   - Lambda image layers with `docker/build-push-action` and `type=gha` (ADR 0003).
   - The Terraform provider directory.

   The GitHub cache limit is 10 GB per repo with LRU eviction. A miss on the models costs about 2 to 3 minutes.
4. **Cadence:**
   - Every push and PR: lint, unit tests, consistency tests (ADR 0007), and the e2e smoke subset.
   - Full 30-case eval with the leak gate: PRs that touch guardrail, retrieval, prompt, corpus or eval paths, pushes to `master`, and nightly.
5. **If the stack does not fit, shrink the model before shrinking the gate.**
   1. Switch CI to `qwen2.5:1.5b` (ADR 0001's fallback) and re-run the eval.
   2. The leak gate stays hard, but it measures the CI model. The README says which model produced the published number.
   3. If CI uses a different model from the demo, the nightly job still runs `llama3.2:3b` where it fits, or the gap is stated in the README.

## Alternatives rejected

- Deciding the runner from the spike numbers alone: the spike host was a 16 GB machine with CPU inference, not a 2 vCPU runner.
- Full eval on every push: 30 CPU generations per push is too slow and wastes the cache.
- Mocking the LLM in CI: the leak gate would then say nothing about a real model.

## Triggers to revisit

- The measurement workflow shows peak memory above about 6 GiB or a full eval above about 10 minutes: apply decision 5, or change the runner.
- The model cache is evicted often: pull the models from a mirror, or drop the nightly job's cache key to the model name only.
- Floci's CORS preflight fails: record it in `docs/spike.md` and revisit ADR 0006 decision 8.

## Still open

- Real peak memory and per-case latency on a 2 vCPU runner.
- Whether `qwen2.5:1.5b` holds the redaction-correctness rate (ADR 0001 and 0007 still list it as unmeasured).
