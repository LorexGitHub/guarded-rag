.PHONY: test lint up down lambda-image
test:
	uv run ruff check .
	uv run pytest -q
up:
	docker compose up -d
down:
	docker compose down
lambda-image:
	docker compose build lambda-image
