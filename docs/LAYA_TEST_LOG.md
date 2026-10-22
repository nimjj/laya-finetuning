# Laya vs Ollama test log: Main tests, 2026-10-12

## What was run
- **Calls:** the 4 hand-graded calls in `inputs/Main tests/`. The expected scorecards are in `expected/` (graded by Claude, not yet human-reviewed).
- **Ollama:** `origin/version-10` (llama3.1 + nomic-embed-text), run from a local worktree.
- **Laya:** `version-10-laya` (English checkpoint, CPU).
- **Same setup for both:**
  - The 11 criteria from `resources/criteria_config.json`, sent inline, with no database.
  - The profanity auto-fail checks agent lines only.
  - The service ran on the PC (no Docker), one engine at a time.
- **Results:** `inputs/Test (results)/Main tests (ollama|laya)/`.

## Scores

| Call | Expected | Ollama | Laya |
|---|---|---|---|
| 1 Excellent (22 min) | 100.0 | 100.0 | 61.7 |
| 2 Good (17 min) | 88.3 | 83.3 | 68.3 |
| 3 Okay (22 min) | 56.7 | 78.3 | 56.7* |
| 4 Bad (16 min) | 13.3 | 23.3 | 20.0 |
| Items matching expected | | 40/44 (91%) | 34/44 (77%) |
| Mean score error | | 9.2 | 16.3 |
| Time per call | | ~6.4 min | ~8.5 s |

\* Call 3 is correct by coincidence: a wrong Paraphrasing PASS and a wrong Resolved FAIL cancel out.

Ollama keeps the calls in the right order. Laya ranks the Excellent call below the Good one.

## Item results (✗ = disagrees with expected)

| Item | Ollama | Laya |
|---|---|---|
| Branding, Verified customer, Personalized | 12/12 | 12/12 |
| Took ownership | 4/4 | 4/4 |
| Hold time and Dead Air | 3/4 (✗ call 2) | 3/4 (✗ call 2) |
| Empathy | 3/4 (✗ call 3) | 2/4 (✗ calls 1, 2) |
| Paraphrasing | 2/4 (✗ calls 3, 4) | 3/4 (✗ call 3) |
| Active listening | 4/4 | 3/4 (✗ call 2) |
| Build rapport | 4/4 | 3/4 (✗ call 4) |
| Probing | 4/4 | 3/4 (✗ call 1) |
| Confirmed resolved | 4/4 | 1/4 (✗ calls 1, 2, 3) |

## Laya's raw scores
These come from a re-run that recorded Laya's output. The scores matched the service run exactly.

"Pass score" is P(yes) for checks where yes means PASS (Empathy, Paraphrasing, Probing, Resolved). For Rapport and Ownership, where yes means FAIL, it is 1 − P(yes).

| Check | Cutoff | Should PASS | Should FAIL | Can a cutoff separate them? |
|---|---|---|---|---|
| Confirmed resolved | 0.80 | 0.725, 0.737, 0.741 | 0.677 | Yes at ~0.70, but the margin is only 0.05 |
| Empathy | 0.78 | 0.780, 0.725, 0.656 | 0.567, 0.639 | Barely (0.656 vs 0.639) |
| Paraphrasing | 0.50 | 0.527, 0.646 | **0.658**, 0.499 | **No.** The call with no paraphrase scores highest. |
| Build rapport | 0.81 | (no lines flagged) | **0.851** (P(rude) = 0.149) | **No.** Clearly condescending lines are rated polite. |
| Probing | 0.60 | **0.582**, 0.696, 0.826 | 0.506 | Yes, once the input is fixed (see below) |
| Took ownership | 0.52 | 0.814 | 0.286 | Yes, with a wide margin |
| Active listening | 0.19 | no Laya call | no Laya call | Not tested: the pre-filter sent nothing |

## Where to focus Laya training

### 1. Build rapport and observed professionalism: high priority
- **The miss:** in call 4, Laya rated these agent lines as polite, with P(rude) = 0.15:
  - "You should have restarted the router before you called, that's the first thing anyone should do."
  - "That's basic stuff."
  - "It's not difficult."
  - "Obviously if you want the full 500…"
- **Why training, not a cutoff:** Laya treats condescension as polite when there is no insult or swear word.
- **Training data:**
  - Rude: condescending, blaming, belittling and dismissive lines, labelled rude even without insults.
  - Not rude: ordinary professional lines that contain the same trigger words ("obviously", "as I said"), so the model learns the tone rather than the words.

### 2. Paraphrasing: high priority
- **The miss:** call 1 has a textbook paraphrase ("Let me make sure I've got the full picture… Is that right?") but scored only 0.53. Call 3 never restates the problem, only asks follow-ups that reuse the customer's words ("Which light is blinking orange?"), yet scored 0.66.
- **Why training:** no cutoff works. Laya can't tell restating the problem from asking about it. Ollama's embedding method also failed here (it passed every call).
- **Training data:**
  - Paraphrase: the customer's opening plus an agent summary that restates it.
  - Not a paraphrase: the same opening plus agent questions that echo the customer's words without restating.
- **Input fix first:** drop the verification and greeting lines from the agent text. In calls 1 and 2 they take up most of the 150-word agent budget.

### 3. Confirmed the issue is resolved: high priority (largest score impact)
- **The miss:** this fails every good call, which costs about 10 final-score points per call. Calls 1 and 2 end with an explicit "Would you say the issue is resolved?" / "Yes, completely", yet score only 0.72–0.74.
- **Short-term fix:** lower the cutoff from 0.80 to ~0.70. That fixes this set.
- **Why training too:** the margin to the bad call (0.68) is only 0.05, which is too thin to trust.
- **Training data:**
  - Resolved: endings where the agent explicitly checks and the customer confirms.
  - Not resolved: endings that stop without a check, where the customer says it still fails, or where the call is handed off. Include long endings with small talk and surveys mixed in.

### 4. Empathy and acknowledgment: medium priority
- **What Laya does:**
  - Good replies score 0.73–0.78. Example: "Freezing in the middle of a pitch to a new client is about the worst timing there is."
  - Cold replies score 0.57–0.64. Example: "They can help with that." in reply to a customer threatening to cancel.
- **Why it's medium:** the order is right, but the gap is too small for one cutoff.
- **Input fix first:** call 2's only snippet was a calm problem description, picked because of a sentiment drop, with no emotion to acknowledge. The real frustrated moment was skipped because the agent said "understand"/"frustrating".
- **Training data:** pairs of a frustrated customer turn with a warm reply, and the same turn with a cold, purely procedural or dismissive reply.

### Working: no training needed now
- **Took ownership:** good separation (0.81 vs 0.29). Keep it as a regression check.
- **Probing:** Laya's verdicts are right (0.70 and 0.83 for real diagnostic questions, 0.51 for "What's the issue?" only). Call 1 failed because of the input, not the model: see the next section.

## Pipeline fixes (not Laya training)
These caused wrong grades without Laya being involved, or before it was. Fix them first; otherwise training data will contain the same errors.

| Item | Problem | Fix |
|---|---|---|
| Probing | The 100-word budget is used up by boilerplate before the real questions are reached. In call 1 Laya saw only "Who do I have the pleasure of speaking with…", "confirm the service address…", "what's going on with the service today?" and "Do you mind if I ask a few questions first?". Whole turns are sent, including the statements before the question. | Extend the boilerplate filter to cover these phrasings, and send only the question sentence of each turn. |
| Active listening | Laya was never asked. In call 2 the agent re-asked two answered questions, with difflib similarity 0.23 and 0.64, both under the 0.70 cutoff. The Ollama version caught them with embeddings. | Detect "question already answered" instead of near-identical wording (embeddings, or lower the cutoff to ~0.55 and let Laya decide), then train if Laya then misjudges. |
| Hold time and Dead Air | The rule counts an announced hold with check-ins as 2 dead-air gaps. Both engines fail call 2. | Skip gaps that follow a hold announcement ("place you on a brief hold", "bear with me") or end in a check-in or a thank-you for waiting. |
| Empathy | The sentiment pre-filter picks problem descriptions, and the keyword skip hides real frustrated moments. | Trigger on customer emotion words as well as sentiment drops. Check the agent's reply rather than skipping on keywords. |

## Caveats
- **Sample size:** 4 calls is a small sample, and most checks got one Laya call per call. Treat this as a direction, not a measurement.
- **Labels:** the calls and expected grades were written by Claude. A human should spot-check them before any training data is built from them.
- **Training data needed:** a few hundred balanced, human-labelled examples per category above, taken from real calls. This should run on a GPU.
- **Order of work:** apply the pipeline fixes and the Resolved cutoff change first, re-run `python Scripts/batch_test.py main --label laya` and `bulk`, and only then start training.

---

# Round 2: pipeline fixes (2026-10-12)

## What changed
All changes are in `src/services/rule_engine.py` and `dynamic_evaluator.py`, uncommitted.

| Item | Change |
|---|---|
| Hold time and Dead Air | A gap after an announced hold, or one the agent ends with "thanks for holding/waiting", isn't dead air (up to 120 s). |
| Empathy | Bug fix: the sentiment drop is measured against the customer's own earlier turns. It used to include agent turns, so call 1 had 33 candidates and now has 7. Frustration words ("nightmare", "third time" …) also trigger. The apology-keyword skip is kept. |
| Active listening | Question sentences are compared instead of whole turns. A customer "like I said / I mentioned" reply pairs the question with the earlier one and is sent along. |
| Probing | Only question sentences are sent; the opener and check-in phrasings were added to the boilerplate list. The customer-problem text skips account-detail answers. |
| Paraphrasing | Greeting and verification lines and account-detail answers are removed from the input. |
| Confirmed resolved | Cutoff 0.80 → 0.73. |

### How the Resolved cutoff was chosen
It was picked on the 35 `b_*` bulk calls, whose filenames name the missing confirmation, so it isn't tuned to the Main calls. Laya barely separates them: no-confirmation endings score 0.66–0.75 and confirmed ones 0.47–0.79. No cutoff is good:

| Cutoff | b_* confirmed passed | b_* missing confirmation failed | b_* balanced | Main good passed | Main bad failed |
|---|---|---|---|---|---|
| 0.68 | 30/31 | 1/4 | 0.61 | 3/3 | 1/1 |
| 0.70 | 21/31 | 1/4 | 0.46 | 3/3 | 1/1 |
| **0.73** | 19/31 | 3/4 | **0.68** | 2/3 | 1/1 |
| 0.75 | 19/31 | 3/4 | 0.68 | 0/3 | 1/1 |
| 0.80 (old) | 0/31 | 4/4 | 0.50 | 0/3 | 1/1 |

## Results
Result folders: `Main tests (laya-v2)` and `Bulk tests (laya-v2)`. The bulk "before" run is `Bulk tests (laya)`. Run `python Scripts/compare_results.py ollama laya laya-v2` for the full tables. The raw Laya probabilities are in `laya-finetuning/inputs/Test (results)/Laya probes/` (`probe_laya.json` before, `probe_laya-v2.json` after); rebuild them with `python laya-finetuning/eval/probe_laya.py <out.json>` and the cutoff tables with `python laya-finetuning/eval/laya_cutoffs.py <probe.json>`.

| | Ollama | Laya before | Laya v2 |
|---|---|---|---|
| Main scores (expected 100 / 88.3 / 56.7 / 13.3) | 100 / 83.3 / 78.3 / 23.3 | 61.7 / 68.3 / 56.7 / 20.0 | 78.3 / 83.4 / 60.0 / 30.0 |
| Main items matching | 40/44 | 34/44 | 36/44 |
| Main mean score error | 9.2 | 16.3 | 11.7 |
| Bulk b_* items matching | – | 332/372 (89%) | 348/372 (94%) |

Laya v2 still ranks the Excellent call (78.3) below the Good one (83.4).

### Per item (Main tests | b_* calls)

| Item | Before | v2 | Verdict |
|---|---|---|---|
| Hold time and Dead Air | 3/4 · 34/34 | **4/4** · 34/34 | Keep. Fixed call 2 with no bulk regressions. |
| Probing | 3/4 · 30/34 | **4/4** · 30/34 | Keep. Fixed call 1. The 4 bulk misses are "no probing" calls scoring 0.57–0.68 against a 0.60 cutoff; real probing scores 0.745 or more. **A cutoff of 0.70 separates all 34 b_* calls and all 4 Main calls** (recommended next change). |
| Confirmed resolved | 1/4 · 4/33 | **3/4** · **22/33** | Keep for now. This is the largest gain, but Laya can't really tell the endings apart (see table above). Still a training priority. |
| Empathy | 2/4 · 34/34 | 2/4 · 34/34 | No change in outcome. The bug fix cut noise, but the 0.78 cutoff still fails calls 1 and 2. Training. |
| Paraphrasing | 3/4 · 27/34 | 2/4 · 28/34 | Inconclusive. On b_* the cleaner input separates better (best balanced accuracy 0.67 → 0.80), but at the 0.50 cutoff it flips real calls both ways and now passes call 4. Training. |
| Active listening | 3/4 · 33/33 | **2/4 · 30/33** | **Regression.** See below. |
| Build rapport | 3/4 · 33/33 | 3/4 · 33/33 | Not changed (training). |

### Why Active listening regressed
- **The attached reply confuses Laya.** Sending the customer's "…I just said, it's red." with the pair drops Laya's repeat score for the planted bulk repeats from 0.89 to 0.51, under the 0.81 needed to fail. Without that line they score 0.895 again.
- **Call 2's real repeats still pass.** Without the reply line they score 0.71 and 0.74, still under 0.81.
- **New false fail on call 3.** Sentence-level comparison now catches call 3's status re-check ("What is the globe light doing now?" / "What's the light doing?"). Laya rates it 0.82, a repeat, so call 3 now fails wrongly.
- **Conclusion:** Laya rates asking for a changing status again as more of a repeat than re-asking for information the customer already gave. A filter can't fix that; it needs training examples of both.

### Real and v8 calls (no item labels)
- **Resolved:** now passes on the high, above-average and perfect calls.
- **Paraphrasing:** flipped both ways, failing two strong calls and passing three weak ones (real_long midlow, low and poor).
- **Probing:** flipped on 3 calls.
- **Effect on real_long scores:** they are less spread out. Before they ran from 90 down to 41.6 in tier order. Now mid, midlow, low and poor all score 51.7. Paraphrasing and Probing account for most of this.

## Updated training focus (most important first)
1. **Active listening:** repeats of information already given vs. re-checking a changing status.
2. **Confirmed resolved:** explicit confirmation vs. an ending without a check.
3. **Paraphrasing:** restating the problem vs. asking about it in the customer's words.
4. **Build rapport:** condescension without insults.
5. **Empathy:** warm vs. cold replies to a frustrated customer.


---

# Round 3: Phase 1 input changes (2026-10-16)

Code: `fcc6869` (all input-building moved to `src/services/laya_inputs.py`, byte-identical inputs on 80 calls), `9050b41` (Rapport chunk scan, Active-listening snippet, Probing cutoff), then an interim Rapport cutoff (below). Result folders: `Main tests (laya-v3|laya-v3.1)`, `Bulk tests (laya-v3|laya-v3.1)`; raw probabilities in `Laya probes/probe_laya-v3.json`. `laya-v3` is the first run (Rapport cutoff 0.81); `laya-v3.1` is the final Phase 1 state (Rapport cutoff 0.50).

## What changed
| Item | Change |
|---|---|
| Rapport | Every agent line is checked, in chunks of at most 8 lines / 120 words, one Laya call per chunk; one rude chunk fails the item. The 27-phrase gate is gone. Question reworded for chunks. |
| Active listening | Snippet is first question / the customer's answer / second question (up to 3 pairs). The customer's "like I said" reply is no longer sent. Similarity cut 0.70 to 0.55. Question reworded. |
| Probing | Cutoff 0.60 to 0.70. |

## Results (answer key = Claude-written grades, not human-reviewed)
| | Ollama | Laya v2 | Laya v3 (0.81) | **Laya v3.1 (final)** |
|---|---|---|---|---|
| Main items matching (of 44) | 40 | 36 | 35 | **37** |
| Main scores (expected 100 / 88.3 / 56.7 / 13.3) | 100 / 83.3 / 78.3 / 23.3 | 78.3 / 83.4 / 60.0 / 30.0 | 71.7 / 76.7 / 60.0 / 23.3 | 78.3 / 83.4 / 66.7 / 30.0 |
| Main mean score error | 9.2 | 11.7 | 13.3 | **13.3** |
| Bulk `b_*` items matching (of 372) | n/a | 348 | 326 | **351** |
| Time per call, Main / bulk mean | ~6.4 min | ~8.5 s | 13.5 s / 9.5 s | **22.4 s / 12.8 s** |

Laya still ranks the Excellent call (78.3) below the Good call (83.4). More items are right than in v2, but the mean score error is higher: in v2 a wrong Active-listening FAIL on call 3 cancelled a wrong Paraphrasing PASS; with the Active-listening fix the Paraphrasing error shows (60.0 became 66.7 against 56.7).

## Per check
- **Probing:** 4/4 Main, 34/34 bulk (was 30/34). The 0.70 cutoff does what the Round 2 probe predicted.
- **Active listening:** bulk 33/33 (was 30/33). Planted repeats score 0.82-0.85 against a 0.81 cutoff; every other call that produced a snippet scores 0.55-0.81 (the highest, `real_20min_low`, 0.807), so the margin is thin. The genuine repeats in Main call 2 still score only 0.73 and are missed (Main 3/4).
- **Rapport: the untrained model has no signal on this question.** Across all 44 labelled calls the highest chunk P(rude) is 0.19-0.22 for the five rude calls (0.199-0.217) and for the median polite call (0.198; maximum 0.488). No cutoff separates them. The first cutoff, 0.81 (P(rude) above 0.19), sat on that floor and failed 29 of 33 polite bulk calls and 3 of 4 Main calls (Main 1/4, bulk 4/33). The interim cutoff 0.50 never fails a call: bulk 29/33 (the 4 planted rude calls are missed), Main 3/4 (the rude call 4 is missed, as in v2). This needs fine-tuning, then a cutoff tuned at call level.
- **Unchanged and still to train:** Empathy 2/4 (bulk 34/34), Paraphrasing 2/4 (bulk 28/34), Confirmed resolved 3/4 (bulk 22/33).

## Cost
Rapport now makes about 8 Laya calls per call (mean 7.9, up to 21 for Main call 1). With nothing failing early, a Main call takes 22.4 s on CPU against a 15 s target. Planned mitigation if it stays: score the chunks in one batched forward pass.

# Round 4: fine-tuned checkpoint (2026-10-17)

Checkpoint: laya-training run `ft2-20261017-0354`, variant `softce` (full fine-tune of the English checkpoint on Claude-written synthetic data; see laya-training/README.md). Served with `LAYA_CHECKPOINT` set; the fine-tuned cutoffs in `FINETUNED_CUTOFFS` (dynamic_evaluator.py) apply only then. Results come from the running service (`batch_test.py main|bulk --label laya-ft`); the full per-call tables (`Docs/LAYA_ROUND4_COMPARISON.md`) were generated by `python Scripts/compare_results.py ... --out` and removed from the repo on 2026-10-22; the last copy is in commit `8a6842b`.

| | Ollama | Laya v2 | Laya v3.1 (untrained) | Laya fine-tuned |
|---|---|---|---|---|
| Main items matching (of 44) | 40 | 36 | 37 | **41** |
| Main scores (key 100 / 88.3 / 56.7 / 13.3) | 100 / 83.3 / 78.3 / 23.3 | | 78.3 / 83.4 / 66.7 / 30.0 | 100 / 76.7 / 50.0 / 30.0 |
| Main mean score error | 9.2 | 11.7 | 13.3 | **8.75** |
| Bulk b_* items matching (of 372) | n/a | 348 | 351 | **358** |
| Time per call (CPU) | ~6.4 min | ~8.5 s | 22.4 s | 21.4 s (Main), 12.0 s (all 64 bulk) |

Caveats that matter:
- The answer key and all training data are Claude-written. Nothing here is human-labelled.
- The Main/bulk calls were used to look at failures between training rounds and to choose the Rapport cutoff (0.20, call level; all other fine-tuned cutoffs came from dev data). They are no longer an independent check; no text from them was copied into training data.
- Rapport still flags dismissive lines in the ownership/empathy-defect bulk calls (those are labelled Rapport PASS by filename) and is not reliable on natural polite calls with this cutoff beyond what is listed.
- Speed is still above the 15 s target (planned fix: batch the Rapport chunks into one forward pass).

# Round 5: AG50, an independent test (2026-10-18)

50 calls of 10 to 20 minutes with sentiment scores, **written and graded by Antigravity** (not Claude, not human-reviewed; brief `ANTIGRAVITY_TEST_BRIEF.md`, removed on 2026-10-22; read it with `git show a7ace67:Docs/<name>`, files in `laya-finetuning/inputs/AG50/`). The four rule items, auto-fail detection and score maths of the key were re-checked against the app's code: 0 mismatches. Full report: `laya-finetuning/docs/AG50_REPORT.md`. Its charts page, numbers file and per-call tables (`AG50_DASHBOARD.html`, `ag50_stats.json`, `AG50_RESULTS.md`) are generated on demand and were removed from the repo on 2026-10-22; how to regenerate them is in `Docs/README.md`.

| | Stock Laya | Fine-tuned Laya | Ollama |
|---|---|---|---|
| 7 judged items matching the key (of 350) | 226 (64.6%) | 252 (72.0%) | **275 (78.6%)** |
| All 11 items (of 550) | 426 (77.5%) | 452 (82.2%) | **471 (85.6%)** |
| Mean score error / bias | 16.0 / -4.7 | **12.7 / +1.2** | 12.8 / +11.7 |
| Time per call | 17.1 s | 16.2 s | 386.2 s |

- Ollama beats fine-tuned Laya on the judged items by 6.6 points (95% CI 0.9 to 12.3, McNemar p = 0.014); fine-tuning beat stock by 7.4 points (p = 0.005). The 92% on Eval50 (same author as the training data) was optimistic.
- Pipeline: on long calls the snippets often miss the evidence. 6 of 15 Active-listening faults and 6 of 17 Ownership faults never reach the model; Empathy is checked per upset moment but the key (and the QA definition) is call-level, giving 25 false alarms; Rapport's any-chunk rule on about 10 chunks per call gives 31% false fails; Paraphrasing and Resolved see about 200 of about 1,900 words.
- Training clearly raised ranking quality (AUC) only for Rapport (+0.24, CI 0.08 to 0.42). A Probing cutoff tuned on AG50 (balanced accuracy 0.65 -> 0.79) was tested on the bulk set and rejected: it raises false fails from 1 to 12 of 33 good calls.
- `laya-finetuning/eval/probe_laya.py` gained `--suite <folder>` (default behaviour unchanged). `laya-finetuning/eval/ag50_analysis.py` and `laya-finetuning/eval/build_ag50_dashboard.py` regenerate the statistics and the dashboard.

# Round 6: flow v2, windows chosen by call structure (2026-10-19)

Full write-up: `Docs/FLOW_V2.md`. Lab reports: `Docs/FLOW_V2_LAB.md`, `Docs/FLOW_V2_REGRESSION.md`. Same fine-tuned checkpoint and cutoffs; only what the model is shown changes (Empathy: one window per distinct outburst, strict rubric chosen by the owner; Paraphrasing: restatement-cue gate plus a tight window; Ownership: wider deflection list). On when `LAYA_CHECKPOINT` is set (override with `LAYA_FLOW`).

| | Flow v1 | Flow v2 | Ollama |
|---|---|---|---|
| AG50 judged items (of 350), a development set | 252 (72.0%) | **281 (80.3%)** | 275 (78.6%) |
| AG50 mean score error | 12.7 | **9.0** | 12.8 |
| Main items (of 44) | 41 | **42** | 40 |
| Bulk items (of 372) | 358 | **359** | n/a |
| AG50 time per call | 16.2 s | 15.4 s | 386.2 s |

- v2 vs Ollama on AG50 judged items: +1.7 points, 95% CI -3.7 to +7.1, McNemar p = 0.58: not distinguishable. Gain over v1: +8.3 points, p < 0.001, but AG50 was used to design v2.
- Two regressions on the way (bulk 358 -> 347), both found by rerunning Main and bulk, both fixed: late outbursts with positive sentiment were missed; "you'll have to wait" matched the Ownership phrase.
- Still weak: Active listening (0 of 15 caught), Rapport (31% false fails), Probing, Resolved. Need training data.

# Round 7: retrained on Antigravity data, sealed exam (2026-10-21/22)

Full write-up: `laya-finetuning/runs/ft5-ag/RESULT.md`. New training data: 100 Antigravity-written calls with turn-level markers
(AG-T; 77 were found padded with stock filler by the author's generator and were restored or rewritten before training).
New model `ft5 softce` vs the old `final-softce-3`, each at cutoffs committed before the exam (57304af). Exam: AG-B (50) + AG-B2
(12, filling AG-B's gaps), sealed, probed once. Keys AI-written, not human-reviewed.

| | Old | New |
|---|---|---|
| Judged items right (of 434) | 317 (73.0%) | 323 (74.4%), McNemar p = 0.49 |
| Rapport | 45/62 | **56/62** (p = 0.003) |
| Empathy | 39/62 | 33/62 (p = 0.11) |
| Probing | 51/62 | 47/62 (p = 0.22) |
| Final-score mean absolute error | 9.8 | 11.9 |

- Overall no significant change; Rapport clearly better; Empathy and Probing worse (not significant).
- Both models score about 70% on AG-B against about 81% on AG50: the AG50 numbers were optimistic.
- Resolved (about 50% for both) and Ownership (48/62 for both) are limited by the app's windows and phrase lists, not the model.
- Ollama was not run on AG-B.

# Round 8: ft6 (targeted retrain) on a fresh sealed exam, AG-C (2026-10-22)

Full write-up: `laya-finetuning/runs/ft6/RESULT.md`. ft6 added 141 labelled moments to AG-T (85 "upset-looking but fine"),
Probing rows, and an Empathy length balance. Old, ft5 and ft6 were each scored once on AG-C (50 sealed calls, AI-written keys) at
cutoffs committed beforehand.

| | old | ft5 | ft6 |
|---|---|---|---|
| Judged items right (of 350) | 273 (78.0%) | 276 (78.9%) | 272 (77.7%) |
| Final-score mean absolute error | 11.5 | 10.9 | 10.8 |
| Empathy good calls wrongly failed | 12 | 12 | 9 |

- No difference is statistically significant (McNemar p 0.60 to 1.00). ft6 does not meet its pre-declared "better" criteria.
- Further training on AI-written data has plateaued; the remaining errors are mainly in the app's windows and phrase lists
  (Resolved, Ownership, Empathy triggers), which affect every model equally.

## Decision (2026-10-22)
Production model stays `final-softce-3` (stage 3, flow v2, no Active-listening second source). Over the two sealed exams (AG-B+AG-B2
and AG-C, 112 calls) it is statistically tied with ft5 (590 vs 599 of 784 judged items) and its final scores are closest to the keys
(mean error 10.6 vs 11.5). ft5/ft6 remain available (see `laya-finetuning/runs/CHECKPOINTS.md`). Nothing in `.env` or the cutoffs changed.
