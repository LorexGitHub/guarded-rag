.PHONY: test lint up down
test:
	uv run ruff check .
	uv run pytest -q
up:
	docker compose up -d
down:
	docker compose down
