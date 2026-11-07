# Free, legal SAA-C03 sources and how to fetch them

Research for LorexGitHub/guarded-rag#37 (map #34). Checked on 2026-11-07. Feeds #43 (where retrieval comes from) and #48 (eval v2).

Labels: **verified** means read on the AWS-owned source named in the row. **Unverified** means only seen on third-party pages or not checkable without logging in.

## Short answer

- The **docs.aws.amazon.com** content is the safe core of the corpus. The AWS Site Terms say documentation there is licensed under **CC-BY-SA-4.0**, and code samples in it under **MIT-0**. That covers user guides, the Well-Architected Framework and pillars, and whitepapers hosted under `docs.aws.amazon.com/whitepapers/`. Every guide has a sitemap, an `llms.txt` file and a Markdown version of each page (`<page>.md`), so a polite fetcher can get clean text without scraping HTML.
- **aws.amazon.com** (service FAQs, product pages, certification pages, and the `d1.awsstatic.com` PDFs) falls under the general Site Terms: a "limited license to access and make personal use", no downloading "other than page caching" without written consent, no "derivative use", and no "data mining, robots, or similar data gathering and extraction tools". Indexing FAQs with a crawler conflicts with that wording. Read them live or by hand instead.
- The **official sample questions** are a 10-question, 5-page PDF with an answer key and a short explanation per question. They are a fine personal eval set. They are under the Site Terms, not CC-BY-SA, so do not commit the text to this public repo: fetch at eval time into a gitignored folder.
- The **Skill Builder Official Practice Question Set** (20 questions, free with a Skill Builder account) is for use by hand only. I found no export and no license that allows copying.

## Exam facts (verified)

Source: the HTML exam guide at <https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html>, and the certification page <https://aws.amazon.com/certification/certified-solutions-architect-associate/>.

- 65 questions: 50 scored and 15 unscored (the unscored ones are not marked). 130 minutes, 150 USD.
- Scaled score 100 to 1,000, pass mark 720, compensatory scoring (no per-domain minimum).
- Two question types: **multiple choice** (1 correct answer, 3 distractors) and **multiple response** (2 or more correct answers out of 5 or more options). No penalty for guessing.
- Domains and weights (share of scored content):

| Domain | Weight |
| --- | --- |
| 1. Design Secure Architectures | 30% |
| 2. Design Resilient Architectures | 26% |
| 3. Design High-Performing Architectures | 24% |
| 4. Design Cost-Optimized Architectures | 20% |

- The certification page mentions no SAA-C04. It does say the Italian-language exam retires after 2026-12-31, and that the exam now uses short names for some services (a list is available from the Help button during the exam).

## Sources

### 1. Exam guide (verified)

- **HTML (current):** <https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html>. One page per domain (task statements, "Knowledge of" and "Skills in" bullets), plus pages for technologies and concepts, service mentions, in-scope services, out-of-scope services, and revisions.
- **License:** it is on docs.aws.amazon.com, so CC-BY-SA-4.0 under the Site Terms. It may be indexed, and it may be committed with attribution.
- **Size:** small. The PDF version is 23 pages and about 4,000 words.
- **In-scope services:** 16 categories and about 118 services (Redshift is listed under both Analytics and Database). The page itself says the list is "non-exhaustive and is subject to change". This list is the natural scope filter for which user guides to ingest.
- **Revisions page:** lists version 1.0 (2026-08-28) and 1.1 (2026-10-29). Changes: Amazon Elastic Transcoder removed from the in-scope list; DeepComposer, DevOps Guru, Elastic Inference, Managed Blockchain and Sumerian removed from the out-of-scope list. AWS says it publishes guide updates about one month before they reach the exam. (These dates are as shown on the page; they look like a re-dated docs version, because the PDF below is also labelled 1.1 and was last modified in 2025.)
- **PDF (older copy):** <https://d1.awsstatic.com/training-and-certification/docs-sa-assoc/AWS-Certified-Solutions-Architect-Associate_Exam-Guide.pdf>, 180 KB, 23 pages, "Version 1.1 SAA-C03", last modified 2025-02-07. It is on awsstatic, so Site Terms apply. Prefer the HTML guide.
- **Fetch:** the guide's pages, by URL (`.md` variant confirmed for the main page: `.../solutions-architect-associate-03.md`) or through the AWS Knowledge MCP `read_documentation` tool.
- **Whitepapers:** the SAA-C03 guide does **not** list recommended whitepapers. A search of the PDF text for "whitepaper" found nothing. It names the Well-Architected Framework as the basis of the exam and lists the Well-Architected Tool as in scope.

### 2. Official sample questions (verified)

- **URL:** <https://d1.awsstatic.com/training-and-certification/docs-sa-assoc/AWS-Certified-Solutions-Architect-Associate_Sample-Questions.pdf> (189 KB, 5 pages, © 2022, created 2022-02-17).
- **Count and format:** 10 questions. 7 are multiple choice with options A to D; 3 are "Select TWO" with options A to E (questions 1, 5 and 8). The last page is an answer key, with 1 to 7 sentences of explanation per question. The explanations mostly justify the correct option; a few say why a distractor is wrong (question 6 explains why Spot Instances are wrong). Questions carry **no domain tags**.
- **Topics:** NAT gateway routing, EC2 hibernation, moving an ENI to a standby instance, S3 CORS, SSE-C and client-side encryption, On-Demand for a job that cannot be interrupted, SQS buffering in front of RDS, Multi-AZ with ALB and RDS, Auto Scaling warm-up, Aurora replicas.
- **License:** Site Terms (personal use). Not CC-BY-SA.
- **Fetch:** plain HTTPS GET, then `pdftotext -layout`. The layout is regular: `N) stem`, then indented `A) ... E)`, then `Answers` with `N) X, Y – explanation`. A small parser can turn this into eval cases.
- **Caveat:** the questions are from 2022. AWS facts can drift (for example, whether an answer is still the cheapest option). Check each case against the current docs before using it as gold.

### 3. Skill Builder Official Practice Question Set (partly verified)

- **Verified** (<https://aws.amazon.com/certification/certification-prep/>): the Official Practice Question Sets are "Free on AWS Skill Builder". They are "20-question sets, developed by AWS" with "detailed feedback and recommended resources". The full-length Official Practice Exams need a subscription ("starts at $29 USD per month") and are out of bounds for this project.
- **Verified:** the free Exam Prep courses (about 2 hours each) "review sample certification questions for each domain". Catalog: <https://explore.skillbuilder.aws/learn/public/catalog/view/40>. The SAA-C03 prep plan: <https://skillbuilder.aws/category/exam-prep/solutions-architect-associate-SAA-C03>.
- **Unverified:** that the SAA-C03 English set has exactly 20 questions, and whether its feedback covers every option. Only third-party listings say so, and the Skill Builder pages are a JavaScript app that renders nothing without logging in.
- **Unverified:** export. I found no export feature and no license that allows copying. The content sits behind a login under AWS terms.
- **Recommendation:** use it by hand only, as a study and readiness check. Do not index it, scrape it or copy it into the eval.

### 4. Service user guides and the Well-Architected Framework on docs.aws.amazon.com (verified)

- **License:** the Site Terms (last updated 2025-06-04) say: "The materials hosted on docs.aws.amazon.com are licensed as follows: documentation (e.g., user guides, developer guides, other publications) is licensed under CC-BY-SA-4.0, while any code therein is licensed under MIT-0." Personal indexing is fine. If indexed text or derived chunks are ever published, keep attribution and share-alike.
- **Fetch options (all checked with a GET):**
  - `https://docs.aws.amazon.com/robots.txt` names `Sitemap: https://docs.aws.amazon.com/sitemap_index.xml` (13,862 sitemap entries) and disallows only old dated API versions.
  - Each guide has its own sitemap, for example `.../AmazonS3/latest/userguide/sitemap.xml`.
  - Site-wide `https://docs.aws.amazon.com/llms.txt` (about 400 KB) and an `llms.txt` per guide link to the Markdown pages.
  - Every page is also served as Markdown: replace `.html` with `.md`, for example `.../AmazonS3/latest/userguide/Welcome.md` (`text/markdown`). This is the cleanest input for chunking.
  - Every guide has a full PDF, for example the S3 User Guide (31.7 MB) and the Well-Architected Framework (14.2 MB).
  - **AWS Knowledge MCP server** at `https://knowledge-mcp.global.api.aws`: no auth, rate limited (no numbers published), tools `search_documentation`, `read_documentation`, `list_regions`, `get_regional_availability` and `retrieve_skill`. It covers docs, API references, What's New, blogs and Well-Architected guidance. Its use is subject to the AWS Site Terms. Source: <https://awslabs.github.io/mcp/servers/aws-knowledge-mcp-server>.
- **Rough size (pages per sitemap):** S3 User Guide 809, EC2 User Guide 732, RDS User Guide 1,403, IAM User Guide 629, VPC User Guide 204, Well-Architected Framework 475, the "Overview of AWS" whitepaper 36. All 118 in-scope services would mean tens of thousands of pages. Too big for a 16 GB CPU box, so a curated subset is needed (see the recommendation below).
- **Well-Architected:** the framework is at `https://docs.aws.amazon.com/wellarchitected/latest/framework/` and each pillar at `.../wellarchitected/latest/<pillar>-pillar/` (checked: `security-pillar/welcome.md`). The four exam domains map onto the security, reliability, performance efficiency and cost optimization pillars.
- **Whitepapers:** the ones under `docs.aws.amazon.com/whitepapers/latest/...` fall under the same CC-BY-SA clause. The `aws.amazon.com/whitepapers` landing page and older awsstatic PDFs fall under the Site Terms.

### 5. Service FAQs on aws.amazon.com (verified, restricted)

- **URLs:** `https://aws.amazon.com/<service>/faqs/`, for example <https://aws.amazon.com/s3/faqs/> (1.5 MB of HTML) and <https://aws.amazon.com/ec2/faqs/>. Both return HTTP 200, and `aws.amazon.com/robots.txt` does not block them.
- **License:** the general Site Terms. Personal use only, no downloading beyond page caching, no derivative use, and "any use of data mining, robots, or similar data gathering and extraction tools" is excluded. robots.txt allowing a path does not override those terms.
- **Recommendation:** do not crawl FAQs into the index. They are useful for study, so link to them or read them live (by hand, or through the Knowledge MCP, whose own use is under the same Site Terms). Most FAQ facts are also in the CC-BY-SA user guides.

### 6. Out of bounds

- Exam dumps and "real exam question" sites (several turned up in searches). They break the AWS Certification Program Agreement, which governs the program (see <https://aws.amazon.com/certification/policies/>), and they are copyright infringement. I did not check the exact CPA clause text. That re-uploaded copies of the sample PDF exist on third-party sites changes nothing: fetch it from awsstatic.
- Paid Official Practice Exams, subscription Exam Prep content, and third-party practice tests (Tutorials Dojo, Udemy and similar), including their "free samplers": their own terms apply and they are not AWS primary sources.

## Recommendation for #43 (retrieval) and #48 (eval)

1. **Corpus = docs.aws.amazon.com only**, fetched as `.md` through each guide's sitemap or `llms.txt`. Scope it with the exam guide: the guide's own pages, the Well-Architected Framework plus the four pillars that map to the domains, and the user guides for the core services the task statements name again and again (VPC, EC2, EC2 Auto Scaling, ELB, S3, EBS, EFS, FSx, RDS, Aurora, DynamoDB, ElastiCache, IAM, KMS, Organizations, CloudFront, Route 53, SQS, SNS, Lambda, API Gateway, CloudWatch, Backup, Storage Gateway, DataSync, Direct Connect, Transit Gateway). Record source URL and fetch date per chunk (needed for CC-BY-SA attribution and for "keeping up with AWS changes"). Throttle, and set a real User-Agent. Keep fetched text out of git.
2. **Live fallback:** the AWS Knowledge MCP (`read_documentation`, `search_documentation`) for anything outside the curated set, including FAQs read on demand. Not a crawl.
3. **Eval set:** the 10 official sample questions, fetched from the awsstatic URL at eval time into a gitignored folder and parsed into cases. Commit only the parser, the URL and a checksum. Add domain tags by hand in the committed case metadata (IDs, domain, correct letters), not the question text. Ten cases are a smoke test, not a benchmark: grow the set with hand-written questions grounded in CC-BY-SA docs (those can be committed with attribution) and with generate-mode output checked by a human.
4. **Skill Builder 20-question set:** by hand only, as a readiness check outside the app.

## Unverified or open

- Exact question count and export options of the Skill Builder SAA-C03 practice set (needs a logged-in look).
- Rate-limit numbers for the AWS Knowledge MCP, and whether it is free at every volume (the page says no auth and does not mention pricing).
- Exact CPA clause wording on dumps (the policies page was not read in full).
- Whether the docs `.md` variant exists for every docs page, including the exam guide pages (checked on S3, Well-Architected, the security pillar and the main exam guide page only).
- Why the HTML exam guide's revision table carries 2026 dates while the PDF labelled 1.1 is from 2025.
