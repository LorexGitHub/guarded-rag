#!/usr/bin/env bash
cd "$(dirname "$0")/.."
docker build -q -t guarded-rag-opensearch:512m docker/opensearch
curl -s -XDELETE localhost:4566/2021-01-01/opensearch/domain/rag >/dev/null; sleep 5
docker compose up -d floci </dev/null 2>&1 | tail -1
until curl -s localhost:4566 >/dev/null; do sleep 2; done
curl -s -X POST localhost:4566/2021-01-01/opensearch/domain -H 'content-type: application/json' -d '{"DomainName":"rag","EngineVersion":"OpenSearch_2.19"}' >/dev/null
until curl -s localhost:9400 >/dev/null; do sleep 3; done; sleep 25
echo "--- 512m heap"; curl -s 'localhost:9400/_nodes/stats/jvm?filter_path=nodes.*.jvm.mem.heap_max_in_bytes'; echo
echo "--- IDLE (full stack)"; docker stats --no-stream --format '{{.Name}} {{.MemUsage}}'; free -m | sed -n 2,3p
( for i in 1 2 3 4 5 6; do docker stats --no-stream --format '{{.Name}} {{.MemUsage}}' | grep ollama; sleep 3; done > /tmp/peak.txt ) &
curl -s -m 300 -w '\nt=%{time_total}s\n' localhost:4566/model/x/converse -H 'content-type: application/json' \
 -d '{"messages":[{"role":"user","content":[{"text":"Explain in about 150 words why the sky is blue."}]}],"inferenceConfig":{"maxTokens":200}}' | tail -c 350
echo "--- DURING/AFTER GENERATION"; docker stats --no-stream --format '{{.Name}} {{.MemUsage}}'; free -m | sed -n 2,3p
wait; sort -k2 -h /tmp/peak.txt | tail -1
