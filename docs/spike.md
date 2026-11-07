# Spike: Compose stack, Bedrock converse proxy, and memory

Issue: LorexGitHub/guarded-rag#4. Run on 2026-11-07, 16 GB host (Intel Iris Xe, CPU-only Ollama), Docker 29.9.2, Compose 5.6.1.

## Result

| Question | Answer |
|---|---|
| Floci + Ollama up under Compose on one network, both models pulled | Yes |
| `bedrock-runtime.converse` through Floci returns real Ollama output | Yes (`llama3.2:3b`) |
| OpenSearch domain with a 512 MB heap | Yes, but Floci has no heap setting. Use a derived image (below). |
| Bonus: `knn_vector` mapping and k-NN query on the Floci domain | Works (OpenSearch 2.19) |

## Files

- `docker-compose.yml`: `ollama` and `floci` on the network `guarded-rag`.
- `spike/opensearch/Dockerfile`: OpenSearch 2.19 with `OPENSEARCH_JAVA_OPTS=-Xms512m -Xmx512m`.
- `spike/run.sh`, `os.sh`, `os2.sh`, `os3.sh`: the exact scripts that produced the numbers.

## Commands

```bash
docker compose up -d
docker compose exec -T ollama ollama pull llama3.2:3b
docker compose exec -T ollama ollama pull nomic-embed-text

# Converse through Floci (any model id works, because DEFAULT_MODEL maps it)
curl -s localhost:4566/model/anthropic.claude-3-haiku-20240307-v1:0/converse \
  -H 'content-type: application/json' \
  -d '{"messages":[{"role":"user","content":[{"text":"Reply with exactly: pong"}]}],"inferenceConfig":{"maxTokens":20}}'

# OpenSearch domain (Floci starts a real container, exposed on host port 9400)
docker build -t guarded-rag-opensearch:512m spike/opensearch
curl -s -X POST localhost:4566/2021-01-01/opensearch/domain -H 'content-type: application/json' \
  -d '{"DomainName":"rag","EngineVersion":"OpenSearch_2.19"}'
```

Response from converse: `{"output":{"message":{"role":"assistant","content":[{"text":"pong"}]}},"stopReason":"end_turn","usage":{"inputTokens":30,"outputTokens":2,...},"metrics":{"latencyMs":4118}}`. The 4.1 s includes loading the model into memory. A 166-token answer took 12.6 s warm.

## Floci config that matters

```yaml
FLOCI_SERVICES_BEDROCK_RUNTIME_BACKEND: proxy
FLOCI_SERVICES_BEDROCK_RUNTIME_PROXY_URL: http://ollama:11434/v1   # the /v1 is required
FLOCI_SERVICES_BEDROCK_RUNTIME_PROXY_DEFAULT_MODEL: llama3.2:3b    # else 400 ValidationException
FLOCI_SERVICES_DOCKER_NETWORK: guarded-rag                          # spawned OpenSearch/Lambda containers join this network
FLOCI_SERVICES_OPENSEARCH_DEFAULT_IMAGE: guarded-rag-opensearch:512m
```

## Memory

Measured with `docker stats --no-stream` (container RSS) and `free -m`. The host was not otherwise idle: a `kindest/node` container (~1.4 GiB) and a desktop session ran alongside, and swap was already in use (6 to 8 GB). Treat the host-level `free` numbers as noisy. The per-container numbers are reliable.

| Container | Idle | During/after one generation |
|---|---|---|
| floci | 30 to 78 MiB | 43 to 52 MiB |
| ollama (models loaded) | 11 to 300 MiB | **2.42 GiB** (`llama3.2:3b` resident) |
| OpenSearch, default heap (1 GB) | 1.41 GiB | not measured |
| OpenSearch, **512 MB heap** | **953 MiB** | 953 MiB |
| **Stack total with 512 MB heap** | **about 1.0 GiB** | **about 3.4 GiB** |

- Ollama frees the model after its idle timeout (5 minutes by default), so idle memory is small. The first request after that pays the load time.
- `nomic-embed-text` (274 MB on disk) would add a few hundred MiB while loaded. It was not run during the generation measurement. Ollama keeps both models resident if they fit.
- Lambda containers (Presidio + spaCy images) are not included here. They are the next big unknown.

## Findings and gotchas

1. **Floci cannot set the OpenSearch heap.** It starts the container with only `discovery.type`, `DISABLE_SECURITY_PLUGIN` and an admin password, so the JVM gets the image default (1 GB heap). The workaround is a derived image that sets `OPENSEARCH_JAVA_OPTS`, selected with `FLOCI_SERVICES_OPENSEARCH_DEFAULT_IMAGE`. Verified: `heap_max_in_bytes` was 1073741824 before and 536870912 after. Decision #21 holds.
2. The converse proxy needs `PROXY_URL` to end in `/v1`, and it needs either `DEFAULT_MODEL` or a model mapping.
3. Domain creation returns immediately with `Processing: true`. Poll `DescribeDomain` (or the host port) before use. The domain endpoint it reports is the container IP (`172.x.x.x:9200`), reachable from other containers on the `guarded-rag` network.
4. `docker compose exec` reads stdin. Inside a heredoc or script it swallows the remaining lines, so use `-T` and `</dev/null`.
5. The aws CLI isn't installed, so calls used raw `curl` against Floci's REST routes.

## Not covered (still open from the handoff checklist)

S3 to Lambda trigger, container-image Lambda, and Lambda-to-Ollama/OpenSearch reachability. This issue only covered the Compose stack, converse proxy and memory.
