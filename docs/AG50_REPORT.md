# AG50 report: three grading engines on 50 independent long calls

Interactive version with charts: generate `laya-finetuning/docs/AG50_DASHBOARD.html` with `python laya-finetuning/eval/ag50_analysis.py && python laya-finetuning/eval/build_ag50_dashboard.py` and open it in a browser (one file, works offline). It needs `pip install scipy scikit-learn`. The generated files were removed from the repo on 2026-10-22; the last copies are in commit `8a6842b`. The script rebuilds an earlier three-engine layout; the final page, edited by hand to add the flow-v2 engine, is only in that commit.
> **Update 2026-10-19:** after this report I changed what the model is shown for Empathy, Paraphrasing and Ownership ("flow v2", `Docs/FLOW_V2.md`) and re-ran. With no retraining, fine-tuned Laya reaches 80.3% of the judged items on AG50 (a development set, so optimistic), against Ollama's 78.6% (not distinguishable, p = 0.58), and Main and bulk did not regress (42/44, 359/372). The tables below describe the flow *before* that change.

Raw numbers (generated, no longer kept in the repo): `laya-finetuning/docs/ag50_stats.json` and `laya-finetuning/docs/AG50_RESULTS.md` (every call and every disagreement). Reproduce with `python laya-finetuning/eval/ag50_analysis.py && python laya-finetuning/eval/build_ag50_dashboard.py` for the first, and `python laya-finetuning/eval/compare_eval.py AG50 laya-stock laya-ft ollama --out laya-finetuning/docs/AG50_RESULTS.md` for the second.

## 1. In one minute

- **Ollama is better than our fine-tuned Laya on this test, by a modest but real margin.** On the 7 items a model has to judge, Ollama matched the key 78.6% of the time, fine-tuned Laya 72.0%, stock Laya 64.6%. The 6.6-point gap between Ollama and fine-tuned Laya is statistically solid (95% interval 0.9 to 12.3 points, McNemar p = 0.014).
- **Fine-tuning worked, but less than hoped.** It lifted Laya by 7.4 points over stock (p = 0.005). The earlier 92% on Eval50 was too optimistic: that test and the training data had the same author.
- **Part of the gap never involves the model.** The app cuts a small snippet out of each call before the model sees it. On these 10-20 minute calls the snippet often misses the evidence: 6 of 15 Active-listening faults and 6 of 17 Ownership faults never reached the model at all.
- **Fine-tuned Laya is 24 times faster** (16 s a call against 386 s) and its final scores are nearly unbiased (+1.2 points). Ollama is lenient: its scores average 11.7 points above the key.
- **Verdict:** not ready to replace Ollama. Fine for a shadow-mode trial next to it. The most promising route is fixing the snippet-building first, then retraining (section 8).

## 2. What was tested

- 50 customer-support calls for S-Net, 10 to 20 minutes each, with a sentiment score on every turn. **Written and graded by Antigravity**, a different AI from the one that wrote the training data. The brief (`ANTIGRAVITY_TEST_BRIEF.md`, removed on 2026-10-22; read it with `git show a7ace67:Docs/<name>`); the files are in `laya-finetuning/inputs/AG50/`.
- Mix: 8 excellent calls, 15 with 1-2 faults, 12 with 3-4, 11 with 5 or more, 4 auto-fails. 65% of the keyed FAILs and 34% of the keyed PASSes were tagged "hard cases".
- I re-checked the four rule-based items, the auto-fail detection and the final-score maths against the app's own code: **0 mismatches**.
- Every engine received the same payloads through the normal app (`/api/evaluate`), so the whole pipeline ran: rules, snippet extraction, then the model. Settings: stock Laya with its original cutoffs, fine-tuned Laya (`final-softce-3`) with its tuned cutoffs, Ollama through the older copy of the app (`qa-analysis-ollama`).
- **The 4 rule-based items** (Branding, Dead air, Verified, Personalized) scored 100% for both Laya versions because the same fixed code decides them. Only the 7 model-judged items test the models. Ollama scored 46/50 on Dead air because its older copy has an older version of that rule, not because of its model.

## 3. Results

| | Stock Laya | Fine-tuned Laya | Ollama |
|---|---|---|---|
| **7 judged items matching the key** | 226/350 = 64.6% (60.9-68.3) | 252/350 = 72.0% (66.9-76.9) | **275/350 = 78.6% (73.4-83.4)** |
| All 11 items matching the key | 77.5% (75.1-79.8) | 82.2% (78.9-85.3) | **85.6% (82.4-88.7)** |
| Average final-score error (points) | 16.0 (12.9-19.0) | **12.7 (10.0-15.3)** | 12.8 (9.3-16.7) |
| Average score bias (+ = too generous) | -4.7 | **+1.2** | +11.7 |
| Rank agreement of scores with key (Spearman) | 0.73 | 0.77 | **0.84** |
| Agreement with key beyond chance (kappa, judged items) | 0.19 | 0.35 | **0.42** |
| Auto-fail decisions correct | 50/50 | 50/50 | 50/50 |
| Time per call | 17.1 s | **16.2 s** | 386.2 s |

Intervals in brackets are 95% bootstrap intervals that resample whole calls.

## 4. What the statistics say

**Is Ollama really better, or is it luck?** The test is paired: the same 350 items go to both engines. Ollama was right where fine-tuned Laya was wrong on 52 items. Laya was right where Ollama was wrong on 29. If the two were equally good, a split this lopsided would appear about 1.4% of the time (McNemar exact test). So the gap is real. It is also small: roughly one more item in 15 right.

| Comparison on the 7 judged items | Difference | 95% interval | Only A right | Only B right | p |
|---|---|---|---|---|---|
| Fine-tuned Laya vs Ollama | -6.6 pts | -12.3 to -0.9 | 29 | 52 | 0.014 |
| Fine-tuned Laya vs stock Laya | +7.4 pts | +2.6 to +12.3 | 54 | 28 | 0.005 |
| Ollama vs stock Laya | +14.0 pts | +8.9 to +18.6 | 70 | 21 | <0.001 |

Including the 4 rule items, the difference between Ollama and fine-tuned Laya shrinks to 3.5 points and its interval (-7.1 to +0.2) just touches zero. The rule items dilute the comparison, which is why the judged items are the right yardstick.

**Both are "fair", neither is "good" at agreeing with the key.** Kappa (agreement beyond chance, 0 = chance, 1 = perfect) is 0.35 for fine-tuned Laya and 0.42 for Ollama. Conventionally both sit in the "fair to moderate" band. Before human reviewers are involved, this is also what a noisy key and a hard task look like.

**How much to trust each number.** With 50 calls and 13-19 keyed faults per item, a single item's balanced accuracy has an interval of about plus or minus 0.12 to 0.14. Pooled numbers (350 items) are much tighter. So: trust the pooled comparison, treat any single-item ranking as a pointer, not a finding.

**Scores, not only verdicts.** Average error is a tie (12.7 vs 12.8), but for different reasons. Ollama ranks calls best (0.84) yet shifts every call upward by about 12 points: poor calls average 61 against a key of 36. Fine-tuned Laya is unbiased on average but compresses the range, scoring excellent calls at 82 (key 100) and poor calls at 51 (key 36). Both pull toward the middle. Neither would rank an excellent agent above a good one reliably.

**Call length.** No engine collapses on 18-20 minute calls and there is no clean trend (10-15 calls per bucket, so differences between buckets are noise).

## 5. Item by item (balanced accuracy, 0.50 = coin flip)

| Item | Faults in key | Stock | Fine-tuned | Ollama | Fine-tuned: missed / false alarms | Ollama: missed / false alarms |
|---|---|---|---|---|---|---|
| Empathy | 17 | 0.50 | 0.62 | **0.70** | 0 / 25 | 9 / 2 |
| Paraphrasing | 16 | 0.54 | 0.58 | 0.50 | 11 / 5 | 16 / 0 |
| Active listening | 15 | 0.50 | 0.50 | 0.50 | 15 / 0 | 15 / 0 |
| Ownership | 17 | 0.62 | **0.79** | 0.74 | 7 / 0 | 9 / 0 |
| Rapport | 15 | 0.50 | **0.71** | 0.63 | 4 / 11 | 11 / 0 |
| Probing | 13 | 0.64 | 0.67 | **0.81** | 8 / 2 | 4 / 3 |
| Resolved | 19 | **0.82** | 0.77 | 0.84 | 7 / 3 | 6 / 0 |

- Fine-tuned Laya **wins** on Ownership and Rapport and **loses** on Empathy, Probing and Resolved. Active listening is a coin flip for all three.
- **Error style differs.** Ollama almost never raises a false alarm (5 in total) but misses 70 faults. Fine-tuned Laya is more balanced (52 missed, 46 false alarms). Stock Laya has 61 missed and 63 false alarms.

## 6. Why the model is wrong: where the faults get lost

Laya never reads a whole call. The app builds a snippet per check, and the model judges only that. I measured, for each keyed fault, whether any snippet containing it was built.

| Item | Keyed faults | Never reached the model | Reached it, fine-tuned Laya caught | Reached it, missed |
|---|---|---|---|---|
| Active listening | 15 | 6 | 0 of 9 | 9 |
| Ownership | 17 | 6 | **10 of 11** | 1 |
| Empathy | 17 | 0 | 17 of 17 | 0 |
| Paraphrasing | 16 | 0 | 5 of 16 | 11 |
| Rapport | 15 | 0 | 11 of 15 | 4 |
| Probing | 13 | 1 | 4 of 12 | 8 |
| Resolved | 19 | 0 | 12 of 19 | 7 |

Findings, from opening the actual snippets (so sample sizes are small and stated):

1. **Active listening: two separate problems.** (a) 6 of the 15 faults never reach the model. The app pairs one *agent question* with a similar later *agent question*, and these are cases such as "the customer volunteered the router model in the first minute, and the agent asked for it again 8 minutes later", where no earlier question exists. (b) For the other 9, the snippet *was* built, 8 of them with the correct pair, and the fine-tuned model still said PASS every time: its probability of "this is a repeat" was only 0.05 to 0.12 on all nine (stock Laya gave 0.20 to 0.65). So the model itself, not only the snippet, misses reworded repeats that are minutes apart. *(An earlier version of this report said most snippets showed the wrong pair. That came from reading four examples and was wrong; the full count is above.)*
2. **Ownership: the phrase check blocks 6 of 17 faults.** When the model gets the snippet, it is excellent (10 of 11). The ceiling is set by the phrase list.
3. **Empathy: the app and the key use different definitions.** The app checks each upset customer moment on its own and flags it if no apology appears within the next 3 turns. The key (and the QA definition I gave Antigravity) says one acknowledgement anywhere in the call is enough. In the 3 false alarms I opened, the agent had already acknowledged the customer in the first 30 seconds; the snippet shown was a later upset moment. Fine-tuned Laya caught all 17 real faults but raised 25 false alarms in 33 good calls. That is a spec mismatch, not a model weakness.
4. **Rapport: the rule compounds small errors.** A call fails if any chunk looks rude. These calls have 7 to 13 chunks (10.2 on average). A per-chunk false-alarm rate of about 3.6% gives roughly 31% of good calls failing, which is what we saw (11 of 35). The cutoff of 0.20 was tuned on four calls with fewer chunks.
5. **Paraphrasing, Probing, Resolved see little.** On a 1,900-word call the model gets about 200 words for Paraphrasing and about 195 for Resolved (last 10 lines). If the agent restated the problem at minute 9, the model never sees it.

## 7. Did training change what the model can tell apart? (AUC)

AUC is the chance that the model ranks a faulty call as worse than a good call, ignoring any cutoff. 0.5 means no skill. This is the cleanest measure of what training changed.

| Item | AUC fine-tuned | AUC stock | Training effect | Balanced acc. now | Re-tuned cutoff, cross-validated |
|---|---|---|---|---|---|
| Empathy | 0.69 | 0.74 | -0.04 (-0.19 to +0.10) no clear change | 0.62 | 0.59 |
| Paraphrasing | 0.63 | 0.63 | +0.01 (-0.17 to +0.17) no clear change | 0.58 | 0.55 |
| Active listening* | 0.80 | 0.80 | 0.00 | 0.50 | 0.80 |
| Ownership* | 0.82 | 0.82 | 0.00 | 0.79 | 0.82 |
| Rapport | 0.82 | 0.58 | **+0.24 (+0.08 to +0.42) clear gain** | 0.71 | 0.70 |
| Probing | 0.88 | 0.73 | +0.14 (-0.01 to +0.33) probable gain | 0.65 | **0.79** |
| Resolved | 0.85 | 0.92 | -0.07 (-0.22 to +0.06) no clear change | 0.77 | 0.77 |

\*Only 9 and 11 calls reached the model; these AUCs mostly reflect the snippet rule. For Active listening all 9 snippets came from faulty calls (no good call produced one), so the model's false-alarm control cannot be assessed on this data.

What it means:
- **Training clearly improved ranking on one item: Rapport.** Probing probably improved. For Empathy, Paraphrasing and Resolved the change is not distinguishable from zero, and Resolved trends worse.
- **Probing ranks well (AUC 0.88) but a new cutoff is not a safe fix.** A cutoff chosen on half of AG50 and tested on the other half lifts balanced accuracy from 0.65 to 0.79, but that cutoff (about 0.94) lands in the middle of the *good* cluster on the earlier bulk set, where it raises false fails from 1 to 12 of 33 good calls (balanced accuracy 0.98 to 0.82). The model's probabilities sit in tight clusters, and where the gap falls differs between data sets. *(An earlier version of this report called the cutoff "the biggest cheap win"; the bulk check showed it is not.)*
- **Paraphrasing and Empathy are not cutoff problems.** Re-tuning does not help them. Their ranking is weak, which points at the snippet or the key.

## 8. Would more fine-tuning help?

**Short answer: not more of the same.** Training makes the model better at what it is shown. These results say that on several items the problem is what it is shown, or where the cutoff sits, or what the key means.

| Lever | Evidence | Needs retraining? | Expected value |
|---|---|---|---|
| ~~Retune the Probing cutoff~~ (tested, rejected) | Fits AG50 but breaks the bulk set (12 false fails); Probing needs better discrimination, not a new cutoff | n/a | None |
| Make Empathy call-level (acknowledged anywhere = pass, or send the first upset moment plus the agent's reply) | 25 false alarms, all 17 faults already caught | Probably yes, to re-train on the new snippet | High |
| Active listening: add a second candidate source (customer statement vs later agent question) and train on reworded, far-apart repeats | 15 faults, 0 caught; 6 never reach the model; on the 9 that do (8 right pair) the fine-tuned model gives P(repeat) 0.05-0.12 | Yes, mainly for the model | Medium (worth 10 points of the score, but 0 of 15 caught today) |
| Widen the Ownership gate (semantic, not a fixed phrase list) | 6 of 17 faults blocked | Yes | Medium |
| Longer windows for Paraphrasing / Resolved (Laya has a 512-token limit, so use several windows and combine) | sees ~200 of 1,900 words | Yes | Medium |
| More fine-tuning on the existing snippets | Training effect on AUC is only clear for Rapport | n/a | Low |

How fine-tuning works, since you asked: it adjusts the model's weights using labelled examples. More epochs or more examples of the *same kind* help until the model has learned what those examples teach, then it just memorises them. Gains come from examples that (a) match what the model will really see and (b) cover cases it currently gets wrong. Both depend on fixing the snippet-building first. If we retrain on examples built from today's snippets, the model learns to be good at snippets that are missing the evidence.

**A sensible plan, if you want to put in effort:**
1. **Window changes (no training).** Empathy, Paraphrasing and Ownership windows chosen by call structure: see `Docs/FLOW_V2_LAB.md`. (Probing cutoff re-tuning was tested and rejected, see section 7.)
2. **Fix the snippet builders** for Active listening, Empathy and the Ownership gate. This changes the frozen inputs, so the frozen-input hash and the data for those checks must be regenerated.
3. **New training data from a different author.** Have Antigravity write a *new* batch (not AG50) in the new snippet format, with different scenarios, and mix it with the existing Claude data. A second author makes the training less dependent on one writing style.
4. **Keep AG50 sealed.** Do not train on it; otherwise it can no longer tell us anything.
5. **The most valuable effort from you:** a human review of the disagreements (about 30 items, around an hour). It answers the question hanging over everything here: when the engines disagree with the key, who is right? If the key is wrong about a third of the time, the models are better than they look.

I cannot promise a number. What I can say: the gap to Ollama is 23 items out of 350. At least 12 faults (Active listening and Ownership) are unreachable today, and fixing the other snippet problems has a plausible path to closing much of it. Matching Ollama on accuracy is reachable; clearly beating it is not shown by any evidence here.

## 9. Does the test follow the real app flow?

Yes. The calls went through `/api/evaluate`, the same route production uses. The app ran the four rule checks, built the snippets, asked the model, applied the cutoffs, and calculated the score. Nothing was pushed straight into a model. But this is exactly where the problem sits: the **snippet-building design was made for short calls and for the Claude-written data**. On 10-20 minute calls with a different author's style, the way content is pushed into the model is a major source of error (section 6). So your instinct was correct: it is partly "how we push the content in", not only the model.

## 10. Limits of this evidence

- **The key is an AI's opinion, not human truth.** Antigravity is independent of Claude, but an AI-written key may agree more with an LLM judge (Ollama) than with a small classifier. That could slightly favour Ollama. A human review of disagreements is the way to find out.
- **One key author, 50 calls.** Item-level numbers are noisy.
- **Cutoffs for the fine-tuned model were tuned earlier on Claude data.** That penalises it a little on a new author's calls; the re-tuned numbers in section 7 are upper bounds because the same key is used.
- **Ollama ran through an older copy of the app** with an older Dead-air rule. This does not affect the judged items.
- **The Empathy explanation is from opening 3 examples**, not from a full audit. The counts in the "never reached the model" column and the Active-listening probabilities are complete.
- **AG50 is now a development set.** After writing this report I studied all 50 calls to find where each criterion's evidence sits. Design choices made from that cannot be fairly tested on the same calls, so the final verdict needs a new, sealed set.
- **Agent sentiment in AG50 is an artifact.** My brief told Antigravity to give rude agent lines negative sentiment. Production has customer-side sentiment only, so nothing may rely on agent sentiment.
- **Not a production test.** No real calls, no real speech-to-text noise beyond what Antigravity wrote in.

## 11. Recommended next steps

1. Review the disagreement list (the bottom table of the generated `laya-finetuning/docs/AG50_RESULTS.md`, see above) with a person: about 30 items, one hour.
2. Adopt the flow-v2 windows that the lab supports (Empathy, Paraphrasing, Ownership) and test them end to end.
3. Rebuild the Active-listening and Empathy snippets; regenerate their data; retrain; test on sealed AG50.
4. Run the fine-tuned model in **shadow mode** beside Ollama on real calls, and compare against human QA scores.

## 12. Files

`laya-finetuning/docs/AG50_DASHBOARD.html` (charts), `laya-finetuning/docs/ag50_stats.json` (all numbers) and `laya-finetuning/docs/AG50_RESULTS.md` (per-call tables), all three generated on demand as described at the top, `laya-finetuning/inputs/AG50/` (calls and keys), `laya-finetuning/inputs/Test (results)/AG50 (laya-stock|laya-ft|ollama)/` (raw results), `laya-finetuning/inputs/Test (results)/Laya probes/probe_AG50_*.json` (every model probability), `laya-finetuning/eval/ag50_analysis.py`, `laya-finetuning/eval/build_ag50_dashboard.py`, `laya-finetuning/eval/probe_laya.py --suite`.
