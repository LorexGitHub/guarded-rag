# 0003. Lambda packaging

Status: proposed. Issue: LorexGitHub/guarded-rag#11. Covers handoff decision #17. Builds on ADR 0001 and ADR 0002.

## Decision

1. **One container image holds both Lambdas.** A single Dockerfile, based on `public.ecr.aws/lambda/python:3.12`, contains the ingest and query handlers plus their dependencies (Presidio, the spaCy model, the OpenSearch client). The handler is chosen per function, not per image.
2. **Terraform creates two `aws_lambda_function` resources with the same `image_uri`** and a different `image_config { command = [...] }` each (for example `ingest.handler` and `query.handler`). Each function sets its own `memory_size`: Floci defaults to 128 MB and hard-caps the container at it, which is too small for Presidio.
3. **Compose builds the image; Terraform only references it.** A `docker compose build` (or a make target) builds it under a fixed local tag such as `guarded-rag-lambda:latest`. Floci resolves `image_uri` from the local Docker daemon first, as the #5 spike showed, so nothing is pushed. Terraform never builds. To redeploy after a code change, rebuild and then force a function update (a digest or version tag in `image_uri` does that).
4. **CI keeps build time down with layer order and cache.** The Dockerfile installs dependencies and the spaCy model before `COPY`ing the source, so a code-only change rebuilds one layer. CI builds with `docker/build-push-action` and `cache-from/to: type=gha`. Unit tests run without the image, so CI builds it only for jobs that need it.

## Alternatives rejected

- **Two images.** Each carries only its own dependencies, but CI builds twice and the savings are a few unused MB. Revisit if the two functions' dependency sets diverge a lot.
- **Zip plus layers.** This was the #5 fallback if image Lambdas failed. They didn't. A layer holding the spaCy model also risks the 250 MB unzipped limit.
- **Terraform builds the image (`kreuzwerker/docker`).** One place for build and reference, but it adds a provider and a Docker-daemon dependency inside Terraform, and it diverges from how real AWS deploys.
- **Local ECR repository plus push.** The most AWS-shaped option, with an extra push step and a reliance on Floci's ECR.
- **Prebuilt Presidio base image in GHCR.** Fastest per run, but it needs a second pipeline.

## Triggers to revisit

- A cold CI build of the image takes more than a few minutes even with the cache: move to the prebuilt base image.
- The ingest and query dependency sets diverge, or one function's image size causes cold-start trouble: split into two images.
- Floci's ECR proves reliable: push to a local repo so `image_uri` looks like production.

## Still open

- Image size and Lambda cold start are unmeasured with Presidio and the spaCy model in the image (ADR 0001 flagged the same gap).
- Whether Floci re-pulls or re-uses a stale local image after a rebuild under the same tag is unchecked. Decision 3 assumes a digest or version tag forces it.
