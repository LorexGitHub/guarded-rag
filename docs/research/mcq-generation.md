# Generating and checking exam-style multiple-choice questions with LLMs

Research for LorexGitHub/guarded-rag#39 (map #34). Feeds #46 (generate mode: topic choice, checking and what you see). Researched 2026-11-07.

**Unverified** marks a claim I could not confirm from the primary source itself (I saw it only quoted in another paper). **Inference** marks my own reasoning about guarded-rag, not a finding from a source.

## Short answer

- **Generated questions fail at a few percent per question, mostly by having two correct options.** GPT-4 questions for Python courses: 4.9% had more than one correct option (human-written: 1.1%), and 81.7% passed every quality check ([Doughty et al., ACE 2024][doughty]). Across 71 medical-education studies, error rates ran from under 1% to 45% ([Kıyak et al., 2026][kiyak]). Even the human-written MMLU benchmark has an estimated 6.49% bad questions, including 1.42% wrong keys and 1.54% with more than one correct answer ([Gema et al., MMLU-Redux][mmlu]).
- **LLMs are poor at spotting a bad question, so a solver that agrees with the key is weak evidence.** The best LLM error detector on MMLU-Redux reached an F1 of 34.68 ([Gema et al.][mmlu]). SAQUET's GPT-4-assisted "more than one correct" check scored an F1 of 0.00 to 0.46 across five domains ([Moore et al., AIED 2024][saquet]). Disagreement is the useful signal. Agreement proves little.
- **Independence matters, and the same model as solver is the weakest choice.** LLMs recognise and favour their own outputs ([Panickssery et al.][selfpref]). Model errors grow more alike as models get better ([Goel et al.][alike]). Self-correction without outside feedback does not work on reasoning tasks ([Huang et al., ICLR 2024][selfcorrect]).
- **Several checks are nearly free per question:** rule-based item-writing-flaw checks, shuffling the option order, a choices-only solve, and a second solve with the options permuted.
- **Discard rather than repair, and keep a human report button.** Automated checks will miss some wrong keys, so the learner is the last line of defence.

## How often generated questions are wrong

| Source | Setting | Number |
|---|---|---|
| [Doughty et al., ACE 2024][doughty] | 651 GPT-4 and 449 human-written Python-course questions, rated by people | More than one correct option: **4.9%** generated vs **1.1%** human. A distractor that gives the answer away: **4.0%** vs **0.9%**. **81.7%** of generated questions passed all criteria. The authors call the multiple-correct issue "serious" and say it "requires human review" |
| [Doughty et al.][doughty] | Same study | The authors name implausible or plainly incorrect distractors, plus a stem that reveals the answer, as the most serious issues |
| [Kıyak, Kaya & Emekli, Postgrad Med J 2026][kiyak] | Systematic review of 71 studies on AI-generated medical MCQs | "Error rates ranged from <1% to 45%." "Current evidence does not yet support unsupervised use in summative assessment." Most studies used expert review, not learner data |
| [Gema et al., MMLU-Redux][mmlu] | 5,700 MMLU questions re-annotated by people (human-written benchmark) | 6.49% bad overall: wrong key **1.42%**, more than one correct **1.54%**, no correct option **0.62%**, unclear question 2.47%, unclear options 0.44%. In the Virology subset, 57% of questions were bad |

Read these together: even careful human item banks carry about 1–2% wrong keys and about 1–2% double-correct questions. A one-shot LLM generator adds about 5% double-correct on top. The ambiguity check in #46 targets the commonest failure.

## How well LLMs detect bad questions

| Source | Check | Result |
|---|---|---|
| [Gema et al.][mmlu] | LLM flags MMLU errors (all error types) | Best F1 **34.68** (Claude 3 Opus, zero-shot chain of thought). With retrieval, best F1 was 31.52 but best **recall was 83.91** (Claude 3 Opus, zero-shot, MS MARCO index). A fine-tuned Llama3-8B detector reached F1 34.06 (Appendix J). The authors call detection "a challenging task" |
| [Moore et al., SAQUET, AIED 2024][saquet] | GPT-4-assisted "More Than One Correct" check against human labels on 271 MCQs | F1 per domain: 0.00, 0.00, 0.38, 0.46, 0.11. It tended to over-flag |
| [Moore et al.][saquet] | Whole 19-flaw rubric, acceptable vs unacceptable (two or more flaws) | 75.3% agreement with people. The headline "94.13% accuracy" is per flaw label. [Moore & Diana 2026][qa-review] point out that labelling everything "no flaw" scores 93.09% |
| [Moore et al.][saquet], Table 2 | GPT-4 "answerability" (can a solver answer it?) | It did **not** separate flawed from sound questions. Questions with two or more flaws sometimes scored *higher* |
| Wu et al. 2026, as quoted in [Moore & Diana 2026][qa-review] | GPT-4 reviews 43 defective dental MCQs | Caught 12 of 44 flaws overall and **1 of 6** incorrect or missing answers. **Unverified:** I did not read the primary paper |
| Gérard et al. 2026, as quoted in [Aydin et al. 2026][aydin] and [Moore & Diana 2026][qa-review] | ChatGPT and Gemini both pick the same option, and it is not the key | As a flag for a bad item: sensitivity **35.3%**, specificity **92.9%**, precision 54.6% (87 pharmacology items). About a quarter of LLM "errors" on local exams came from ambiguous or wrongly keyed items. **Unverified:** I could not find the primary paper |
| [Aydin et al., Front Med 2026][aydin] | Three LLMs judge 85 internal-medicine MCQs for any technical flaw | Sensitivity: Claude Sonnet 4 about 86%, Gemini 2.5 Flash about 88%, Llama 3.3 70B **10%** (specificity 94.3%). Small open models can miss nearly everything |

What this means for the explain-mode check (**inference**):

- **When the solver disagrees with the key, that is a strong signal. Discard the question.** Discarding costs only a regeneration, so the filter can favour recall and accept false alarms.
- **When the solver agrees, that is weak evidence.** It does not prove the key right or the question unambiguous. The "second supported option" test is the part of the check that matters, and it is also the part LLMs do worst. Make it explicit: one verdict and one citation per option, not a single "pick the best" call.
- A small local solver in dev will miss most flaws (Llama 3.3 70B: 10% sensitivity, and a 16 GB CPU model will be smaller). Treat dev runs as plumbing tests, not quality evidence.

## Making the solver independent

- **Round-trip consistency is the established form of this check.** [Alberti et al., ACL 2019][roundtrip] generate a question from an answer, have a separate QA model answer it, and keep only examples where the answers match. The planned "explain without the key" check does the same thing.
- **Self-preference:** LLM evaluators can tell their own outputs from others' and favour them. Self-recognition correlates linearly with the strength of this bias ([Panickssery, Bowman & Feng 2024][selfpref]).
- **Correlated errors:** judges favour models similar to themselves, and "model mistakes are becoming more similar with increasing capabilities" ([Goel et al. 2025][alike]). Even a different model may share the generator's blind spots.
- **No self-repair:** without outside feedback, LLMs struggle to correct their own reasoning, and sometimes get worse ([Huang et al., ICLR 2024][selfcorrect]). Iterative self-critique pipelines such as [MCQG-SRefine (NAACL 2025)][srefine] exist and report better expert ratings. They cost several calls per question, and I did not verify their numbers.

How to get independence in guarded-rag (**inference**):

1. **No key and no generator reasoning:** give the solver only the stem and the options.
2. **Fresh retrieval:** the solver retrieves its own passages from the question text, not the passages the generator used. A question that depends on facts outside the passages it was built from then fails.
3. **A different prompt, and a different model where possible:** for example, a different Claude tier for the solver in production. Both models are still Claude, so expect correlated errors (Goel et al.).
4. **Citations as outside feedback:** each verdict must quote a passage, so the result does not rest on the model's opinion alone.

## Position and answer-leak checks

- **Option order changes answers.** LLMs prefer certain option letters ([Zheng et al., ICLR 2024][selector]; tested on 20 LLMs). Reordering options moved accuracy by about 13% to 75% across benchmarks ([Pezeshkpour & Hruschka 2023][order]). Cheap check: solve twice with the options permuted, and require the same option *content* both times.
- **The options alone can give the answer away.** Without the question, LLMs beat a majority baseline in 11 of 12 cases, by up to 0.33 accuracy ([Balepur et al., ACL 2024][choices]). Cheap check: a choices-only solve. If it picks the key with high confidence, the distractors are probably weak or the key stands out. The paper measured this across whole datasets. Using it on single questions is my adaptation (**inference**).
- **Shuffle the key's position in code** after generation, so the generator's own letter preferences never reach the learner. The claim that generators skew key positions comes only from a letter in a medical-education journal (**unverified** as a measured rate). The shuffle costs nothing either way.

## Distractor quality

- LLMs write valid distractors, but they are "less adept at anticipating common errors or misconceptions among real students" ([Feng et al., NAACL Findings 2024][feng]).
- Doughty et al. found implausible or plainly wrong distractors to be the main quality gap ([Doughty et al.][doughty]).
- Common text metrics such as BLEU, perplexity and diversity do not track question quality ([Moore et al.][saquet]; [QGEval, EMNLP 2024][qgeval]). QGEval also finds most question generators weak on answerability and answer consistency.
- Suggestion for SAA-C03 (**inference**): ask the generator to state, for each distractor, which requirement in the scenario it fails, such as cost, availability, operational overhead or a limit, and to cite the passage that shows it. That gives the solver a specific claim to check, which is easier than judging plausibility. It matches how SAA-C03 distractors work: a real service that fails one constraint.

## Item-writing flaws that rules can catch

SAQUET ([Moore et al.][saquet], code at [github.com/StevenJamesMoore/AIED24][saquet-code]) checks 19 item-writing flaws. Eight of them use plain string matching:

- None of the Above
- All of the Above
- Fill-in-the-Blank
- True or False
- Longest Answer Correct
- Negatively Worded
- Lost Sequence
- Vague Terms

Its rule-based "Longest Option Correct" check scored an F1 of 0.77 to 1.00 across domains. "None/All of the Above" scored 0.80 to 1.00 where present. Rules like these cost nothing per question. The generator prompt should forbid the same patterns.

## Cost per question

| Check | Cost | Catches |
|---|---|---|
| Rule checks: longest option is the key, "all/none of the above", negative stem, absolute terms, exactly four distinct options | Free (string matching) | Cueing and format flaws |
| Shuffle option order before showing | Free | Generator letter bias |
| Choices-only solve | 1 short LLM call, no retrieval | The answer leaks from the options |
| Explain solve without the key, with fresh retrieval and a verdict plus citation per option | 1 retrieval and 1 LLM call (already planned) | Wrong key, a second supported option, an unsupported key |
| Second explain solve with options permuted | +1 LLM call (can reuse the retrieval) | Position-driven agreement |
| Second-model solver | +1 call on another model | Some same-model blind spots (still correlated) |
| Self-critique or repair loop | Several calls | Weak evidence of a gain, and self-correction is unreliable |

## Recommendation for #46

1. **The pipeline.** The generator writes a scenario, a requirement, four options and a key. For the key and for each distractor, it cites a passage, and for each distractor it names the requirement that distractor fails. Then:
   1. Run the rule checks.
   2. Shuffle the options.
   3. Run the explain solver without the key, with its own retrieval, giving a verdict and a citation per option.
   4. Run a second solve with the options permuted (cheap; can be production only).
   5. Run the choices-only solve.
2. **Accept only if all of these hold:**
   - Both solves pick the key.
   - Every distractor gets "not supported" with a cited reason.
   - The choices-only solve does not confidently pick the key.

   Any doubt means discard.
3. **Discard. Do not repair.** Regenerate from scratch, and log the reason for each rejection. The rejection rate per topic is a useful eval number. **Unverified estimate:** expect at least 5–20% rejected with Claude, and much more with a small local model.
4. **Show citations for every option, and add a "this question is wrong" button.** Detection recall is low (F1 about 0.35 at best on MMLU-Redux), so some wrong keys will reach the learner. A flagged question leaves the bank, and the flag feeds the mistakes log and the eval set.
5. **In dev with a small local model,** test the plumbing and the rejection path only. Do not read the pass rate as a sign of quality.

## Not verified

- The Wu et al. 2026 dental numbers (1 of 6 wrong keys caught) and the Gérard et al. 2026 two-model numbers (sensitivity 35.3%, specificity 92.9%). I read both only as quoted in [Moore & Diana 2026][qa-review] and [Aydin et al. 2026][aydin].
- MCQG-SRefine's quantitative gains: I read only the abstract.
- Feng et al.'s match rates against real student errors: the abstract gives no numbers.
- The peer-reviewed venues for MMLU-Redux, Panickssery et al. and Goel et al. The arXiv pages I read list none.
- The idea that generators skew key positions: I found it only in a non-research letter.
- The 5–20% rejection-rate estimate: no source measures this exact pipeline.

## Sources

- [doughty]: Doughty et al., "A Comparative Study of AI-Generated (GPT-4) and Human-crafted MCQs in Programming Education", ACE 2024. https://arxiv.org/abs/2312.03173
- [kiyak]: Kıyak, Kaya & Emekli, "Validity of AI-generated multiple-choice questions in medical education: a systematic review", Postgraduate Medical Journal, 2026. https://doi.org/10.1093/postmj/qgag057
- [mmlu]: Gema et al., "Are We Done with MMLU?" https://arxiv.org/abs/2406.04127
- [saquet]: Moore, Costello, Nguyen & Stamper, "An Automatic Question Usability Evaluation Toolkit", AIED 2024. https://arxiv.org/abs/2405.20529
- [saquet-code]: https://github.com/StevenJamesMoore/AIED24
- [qa-review]: Moore & Diana, "AI-Enabled Quality Assurance for Multiple-Choice Assessment Items", 2026. https://arxiv.org/abs/2610.04267
- [aydin]: Aydin, Coşkun & Hamal, "Assessing multiple-choice question quality in internal medicine: a comparative analysis of three large language models against expert consensus", Frontiers in Medicine, 2026. https://pmc.ncbi.nlm.nih.gov/articles/PMC13391911/
- [roundtrip]: Alberti et al., "Synthetic QA Corpora Generation with Roundtrip Consistency", ACL 2019. https://aclanthology.org/P19-1620/
- [selfpref]: Panickssery, Bowman & Feng, "LLM Evaluators Recognize and Favor Their Own Generations". https://arxiv.org/abs/2404.13076
- [alike]: Goel et al., "Great Models Think Alike and this Undermines AI Oversight". https://arxiv.org/abs/2502.04313
- [selfcorrect]: Huang et al., "Large Language Models Cannot Self-Correct Reasoning Yet", ICLR 2024. https://arxiv.org/abs/2310.01798
- [srefine]: Yao et al., "MCQG-SRefine", NAACL 2025. https://arxiv.org/abs/2410.13191
- [selector]: Zheng et al., "Large Language Models Are Not Robust Multiple Choice Selectors", ICLR 2024. https://arxiv.org/abs/2309.03882
- [order]: Pezeshkpour & Hruschka, "Large Language Models Sensitivity to The Order of Options in Multiple-Choice Questions". https://arxiv.org/abs/2308.11483
- [choices]: Balepur, Ravichander & Rudinger, "Artifacts or Abduction: How Do LLMs Answer Multiple-Choice Questions Without the Question?", ACL 2024. https://arxiv.org/abs/2402.12483
- [feng]: Feng et al., "Exploring Automated Distractor Generation for Math Multiple-choice Questions via Large Language Models", NAACL Findings 2024. https://arxiv.org/abs/2404.02124
- [qgeval]: Fu et al., "QGEval: Benchmarking Multi-dimensional Evaluation for Question Generation", EMNLP 2024. https://arxiv.org/abs/2406.05707

[doughty]: https://arxiv.org/abs/2312.03173
[kiyak]: https://doi.org/10.1093/postmj/qgag057
[mmlu]: https://arxiv.org/abs/2406.04127
[saquet]: https://arxiv.org/abs/2405.20529
[saquet-code]: https://github.com/StevenJamesMoore/AIED24
[qa-review]: https://arxiv.org/abs/2610.04267
[aydin]: https://pmc.ncbi.nlm.nih.gov/articles/PMC13391911/
[roundtrip]: https://aclanthology.org/P19-1620/
[selfpref]: https://arxiv.org/abs/2404.13076
[alike]: https://arxiv.org/abs/2502.04313
[selfcorrect]: https://arxiv.org/abs/2310.01798
[srefine]: https://arxiv.org/abs/2410.13191
[selector]: https://arxiv.org/abs/2309.03882
[order]: https://arxiv.org/abs/2308.11483
[choices]: https://arxiv.org/abs/2402.12483
[feng]: https://arxiv.org/abs/2404.02124
[qgeval]: https://arxiv.org/abs/2406.05707
