# Research: a local stand-in model for development on a 16 GB CPU host

Ticket: LorexGitHub/guarded-rag#40 (map #34). Feeds #44 "Model tiers and the Bedrock budget" and may reopen ADR 0001. Researched 2026-11-07.

## Question

Which local Ollama model gives the most useful **explain** (per-option cited verdicts as structured output) and **generate** (exam-style questions) output on the dev host (16 GB, 8 threads, no GPU), alongside the rest of the stack? Compare memory, tokens per second, JSON output through the Floci converse proxy, and quality evidence.

## Answer

- **Recommend `qwen3:4b-instruct-2507-q4_K_M` as the dev stand-in**, replacing `llama3.2:3b`. It is the strongest model in the 3 to 4B class on published benchmarks, costs about 0.6 GB more memory than `llama3.2:3b`, and in a small smoke test it cited the right passage for every option. Generation is about 20% slower (12 to 13 vs. 15 to 16 tokens/s, measured).
- **Keep `llama3.2:3b` as the low-memory and fast fallback.** It still returns schema-valid JSON, but in the smoke test it cited the wrong passage for 2 of 12 options, and with a weaker prompt it agreed with the user's wrong answer.
- **Do not use a 7 to 8B model as the default.** `qwen2.5:7b` was the best on quality in the smoke test but runs at about 8 tokens/s, needs about 4.9 GiB, and makes each explain call take about 30 s. Its published scores are also below `qwen3:4b-instruct-2507`. `llama3.1:8b` was not measured. Its published scores are below `qwen2.5:7b` on everything except IFEval.
- **Ask for structured output with `outputConfig.textFormat` (JSON schema), not tool use.** Through Floci and Ollama the schema is enforced. A forced tool call came back with arguments that did not match the schema.
- **The stand-in is for development, not for quality claims.** Score eval quality on Claude on Bedrock, run by hand. The local model only needs to exercise the same code path with plausible output.

## Sources and what they say

### Floci converse proxy (primary: Floci docs)

[Floci Bedrock Runtime docs](https://floci.io/floci/services/bedrock-runtime/):

- The `proxy` backend forwards `Converse` and `ConverseStream` to any OpenAI-compatible `/chat/completions` endpoint and "translates request/response shapes including tool use".
- Translated: `system`, `toolConfig.tools`, `toolConfig.toolChoice`, `inferenceConfig` (`maxTokens`, `temperature`, `topP`, `stopSequences`).
- **`outputConfig.textFormat` with `type: "json_schema"` becomes `response_format.json_schema`.** The proxy does not add OpenAI's `strict` flag and does not validate the response against the schema.
- Model resolution is an explicit `model-mapping` entry first, then the raw id if passthrough is on, then `default-model`. To change the stand-in, set `FLOCI_SERVICES_BEDROCK_RUNTIME_PROXY_DEFAULT_MODEL`. No code changes.
- `InvokeModel` is not proxied (stub only), as ADR 0001 already notes.

### Ollama OpenAI compatibility (primary: Ollama docs)

[Ollama OpenAI compatibility](https://docs.ollama.com/api/openai-compatibility): `/v1/chat/completions` supports `response_format` (JSON mode), `tools` and `reasoning_effort`. **`tool_choice` is listed as unsupported**, so a Bedrock `toolChoice` that forces a specific tool has no effect locally. The local run below confirms this.

### Bedrock structured outputs (primary: AWS docs)

[Bedrock structured outputs](https://docs.aws.amazon.com/bedrock/latest/userguide/structured-output.html):

- Converse uses `outputConfig.textFormat`, the same field Floci translates, so one request shape works in dev and production.
- Supported schema subset: `enum`, `const`, `anyOf`, internal `$ref`, `pattern`, **array `minItems` of 0 or 1 only**. Not supported: `minimum`/`maximum`, `minLength`/`maxLength`, recursion. **Every object must set `additionalProperties: false`** or Bedrock returns a 400 error.
- The first request with a new schema compiles a grammar, which takes up to about 90 s. Set the client read timeout to at least 120 s.
- **Structured outputs cannot be combined with Anthropic citations** (400 error). Explain mode's citations must therefore be a field in our own schema (for example `source`), not Bedrock's citations feature.
- The doc points to a separate model list for which Claude models support it. That list was not checked here (**unverified**: which Bedrock Claude models #44 can pick that support structured outputs).

### Model sizes (primary: Ollama library tag pages)

| Model tag | Download | Context (library) | Source |
|---|---|---|---|
| `llama3.2:3b` | 2.0 GB | 128K | already pulled |
| `qwen3:4b-instruct-2507-q4_K_M` | 2.5 GB | 256K | [qwen3 tags](https://ollama.com/library/qwen3/tags) |
| `gemma3:4b` | 3.4 GB | 128K | [gemma3 tags](https://ollama.com/library/gemma3/tags) (no `tools` capability listed) |
| `qwen2.5:7b` | 4.7 GB | 32K | [qwen2.5 tags](https://ollama.com/library/qwen2.5/tags) |
| `llama3.1:8b` | 4.9 GB | 128K | [llama3.1 tags](https://ollama.com/library/llama3.1/tags) |
| `qwen3:8b` | 5.2 GB | 40K | [qwen3 tags](https://ollama.com/library/qwen3/tags) (a hybrid thinking model, not instruct-only) |

### Published quality evidence (primary: model cards and vendor reports)

The scores are self-reported by each vendor, measured on different harnesses and mostly at full precision, not the Q4 quantization that Ollama ships. Compare within a column only roughly.

| Model | MMLU-Pro | GPQA | IFEval | Function calling | Source |
|---|---|---|---|---|---|
| Llama 3.2 3B Instruct | n/a | 32.8 | 77.4 | BFCL v2 67.0 | [model card](https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct) |
| Llama 3.1 8B Instruct | 48.3 | 32.8 | 75.9 (strict prompt, Qwen's run) / 80.4 (Meta) | BFCL v2 67.1 | Meta card above; [Qwen2.5 blog](https://qwenlm.github.io/blog/qwen2.5-llm/) |
| Qwen2.5 3B Instruct | 43.7 | 30.3 | 58.2 | n/a | [Qwen2.5 blog](https://qwenlm.github.io/blog/qwen2.5-llm/) |
| Qwen2.5 7B Instruct | 56.3 | 36.4 | 71.2 | n/a | [Qwen2.5 blog](https://qwenlm.github.io/blog/qwen2.5-llm/) |
| Gemma 3 4B IT | 43.6 | 30.8 (Diamond) | 90.2 | n/a | [Gemma 3 model card](https://ai.google.dev/gemma/docs/core/model_card_3) |
| **Qwen3 4B Instruct 2507** | **69.6** | **62.0** | 83.4 | BFCL v3 61.9 | [model card](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507) |

- MMLU-Pro and GPQA are the closest public proxies for "knows AWS-exam-style facts and reasons over options". Qwen3-4B-Instruct-2507 leads by a wide margin. The 2507 card also reports Arena-Hard v2 at 43.4, against 9.5 for the original Qwen3-4B non-thinking.
- Qwen3-4B-Instruct-2507 is non-thinking only ("does not generate `<think></think>` blocks"), so it adds no reasoning tokens to latency or to the JSON.
- BFCL v2 and v3 are different benchmarks, so the function-calling column does not compare across rows.
- There is no public benchmark for "SAA-C03 explanation with citations". The project's own eval is the only real test.

### Newer models (not evaluated)

The Ollama library lists newer small models with the `tools` capability ([tools search](https://ollama.com/search?c=tools)), for example `bonsai-2` (2b/4b/9b), `tev1` (4b), `lfm3` (1.7b) and `mimo-v2.6` (9b), all updated within the last month. **Not evaluated.** I found no primary model cards or measurements for them in this pass. Re-check them when the eval exists.

## Local measurements (measured on the dev host)

Host: Intel i5-1135G7 (4 cores / 8 threads), 16 GB, CPU-only Ollama 0.40.15 in the Compose `ollama` container, default context 4096. The host was busy: a kind cluster (about 1.4 GiB), a desktop and the guarded-rag stack were running, swap was partly used, and available memory was 2.5 to 5.5 GB. `llama3.2:3b` and `nomic-embed-text` were unloaded for each run, then restored afterwards. The candidate models were deleted afterwards.

Script: [`local-stand-in-model-bench.py`](local-stand-in-model-bench.py). For each model it sends 3 hand-written SAA-style explain cases (4 context passages, 4 options, a wrong user answer, temperature 0) through Ollama's `/v1/chat/completions` with `response_format: json_schema`, which is exactly what Floci sends. It then times one explain prompt (uncached) and one generate prompt through `/api/chat`.

| Model | Resident (`ollama ps`, ctx 4096) | Container RSS | Load | Prompt eval | Generation | Explain call (about 200 to 270 output tokens) | Generate call |
|---|---|---|---|---|---|---|---|
| `llama3.2:3b` | 2.6 GB | 2.78 GiB | warm | 80 tok/s | 15.9 tok/s | 12 to 14 s | 15.8 s, 240 tok |
| `qwen3:4b-instruct-2507-q4_K_M` | 3.2 GB | 3.34 GiB | 3.5 s | 57 tok/s | 12.4 tok/s | 20 to 26 s | 17.0 s, 214 tok |
| `qwen2.5:7b` | 5.1 GB | 4.86 GiB | 6.5 s | 34 tok/s | 7.8 tok/s | 28 to 35 s | 20.7 s, 147 tok |

Explain smoke test (3 cases, 12 option verdicts per model; **too small to rank models, treat as a sanity check**):

| Model | Valid JSON | All 4 options | Correct option marked | Right source cited per option |
|---|---|---|---|---|
| `llama3.2:3b` | 3/3 | 3/3 | 3/3 | 10/12 (cited `s1` twice for an option supported by `s2`) |
| `qwen3:4b-instruct-2507-q4_K_M` | 3/3 | 3/3 | 3/3 | 12/12 |
| `qwen2.5:7b` | 3/3 | 3/3 | 3/3 | 12/12 |

Generate (one SQS vs. SNS question each, read by hand):

- `llama3.2:3b`: two options are both defensible (B and D both say "use SNS"), so the question is ambiguous.
- `qwen3:4b-instruct-2507`: answer B is right, but the scenario asks for "ordered" delivery, which SNS standard topics do not give. The question is usable after a check.
- `qwen2.5:7b`: the classic SNS-to-SQS fan-out, with a clean single answer.

All three need the planned "checked by explain" step. None is reliable enough to skip it.

### Through Floci itself (measured, `llama3.2:3b`, which is what the running stack maps to)

- `converse` with `outputConfig.textFormat` (json_schema with `enum`s, Bedrock-subset form with `additionalProperties: false` and `minItems: 1`): the response text was pure JSON that matched the schema, latency 4.3 to 7.1 s. **The proxy and schema path works end to end.**
- The same request without `outputConfig`: free text ("Verdict: Incorrect\nReason: ..."). The schema is what makes the JSON.
- The same request with `toolConfig` and `toolChoice: {tool: record_verdicts}` instead: Floci returned a proper `toolUse` block with `stopReason: tool_use`, **but the input broke the schema**: `verdicts` was a JSON string, not an array, and `reason` and `source` were swapped. Ollama does not constrain tool arguments with the schema, and it ignores `tool_choice`.
- With a weaker system prompt (it did not say "judge every option" or "do not trust the user's answer"), `llama3.2:3b` returned only one verdict and marked the user's wrong answer C as correct. The schema allows that, because Bedrock only permits `minItems` 0 or 1. **Encode "all four options" in the schema shape, not in `minItems`**: use an object with required keys `A`, `B`, `C`, `D` (plus `additionalProperties: false`), which both Bedrock and Ollama can enforce.
- Other models were not run through Floci, because that needs a Compose env change (`PROXY_DEFAULT_MODEL`). The Ollama `/v1` path that the bench used is the same backend endpoint that Floci calls.

## Memory budget impact (ADR 0001 table, generation row swapped)

| Component | `llama3.2:3b` | `qwen3:4b-instruct-2507` | `qwen2.5:7b` |
|---|---|---|---|
| Floci + OpenSearch (512 MB heap), measured in spike | 1.0 GiB | 1.0 GiB | 1.0 GiB |
| `nomic-embed-text`, measured here (`ollama ps`) | 0.39 GB | 0.39 GB | 0.39 GB |
| Generation model, measured here | 2.6 GB | 3.2 GB | 5.1 GB |
| Lambda containers | unmeasured | unmeasured | unmeasured |
| **Total excluding Lambdas** | **about 4.0 GB** | **about 4.6 GB** | **about 6.5 GB** |

ADR 0001's "switch down" trigger is about 8 GiB total. `qwen3:4b-instruct-2507` leaves room for Lambdas. `qwen2.5:7b` would reach the trigger once the Lambdas are counted.

- **Context length.** Ollama ran at context 4096 here. An explain prompt with several retrieved AWS doc chunks may exceed it, and Ollama then truncates the prompt. If explain prompts grow, set `OLLAMA_CONTEXT_LENGTH` (for example 8192). This raises KV-cache memory by an amount I did not measure (**unverified**).
- **CI (estimate, not measured).** The free runner is 4 vCPU / 16 GB. The measure workflow got 5 to 15 s per `llama3.2:3b` call on it, similar to this host, so expect `qwen3:4b-instruct-2507` explain calls of about 20 to 30 s there. A 30-case explain eval would take roughly 10 to 15 minutes, past ADR 0008's roughly 10-minute trigger. Options: run a smaller CI subset, keep `llama3.2:3b` for CI, or cap `maxTokens`. Runner download is 2.5 GB (about 0.5 GB more than now).

## Recommendation for the decisions this feeds

- **#44 (model tiers), "which local model stands in on Floci":** `qwen3:4b-instruct-2507-q4_K_M` for local development, set through `FLOCI_SERVICES_BEDROCK_RUNTIME_PROXY_DEFAULT_MODEL`. `llama3.2:3b` stays as the named fallback (memory pressure, or a CI-time trigger). This supersedes ADR 0001 decision 3 (models), and ADR 0001's `qwen2.5:1.5b` fallback falls away. Record it as a new or updated ADR.
- **Explain and generate request shape:** use `outputConfig.textFormat` json_schema in the Bedrock subset (`additionalProperties: false` on every object, no `minItems` above 1, options as required keys `A` to `D`, citation as a schema field). Do not use tool use or Anthropic citations for the verdicts. Validate the JSON in the app anyway, because Floci does not validate it.
- **Eval:** score quality claims on Bedrock Claude. Use the local model to test the pipeline and as a rough floor.

## Not verified

- Which Bedrock Claude models support `outputConfig.textFormat` (the AWS model list page was not read).
- `llama3.1:8b`, `gemma3:4b` and `qwen3:8b` were not measured locally (published numbers only).
- The newer library models (`bonsai-2`, `tev1`, `lfm3`, `mimo-v2.6`) were not evaluated.
- Latency on the CI runner for any model except `llama3.2:3b`. KV-cache memory at a context above 4096.
- Quality beyond a 3-case smoke test. All local numbers are single runs on a busy host.
