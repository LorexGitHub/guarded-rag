.PHONY: test lint up down lambda-image e2e
test:
	uv run ruff check .
	uv run pytest -q
# Images, Compose stack, then Terraform (ADR 0008 decision 1). Repeatable: a second run is a no-op apply.
up:
	docker compose up -d --build
	docker compose wait ollama-pull
	scripts/wait-for-floci.sh
	terraform -chdir=infra init -input=false
	terraform -chdir=infra apply -auto-approve -input=false
# Floci starts OpenSearch and Lambda containers itself, so Compose does not know them.
down:
	docker compose down
	docker ps -aq --filter name=floci-aws | xargs -r docker rm -f
	docker volume ls -q --filter name=floci-aws | xargs -r docker volume rm
	rm -rf infra/terraform.tfstate infra/terraform.tfstate.backup
lambda-image:
	docker compose build lambda-image
e2e:
	uv run pytest -q -m e2e tests/e2e
