# AWS Knowledge MCP server: tools, limits and fit as a retriever

Research for LorexGitHub/guarded-rag#36 (map #34). Feeds #43 (where retrieval comes from). Researched 2026-11-07.

**Unverified** marks a claim I could not confirm from a primary source. **Observed** marks something I saw by calling the live endpoint on 2026-11-07, not a documented guarantee.

## Short answer

- A free, public, unauthenticated, read-only MCP server over HTTPS. It searches AWS docs, blogs, What's New posts and Well-Architected material, and reads pages as markdown.
- A Lambda can call it. It is plain JSON-RPC over HTTPS POST, with no session needed.
- A search returns **rank order only, with no score**: `rank_order`, `url`, `title`, and `context`, which is a verbatim chunk of the page.
- It **always returns results**, even for nonsense queries. A refusal rule like ADR 0004's cannot run on its output as is.
- It can serve as a live **fallback or citation source** behind the `VectorStore` seam. It cannot replace the local index as the gate that decides when to refuse.

## What it is

| Fact | Value | Source |
|---|---|---|
| Endpoint | `https://knowledge-mcp.global.api.aws` | [awslabs README][readme] |
| Transport | MCP Streamable HTTP. Clients without HTTP support can use a stdio-to-HTTP proxy (`uvx fastmcp run <url>`) | [readme] |
| Auth | "does not require authentication but is subject to rate limits"; no AWS account needed | [readme], [GA post][ga] |
| Cost | "publicly accessible at no cost" | [ga] |
| Availability | GA on 2025-10-01, "available globally" | [ga] |
| Content | Latest AWS docs, API references, What's New, Getting Started, blogs, architecture references, Well-Architected, troubleshooting, Amplify, CDK, CloudFormation, Strands SDK, agent skills | [readme], [ga] |
| Terms | Use is subject to the [AWS Site Terms][terms]. Telemetry is not used for model training | [readme] |
| Server info | `serverInfo: AWSKnowledgeMCP 1.0.0`, negotiates `protocolVersion: 2025-03-26`, served through CloudFront | observed (`initialize`) |

## Tools

These schemas come from the live `tools/list` call (observed). The README lists the same five tools by their short names. The live names carry an `aws___` prefix.

| Tool | Input | Output |
|---|---|---|
| `aws___search_documentation` | `search_phrase` (required), `limit` (default 4), `topics` (up to 3 of `reference_documentation`, `current_awareness`, `troubleshooting`, `amplify_docs`, `cdk_docs`, `cdk_constructs`, `cloudformation`, `agent_skills`, `strands_docs`, `general`; default `general`) | `{"content":{"result":[{rank_order, title, context, url}]}}`. `rank_order` is "lower=better". `context` is "verbatim page text -- a real chunk of the actual page, not a short snippet" |
| `aws___read_documentation` | `requests: [{url, max_length? (default 10000), start_index?}]`, batch 2–5 | Markdown, plus `total_length, start_index, end_index, truncated, redirected_url?`. On error, `error_code` is one of `not_found, invalid_url, throttled, downstream_error, validation_error`. Only allow-listed URL prefixes work, for example `docs.aws.amazon.com`, `aws.amazon.com` (except `/marketplace`) and `repost.aws/knowledge-center` |
| `aws___list_regions` | none | Region IDs and names |
| `aws___get_regional_availability` | `resource_type` (`product`/`api`/`cfn`), `regions` (max 10), `filters`, `next_token` | Per-region status (`isAvailableIn`, `isNotAvailableIn`, `isPlannedIn`, or `Not Found`) |
| `aws___retrieve_skill` | `skill_name` (taken from search results), `file?` | `SKILL.md` or a reference file |

## What a search returns

A real call (observed) to `search_documentation` for "S3 Standard-IA minimum storage duration" with `limit: 3` returned:

1. `rank_order: 1`: "Amazon S3 FAQs", `https://aws.amazon.com/s3/faqs/`, with a short Q&A chunk that answers the question (30-day minimum).
2. `rank_order: 2`: "Understanding and managing Amazon S3 storage classes" (S3 User Guide), with a chunk of about 2 KB ending in `*[truncated — additional content omitted]*`.
3. `rank_order: 3`: a re:Post Knowledge Center article.

The useful properties:

- **Ranking only.** No similarity, BM25 or confidence value appears anywhere in the response. Neither the README nor the tool description documents how ranking works.
- **Chunks, not full pages.** Chunks range from a few hundred characters to about 2 KB and can be truncated. Use `read_documentation` with the URL to get the full page.
- **Mixed source types.** FAQs, user guides, blogs, re:Post and third-party readthedocs (Braket) all appear in one result list. The response has no `source_type` field. Only the URL host and path tell the sources apart.
- **No empty result.** A nonsense query ("quantum flux capacitor pricing for llamas") returned 3 results ranked 1–3 (a Braket SDK page, a SageMaker pricing-metrics page, a Llama blog post). They look exactly like a good answer. **This is the key fact for refusal.**

## Rate limits

- The documentation says only "subject to rate limits", with **no published numbers** ([readme], [ga]). **Unverified**: the actual per-IP limits.
- AWS documents quotas for the *separate* AWS MCP Server (agent toolkit), which has per-account and per-IP limits ([aws-mcp-limits]). Those numbers do not apply to the Knowledge server.
- Observed: 30 parallel `search_documentation` calls from one IP all returned HTTP 200. Latency was 1.3 s for the first and up to 8.4 s under the burst. I saw no throttling, but I did not check every response body for a `throttled` error.
- Plan for throttling anyway: back off and retry on `throttled`, and treat a failure as an error, not a refusal (ADR 0005 decision 5).

## Terms of use

- The README defers to the [AWS Site Terms][terms]. The relevant clauses:
  - "The materials hosted on docs.aws.amazon.com are licensed as follows: documentation (e.g., user guides, developer guides, other publications) is licensed under CC-BY-SA-4.0, while any code therein is licensed under MIT-0."
  - The general site license excludes "any resale or commercial use … any derivative use … or any use of data mining, robots, or similar data gathering and extraction tools", "unless otherwise specified by AWS in a separate license".
- What this means for guarded-rag:
  - **docs.aws.amazon.com content** is CC-BY-SA-4.0. You may store it, chunk it, quote it and show it, with attribution. Anything derived from it and shared carries the share-alike obligation. That covers the local index and generated questions if they are published. This is a reading of the terms, not legal advice.
  - **Other `aws.amazon.com` content** that the MCP returns (FAQs, blogs, What's New) has no separate license on the terms page. It falls under the general Site Terms, which forbid data mining and derivative use. Quoting a chunk live as a citation fits what the server is for. **Bulk-harvesting MCP results into a stored corpus** is arguably the "data gathering and extraction" the terms prohibit. **Unverified**: AWS gives no explicit statement either way for content fetched through the MCP. To stay safe, build the stored index only from docs.aws.amazon.com pages, or limit stored non-docs content to what the user saw at query time.
- A personal, non-commercial study tool matches the server's intended use, which is AI agents answering AWS questions.

## Can a Lambda call it?

Yes. Observed: one HTTPS POST of JSON-RPC (`tools/call`) without an `initialize` handshake or `Mcp-Session-Id` header returned a full result. The server works statelessly, so a handler needs only `httpx`/`urllib` and does not need the MCP SDK. Required headers: `Content-Type: application/json` and `Accept: application/json, text/event-stream`. Responses come back as plain JSON, not SSE.

Constraints:

- **Egress.** The Lambda needs public internet. That works outside a VPC. Inside a VPC it needs a NAT gateway, and no AWS PrivateLink endpoint is documented for this server.
- **Floci.** **Unverified**: whether Floci's Lambda containers have outbound internet by default. They likely do (they are Docker containers), but I did not test it. CI would then depend on a live external service, which conflicts with "development and CI run free and reproducible". Use a recorded fake in CI.
- **Latency.** About 1.3 s per search (observed, from Europe through CloudFront DUS51). That is noticeable but small next to a local `llama3.2:3b` generation.

## Fit with the `VectorStore` seam (ADR 0005)

`VectorStore.search(vector, k, min_score) -> list[Hit]` takes an **embedding** and returns `Hit(chunk, score, passed)`. The MCP takes a **text phrase** and returns no score. So:

- **It cannot implement `VectorStore` as written.** It has no vector input, no `ensure_index` or `replace_document` (the corpus is read-only and run by AWS), and no score.
- **A text-level `Retriever` seam** above `VectorStore` would fit it. A sketch: `retrieve(question: str, k: int) -> list[Hit]`, with `Hit.score: float | None`. `LocalRetriever` would wrap `Embedder` + `VectorStore`. `AwsKnowledgeRetriever` would wrap the MCP. That is a second real backend, which is ADR 0005's own trigger for adding a selection point.
- `Chunk` maps across cleanly: `source` is the `url`, `text` is the `context`, `doc_id` is the url, and `chunk_index` is unknown (use `rank_order` or 0). A URL is a better citation for a study tool than an S3 key.

## Refusal without similarity scores (ADR 0004)

Rank order cannot say "nothing relevant", and the nonsense-query test shows that a top result always exists. Options, from most to least robust:

1. **Score the MCP chunks locally.** Embed the question and each returned `context` with the existing `Embedder` (nomic, ADR 0002) and compute the same `(1+cos)/2` score. Apply `MIN_SCORE`. This brings back a real `Hit.score`, keeps one threshold and one calibration path (ADR 0004 "Still open"), and costs k extra embeddings per query. The local index and the MCP can then share one refusal rule.
2. **Cross-check with the local index.** Use the MCP only when the local index has a hit above threshold, as enrichment or a fresher citation. Refusal stays exactly as in ADR 0004. The MCP never decides on its own.
3. **Let the LLM judge support.** Ask the model whether a chunk supports the verdict, and refuse when it cites no chunk. This conflicts with ADR 0004 decision 5 (the refusal path "does not depend on `llama3.2:3b` declining"), so it is not recommended as the gate.

Option 1 is the cheapest way to keep a deterministic, calibratable refusal rule with the MCP in the loop.

## Recommendation for #43

- **Local index first.** Keep the local OpenSearch index of SAA material, built from docs.aws.amazon.com pages (CC-BY-SA-4.0) as the corpus and gate. It keeps scores, a deterministic refusal, offline and free CI, and clear licensing.
- **The MCP as a live fallback and enrichment source**, behind a text-level `Retriever` seam. Re-score its chunks with the local `Embedder` and the same `MIN_SCORE` (option 1), so refusal works the same way whichever source answered.
- **The MCP as a discovery tool for building the index.** Use `search_documentation` to find which doc URLs cover each SAA domain, then ingest those docs.aws.amazon.com pages directly. That keeps the stored corpus on CC-BY-SA content.
- **In CI, a recorded fake** (`FakeKnowledgeRetriever` with canned JSON). Live MCP calls run only in by-hand or `slow` tests.
- Flag for ADR 0004 and ADR 0005: `Hit.score` may need to be computed after retrieval for remote sources, and a `Retriever` seam may sit above `VectorStore`.

## Sources

- [readme]: awslabs/mcp, `src/aws-knowledge-mcp-server/README.md`, https://github.com/awslabs/mcp/tree/main/src/aws-knowledge-mcp-server (also https://awslabs.github.io/mcp/servers/aws-knowledge-mcp-server)
- [ga]: "AWS Knowledge MCP Server now generally available", https://aws.amazon.com/about-aws/whats-new/2025/10/aws-knowledge-mcp-server-generally-available
- [terms]: AWS Site Terms, https://aws.amazon.com/terms/
- [aws-mcp-limits]: AWS MCP Server limits (a different server), https://docs.aws.amazon.com/agent-toolkit/latest/userguide/aws-mcp-limits.html
- Live endpoint: `initialize`, `tools/list`, and `tools/call` on `aws___search_documentation` against `https://knowledge-mcp.global.api.aws`, 2026-11-07

[readme]: https://github.com/awslabs/mcp/tree/main/src/aws-knowledge-mcp-server
[ga]: https://aws.amazon.com/about-aws/whats-new/2025/10/aws-knowledge-mcp-server-generally-available
[terms]: https://aws.amazon.com/terms/
[aws-mcp-limits]: https://docs.aws.amazon.com/agent-toolkit/latest/userguide/aws-mcp-limits.html
