#!/usr/bin/env bash
# Brings the Compose stack up, runs a few cases, and prints a Markdown report of peak memory and
# per-case latency (ADR 0008 decision 2). Assumes guarded-rag-opensearch:512m is already built.
set -euo pipefail
cd "$(dirname "$0")/.."

SAMPLES=$(mktemp)
log() { echo "$*" >&2; }
now() { date +%s.%N; }
since() { awk -v a="$1" -v b="$(now)" 'BEGIN { print b - a }'; }

# Sum container memory (MiB) plus host "used" every 2 s, one line per sample.
sample_loop() {
  while true; do
    docker stats --no-stream --format '{{.MemUsage}}' 2>/dev/null | awk '
      { v=$1; u=v; gsub(/[0-9.]/,"",u); sub(/[A-Za-z]+$/,"",v)
        m = (u=="GiB") ? v*1024 : (u=="MiB") ? v : (u=="KiB") ? v/1024 : v/1048576
        s += m }
      END { printf "%.0f ", s }' >> "$SAMPLES"
    free -m | awk '/^Mem:/ {print $3}' >> "$SAMPLES"
    sleep 2
  done
}

docker compose up -d --no-build
sample_loop & SAMPLER=$!
trap 'kill $SAMPLER 2>/dev/null || true; docker compose down -v >/dev/null 2>&1 || true' EXIT

t0=$(now)
docker compose wait ollama-pull >/dev/null
pull_s=$(since "$t0")

curl -fsS --retry 30 --retry-delay 2 --retry-connrefused -o /dev/null localhost:4566/_floci/health \
  || curl -fsS --retry 30 --retry-delay 2 --retry-connrefused -o /dev/null localhost:4566/

t0=$(now)
curl -fsS -X POST localhost:4566/2021-01-01/opensearch/domain -H 'content-type: application/json' \
  -d '{"DomainName":"rag","EngineVersion":"OpenSearch_2.19"}' >/dev/null
until curl -fsS -o /dev/null localhost:9400 2>/dev/null; do sleep 2; done
domain_s=$(since "$t0")

declare -a NAMES=() TIMES=()
converse() { # name prompt
  local t0
  t0=$(now)
  curl -fsS localhost:4566/model/anthropic.claude-3-haiku-20240307-v1:0/converse \
    -H 'content-type: application/json' \
    -d "{\"messages\":[{\"role\":\"user\",\"content\":[{\"text\":\"$2\"}]}],\"inferenceConfig\":{\"maxTokens\":160}}" \
    >/dev/null
  NAMES+=("$1"); TIMES+=("$(since "$t0")")
}
converse "generate, cold (model load)" "Reply with exactly: pong"
converse "generate, warm 1" "Explain in three sentences what a RAG system does."
converse "generate, warm 2" "List two risks of storing personal data in a vector index."
converse "generate, warm 3" "Summarise why redaction should happen before generation."

t0=$(now)
curl -fsS localhost:11434/api/embeddings -d '{"model":"nomic-embed-text","prompt":"hello world"}' >/dev/null
NAMES+=("embed, nomic-embed-text"); TIMES+=("$(since "$t0")")

kill $SAMPLER 2>/dev/null || true
peak_containers=$(awk '{print $1}' "$SAMPLES" | sort -n | tail -1)
peak_host=$(awk '{print $2}' "$SAMPLES" | sort -n | tail -1)

echo "## Stack measurement"
echo
echo "Runner: $(nproc) vCPU, $(free -m | awk '/^Mem:/ {print $2}') MiB RAM."
echo
echo "| Metric | Value |"
echo "|---|---|"
printf '| Peak container memory (sum) | %s MiB |\n' "$peak_containers"
printf '| Peak host memory used | %s MiB |\n' "$peak_host"
printf '| Model pull (cold cache) / cache check | %.1f s |\n' "$pull_s"
printf '| OpenSearch domain ready | %.1f s |\n' "$domain_s"
echo
echo "| Case | Latency |"
echo "|---|---|"
for i in "${!NAMES[@]}"; do printf '| %s | %.2f s |\n' "${NAMES[$i]}" "${TIMES[$i]}"; done
