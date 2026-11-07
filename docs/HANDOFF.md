# guarded-rag: handoff for the next session

Decided on 2026-11-07 in a grilling session. Every decision below is settled, so don't reopen it. If a spike result forces a change, use the fallback written next to that decision.

## Goal

This is a portfolio-grade **RAG system with PII guardrails**. Terraform defines it, and it runs fully locally on **Floci**, an AWS emulator. We treat Floci as if it were real AWS: the project never deploys to a real AWS account.

The demo should prove this resume line: *"PII leaks: 0 across N adversarial queries, with a CI-gated eval."*

## Facts about the environment (checked on 2026-11-07)

- GitHub CLI is logged in as **LorexGitHub** over SSH. `LorexGitHub/guarded-rag` does **not** exist yet.
- **Installed:** docker, python3, `uv`, `mise`.
- **Not installed:** terraform and the aws CLI. Install terraform with `mise use -g terraform@latest`.
- **Hardware:** 16 GB RAM, 8 cores, Intel Iris Xe. There's no usable GPU, so Ollama runs on the CPU and memory is tight.
- **Hallmark design skill:** not installed. Install it with `npx skills add nutlope/hallmark` (https://github.com/Nutlope/hallmark).

## Floci (https://github.com/floci-io/floci, MIT)

- **Image:** `floci/floci:latest`. It serves port **4566** and needs `/var/run/docker.sock` mounted, because Lambda and OpenSearch run as real containers.
- **What really works:** S3, S3 → Lambda notifications, Lambda, API Gateway v1 and v2, DynamoDB, and OpenSearch (a real `opensearchproject/opensearch:2` container).
- **Bedrock Runtime** returns a stub unless you set `FLOCI_SERVICES_BEDROCK_RUNTIME_BACKEND=proxy`. That mode forwards `Converse` and `ConverseStream` to an OpenAI-compatible server (Ollama). `InvokeModel` and embeddings are still stubs.
- **Bedrock Guardrails:** you can create them, but Floci **never applies them**, so we use Presidio instead.
- **Comprehend PII:** returns canned output that finds no PII, so don't use it.
- **IAM:** policies are probably not enforced. Write least-privilege policies anyway, because they are part of the portfolio.
- **Terraform:** use `hashicorp/aws` 6.x with region `us-east-1` and `test`/`test` keys. Set `skip_credentials_validation`, `skip_metadata_api_check`, `skip_requesting_account_id` and `s3_use_path_style = true`. Point every service in the `endpoints {}` block at `http://localhost:4566`: s3, lambda, apigateway, apigatewayv2, iam, opensearch, dynamodb, sts, logs and bedrock.
- Docs: https://floci.io/floci/services, plus `docs/getting-started/terraform.md` in the repo.

## Decisions

| # | Topic | Decision |
|---|---|---|
| 1 | Purpose | Resume/portfolio piece. The README, a diagram, evals, CI and the demo matter as much as the code. |
| 2 | Repo | `LorexGitHub/guarded-rag`, **private** for now, MIT. The user makes it public later. |
| 3 | Language | Python 3.12, `uv`, pytest, ruff. |
| 4 | Target | Floci only, treated as real AWS. No real-AWS profile. |
| 5 | IaC | Terraform, installed with mise. |
| 6 | Corpus | Synthetic company docs (HR policies, an employee directory, support tickets) with **seeded fake PII**: names, phone numbers, emails. |
| 7 | UI | Web UI designed with the **Hallmark** skill. |
| 8 | CI | GitHub Actions running ruff, pytest, `terraform fmt -check` and `validate`, plus the e2e and eval runs against Floci in Docker. |
| 9 | LLM | Query Lambda calls `bedrock-runtime.converse`. Floci proxies it to Ollama `llama3.2:3b`. |
| 10 | Guardrail | A `Guardrail` interface: `redact(text) -> (redacted_text, findings)`. Its only backend is **Presidio** inside the Lambda. |
| 11 | Embeddings | An `Embedder` interface backed by Ollama `nomic-embed-text`, called **directly over HTTP**. Floci doesn't proxy embeddings, and this is the only call that doesn't go through an AWS API. |
| 12 | Vector store | **OpenSearch k-NN** on Floci, behind a `VectorStore` interface. |
| 13 | UI stack | Vite + React + TypeScript, built to static files and served from an S3 website bucket on Floci, calling API Gateway. `vite dev` for development. |
| 14 | UI content | (a) An ask box showing the answer and cited sources. (b) A **guardrail trace panel** showing the retrieved chunks, the PII found in the question and the answer, and the redactions. (c) Document upload to S3, which triggers ingest live. |
| 15 | Backends | Build only the local backends. Write no unused Bedrock Guardrails or Titan code. Keep the interfaces as seams. The README maps each piece to the AWS service it stands in for. |
| 16 | Guardrail placement | Redact PII in **both the question and the answer**, using typed placeholders (`<PERSON_1>`, `<PHONE_1>`, `<EMAIL_1>`). Raw docs stay unredacted in S3 and OpenSearch. Ingest-time redaction goes in "Next steps". |
| 17 | Lambda packaging | **Container images**, because Presidio and spaCy are too big for a zip. Fallback: a zip plus a layer with `en_core_web_sm`. |
| 18 | Start | A spike that proves the risky Floci assumptions first (see below). |
| 19 | Build order | Spike → thin end-to-end slice → eval and CI → UI (Hallmark) → README and diagram. |
| 20 | Dev loop | `make up`: Docker Compose (Floci + Ollama, with the models pulled) followed by `terraform apply`. Also `make test`, `make eval` and `make down`. |
| 21 | Models | `llama3.2:3b` and `nomic-embed-text`. Cap the OpenSearch JVM heap at 512 MB (`-Xms512m -Xmx512m`) so everything fits in 16 GB. |
| 22 | Eval | About 20 question/expected-source pairs, including adversarial PII questions ("what's Jane's phone number?"). It reports three numbers: retrieval hit rate in the top k, **PII leak count (CI fails if it's above 0)**, and refusal/redaction correctness. |

## Architecture

```
Upload (UI or CLI) ─▶ S3 docs bucket ──event──▶ ingest Lambda (image)
                                                  ├─ chunk
                                                  ├─ embed ──HTTP──▶ Ollama nomic-embed-text
                                                  └─ index ───────▶ OpenSearch k-NN

UI (S3 website) ─▶ API Gateway ─▶ query Lambda (image)
                                   ├─ Presidio: redact question
                                   ├─ embed question ─▶ Ollama
                                   ├─ k-NN top-k ─────▶ OpenSearch
                                   ├─ bedrock-runtime.converse ─▶ Floci proxy ─▶ Ollama llama3.2:3b
                                   ├─ Presidio: redact answer
                                   └─ return { answer, sources, trace: { chunks, findings_in, findings_out } }
```

Networking: Floci runs the Lambda containers, and they must be able to reach Ollama and OpenSearch. Put everything on one Compose network. Pass the Ollama URL to the Lambdas as an env var, such as `OLLAMA_URL=http://ollama:11434`, and check during the spike that the Lambda containers can resolve that name.

## Suggested repo layout

```
guarded-rag/
  Makefile
  docker-compose.yml        # floci, ollama (+ model pull init)
  infra/                    # terraform: provider.tf (floci endpoints), s3, lambda, apigw, opensearch, iam, ui bucket
  src/guarded_rag/
    guardrail.py            # Guardrail protocol + PresidioGuardrail
    embedder.py             # Embedder protocol + OllamaEmbedder
    vector_store.py         # VectorStore protocol + OpenSearchStore
    chunking.py
    llm.py                  # Converse call
    handlers/ingest.py
    handlers/query.py
  lambdas/Dockerfile        # one image, handler picked via CMD
  corpus/                   # synthetic docs with seeded PII
  evals/cases.yaml + run.py
  tests/                    # unit (pure) + e2e (against floci)
  ui/                       # vite + react + ts
  .github/workflows/ci.yml
  README.md                 # diagram, AWS-service mapping, eval numbers, next steps
```

## Next session: step by step

1. **Setup.** Run `mise use -g terraform@latest` and `npx skills add nutlope/hallmark`. Then create the repo with `gh repo create LorexGitHub/guarded-rag --private --license mit --clone` and copy this file in as `docs/HANDOFF.md`.
2. **Spike** (about 30 to 60 minutes; record the results in `docs/spike.md`). Prove each of these:
   - [ ] Floci and Ollama come up under Compose with both models pulled.
   - [ ] OpenSearch on Floci accepts a `knn_vector` mapping and returns k-NN results. **Fallback:** DynamoDB with brute-force cosine search behind `VectorStore`.
   - [ ] An S3 put triggers a Lambda.
   - [ ] Floci can run a **container-image** Lambda. **Fallback:** a zip plus a layer with a small spaCy model.
   - [ ] `bedrock-runtime.converse` through the Floci proxy returns real Ollama output.
   - [ ] The Lambda container can reach `ollama` and OpenSearch over the network.
3. **Thin slice.** Upload one doc, ingest it, `curl` the API, and get a redacted answer with a trace. Write pure unit tests for chunking, redaction and prompt building.
4. **Corpus, evals and CI.** Build the full synthetic corpus, write `make eval`, and add a CI gate that fails on any PII leak.
5. **UI.** Build it with Hallmark: the ask box with sources, the trace panel, and upload. Host it from the S3 website bucket.
6. **README.** Add the architecture diagram, a table mapping each piece to its AWS service, the eval numbers, a demo GIF, and next steps: ingest-time redaction, real-AWS deploy, and Bedrock Guardrails / Titan backends.

## Risks to keep in mind

- **Memory.** If the stack runs out of RAM, drop to `qwen2.5:1.5b` or run OpenSearch with a smaller heap.
- **Floci fidelity.** Anything not covered by the spike may behave differently from real AWS. Note any differences in the README so you're open about them.
- **Presidio names.** Presidio's name detection depends on spaCy NER. Names will be its weakest entity type, so seed tricky name cases in the eval set.
