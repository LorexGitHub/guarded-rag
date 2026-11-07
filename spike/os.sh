#!/usr/bin/env bash
cd "$(dirname "$0")/.."
docker compose up -d floci </dev/null 2>&1 | tail -2
until curl -sf localhost:4566/_floci/health >/dev/null 2>&1 || curl -s localhost:4566 >/dev/null; do sleep 2; done
curl -s -X POST localhost:4566/2021-01-01/opensearch/domain -H 'content-type: application/json' \
  -d '{"DomainName":"rag","EngineVersion":"OpenSearch_2.19","ClusterConfig":{"InstanceType":"t3.small.search","InstanceCount":1}}' | head -c 400; echo
for i in $(seq 1 60); do
  c=$(docker ps --filter name=floci-aws-opensearch -q); [ -n "$c" ] && curl -s localhost:4566/2021-01-01/opensearch/domain/rag | grep -q '"Processing":false' && break; sleep 5; done
docker ps --filter name=floci-aws-opensearch --format '{{.Names}} {{.Image}} {{.Ports}}'
docker inspect $(docker ps --filter name=floci-aws-opensearch -q) --format '{{json .Config.Env}} {{json .HostConfig.Memory}}'
