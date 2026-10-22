# ft6 vs ft5 vs the old model: sealed AG-C exam, 2026-10-22

Keys are AI-written (Antigravity), none human-reviewed. AG-C (50 calls) was written in a fresh session, validated (every check PASS,
call length vs failed items r = +0.08), fingerprinted before any model saw it (unchanged afterwards), sealed in 14ec20a, and probed
exactly once, after the model choice and every model's cutoffs were committed (e834a8b).

## Models and cutoffs
| | Checkpoint | Cutoffs (runs/ft6/agc_cutoffs_*.json) |
|---|---|---|
| old | `final-softce-3` (stage 3, Claude data), no Active-listening second source | base; Active listening 0.947 (split-half rule) |
| ft5 | `ft5-20261021-1621/final-softce` (stage 3 + clean AG-T) | base; Active listening 0.92, Probing 0.926 |
| ft6 | `ft6-20261022-0453/final-softce` (ft5 data + 141 labelled moments, Probing rows, Empathy length balance) | base |

ft6 softce was chosen over ft6 softce_ag2 on cross-validated development accuracy (704 vs 670 of 882 items; old 682, ft5 695).

## AG-C results (50 calls, 7 judged items each)
| Check | old | ft5 | ft6 |
|---|---|---|---|
| Empathy | 37 | 37 | **40** |
| Build rapport | 43 | **45** | 43 |
| Paraphrasing | 48 | **49** | 45 |
| Active listening | **43** | 41 | 42 |
| Took ownership | 37 | 37 | 37 |
| Probing | **38** | **38** | 36 |
| Confirmed resolved | 27 | **29** | **29** |
| **All 7 (of 350)** | 273 (78.0%) | **276 (78.9%)** | 272 (77.7%) |
| Final-score mean absolute error | 11.5 | 10.9 | **10.8** |
| Empathy: good calls wrongly failed / faults missed | 12 / 1 | 12 / 1 | **9** / 1 |

Paired McNemar on all judged items: ft6 vs ft5 p = 0.60, ft6 vs old p = 1.00, ft5 vs old p = 0.70. No per-check difference is
significant (smallest p: ft6 vs ft5 on Paraphrasing, 0.12).

## Pre-declared success criteria for ft6 (from the plan)
| Criterion | Result |
|---|---|
| Beats ft5 on judged items | **No** (272 vs 276) |
| Beats ft5 on final-score error | Yes, barely (10.8 vs 10.9) |
| Rapport within 2 calls of ft5 | Yes (43 vs 45) |
| Fewer Empathy false fails than ft5 and old | Yes (9 vs 12 and 12) |

**Verdict: ft6 is not "better" by the criteria set in advance.** The three models are statistically indistinguishable on AG-C
(77.7% to 78.9%). ft6 did fix what it targeted (fewest Empathy false fails) but lost a little on Paraphrasing and Probing.

## What it means
- Retraining on more AI-written data has plateaued for this pipeline: three model generations land within 4 items of each other.
- The largest error sources are the same for every model and sit in the app, not the model: Confirmed resolved (21-23 of 50
  wrong; the app reads only the last 10 lines), Took ownership (13 wrong for all three; the deflection phrase list misses new
  wordings), and Empathy windows opened on any upset-looking line.
- Every number is against one AI author's keys on 50 calls; a human review of the disagreements is still missing.

Probes: `laya-finetuning/inputs/Test (results)/Laya probes/exam_*-agc.json` (no snippet text). Scored with `laya-finetuning/eval/cutoff_eval.py` functions.
