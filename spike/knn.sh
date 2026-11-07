#!/usr/bin/env bash
# k-NN on the Floci OpenSearch domain: 768-dim knn_vector, 5 docs, top-3 query.
# Needs only curl and python3. Domain is reachable on host port 9400.
set -e
OS=localhost:9400
curl -s -XDELETE $OS/chunks >/dev/null || true
echo "--- create index"
curl -s -XPUT $OS/chunks -H 'content-type: application/json' -d '{
 "settings":{"index.knn":true},
 "mappings":{"properties":{"text":{"type":"text"},
  "embedding":{"type":"knn_vector","dimension":768,
   "method":{"name":"hnsw","space_type":"cosinesimil","engine":"lucene"}}}}}'; echo
python3 - <<'PY'
import json, random, urllib.request, time
random.seed(1)
def v(): return [random.uniform(-1,1) for _ in range(768)]
docs=[v() for _ in range(5)]
def req(m,p,b=None):
    r=urllib.request.Request("http://localhost:9400"+p,data=json.dumps(b).encode() if b else None,method=m,headers={"content-type":"application/json"})
    return json.load(urllib.request.urlopen(r))
for i,d in enumerate(docs):
    req("PUT",f"/chunks/_doc/{i}?refresh=true",{"text":f"doc {i}","embedding":d})
print("--- indexed", req("GET","/chunks/_count")["count"])
q=[x+random.uniform(-0.05,0.05) for x in docs[2]]   # near doc 2
lat=[]
for _ in range(20):
    t=time.perf_counter()
    r=req("POST","/chunks/_search",{"size":3,"query":{"knn":{"embedding":{"vector":q,"k":3}}}})
    lat.append((time.perf_counter()-t)*1000)
print("top-3:",[(h["_id"],round(h["_score"],3)) for h in r["hits"]["hits"]])
print("server took ms:",r["took"],"| client latency ms min/median/max: %.1f/%.1f/%.1f"%(min(lat),sorted(lat)[10],max(lat)))
PY
