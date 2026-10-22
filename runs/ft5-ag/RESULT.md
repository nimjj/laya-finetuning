# ft5 (clean Antigravity data) vs the old fine-tuned model: sealed exam, 2026-10-22

All keys are AI-written (Antigravity), none human-reviewed. AG-B and AG-B2 were written in separate sessions, sealed by commit
(c12a8c3, bdd74d0), and probed exactly once, after the model choice and cutoffs were committed (57304af).

## What was compared
| | Old model | New model |
|---|---|---|
| Checkpoint | `final-softce-3` (stage 3, Claude-written data) | `ft5-20261021-1621/final-softce` (stage 3 data + 100 clean AG-T calls) |
| Flow | v2 | v2 with the Active-listening second source (`LAYA_AL_SOURCE2=1`) |
| Cutoffs | `exam_cutoffs_old.json` (in force since 2026-10-17) | `exam_cutoffs_softce.json` (same, Active listening 0.92) |

## Sealed exam: AG-B (50 calls) + AG-B2 (12 calls), 7 judged items each (434)
| Check | Old right | New right | Only old right / only new right | McNemar p |
|---|---|---|---|---|
| Build rapport | 45/62 | **56/62** | 1 / 12 | **0.003** |
| Active listening | 46/62 | 48/62 | 5 / 7 | 0.77 |
| Paraphrasing | 58/62 | 60/62 | 0 / 2 | 0.50 |
| Confirmed resolved | 30/62 | 31/62 | 4 / 5 | 1.00 |
| Took ownership | 48/62 | 48/62 | 0 / 0 | 1.00 |
| Probing | **51/62** | 47/62 | 5 / 1 | 0.22 |
| Empathy | **39/62** | 33/62 | 8 / 2 | 0.11 |
| **All 7** | **317/434 (73.0%)** | **323/434 (74.4%)** | 23 / 29 | **0.49** |

Final score vs key: old mean absolute error 9.8 (bias +0.5), new 11.9 (bias -1.4). AG-B alone: old 244/350, new 246/350 (p 0.88).
AG-B2 alone: old 73/84, new 77/84 (p 0.29).

## What it means
- **No overall difference** (+1.4 points, p 0.49). The new model is not a clear upgrade.
- **Rapport is a real, significant gain** (12 calls fixed, 1 broken). The long-call false-fail problem the old model had is largely gone.
- **Empathy and Probing moved the wrong way** (not significant, but consistent with AG50 for Probing). Empathy errors cost 35 points
  each, which is why the final-score error rose.
- **Both models are much weaker on AG-B than on AG50** (about 70% vs 81% of judged items). AG50 was used to design flow v2 and to
  pick cutoffs, so its numbers were optimistic, as expected. AG-B has customer-only noisy sentiment, like production.
- **The weakest checks are pipeline problems, not model problems**: Resolved is at chance for both (30-31/62; the last-10-lines
  window), Ownership 48/62 for both (the deflection phrase list was tuned on AG50 and misses AG-B's phrasings), and on AG-T the
  Empathy windows contained only 19% of authored unhandled outbursts.
- Not measured: Ollama on AG-B (needs the Ollama copy and about 6.5 hours of CPU). No claim against Ollama can be made from this.
- AG-B and AG-B2 are now spent for these two models: any change designed after reading this makes them development sets.

Probes: `inputs/Test (results)/Laya probes/exam_*.json` (stored without snippet text). Scoring: `Scripts/cutoff_eval.py --cutoffs`.
