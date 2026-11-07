"""Smoke bench: explain (per-option verdicts, JSON schema) and generate, via Ollama.

Explain goes through /v1/chat/completions with response_format json_schema, which is
what Floci's converse proxy sends. Timing comes from native /api/chat (eval_count,
eval_duration) using the same schema as `format`.
"""
import json, sys, time, urllib.request

OLLAMA = "http://localhost:11434"
MODEL = sys.argv[1]

VERDICT_SCHEMA = {
    "type": "object",
    "properties": {
        "verdicts": {
            "type": "array", "minItems": 4, "maxItems": 4,
            "items": {
                "type": "object",
                "properties": {
                    "option": {"type": "string", "enum": ["A", "B", "C", "D"]},
                    "verdict": {"type": "string", "enum": ["correct", "incorrect"]},
                    "reason": {"type": "string"},
                    "source": {"type": "string"},
                },
                "required": ["option", "verdict", "reason", "source"],
            },
        }
    },
    "required": ["verdicts"],
}

SYSTEM = ("You are an AWS SAA-C03 tutor. Judge every option A to D independently. "
          "Exactly one option is correct. For each option give verdict correct or incorrect, "
          "a one-sentence reason, and the id of the context passage that supports it (e.g. s1). "
          "Use only the context. Do not trust the user's answer.")

CASES = [
    ("B", "[s1] S3 Glacier Deep Archive is the lowest-cost S3 storage class, for data retained 7 to 10 years or longer; standard retrieval completes within 12 hours.\n"
          "[s2] S3 Standard-IA is for data accessed less frequently but requiring rapid access, with millisecond retrieval.\n"
          "[s3] S3 Intelligent-Tiering automatically moves objects between access tiers when access patterns change, for a small monthly monitoring fee.\n"
          "[s4] S3 Standard is for frequently accessed data.",
     "A company must keep compliance archives for 7 years at the lowest possible cost. Retrieval within 24 hours is acceptable. Which storage class should it use?\n"
     "A. S3 Standard-IA\nB. S3 Glacier Deep Archive\nC. S3 Intelligent-Tiering\nD. S3 Standard\nUser answer: C"),
    ("D", "[s1] A NAT gateway lets instances in a private subnet connect to the internet, but the internet cannot initiate connections to them.\n"
          "[s2] An internet gateway allows resources in a public subnet with public IPs to connect to the internet and be reached from it.\n"
          "[s3] A gateway VPC endpoint provides private connectivity to Amazon S3 and DynamoDB without an internet gateway or NAT device.\n"
          "[s4] Security groups are stateful and control traffic at the instance level.",
     "EC2 instances in a private subnet must read objects from Amazon S3. Traffic must not traverse the internet and the solution should be cheapest. What should a solutions architect do?\n"
     "A. Add a NAT gateway in a public subnet\nB. Attach an internet gateway and give instances public IPs\nC. Open the security group to 0.0.0.0/0\nD. Create a gateway VPC endpoint for S3\nUser answer: A"),
    ("A", "[s1] Amazon RDS Multi-AZ deployments maintain a synchronous standby in a different Availability Zone and fail over automatically.\n"
          "[s2] RDS read replicas use asynchronous replication and are used to scale read traffic; promotion is manual.\n"
          "[s3] Automated backups enable point-in-time recovery within the retention period.\n"
          "[s4] Amazon ElastiCache is an in-memory cache.",
     "A database on Amazon RDS must stay available if an Availability Zone fails, with automatic failover. What should be enabled?\n"
     "A. Multi-AZ deployment\nB. A read replica in the same AZ\nC. Automated backups\nD. An ElastiCache cluster\nUser answer: B"),
]

GEN_PROMPT = ("Write one AWS SAA-C03 style multiple-choice question about choosing between SQS and SNS. "
              "Give a 2-sentence scenario, options A to D, the correct letter and a one-sentence explanation.")


def post(path, body):
    req = urllib.request.Request(OLLAMA + path, json.dumps(body).encode(), {"content-type": "application/json"})
    t = time.time()
    with urllib.request.urlopen(req, timeout=900) as r:
        return json.load(r), time.time() - t


def msgs(ctx, q):
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": f"Context:\n{ctx}\n\nQuestion: {q}"}]


out = {"model": MODEL, "explain": [], "generate": None}

# load (cold) timing
_, load_s = post("/api/generate", {"model": MODEL, "prompt": "", "keep_alive": "10m"})
out["load_s"] = round(load_s, 1)

for want, ctx, q in CASES:
    # OpenAI-compatible path, as Floci forwards it
    v1, wall = post("/v1/chat/completions", {
        "model": MODEL, "messages": msgs(ctx, q), "temperature": 0, "max_tokens": 600,
        "response_format": {"type": "json_schema", "json_schema": {"name": "verdicts", "schema": VERDICT_SCHEMA}},
    })
    text = v1["choices"][0]["message"]["content"]
    rec = {"want": want, "wall_s": round(wall, 1), "out_tokens": v1["usage"]["completion_tokens"]}
    try:
        data = json.loads(text)
        vs = data["verdicts"]
        rec["json_ok"] = True
        rec["options"] = [v["option"] for v in vs]
        correct = [v["option"] for v in vs if v["verdict"] == "correct"]
        rec["marked_correct"] = correct
        rec["right"] = correct == [want] and sorted(rec["options"]) == ["A", "B", "C", "D"]
        rec["sources"] = [v["source"] for v in vs]
    except Exception as e:  # noqa: BLE001
        rec["json_ok"] = False
        rec["raw"] = text[:300]
    out["explain"].append(rec)

# native path for token rates (same first case)
want, ctx, q = CASES[0]
nat, _ = post("/api/chat", {"model": MODEL, "messages": [{"role": "system", "content": "Timing run " + str(time.time()) + ". " + SYSTEM}] + msgs(ctx, q)[1:], "stream": False, "format": VERDICT_SCHEMA,
                            "options": {"temperature": 0, "num_predict": 600}})
out["prompt_tok_s"] = round(nat["prompt_eval_count"] / (nat["prompt_eval_duration"] / 1e9), 1)
out["gen_tok_s"] = round(nat["eval_count"] / (nat["eval_duration"] / 1e9), 1)

g, wall = post("/api/chat", {"model": MODEL, "messages": [{"role": "user", "content": GEN_PROMPT}], "stream": False,
                             "options": {"temperature": 0.7, "num_predict": 400}})
out["generate"] = {"wall_s": round(wall, 1), "tokens": g["eval_count"],
                   "tok_s": round(g["eval_count"] / (g["eval_duration"] / 1e9), 1),
                   "text": g["message"]["content"]}
print(json.dumps(out, indent=1))
