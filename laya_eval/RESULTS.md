# Laya out of the box vs Ollama llama3.1 8B: first benchmark

**Read this first.** The gold set is synthetic. I wrote 320 snippets with a known intended verdict each, and no human has reviewed them. Every number here is optimistic and only shows how the two models do on *this* test, not on real calls. Each criterion has 40 items, and the comparison uses an 18-item held-out half (9 PASS / 9 FAIL), so the 95% intervals are roughly ±15 points. Gaps under about 10-15 points are noise.

## What was run
- **Gold set** (`data/*.jsonl`, built by `build_gold.py`): 8 criteria x 40 items (20 PASS / 20 FAIL, about a third hard cases). Empathy, Ownership and Rapport snippets are produced by the pipeline's own extractors in `rule_engine.py`, so they have the format and gate the real pipeline uses.
- **Laya** (`run_laya.py`): checkpoints `english` and `multilingual`, no training, CPU. Each criterion is asked four ways in one forward pass: two criteria wordings, one with neutral A/B labels, and a two-option choice (`questions.py`).
- **Ollama** (`run_ollama.py`): llama3.1 8B through the pipeline's own adapter, with the one-word prompts and the batch prompt and parser copied from `dynamic_evaluator.py`. Escalation and Hostility are not in the repo's default criteria, so I wrote their descriptions in the repo's VIOLATION-BASED style (an assumption).
- **Scoring** (`score.py`): Laya's threshold is tuned on the dev half and scored on the test half. The question form is also picked on dev only. Ollama needs no tuning. Full tables are in `results/summary.md`.

## Result: held-out test half, balanced accuracy

| Criterion | Laya English | Laya multilingual | Ollama llama3.1 | Read |
|---|---|---|---|---|
| Empathy | 0.83 | 0.44 | **1.00** | Ollama better. Multilingual is unusable here. |
| Active listening | **0.78** | **0.78** | 0.50 | Laya better. Ollama answers FAIL for 16 of 18. |
| Ownership | 0.83 | 0.72 | **0.94** | Ollama slightly better, within noise. |
| Rapport | **0.83** | 0.72 | 0.56 | Laya better. Ollama answers PASS for 17 of 18, even for blatant rudeness. |
| Probing | **0.83** | 0.67 | 0.56 | Laya better. Ollama answers FAIL for 17 of 18, even for clear diagnostic questions. |
| Confirmed resolved | 0.83 | 0.89 | **1.00** | Ollama better, close. |
| Escalation | 0.78 | **0.83** | 0.83 | Tie. |
| Hostility | 0.83 | 0.83 | **0.94** | Ollama slightly better, within noise. |
| **Average of 8** | **0.82** | 0.74 | **0.79** | Equal within noise. |

Laya's AUROC (threshold-free) averages 0.86 for English. It is 0.93 to 1.00 for Ownership, Probing and Confirmed-resolved.

## What this means
1. **The two models fail on different criteria.** Ollama is strong on Empathy, Confirmed-resolved, Ownership and Hostility, and near chance on Active listening, Rapport and Probing, where it says the same verdict almost every time. Laya is steadier across all eight. This is not a parsing artifact: scoring the first word of each reply gives the same numbers.
2. **Laya is not a free drop-in.** At the default 0.5 threshold Laya averages only 0.64, and the thresholds tuned on dev ranged from 0.06 to 0.99. It needs a labelled set to calibrate, and Ollama got no such tuning here, so part of Laya's edge on Rapport and Probing comes from that. The Ollama prompts could probably also be improved.
3. **Wording is a big lever.** The same criterion moved by up to 33 points between phrasings (English Probing: 0.50 to 0.83). Picking the best form on 22 dev items flatters the result a little.
4. **English checkpoint, not multilingual**, for these snippets. Multilingual is below chance on Empathy and weaker on most criteria.
5. **Hard cases are the weak spot.** On clear items Laya's AUROC is 0.88 to 0.98. On hard items it falls. Hostility on hard items is 0.37, below chance, because Laya treats an abusive customer's words as agent hostility. Empathy (0.69) and Active listening (0.73) also drop.
6. **Speed.** Laya takes about 2 s on CPU for all four forms together (English) or about 0.6 s (multilingual), measured alone. Ollama took about 5 to 10 s for one-word calls and 27 to 266 s for the batch calls on CPU. Nothing in the Laya run was truncated (max 617 input tokens).
7. **No criterion falls below the 0.60 "train" line** for the best English form, so the test does not show a need to fine-tune yet. That is a statement about this synthetic set only.

## Provisional per-criterion call (to confirm with real labels)
| Move to Laya (English) | Keep testing / improve first | Not decided |
|---|---|---|
| Active listening, Rapport, Probing | Ownership, Empathy, Confirmed resolved, Hostility (Ollama is ahead by 0.11-0.17 with intervals that include zero; try wording and agent-only input) | Escalation (tie; also needs the long-transcript test) |

Coaching tips and embeddings stay on Ollama regardless (this was the plan before version 10 replaced Ollama; the analysis document `PIPELINE_FLOWCHART_LAYA.md` was removed on 2026-10-22 and is in git history at commit `8a6842b`).

## Known limits of this test
- **Synthetic, unreviewed labels** (see top). A 10-15% human spot-check of the gold set is the cheapest next step.
- **Short snippets only.** Real Empathy snippets average about 59 words against 43 in the gold set, and the pipeline joins *all* empathy snippets from a call into a single prompt with one verdict; the gold set uses one snippet per item. Real calls (500-2,000 words) are also far longer than anything tested here.
- **Active listening is a weaker test than it looks.** The pipeline's snippet contains only the two agent questions, not the customer's answers in between, so a legitimate re-ask is indistinguishable from a careless repeat. The label here means "same request vs a different request".
- **Ollama coverage:** 216 of 320 items. The full 144-item test half is complete for all 8 criteria, which is all the comparison uses. I stopped the run early, so dev items are missing for Ownership, Rapport, Probing, Resolved and Hostility, and the "all 40" Ollama column is only filled for Empathy, Active listening and Escalation.
- **Not done:**
  - The long-transcript test for Escalation/Hostility (`run_long.py`). It stopped after 20 rows and is not scored.
  - The Hostility fix of feeding Laya only the agent's lines.
  - Both are resumable. They were paused because Ollama and Laya were competing for CPU and memory (15.7 GB machine, nearly full).

## Reproduce
```
python laya-finetuning/laya_eval/build_gold.py     # build + validate the 320 items
python laya-finetuning/laya_eval/run_laya.py       # ~15 min on CPU, run alone
python laya-finetuning/laya_eval/run_ollama.py     # needs Ollama + a version-10 checkout (QA_OLLAMA_ROOT); hours on CPU, run alone
python laya-finetuning/laya_eval/score.py          # writes results/summary.md
python laya-finetuning/laya_eval/analyze.py        # hard-vs-clear and worst misses
```
Run the two model jobs one at a time. Together they slow each other down and exhaust RAM.
