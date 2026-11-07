#!/usr/bin/env bash
# Spike steps 1 and 5: pull models, measure idle memory, call Converse through Floci.
cd "$(dirname "$0")/.."
dc() { docker compose "$@" </dev/null; }
dc exec -T ollama ollama pull nomic-embed-text
dc exec -T ollama ollama list
echo "--- IDLE"; docker stats --no-stream --format '{{.Name}} {{.MemUsage}}'; free -m | sed -n 1,3p
echo "--- CONVERSE via Floci"
curl -s -m 300 -w '\nhttp=%{http_code} t=%{time_total}s\n' localhost:4566/model/anthropic.claude-3-haiku-20240307-v1:0/converse \
  -H 'content-type: application/json' \
  -d '{"messages":[{"role":"user","content":[{"text":"Reply with exactly: pong"}]}],"inferenceConfig":{"maxTokens":20}}'
echo "--- AFTER GENERATION"; docker stats --no-stream --format '{{.Name}} {{.MemUsage}}'; free -m | sed -n 1,3p
