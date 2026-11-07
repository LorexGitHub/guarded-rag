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

## Lambda: container image, S3 trigger, network reach

Issue: LorexGitHub/guarded-rag#5. Run on 2026-11-07, Floci latest, Terraform 1.17.1, `hashicorp/aws` 6.x.

### Result

| Question | Answer |
|---|---|
| Terraform deploys a **container-image** Lambda (`package_type = "Image"`) on Floci | Yes. Creation took 5 s. |
| An S3 put triggers it (`aws_s3_bucket_notification` + `aws_lambda_permission`) | Yes. The Lambda ran about 1 s after the PUT, with a real S3 event record. |
| Lambda container resolves `ollama` by name | Yes (`172.21.0.2`) |
| Lambda container calls Ollama (`GET http://ollama:11434/api/tags`) | Yes, 200, lists both models |
| Lambda container calls OpenSearch (`GET <domain endpoint>`) | Yes, 200, OpenSearch 2.19.0 |
| Zip + layer fallback needed | **No.** It was not tried, so there is nothing to record. |

### Files

- `spike/lambda/{Dockerfile,handler.py}`: base `public.ecr.aws/lambda/python:3.12`. The handler resolves the Ollama host, then calls Ollama and OpenSearch and prints a `PROBE {...}` line.
- `spike/infra/main.tf`: S3 bucket, IAM role, image Lambda, permission, bucket notification. Provider endpoints point at Floci.

### Commands

```bash
docker build -t guarded-rag-spike-probe:latest spike/lambda
# domain "rag" must exist (see above); take its Endpoint from DescribeDomain
terraform -chdir=spike/infra init
terraform -chdir=spike/infra apply -auto-approve -var opensearch_url=http://172.21.0.4:9200
curl -X PUT localhost:4566/spike-docs/hello.txt -d hello       # unsigned PUT is accepted
docker logs guarded-rag-floci-1 2>&1 | grep PROBE              # Lambda output appears in Floci's log
```

### Gotchas

1. **`image_uri` can be a local image.** Floci logs `Image already present locally, skipping pull` and uses the host Docker daemon through the mounted socket. There was no ECR push. Floci also has an `ecr` service, but this spike did not test it. For the real build, `docker build -t <name>` before `terraform apply` is enough.
2. **Lambda containers join the `guarded-rag` network** because of `FLOCI_SERVICES_DOCKER_NETWORK`, which is why `ollama` resolves by name. Without it they would not.
3. **The OpenSearch endpoint is a container IP** (`172.21.0.4:9200`) and can change when the domain is recreated. Pass it to the Lambda from the Terraform domain output, or look it up at run time. Do not hard-code it. The spike hard-coded it through a variable. The Terraform OpenSearch resource was not used here (the domain came from the earlier curl).
4. **The Lambda container starts on first invocation** and stays up (`floci-aws-spike-probe-<id>`). The first S3-triggered run was cold, with no measured cold-start time.
5. **Lambda stdout goes to Floci's container log**, as well as CloudWatch Logs. This is handy for debugging.
6. The probe image is the bare Lambda base image plus one file (518 MB on disk; the probe container used 14 MiB of its 128 MiB). The Presidio + spaCy image size and memory are still unmeasured. That is the next risk to test.

## Not covered

`aws_opensearch_domain` in Terraform. (API Gateway and the Presidio/spaCy image are covered in the next section.)

---

# Spike: OpenSearch k-NN on Floci (Terraform)

Issue: LorexGitHub/guarded-rag#6. Run on 2026-11-07 on the same host and stack as above (Floci + Ollama under Compose, 512 MB heap image).

## Result

| Question | Answer |
|---|---|
| Create an OpenSearch domain on Floci with Terraform | **Yes**, with `hashicorp/aws ~> 5.0` (5.100.0). But `apply` took **10 min** (see gotcha 1). |
| Index with a 768-dim `knn_vector` mapping | Yes (`hnsw`, `lucene` engine, `cosinesimil`) |
| Index vectors and run a top-k query | Yes. 5 random 768-dim vectors, k=3. A query near doc 2 returned doc 2 first (score 0.999), then 1 and 4. |
| Latency | Server `took`: 2 ms. Client round trip (host to container, Python urllib): median 7.6 ms, min 6.3 ms, max 30.7 ms over 20 queries. Tiny index, so this says nothing about scale. |
| Memory | OpenSearch container 990 MiB with the 512 MB heap (`heap_max_in_bytes` = 536870912) after indexing. Floci 66 MiB. Ollama 14 MiB idle (no model loaded). |

## Files

- `spike/terraform/main.tf`: AWS provider with the `opensearch` endpoint set to `http://localhost:4566`, plus one `aws_opensearch_domain`.
- `spike/knn.sh`: creates the index, indexes 5 vectors, runs 20 top-3 queries and prints latency.

```bash
cd spike/terraform && terraform init && terraform apply -auto-approve   # ~1.5 min with the create timeout
cd .. && ./knn.sh
```

Terraform cannot create the index. The AWS provider has no resource for it, so the index step is plain HTTP against the domain (host port 9400). An `opensearch-project/opensearch` Terraform provider could do it declaratively. It was not tried.

## Gotchas

1. **`terraform apply` took about 10 minutes even though the domain is ready within about a minute.** Cause (#14): the provider's `waitForDomainCreation` has a hard-coded `WithDelay(10*time.Minute)` before the first poll, in every provider version checked (v5.0.0 to `main`). It is not caused by Floci's `Endpoint`. Workaround: `timeouts { create = "3m" }` on the domain with the provider on v5.x; the timeout ends the wait and v5.x then does a final `DescribeDomain` check. Tested with a 90s timeout: apply took 1m31s. See ADR 0004. A first run killed at 500 s left an empty `terraform.tfstate` and a live domain behind.
2. The domain `Endpoint` is a container IP, reachable only from the `guarded-rag` network or via the published host port 9400 (not via Terraform's `endpoint` output from the host).
3. `terraform` was installed through mise. The Docker socket needs the `docker` group, which a long-running shell may lack. `newgrp docker` worked.
4. Deleting the domain through the Floci API and recreating it works; Terraform state must be removed by hand if the apply was killed.

## Verdict

OpenSearch k-NN with 768-dim vectors works on Floci at about 1 GiB for the container. The only failure is slow Terraform creation (10 min), not the k-NN itself.


---

# Spike: API Gateway to an image Lambda, and the Presidio/spaCy image

Issue: LorexGitHub/guarded-rag#13. Run on 2026-11-07, same host and Compose stack, Floci latest, Terraform `hashicorp/aws` 6.x.

## Result

| Question | Answer |
|---|---|
| API Gateway **v2 HTTP API** to a container-image Lambda on Floci via Terraform | **Yes.** Apply took about 6 s. v1 was not needed. |
| `curl` from the host | Yes: `POST http://localhost:4566/_aws/execute-api/<api_id>/$default/redact` |
| CORS preflight (`OPTIONS`) from a browser origin | Yes. `cors_configuration` is honoured: `Access-Control-Allow-Origin/Methods/Headers` returned for the allowed origin. |
| CORS on the real `POST` response | Yes, `Access-Control-Allow-Origin` is present |
| Disallowed origin | `204` with no `Access-Control-*` headers, so a browser blocks it |
| Presidio + spaCy `en_core_web_md` image works | Yes. Detects PERSON, PHONE_NUMBER, EMAIL_ADDRESS. |

## Numbers

Image `guarded-rag-presidio:latest` (base `public.ecr.aws/lambda/python:3.12`, `presidio-analyzer`, `presidio-anonymizer`, `en_core_web_md`):

| Metric | Value |
|---|---|
| Image size on disk | **985 MB** (the bare base image is 518 MB, so Presidio + spaCy add about 470 MB) |
| Build time, cold cache | 53 s |
| Module init (import + load spaCy model) | 1.7 to 2.1 s |
| First request through API Gateway (container start + init + first `redact`) | **2.4 to 3.4 s** (image already present locally, so no pull) |
| First `redact` call alone | 0.33 to 0.8 s (spaCy warm-up) |
| Warm `redact`, one sentence | **about 6 to 7 ms** (about 10 ms through API Gateway) |
| Warm `redact`, about 4 KB text (60 repeated sentences) | 125 to 140 ms |
| RSS after init | **about 290 to 400 MB** (varies with the container's limit) |
| `docker stats` of the container once warm | 344 MiB |

## Smallest `memory_size`

| `memory_size` | Result |
|---|---|
| 128 (Floci default) | **Fails.** The runtime process is OOM-killed (exit 137) and API Gateway returns `500`. |
| 256 | Works, but with no headroom: `docker stats` read 255.9 / 256 MiB. Warm requests and a 4 KB input still succeeded. |
| **384** | Works, 344 / 384 MiB. **Smallest comfortable size.** |
| 512, 768, 1024 | Work. Cold and warm timings are the same as 384. |

Recommendation: **512 MB** for the query Lambda, which leaves room for the OpenSearch client and larger inputs. 256 is the hard floor. The ADR 0001 guess of 0.5 to 1 GiB per Lambda container holds at the low end.

## Files

- `spike/presidio/{Dockerfile,handler.py}`: the image. The analyzer is built at module level, so init cost lands on the cold start. The handler reads the v2 proxy event (`event["body"]`) and returns `{statusCode, headers, body}`.
- `spike/apigw/main.tf`: Lambda, HTTP API, `AWS_PROXY` integration (payload 2.0), `POST /redact` route, `$default` stage with `auto_deploy`, Lambda permission. `memory_size` is a variable.

```bash
docker build -t guarded-rag-presidio:latest spike/presidio
terraform -chdir=spike/apigw init
terraform -chdir=spike/apigw apply -auto-approve -var memory_size=512
ID=$(terraform -chdir=spike/apigw output -raw api_id)
curl -X POST "http://localhost:4566/_aws/execute-api/$ID/\$default/redact" \
  -H 'content-type: application/json' -H 'Origin: http://localhost:5173' \
  -d '{"text":"Hi, I am John Smith, call 212-555-0198 or john@example.com"}'
```

## Gotchas

1. **The invoke URL is a path, not a hostname.** Floci serves `/_aws/execute-api/<api_id>/<stage>/<route>`. Quote `$default` in the shell. The `<api_id>` changes on every recreate, so read it from `terraform output`.
2. **A 128 MB function does not fail clearly.** The only symptom at the client is `{"message":"Internal Server Error"}`. The cause (`status 137`, "Lambda runtime process ... exited unexpectedly") shows only in Floci's log. Check `docker logs guarded-rag-floci-1` first.
3. **A handler exception is also a plain `500`.** A bad request body raised `JSONDecodeError` inside the Lambda, with the traceback again visible only in Floci's log. The real handler should catch bad input and return a `400`.
4. **`memory_size` changes recreate the warm container.** The next request is a cold start again, so measure cold start right after an `apply`.
5. **Cold start here excludes an image pull.** Floci uses the local Docker image. A real ECR pull of 985 MB would add time that this spike cannot measure.
6. **Presidio logs a `PlPeselRecognizer ... language is not supported` warning** at init for every non-English recognizer. It is harmless. Not investigated further.
7. **`Access-Control-Max-Age` comes back as `0`** because the spike set no `max_age`. Set one in `cors_configuration` if preflight volume matters; whether Floci honours it was not tested.
8. **No real browser was used.** CORS was checked with `curl` and the `Origin` and `Access-Control-Request-*` headers, which matches what a browser sends.

## Still open

- Whether a different spaCy model (`en_core_web_sm`, about 12 MB against `md`'s about 40 MB) would cut memory and cold start enough to matter. Not tried.
- ADR 0003 "Still open" items: Floci re-pulling a stale image after a rebuild under the same tag is still unchecked. The `memory_size` change above did redeploy the function, but the image was not rebuilt.
