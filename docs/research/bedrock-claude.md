# Research: Claude on Bedrock (models, access, cost, Terraform)

Issue: LorexGitHub/guarded-rag#38 (map #34). Researched on 2026-11-07. Feeds #44 and #45.
All prices are in USD and dated 2026-11-07. Items marked **UNVERIFIED** could not be confirmed from a primary source.

## Short answer

- **Models:** Claude Haiku 5.5, Sonnet 5.5 and Opus 5.5 are on Bedrock with an `eu.` geo inference profile that keeps traffic inside EU regions. Fable 5.1 has no EU geo profile (global only), and Mythos is gated.
- **Access:** no console "model access" page any more. Access starts on first call, but Anthropic needs a one-time use-case form per account. Terraform can submit it (`aws_bedrock_use_case_for_model_access`), but only on provider **6.53.0+**, and `infra/` is pinned to `~> 5.0`.
- **Cost of one eval run** (165 calls, assumptions below): about **$0.15 on Haiku 5.5** and about **$5.80 on Opus 5.5** through the EU profile. If thinking doubles the output tokens, those become about $0.22 and $8.70.
- **Free credits:** new accounts get $100 (up to $200) in credits, but Claude on Bedrock is billed through AWS Marketplace, and the credit terms exclude Marketplace. Plan for Claude to be paid in cash. **UNVERIFIED** in practice.
- **Terraform:** IAM uses `bedrock:InvokeModel`, scoped to the inference-profile ARN plus the foundation-model ARN in every destination region. Use `aws_budgets_budget` for alerts and `aws_budgets_budget_action` with an IAM deny policy as the kill switch.
- **Floci:** the proxy forwards `system`, `toolConfig`, `inferenceConfig` and `outputConfig.textFormat` (JSON schema) to Ollama. Ollama ignores `tool_choice`, and Floci does not guarantee schema adherence. Use structured outputs, not forced tool use, and validate the JSON in our code.

## 1. Models and regions

Source: Bedrock "Models at a glance" and the per-model cards ([index](https://docs.aws.amazon.com/bedrock/latest/userguide/model-cards.html)).

Claude models listed on Bedrock: 5.x (Haiku 5.5, Sonnet 5.5, Opus 5.5, Fable 5.1, Mythos 5.1, Opus 5, Sonnet 5, Mythos 5, Fable 5), 4.x (Opus 4.8/4.7/4.6/4.5/4.1, Sonnet 4.6/4.5/4, Haiku 4.5) and Claude 3 Haiku.

The candidates for this app:

| Model | Bedrock model ID | EU geo profile | In-Region in EU | Notes |
|---|---|---|---|---|
| Haiku 5.5 (launched 2026-10-07) | `anthropic.claude-haiku-5-5` | `eu.anthropic.claude-haiku-5-5` | none | Adaptive thinking on by default, can be turned off. Structured outputs and tool calling supported. [card](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-haiku-5-5.html) |
| Sonnet 5.5 (2026-09-28) | `anthropic.claude-sonnet-5-5` | `eu.anthropic.claude-sonnet-5-5` | none | Thinking cannot be fully disabled. `tool_choice` supports `auto` and `none` only. [card](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-sonnet-5-5.html) |
| Opus 5.5 (2026-09-22) | `anthropic.claude-opus-5-5` | `eu.anthropic.claude-opus-5-5` | eu-west-2 (London) only | Thinking always on. `tool_choice` supports `auto` and `none` only. [card](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-opus-5-5.html) |
| Fable 5.1 (2026-09-01) | `anthropic.claude-fable-5-1` | **none** (EU regions get `global.` only) | none | Requires opting in to `aws_review` data retention. Refusal rates are "materially higher". [card](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-fable-5-1.html) |
| Mythos 5.1 | — | — | — | Non-GA and gated: "contact your Anthropic account team" ([pricing page](https://aws.amazon.com/bedrock/pricing/)). |

**EU geo routing.** Called from eu-central-1 (Frankfurt) or eu-west-1 (Ireland), the `eu.` profile routes to Frankfurt, Stockholm, Milan, Spain, Ireland and Paris. Called from eu-west-2 (London), it also includes London. The same table applies to Haiku, Sonnet and Opus 5.5. The `global.` profile is cheaper (see §3) but can route anywhere in the world.

All three cards list Converse as supported on the `bedrock-runtime` endpoint, which is the API `src/guarded_rag/bedrock_llm.py` already calls.

**Model ID change for our code:** on real Bedrock the `modelId` must be the inference profile ID (for example `eu.anthropic.claude-haiku-5-5`), not the bare model ID. The bare ID works only In-Region, and only Opus 5.5 in London has In-Region. Floci accepts any ID (spike), so this is configuration only.

## 2. Model access, and whether Terraform can grant it

Source: [Request access to models](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html).

- In commercial regions there is no access request any more. "Access to many Amazon Bedrock foundation models is enabled by default with the correct AWS Marketplace permissions." The first call starts a Marketplace subscription in the background, which takes up to 15 minutes.
- Prerequisites for that first call:
  1. The caller needs `aws-marketplace:Subscribe`, `aws-marketplace:Unsubscribe` and `aws-marketplace:ViewSubscriptions`. These are only needed for the first use. After that, the Lambda role needs only `bedrock:InvokeModel`.
  2. **Anthropic only:** submit the First Time Use (FTU) form once per account, via the console or `PutUseCaseForModelAccess`. "If you are an individual developer or student without a company website, you can provide a personal portfolio, GitHub profile, or project URL." The agreement can sit in `PENDING` for a while. Check it with `GetFoundationModelAvailability`.
  3. A valid payment method for Marketplace purchases.
- **Terraform** ([provider docs](https://github.com/hashicorp/terraform-provider-aws/tree/main/website/docs/r)):
  - `aws_bedrock_use_case_for_model_access` (argument `form_data = jsonencode({...})`) submits the FTU form. It adopts an existing submission. It cannot be updated, and `terraform destroy` only drops it from state.
  - `aws_bedrock_foundation_model_agreement` plus the data source `aws_bedrock_foundation_model_agreement_offers` creates the Marketplace agreement explicitly. It is optional, because the first invocation does the same thing.
  - Both were **added in provider v6.53.0 (2026-07-01)** ([CHANGELOG](https://github.com/hashicorp/terraform-provider-aws/blob/main/CHANGELOG.md)). The latest provider is v6.72.0 (2026-11-04). `infra/main.tf` pins `hashicorp/aws ~> 5.0` for the OpenSearch `timeouts` workaround (ADR 0004). **Conflict:** the real-AWS stack either needs its own root module on 6.x, or the repo moves to 6.x and re-tests the OpenSearch wait workaround on Floci (spike notes say the workaround relies on v5.x behaviour).
- Simplest path for one user: fill in the FTU form once in the console and leave it out of Terraform. It is a one-time, per-account step that Terraform cannot really destroy anyway.

## 3. Cost of one eval run

### Prices (USD per million tokens, list price, 2026-11-07)

Source: Anthropic's [pricing page](https://platform.claude.com/docs/en/about-claude/pricing). The AWS [Bedrock pricing page](https://aws.amazon.com/bedrock/pricing/) loads its Anthropic table with JavaScript, and the fetch returned no figures. Anthropic's page says that for Haiku 4.5, Opus 4.5 and later on Bedrock, "Regional and multi-region endpoints include a 10 percent premium over global endpoints." **UNVERIFIED:** that the AWS-published Bedrock figures equal Anthropic's list prices. Third-party trackers show Haiku 4.5 EU at $1.10/$5.50, which is list price plus 10%, so they agree.

| Model | Input (global) | Output (global) | Input (`eu.`, +10%) | Output (`eu.`, +10%) |
|---|---|---|---|---|
| Haiku 5.5 (prompt ≤100k tokens) | $0.10 | $0.50 | $0.11 | $0.55 |
| Haiku 4.5 | $1.00 | $5.00 | $1.10 | $5.50 |
| Sonnet 5.5 | $2.00 | $10.00 | $2.20 | $11.00 |
| Opus 5.5 | $4.00 | $20.00 | $4.40 | $22.00 |
| Fable 5.1 (global only in the EU) | $10.00 | $50.00 | n/a | n/a |

Cache reads cost 0.1× the input price, or 0.05× on Sonnet 5.5 and Opus 5.5. Haiku 5.5 charges more for prompts over 100k tokens, which we will not reach.

### Assumptions

- One eval run = 65 explain calls + 50 generate-plus-check pairs (2 calls each) = **165 calls**.
- Each call: **~4,000 input tokens** (system prompt, retrieved AWS doc chunks, question and options) and **~800 output tokens** (per-option verdicts with citations). Generate calls use the same numbers for simplicity.
- Thinking tokens are billed as output. Sonnet 5.5 and Opus 5.5 always think, so the table shows a second column with output doubled (1,600 tokens per call).
- No prompt caching and no retries.
- Token counts are in Claude tokens. Anthropic notes that Claude 4.7+ models "produce approximately 30% more tokens for the same text" than older models, so measure real counts on the first run.

Totals: input = 165 × 4,000 = 660,000 tokens (0.66 MTok). Output = 165 × 800 = 132,000 tokens (0.132 MTok).

### Calculation

Formula: `0.66 × input price + 0.132 × output price`.

| Model | Global | `eu.` profile | `eu.`, output ×2 (thinking) |
|---|---|---|---|
| **Haiku 5.5 (cheapest suitable)** | 0.066 + 0.066 = **$0.13** | **$0.15** | $0.22 |
| Haiku 4.5 | $1.32 | $1.45 | $2.18 |
| Sonnet 5.5 | $2.64 | $2.90 | $4.36 |
| **Opus 5.5 (strongest with an EU profile)** | 2.64 + 2.64 = **$5.28** | **$5.81** | $8.71 |
| Fable 5.1 (global only) | $13.20 | n/a | $21.78 (global, output ×2) |

So ten full eval runs on Opus 5.5 cost roughly $60–90, and on Haiku 5.5 about $1.50–2.20. A daily habit of 30 explain calls on Haiku 5.5 is about 30 × (0.004 × 0.11 + 0.0008 × 0.55) ≈ **$0.03 a day**.

Other AWS costs (Lambda, API Gateway, S3) are outside this ticket. OpenSearch is likely the largest of them and belongs to the deployment ticket.

## 4. Free credits for new accounts

- [AWS Free Tier](https://aws.amazon.com/free/): new accounts get **$100 at sign-up**, plus up to $100 more for exploring services (five $20 activities, one of which is a prompt in the Bedrock playground, per the [AWS News Blog](https://aws.amazon.com/blogs/aws/aws-free-tier-update-new-customers-can-get-started-and-explore-aws-with-up-to-200-in-credits)). The free plan "closes on its own 6 months after you open it or when your credits run out", and it is "Limited to select services only". The paid plan gets the same credits.
- **Claude is probably not covered.** Every Claude model card says: "This model is a third-party model offered and billed through AWS Marketplace. Charges appear ... under the model provider (not under Amazon Bedrock)." The [AWS Promotional Credit Terms](https://aws.amazon.com/awscredits/) state: "Unless authorized by us, Promotional Credit will not be applied to any fees or charges for ... AWS Marketplace". AWS re:Post answers agree. **UNVERIFIED:** no AWS page says explicitly whether Free Tier credits cover Claude on Bedrock. Check the Billing console after the first real call.
- Practical reading: the credits will absorb the AWS-native parts (Lambda, S3, API Gateway, maybe OpenSearch), and Claude tokens go to the card. At the numbers in §3 that is small, so the budget alarm matters more than credits.
- The free plan may not allow Bedrock or Marketplace at all, since Bedrock's card on the Free Tier page lacks the "Available on both plans" label. **UNVERIFIED.** Expect to need the paid plan.

## 5. Terraform for IAM and the budget alarm

### IAM for `bedrock:Converse`

[Converse](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Converse.html): "This operation requires permission for the `bedrock:InvokeModel` action." There is no separate `bedrock:Converse` action. A cross-region profile needs both the profile ARN and the foundation-model ARN **in every destination region** ([inference profile prerequisites](https://docs.aws.amazon.com/bedrock/latest/userguide/inference-profiles-prereq.html)):

```hcl
locals {
  model   = "anthropic.claude-haiku-5-5"
  profile = "eu.${local.model}"
}

data "aws_iam_policy_document" "bedrock_invoke" {
  statement {
    actions   = ["bedrock:InvokeModel"]
    resources = ["arn:aws:bedrock:${var.region}:${data.aws_caller_identity.me.account_id}:inference-profile/${local.profile}"]
  }
  statement {
    actions   = ["bedrock:InvokeModel"]
    # Any EU region the profile may route to (see §1); region wildcard keeps it short.
    resources = ["arn:aws:bedrock:eu-*::foundation-model/${local.model}"]
    condition {
      test     = "StringLike"
      variable = "bedrock:InferenceProfileArn"
      values   = ["arn:aws:bedrock:${var.region}:${data.aws_caller_identity.me.account_id}:inference-profile/${local.profile}"]
    }
  }
}
```

Attach the policy with `aws_iam_role_policy` on the query Lambda's role. The documented examples list regions one by one. The `eu-*` wildcard in the region field is **UNVERIFIED**. Listing the six or seven regions from §1 is the safe form. `global.` profiles also need the region-less ARN `arn:aws:bedrock:::foundation-model/<model>`, and AWS documents a Deny on `aws:RequestedRegion = "unspecified"` to block global routing.

Add `bedrock:InvokeModelWithResponseStream` only if we stream. The first-ever call also needs the `aws-marketplace:*` permissions listed in §2. Make that call by hand from an admin identity, not from the Lambda.

### Budget alarm

[`aws_budgets_budget`](https://github.com/hashicorp/terraform-provider-aws/blob/main/website/docs/r/budgets_budget.html.markdown) creates a monthly `COST` budget. Use one `notification` block per threshold, each with `subscriber_email_addresses`:

```hcl
resource "aws_budgets_budget" "monthly" {
  name         = "guarded-rag-monthly"
  budget_type  = "COST"
  limit_amount = "10"
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 50
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.alert_email]
  }
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = [var.alert_email]
  }
}
```

Facts that limit how useful it is ([AWS Budgets docs](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html)):

- "AWS Budgets information is updated up to three times a day. Updates typically occur 8–12 hours after the previous update." A budget is an alarm, not a hard cap. A runaway loop can overspend before the email arrives.
- A kill switch is possible: [`aws_budgets_budget_action`](https://github.com/hashicorp/terraform-provider-aws/blob/main/website/docs/r/budgets_budget_action.html.markdown) with `action_type = "APPLY_IAM_POLICY"` and `approval_model = "AUTOMATIC"` can attach a deny-`bedrock:InvokeModel*` policy to the Lambda role when a threshold is crossed. It inherits the same 8–12 h lag. It needs an execution role that `budgets.amazonaws.com` can assume.
- [Pricing](https://aws.amazon.com/aws-cost-management/aws-budgets/pricing/): monitoring and notifications are free. "Your first two action-enabled budgets are free", and each one after that costs $0.10 a day.
- Because Claude charges appear "under the model provider (not under Amazon Bedrock)", a budget filtered on `Service = Amazon Bedrock` would probably miss them. Keep the budget unfiltered, covering the whole account. **UNVERIFIED** which service name Claude charges carry in Cost Explorer.
- The cheapest real guard is in our own code: a per-run call counter and `maxTokens` on every Converse call.

## 6. Does Floci's converse proxy accept what real Claude needs?

Sources: Floci's [bedrock-runtime docs](https://github.com/floci-io/floci/blob/main/docs/services/bedrock-runtime.md) (latest release 2.4.0, 2026-10-31, which includes the structured-output change #5512 from 2026-10-12) and Ollama's [OpenAI compatibility](https://docs.ollama.com/api/openai-compatibility).

| Request shape | Floci proxy | Ollama `/v1/chat/completions` | Real Bedrock Claude 5.5 |
|---|---|---|---|
| `system` | Forwarded | Yes | Yes |
| `inferenceConfig` (maxTokens, temperature, topP, stopSequences) | Forwarded | Yes | Yes. Fable 5.1 restricts temperature and top_p |
| `toolConfig.tools` | Forwarded | `tools` supported | Yes |
| `toolConfig.toolChoice` | Forwarded | **`tool_choice` not supported** (ignored) | Sonnet 5.5 and Opus 5.5 accept `auto` and `none` only |
| `outputConfig.textFormat` `json_schema` (structured outputs) | Translated to `response_format.json_schema`, without the `strict` flag | `response_format` supported (JSON mode) | Supported on Haiku, Sonnet and Opus 5.5 |
| `outputConfig.effort` | Translated to `reasoning_effort` | Supported (model-defined) | Supported (low…max) |
| `InvokeModel` | **Stub only**, not proxied | — | — |

Conclusions:

- **Use structured outputs (`outputConfig.textFormat` with a JSON schema) for the explain verdicts and generated questions. Do not use forced tool use.** Forced `toolChoice` is ignored by Ollama and is unavailable on Sonnet 5.5 and Opus 5.5.
- Floci "does not emulate Bedrock's guaranteed schema adherence", so the code must parse and validate the JSON anyway. Keep a validation step in the domain code.
- Keep using Converse, not InvokeModel, because only Converse is proxied.
- **Not tested here:** whether `llama3.2:3b` in Ollama follows a JSON schema through this path. The spike (docs/spike.md) only verified plain text. One curl with `outputConfig` against the running stack would settle it.

## Recommendations for the decisions this feeds

1. **Default model: Haiku 5.5 through `eu.anthropic.claude-haiku-5-5`, from eu-central-1 or eu-west-1.** A full eval run costs about $0.15. Use **Opus 5.5 (`eu.`) as the "strongest" comparison** for occasional eval runs at about $6–9. Skip Fable 5.1 and Mythos (no EU profile, gated, data-retention opt-in).
2. **Make the model ID configuration** (an environment variable such as `BEDROCK_MODEL_ID`). Floci ignores it, and real AWS needs the `eu.` profile ID.
3. **Use structured outputs with schema validation in code** as the contract for both explain and generate. This works on Floci, Ollama and real Claude.
4. **Real-AWS Terraform:** use a separate root module (for example `infra/aws/`) on `hashicorp/aws ~> 6.53`, so the Floci stack stays on 5.x. It should hold the IAM policy above, an unfiltered `aws_budgets_budget` (around $10/month, 50% actual and 100% forecast), and optionally one `aws_budgets_budget_action` kill switch (free). Fill in the Anthropic FTU form by hand once. Use `aws_bedrock_use_case_for_model_access` only if we want it recorded in code.
5. **Do not count on free credits for Claude.** Budget a few dollars a month of real money, and add an in-code call and token cap, because the budget alarm lags by 8–12 hours.
