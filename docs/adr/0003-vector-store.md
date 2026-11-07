# 0003. Vector store

Status: proposed. Issue: LorexGitHub/guarded-rag#10. Covers handoff decision #12. Builds on ADR 0001 and ADR 0002. Numbers come from `docs/spike.md` (issue #6).

## Decision

1. **The vector store is OpenSearch k-NN on Floci**, behind a `VectorStore` protocol with one `OpenSearchStore` implementation.
2. **Index `chunks`, mapping:**
   - `embedding`: `knn_vector`, `dimension` taken from `Embedder.dim` (768, ADR 0002), `hnsw`, `lucene` engine, `cosinesimil`.
   - `text`: `text`.
   - `doc_id`, `source` (the S3 key): `keyword`.
   - `chunk_index`: `integer`.
   - Settings: `index.knn: true`. No `m` or `ef_search` tuning.
   - `doc_id`, `source` and `chunk_index` serve citations, the trace panel, and deleting a document's old chunks before re-ingest.
3. **Top-k is 5**, a config constant, not a request parameter.
4. **Score threshold is 0.70, provisional.** With `lucene` + `cosinesimil`, `_score = (1 + cosine) / 2`, so 0.70 is cosine 0.40. `VectorStore.search(vector, k, min_score)` filters after retrieving the top-k, not with an OpenSearch `min_score` clause, so the trace panel can show near-miss chunks marked below threshold.
5. **If no chunk passes the threshold, the query Lambda skips generation** and returns a fixed refusal with empty `sources`. The trace still lists the retrieved chunks and their scores. The refusal path is deterministic and does not depend on `llama3.2:3b` declining.
6. **Provisioning:** the domain is created with Terraform `aws_opensearch_domain`. The ingest Lambda creates the index on first use, idempotently (create if missing), and asserts the existing mapping's dimension equals `Embedder.dim`. Terraform has no index resource.

## Alternatives rejected

- **DynamoDB with brute-force cosine.** It was the handoff's fallback if the spike failed. The spike passed, so the fallback is not needed. It would also scan every item per query and drop the "real vector engine" claim.

## Evidence

- 768-dim `knn_vector` index, 5 vectors, top-3: a query near doc 2 returned doc 2 first (score 0.999).
- Latency: server `took` 2 ms, client median 7.6 ms over 20 queries. The index is tiny, so this says nothing about scale.
- Memory: 990 MiB for the OpenSearch container with the 512 MB heap (ADR 0001 budget).

## Triggers to revisit

- The Terraform hang below can't be explained within a time-boxed attempt: replace `aws_opensearch_domain` with a script that creates the domain through Floci's REST API and polls until ready. Record the switch here.
- Eval shows answerable questions refused or unanswerable ones answered: recalibrate the threshold (below) before touching k or the embedder.
- Embedder or dimension changes (ADR 0002): reindex. The dimension assertion fails loudly until then.
- Corpus grows past what 5 chunks of context can serve: raise k and check the `llama3.2:3b` context budget first.

## Still open

- **Terraform hang.** `terraform apply` takes about 10 min on `aws_opensearch_domain` although the domain is ready in about a minute (spike gotcha 1). Cause not isolated. Suspect: Floci reports `Endpoint` as `http://172.x.x.x:9200`, where AWS returns a hostname. Do not apply with a timeout under 15 min until this is understood. Time-box the investigation.
- **Threshold calibration.** 0.70 is a guess, not measured on nomic's score distribution. When the eval corpus exists, set it to the highest value that keeps recall on answerable questions while refusing unanswerable ones, then drop "provisional" from this ADR.
- The OpenSearch endpoint is a container IP that changes when the domain is recreated. Pass it to the Lambdas from the Terraform output, or look it up at run time.
