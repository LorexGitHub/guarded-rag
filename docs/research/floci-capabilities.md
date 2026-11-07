# Floci capability facts (research for #3)

Source of truth: the Floci repo at commit
[`d6aed932`](https://github.com/floci-io/floci/tree/d6aed932a1fa835793cfc84003bf39a100e51511)
(2026-11-06, version 2.4.0 per `pom.xml:9`). Paths below are relative to that commit; prefix
`https://github.com/floci-io/floci/blob/d6aed932a1fa835793cfc84003bf39a100e51511/` to get a permalink.
Java sources live under `src/main/java/io/floci/aws/` (abbreviated `…/` below).

Everything here comes from reading docs and source. Nothing was run. Items marked **spike** still
need to be proven at runtime.

## Contradictions with the handoff ("Facts about Floci")

| # | Handoff says | Source says |
|---|---|---|
| C1 | In proxy mode, "`InvokeModel` and embeddings are still stubs". | **Wrong for proxy mode.** `ProxyBackend.invokeModel` throws `400 ValidationException: InvokeModel is not supported by the bedrock-runtime proxy backend; use Converse.` (`…/services/bedrockruntime/backend/ProxyBackend.java:102-105`). The backend is chosen once for all operations (`…/bedrockruntime/BedrockRuntimeService.java:38-56`), so with `BACKEND=proxy` every InvokeModel call fails. The stub reply comes only from the `stub` backend. The docs (`docs/services/bedrock-runtime.md:11,20,188`) still say InvokeModel "falls back to the stub", so docs and code disagree, and the code wins. Embeddings cannot be reached through Floci in either mode (see Q4). |
| C2 | OpenSearch is "a real `opensearchproject/opensearch:2` container". | The image is pinned per `EngineVersion`. The default `OpenSearch_2.19` maps to `opensearchproject/opensearch:2.19.5`, and 3.0 to 3.7 are also available (`…/services/opensearch/OpenSearchVersions.java:37,45-56`). |
| C3 | (implied) The OpenSearch endpoint looks like AWS's. | `Endpoint` is `http://<host>:<port>`. It includes the scheme and is usually a raw container IP, not a DNS name (see Q1). AWS returns a bare hostname with no scheme and serves it over HTTPS. |
| C4 | (not mentioned) | Lambda containers get a **hard memory limit equal to `MemorySize`**, with memory+swap set to the same value, and the default is 128 MB (`…/services/lambda/launcher/ContainerLauncher.java:297-302`; `docs/services/lambda.md:618`). A Presidio/spaCy Lambda must set `memory_size` explicitly. Count this toward the 16 GB budget. |
| C5 | Terraform endpoints list: s3, lambda, apigateway, apigatewayv2, iam, opensearch, dynamodb, sts, logs, bedrock. | That list is fine. Add `bedrockruntime` only if Terraform ever calls it (it doesn't). Add `ecr` only if images are pushed to emulated ECR, which isn't needed (see Q2). |

Confirmed as written: `floci/floci:latest` on port 4566 needs the Docker socket (`docs/services/lambda.md:758+`, `docs/services/opensearch.md:21-34`). Guardrails can be created but are never applied: Bedrock Runtime has no `guardrailConfig` handling (no match under `…/services/bedrockruntime/`), and `docs/services/bedrock-runtime.md:192` lists Guardrails as out of scope. Comprehend always reports no PII (`docs/services/comprehend.md:23`). IAM is **not enforced by default**: it is opt-in via `enforcement-enabled: true` (`docs/services/iam.md:1672-1676`).

## Q1. OpenSearch: version, k-NN, endpoint format

- **Modes.** Real mode is the default (`FLOCI_SERVICES_OPENSEARCH_MOCK=false`). It starts one Docker container per domain. Mock mode serves no data plane (`docs/services/opensearch.md:9-17,115,279`).
- **Version.** The default engine version is `OpenSearch_2.19`, which maps to `opensearchproject/opensearch:2.19.5`. Supported versions are OpenSearch 1.0 to 3.7 and Elasticsearch 7.1 to 7.10 (`OpenSearchVersions.java:37,45-70`; `docs/services/opensearch.md:153-154`). `FLOCI_SERVICES_OPENSEARCH_DEFAULT_IMAGE` forces one image for every domain (`docs/services/opensearch.md:116`).
- **k-NN.** Floci never mentions k-NN: a repo-wide grep for `knn`/`k-NN` finds nothing in source, docs or tests. Floci runs the **stock upstream image**, though, and the upstream 2.19.5 distribution manifest bundles the `k-NN` plugin at `tags/2.19.5.0` ([opensearch-build `manifests/2.19.5/opensearch-2.19.5.yml` L56-58](https://github.com/opensearch-project/opensearch-build/blob/main/manifests/2.19.5/opensearch-2.19.5.yml)). `neural-search` and `ml-commons` are bundled too. Floci adds no `plugins` customization. The container env is only `discovery.type=single-node` and `DISABLE_SECURITY_PLUGIN=true`, plus `OPENSEARCH_INITIAL_ADMIN_PASSWORD=FlociAdmin1!` for 2.12 and later (`…/opensearch/OpenSearchDomainManager.java:124-126,356-370`). So k-NN should be available. **Spike:** a `knn_vector` mapping plus a k-NN query.
- **Security.** Plain HTTP with no auth. `AccessPolicies` and the encryption and advanced-security options round-trip but are not enforced (`docs/services/opensearch.md:281`).
- **Memory.** Floci sets no JVM heap and no memory limit on the OpenSearch container (no `JAVA_OPTS` or memory setting in `OpenSearchDomainManager.java`). Heap is the image default, and Floci offers no knob to change it short of a custom image via `DEFAULT_IMAGE`. **Spike:** measure RSS.
- **Endpoint format.** `domain.setEndpoint("http://" + endpoint.host() + ":" + endpoint.port())` (`OpenSearchDomainManager.java:188-189`), reported verbatim as `Endpoint` (`…/opensearch/OpenSearchController.java:637-643`). Under VPCOptions it is `Endpoints.vpc` instead.
  - Floci in a container (our Compose case): `http://<container IP on the preferred Docker network>:9200` (`…/core/common/docker/ContainerLifecycleManager.java:1778-1815`).
  - Floci native on the host: `http://localhost:<host port 9400-9499>` (`ContainerLifecycleManager.java:1762-1769`).
  - A host port from 9400-9499 is always published as well, so clients on the host reach it at `localhost:94xx` (`OpenSearchDomainManager.java:135-152`; `docs/services/opensearch.md:118-119`).
  - The container name is `floci-aws-opensearch-<account>-<region>-<domain>` (`docs/services/opensearch.md:161`). That name resolves via Docker DNS on a user-defined network.
  - **Implication:** the Lambda should take the endpoint from Terraform output (`aws_opensearch_domain.endpoint`) and accept a value that already has a scheme. The IP is stable only for the container's lifetime.
- **Readiness.** `Processing=true` until `/_cluster/health` returns green or yellow (`docs/services/opensearch.md:151-152`). Terraform waits on this.

## Q2. Lambda container images (PackageType=Image)

- **Supported.** `CreateFunction` stores `Code.ImageUri` (`…/services/lambda/LambdaService.java:665-667`). When it launches, `"Image".equals(fn.getPackageType())` makes the image the function's `ImageUri` instead of a runtime base image (`ContainerLauncher.java:233-235`). `ImageConfig` `EntryPoint`, `Command` and `WorkingDirectory` are honoured. Without them, `Handler` becomes CMD (`ContainerLauncher.java:370-383`). The image must speak the Lambda Runtime API, as the AWS base images and `awslambdaric` do. Floci passes the Runtime API address in the environment (`ContainerLauncher.java:240-241`).
- **Resolution order (local daemon first):**
  1. An AWS-shaped `<acct>.dkr.ecr.<region>.amazonaws.com/<repo>:<tag>` URI is rewritten to Floci's emulated registry `localhost:<port>/…` **unless** `prefer-local-images` is on (it is by default, `src/main/resources/application.yml:811`) and the image already exists on the Docker daemon. If it exists, it runs as-is (`…/services/ecr/registry/EcrRegistryManager.java:141-168`).
  2. Any other reference, for example `guarded-rag-query:dev`, passes through unchanged (`EcrRegistryManager.java:148-150`).
  3. At container create, `ImageCacheService.ensureImageExists` inspects the local daemon first and skips the pull if the image is present. Only otherwise does it pull from the registry (`…/services/lambda/launcher/ImageCacheService.java:84-93`; called from `ContainerLifecycleManager.java:153-158`).
  - Docs: "build the image under the exact URI the function declares (`docker build -t <ImageUri> .`) and no push is needed" (`docs/services/lambda.md:1156-1158`). Private registries need Docker credentials (`docs/services/lambda.md:1160-1162`).
- **Recommendation:** `docker build -t 000000000000.dkr.ecr.us-east-1.amazonaws.com/guarded-rag-ingest:dev`, then point `image_uri` at that tag. The reference looks like AWS and no push is needed. **Spike.**

## Q3. Lambda Docker network and reaching Compose services by name

- **Network choice:** `FLOCI_SERVICES_LAMBDA_DOCKER_NETWORK`, else `FLOCI_SERVICES_DOCKER_NETWORK`, else **the network Floci's own container is attached to**, auto-detected (`ContainerLauncher.java:303` → `…/core/common/docker/ContainerBuilder.java:90-101,414-417`; `CurrentContainerNetworkResolver.java:19-24`; `docs/configuration/docker.md:259-278`; `docs/configuration/docker-compose.md:106`). Under Compose that is `<project>_default`. Setting `FLOCI_SERVICES_DOCKER_NETWORK=<project>_default` explicitly is the documented belt-and-braces option, and it also covers OpenSearch.
- **Name resolution:** Lambda containers use **Floci's embedded DNS server** as their resolver (`specBuilder.withEmbeddedDns()`, `ContainerLauncher.java:310`). It answers `*.localhost.floci.io` itself and forwards every other query to the upstreams in Floci's `/etc/resolv.conf`, which is Docker's `127.0.0.11`, then to public fallbacks (`…/core/common/dns/EmbeddedDnsServer.java:60-63,73`; `docs/services/lambda.md:942-958`). Docker DNS inside Floci's container resolves Compose service names on Floci's networks, so `http://ollama:11434` and `opensearch` container names should resolve from the Lambda. **Spike**, as the handoff already requires. Escape hatches: `FLOCI_SERVICES_LAMBDA_EXTRA_HOSTS=host:ip` and `FLOCI_SERVICES_LAMBDA_DOCKER_FLAGS="--dns …"` (`docs/services/lambda.md:637-639`).
- **AWS SDK inside the Lambda:** Floci injects `AWS_ENDPOINT_URL=<floci endpoint>`, `FLOCI_ENDPOINT` and `FLOCI_HOSTNAME`, plus credentials (`…/core/common/docker/LaunchedContainerAwsEnv.java:160-174`). boto3 ≥1.34 honours `AWS_ENDPOINT_URL`, so `boto3.client("bedrock-runtime")` reaches Floci with no code change. Set `FLOCI_HOSTNAME=floci` (the Compose service name) so that the injected endpoint is `http://floci:4566` (`docs/services/lambda.md:1066-1077`; `docs/configuration/docker-compose.md:79-106`).
- **Runtime API callback:** auto-detected, with override `FLOCI_SERVICES_LAMBDA_DOCKER_HOST_OVERRIDE` (`docs/services/lambda.md:737-756`).

## Q4. Bedrock proxy: env vars, model mapping, InvokeModel and embeddings

- **Env vars** (`docs/services/bedrock-runtime.md:32-41`):
  - `FLOCI_SERVICES_BEDROCK_RUNTIME_BACKEND=proxy` (default `stub`)
  - `FLOCI_SERVICES_BEDROCK_RUNTIME_PROXY_URL=http://ollama:11434/v1`. This is required. Floci itself makes the call, so the URL must resolve **from the Floci container**. Floci appends `/chat/completions` (`ProxyBackend.java:235-249`).
  - `FLOCI_SERVICES_BEDROCK_RUNTIME_PROXY_API_KEY` (optional bearer token)
  - `FLOCI_SERVICES_BEDROCK_RUNTIME_PROXY_MODEL_MAPPING=bedrockId=ollamaId,...`
  - `FLOCI_SERVICES_BEDROCK_RUNTIME_PROXY_DEFAULT_MODEL`
  - `FLOCI_SERVICES_BEDROCK_RUNTIME_PROXY_PASSTHROUGH` (default `false`)
  - `FLOCI_SERVICES_BEDROCK_RUNTIME_PROXY_ERROR_BODY_TIMEOUT_MILLIS` (default `1000`)
- **Model-id resolution order:** an explicit mapping entry, then the raw id if passthrough is on, then `default-model`, else `400 ValidationException` (`ProxyBackend.java:266-280`). The model id can be a plain id, an inference-profile id or an ARN (`docs/services/bedrock-runtime.md:24`). Example for us: `MODEL_MAPPING=anthropic.claude-3-haiku-20240307-v1:0=llama3.2:3b`, so the code keeps a real Bedrock model id.
- **Proxied:** `Converse` and `ConverseStream` only. Translated fields are `system`, `inferenceConfig` (`maxTokens`, `temperature`, `topP`, `stopSequences`), `toolConfig`, `outputConfig.textFormat` json_schema, and inline images (`docs/services/bedrock-runtime.md:11,19-26,71-151`).
- **InvokeModel:** with `proxy` it returns a 400 error, not the stub (C1). With `stub` it returns a canned Anthropic-shaped body, or a generic `{"outputs":[…]}` (`…/bedrockruntime/backend/StubBackend.java:56-73`). `InvokeModelWithResponseStream` returns 501 (`BedrockRuntimeController.java:77-80`).
- **Embeddings:** **not proxyable.** Bedrock embeddings (Titan or Cohere embed) go through InvokeModel, which fails in proxy mode. Floci has no `/embeddings` forwarding at all: the only upstream path is `/chat/completions` (`ProxyBackend.java:39,249`), and `bedrockruntime` contains no "embed" code. This **confirms handoff decision #11**: call Ollama's embeddings API directly. A consequence is that you can't mix modes. The proxy backend is global, so no InvokeModel of any kind can succeed while Converse is proxied.

## Q5. S3 → Lambda notifications

- `PutBucketNotificationConfiguration` (which Terraform's `aws_s3_bucket_notification` calls) stores `LambdaFunctionConfigurations` and checks that the destination function exists, unless `x-amz-skip-destination-validation` is sent. **Destination resource-policy permissions are not checked**, so `aws_lambda_permission` is optional for Floci but should still be written for realism. Cross-account delivery is not emulated (`docs/services/s3.md:49-60`; `…/services/s3/S3Service.java:5610-5670`).
- **Delivery:** in-process. On an object event, Floci matches each config's events (wildcards such as `s3:ObjectCreated:*`) and the prefix/suffix filter (`ln.matchesKey(key)`). It then calls `LambdaService.invoke(region, fn, payload, InvocationType.Event)`, an **asynchronous** invoke with Floci's async retry semantics. Failures are logged as warnings and never surface to the S3 caller (`S3Service.java:7154-7172,7286-7294`).
- **Payload:** the AWS event structure, keys form-URL-encoded (spaces become `+`), with `configurationId` set to the rule ID or `emulator` (`docs/services/s3.md:786-799`). Presigned or browser POST uploads emit `ObjectCreated:Post`, not `Put`, so subscribe to `s3:ObjectCreated:*` (`docs/services/s3.md:45-46`).

## Q6. Terraform resources known to work

- **Provider configuration:** `hashicorp/aws ~> 6.0`, `us-east-1`, `test`/`test`, the three `skip_*` flags and `s3_use_path_style = true` (`docs/getting-started/terraform.md:25-53`). The compat suite's endpoints include `s3, lambda, iam, sts, dynamodb, logs, apigateway, apigatewayv2, opensearch, ecr, …` (`compatibility-tests/compat-terraform/provider.tf:18-75`). The S3 backend with DynamoDB locking works too (`docs/getting-started/terraform.md:111-142`).
- **Exercised by Floci's own Terraform compatibility suite** (`compatibility-tests/compat-terraform/main.tf` and `test/*-tf/main.tf`), limited to the resources relevant here:
  - S3: `aws_s3_bucket`, `aws_s3_bucket_versioning`, `aws_s3_object`
  - Lambda: `aws_lambda_function` (zip, `python3.14`, `test/lambda-durable-config-tf/main.tf:48-50`)
  - IAM: `aws_iam_role`, `aws_iam_policy`, `aws_iam_role_policy_attachment`
  - DynamoDB: `aws_dynamodb_table`
  - CloudWatch Logs: `aws_cloudwatch_log_group`
  - ECR: `aws_ecr_repository`
  - API Gateway v1: `aws_api_gateway_rest_api`, `_resource`, `_method`, `_integration`, `_deployment`, `_stage`, `_rest_api_policy` (`test/apigateway-rest-readback-tf/main.tf`)
  - API Gateway v2: `aws_apigatewayv2_api` only
  - The suite also covers about 60 other resources outside our scope (VPC, RDS, SQS, SNS and others).
- **Has Terraform-specific handling in the docs but no suite coverage:** `aws_opensearch_domain`. Its `Endpoint` vs `Endpoints.vpc` shape is made to suit the provider, and config fields round-trip "so Terraform detects drift correctly" (`docs/services/opensearch.md:142,281`; `OpenSearchController.java:640-643`). Also `aws_opensearch_vpc_endpoint` and `aws_elasticsearch_domain` (`docs/services/opensearch.md:60,73`).
- **Not covered by the suite.** These have to be proven in our spike:
  - `aws_s3_bucket_notification`
  - `aws_lambda_permission` (but `AddPermission` exists, `docs/services/lambda.md:32`)
  - `aws_lambda_function` with `package_type = "Image"`
  - `aws_apigatewayv2_integration`, `_route`, `_stage`
  - `aws_s3_bucket_website_configuration` (but the S3 Website API exists, `docs/services/s3.md:24,184-189`)
  - `aws_opensearch_domain` end to end

## Suggested Compose env for the spike (derived, unverified)

```yaml
floci:
  image: floci/floci:latest
  ports: ["4566:4566"]
  volumes: ["/var/run/docker.sock:/var/run/docker.sock"]
  environment:
    FLOCI_HOSTNAME: floci
    FLOCI_SERVICES_DOCKER_NETWORK: guarded-rag_default
    FLOCI_SERVICES_BEDROCK_RUNTIME_BACKEND: proxy
    FLOCI_SERVICES_BEDROCK_RUNTIME_PROXY_URL: http://ollama:11434/v1
    FLOCI_SERVICES_BEDROCK_RUNTIME_PROXY_MODEL_MAPPING: anthropic.claude-3-haiku-20240307-v1:0=llama3.2:3b
```
