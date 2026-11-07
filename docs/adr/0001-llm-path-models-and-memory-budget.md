# 0001. LLM path, models and memory budget

Status: proposed. Issue: LorexGitHub/guarded-rag#8. Covers handoff decisions #9 and #21. Numbers come from `docs/spike.md` (16 GB host, CPU-only Ollama).

## Decision

1. **Generation goes through Bedrock `converse` on Floci**, which proxies to Ollama `llama3.2:3b`. The query Lambda never talks to Ollama for generation.
2. **Embeddings call Ollama directly over HTTP** (`nomic-embed-text`). Floci stubs embeddings, so there is no AWS path to use.
3. **Models stay `llama3.2:3b` and `nomic-embed-text`.** `qwen2.5:1.5b` is the fallback if memory runs out. It was not run in the spike, so its quality and speed are unmeasured.
4. **OpenSearch heap is 512 MB**, set by the derived image `guarded-rag-opensearch:512m` (Floci can't set it).

## Why converse over direct Ollama

- The project's claim is "AWS-shaped code against local backends". Calling `converse` means the Lambda code is the same code that would run on real Bedrock, and only the endpoint changes. Calling Ollama directly would put an Ollama-specific client in the query path.
- The proxy's cost is small: Floci used 43 to 52 MiB during a generation, and latency is dominated by the model (4.1 s cold, 12.6 s for 166 tokens warm).
- Cost of the choice: `converse` is the only proxied call, and `InvokeModel` stays a stub. It needs `PROXY_URL` ending in `/v1` and `DEFAULT_MODEL` set (see spike findings).

## Why llama3.2:3b

It is the only model verified end to end through the proxy (`pong` test, 166-token answer). Peak resident size is 2.42 GiB. Switching to `qwen2.5:1.5b` would save roughly 1.3 GiB (estimate from model size, not measured) but a 1.5B model is a worse bet for the eval's refusal and redaction-correctness number.

## Memory budget (16 GB host)

| Component | Peak | Source |
|---|---|---|
| Floci | 0.05 GiB | measured |
| OpenSearch, 512 MB heap | 0.95 GiB | measured |
| Ollama, `llama3.2:3b` resident | 2.42 GiB | measured |
| Ollama, `nomic-embed-text` resident | about 0.3 GiB | estimate, not run alongside generation |
| Lambda containers (Presidio + spaCy) | about 0.5 to 1 GiB each | **unmeasured guess** |
| **Total** | **about 4 to 5 GiB** | |

That leaves ample headroom, but the spike host already used about 13 GB with a desktop and a kind cluster running. The budget is fine on a clean machine and tight on a busy one.

## Triggers to revisit

- Lambda containers measure above about 1.5 GiB each: shrink with the zip + `en_core_web_sm` layer fallback (decision #17) before touching models.
- Total stack exceeds about 8 GiB, or CI runners (GitHub-hosted, 16 GB, no swap tuning) OOM: switch to `qwen2.5:1.5b` and re-run the eval.
- Set `OLLAMA_KEEP_ALIVE` explicitly in Compose. Default 5 minutes frees the model and makes the first request after idle slow, which matters for the demo.

## Still open

- Measure `qwen2.5:1.5b` through the proxy (memory, latency, eval score) once the eval exists.
- Measure the Lambda containers.
