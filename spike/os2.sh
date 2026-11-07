#!/usr/bin/env bash
cd "$(dirname "$0")/.."
until curl -s localhost:9400 >/dev/null; do sleep 3; done; sleep 20
echo "--- default heap"; curl -s 'localhost:9400/_nodes/stats/jvm?filter_path=nodes.*.jvm.mem.heap_max_in_bytes'; echo
docker stats --no-stream --format '{{.Name}} {{.MemUsage}}'
echo "--- knn"
curl -s -XPUT localhost:9400/v -H 'content-type: application/json' -d '{"settings":{"index.knn":true},"mappings":{"properties":{"e":{"type":"knn_vector","dimension":3}}}}'; echo
curl -s -XPUT 'localhost:9400/v/_doc/1?refresh=true' -H 'content-type: application/json' -d '{"e":[1,0,0]}' >/dev/null
curl -s -XPUT 'localhost:9400/v/_doc/2?refresh=true' -H 'content-type: application/json' -d '{"e":[0,1,0]}' >/dev/null
curl -s localhost:9400/v/_search -H 'content-type: application/json' -d '{"query":{"knn":{"e":{"vector":[0.9,0.1,0],"k":1}}}}' | head -c 300; echo
