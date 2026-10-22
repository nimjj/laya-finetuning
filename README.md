# Fine-tuning Laya to replace Ollama in the QA grading pipeline

> **Where this lives now (2026-10-20):** this folder is part of the QA repository (`nimjj/QA-system`, branch `laya-finetuning`); it used to be the separate `nimjj/laya-finetuning` repo, whose history is kept. The app is the repo root, so older notes below that say `qa-analysis/` mean the repo root and `laya-training/` means this folder. Setup on a new PC: `docs/NEW_PC_SETUP.md`. Latest results: `runs/ag50/RESULT.md` and `Docs/FLOW_V2.md` at the repo root.

> Moving to another PC? See `docs/NEW_PC_SETUP.md` (what to copy, setup steps, checks, and how to carry the Claude Code notes).

## This folder is the Laya segment of the repo (layout since 2026-10-22)

The repository has two segments. The **QA application** is at the repo root. **Everything about the Laya model lives here**: training data, row builders, Colab notebooks, the testing and evaluation scripts, every test set and its results, the first benchmark, the experiment weights, and the logs of what was tried. The app keeps only its production weights (`../models/final-softce-3`) and two folders of sample calls.

```
laya-finetuning/
├── README.md              this file: the training project, its plan, status and results
├── 00_smoke_test.ipynb ... 04_train_eval_ft6.ipynb    Colab notebooks that train a checkpoint on a GPU
├── data/                  training material: fragments, rows, the frozen questions and hashes, review sheets
├── tools/                 row builders, notebook builders, the trainer, manifests, the freeze check; paths.py finds the app
├── eval/                  testing and evaluation scripts (validate_calls, probe_laya, v3_compare, v3_gate_lab, golden, ...)
├── inputs/                test sets AG50, AG-T, AG-B, AG-B2, AG-C, Eval50, Tough checks; Test (results)/ with their results and probes
├── laya_eval/             the first synthetic benchmark of Laya vs Ollama
├── runs/                  results, probe files and hash records per round; CHECKPOINTS.md is the catalogue and the decision
├── checkpoints/           experiment weights ft5, ft6 (git-ignored)
└── docs/                  LAYA_TEST_LOG.md, AG50_REPORT.md, data plan, labelling guide, generation notes, new-PC setup
```

**Run the scripts from the repo root**, for example `python laya-finetuning/eval/validate_calls.py --suite agt` or `python laya-finetuning/tools/export_checks.py --check`. They import the app code (`src/...`) through `tools/paths.py` (and `eval/_roots.py`), which treat the parent of this folder as the app. To point them at another checkout of the app, set the environment variable `QA_APP_DIR`.

**Where things moved** (older notes in this folder and in git history use the old paths):

| Old path | New path |
|---|---|
| `Scripts/` ag50_analysis, al_reach_lab, build_ag50_dashboard, choose_cutoffs, compare_eval, cutoff_eval, empathy_lab, golden, laya_cutoffs, probe_laya, v3_compare, v3_gate_lab, v3_service_test, validate_calls, window_lab | `laya-finetuning/eval/` |
| `inputs/AG50`, `AG-T`, `AG-B`, `AG-B2`, `AG-C`, `Eval50`, `Tough checks` | `laya-finetuning/inputs/` |
| `inputs/Test (results)/` AG50 (...), Eval50 (...), Laya probes | `laya-finetuning/inputs/Test (results)/` |
| `laya_eval/` | `laya-finetuning/laya_eval/` |
| `Docs/LAYA_TEST_LOG.md`, `Docs/AG50_REPORT.md` | `laya-finetuning/docs/` |
| `laya-finetuning/checkpoints/final-softce-3` (the production weights) | `models/final-softce-3` at the repo root; set `LAYA_CHECKPOINT=models/final-softce-3` in `.env` |
| (stayed in the app) | `Scripts/` batch_test, compare_results, check_prompt_sizes, dump_laya_inputs; `inputs/Main tests`, `inputs/Bulk tests` and their result folders; `Docs/FLOW_V2*.md` |

**Document status:** review copy for the AI/ML engineer, written 2026-10-16. Everything below is marked **Done**, **In progress** or **Planned**. Section 9 lists the specific points we want challenged. `docs/DATA_PLAN.md` is the working copy of the phase table and data volumes; if the two ever differ, this README is the one reviewed.

## 1. One-paragraph summary

We grade telephony-support calls against 11 criteria with a service (`qa-analysis`) that combines deterministic Python rules with **Laya**, a local, non-generative yes/no classifier (ModernBERT-large encoder, 421M parameters, English checkpoint). Ollama/llama3.1 was removed in version 10. In a first test on 4 hand-written calls Laya made more mistakes than Ollama (mean score error 11.7 after pipeline fixes vs Ollama's 9.2). We propose a **full fine-tune of Laya's English checkpoint on synthetic, extractor-built examples** for the five checks where it is weak, with replay data and regression checks to avoid breaking the rest.

**Decision of 2026-10-16 (time pressure; the owner delegated the ML calls):** the Gemini-written test set and all human labelling were dropped. **Every train, dev and test row was written and labelled by Claude.** To keep the test as far from the training data as possible, the test rows use industries, agent personas and looser wording that the training rows never contain. That makes the test a fair check of generalisation *within Claude's writing*, but **it is not an independent or human-labelled test**. There are no real call transcripts, so every result is "measured on Claude-written synthetic calls", never "proven on real calls". The data is built in stages (small first, scale only if the learning curve says so). Training runs on a Colab L4 GPU (about 15 minutes per run, measured); serving stays on CPU.

**Result so far (2026-10-17, details in `runs/ft3-stage3/RESULT.md`):** after three training rounds the fine-tuned model scores 41/44 items on the 4 Main calls with a mean score error of 8.75 (Ollama 40/44, 9.2; untrained Laya 37/44, 13.3), and 358/372 bulk items (untrained 351). The first two rounds were not good enough on the natural Main calls (errors 16.3 and 15.4); the cause was that training snippets were half the length and much less natural than real ones, fixed with padded rows (stage 2) and complete natural calls cut by the extractors (stage 3). **Limits:** all data, tests and the answer key are Claude-written; the Main/bulk calls were used to pick the Rapport cutoff and to see failure types, so they are no longer independent; the custom-criteria safeguard agrees with the untouched model on 82% of questions (target 90%); speed is 21.4 s per Main call (target 15 s).

**Independent check (2026-10-18, `runs/ag50/RESULT.md`):** on 50 long calls written and graded by a different AI (Antigravity), fine-tuned Laya matched 72.0% of the 7 model-judged items against 64.6% for stock Laya and **78.6% for Ollama** (the 6.6-point gap to Ollama is statistically real, p = 0.014). It is 24 times faster and its final scores are nearly unbiased, but it is **not ready to replace Ollama**: a shadow-mode trial is the supported next step. Much of the loss happens in the app's snippet-building rather than in the model, so the next iteration fixes those inputs first (section 6, phase 12). **Update 2026-10-19:** changing only what the model is shown for Empathy, Paraphrasing and Ownership (`../Docs/FLOW_V2.md`, no retraining) lifted AG50 to 80.3% of the judged items (a development set; Ollama 78.6%, not distinguishable), with Main 42/44 and bulk 359/372 not regressing. Active listening, Rapport, Probing and Resolved still need training data.

## 2. The system and where Laya sits

`POST /api/evaluate` (FastAPI, synchronous) parses a transcript (turns with speaker, start time, per-turn sentiment score) and grades it:

| Criterion | Decided by | Deduction if FAIL | Category (weight) |
|---|---|---|---|
| Branding and Survey Check | rule (exact phrases in first/last 4 agent lines) | 15 | Soft Skills (0.333) |
| Hold time and Dead Air | rule (gaps >30 s, announced holds exempt) | 15 | Soft Skills |
| Personalized the call | rule (customer name appears in an agent line) | 15 | Soft Skills |
| **Empathy & Acknowledgment** | **Laya** | 35 | Soft Skills |
| **Build rapport / professionalism** | **Laya** | 20 | Soft Skills |
| **Paraphrasing** | **Laya** | 15 | Technical Knowledge (0.667) |
| Verified customer | rule (PIN/address/security question in first 240 s) | 25 | Technical Knowledge |
| **Probing** | **Laya** | 25 | Technical Knowledge |
| **Took ownership** | **Laya** | 25 | Technical Knowledge |
| **Active listening** | **Laya** | 10 | Technical Knowledge |
| **Confirmed the issue is resolved** | **Laya** | 15 | Technical Knowledge |

Each category starts at 100 and loses the deduction per FAIL; final score = Soft x 0.333 + Technical x 0.667. Agent profanity auto-fails to 0. Escalation and Hostility also have Laya questions but are not in the reference criteria set. Tenants can add custom criteria; those go to Laya as generic questions built from the criterion's name and description.

**How Laya is used.** For each check a Python pre-filter cuts a short text snippet from the call (Laya's English checkpoint reads at most 512 tokens including the question), and Laya answers one yes/no question about it in one forward pass, returning P(yes). The service applies a per-check cutoff to P(pass) (P(yes) when "yes" means PASS, else 1 - P(yes)). Laya cannot generate text, so coaching strings are static.

**The model input contains the question text.** Laya's input is `[CLS] noul question: <instructions> [SEP] [MASK] <false-option text> [MASK] <true-option text> [SEP] <snippet> [SEP]`. The instructions and the two option texts (the "criteria") are therefore part of what a fine-tuned model learns. For four of the questions (Empathy, Ownership, Probing, Confirmed resolved) the options carry neutral labels A/B because on the English checkpoint the default "true"/"false" labels can outweigh the text. **Changing any question wording after training data is generated invalidates the data.**

## 3. Evidence so far

All numbers are from `../Docs/LAYA_TEST_LOG.md` and `../laya_eval/RESULTS.md`.

**Main tests (4 hand-written 16-22 minute calls, expected grades written by Claude, not human-reviewed)**

| | Items matching expected (of 44) | Mean score error | Time per call |
|---|---|---|---|
| Ollama (llama3.1 + embeddings) | 40 (91%) | 9.2 | ~6.4 min |
| Laya, first run | 34 (77%) | 16.3 | ~8.5 s |
| Laya, after Round 2 pipeline fixes ("v2") | 36 (82%) | 11.7 | ~8.5 s |

Laya v2 still ranks the Excellent call (78.3) below the Good call (83.4). On the 35 `b_*` bulk calls (defect named in the file name) v2 matched 348/372 items (94%).

**Where Laya is weak (measured on those calls, small samples):** Active listening (Round 2 made it worse: attaching the customer's "like I said" reply to the pair lowered the repeat score from 0.89 to 0.51, and a status re-check was rated a repeat), Confirmed resolved (scores barely separate: no-confirmation endings 0.66-0.75, confirmed 0.47-0.79; no cutoff is good), Paraphrasing (cannot tell restating the problem from echoing its words), Build rapport (condescension without insults rated polite), Empathy (right order, gap too small for one cutoff). **Working:** Took ownership (0.81 vs 0.29), Probing (once the input was fixed), Hostility, Escalation.

**Earlier synthetic benchmark (320 hand-written snippets, 8 criteria, no training, balanced accuracy on an 18-item test half per criterion):** Laya English 0.82 average vs Ollama 0.79, with the two failing on different criteria. Interval about +/-15 points; synthetic and unreviewed, so optimistic.

**Fine-tuning evidence from Laya's own docs:** on their typed-decisions benchmark a full fine-tune moves accuracy from 0.36 to 0.77-0.79; on MASSIVE intent from 0.73 to 0.94. Those are different tasks and far more data than we have.

## 4. Goal and success criteria

Goal: a fine-tuned English checkpoint that matches or beats Ollama on grading accuracy so Ollama can be fully retired.

Proposed final criteria (all on synthetic data; cutoffs are re-tuned on dev data and the test set is scored once):

1. **Main calls:** mean score error against the answer key is below Ollama's and at most 9.0, and the 4 calls rank in strict tier order. *The key is currently Claude-written and unreviewed (section 7), so this is a sanity gate, not the headline.*
2. **Trained checks, Claude-written held-out test set (not independent):** balanced accuracy at least 0.85, with the lower 95% bound at least 0.75.
   - **2b. Rapport at call level:** at most 5% of full polite calls fail Rapport. Without Gemini calls this is measured on the polite bulk calls (`b_*`, 33 calls) and the 4 Main calls, locally after integration.
3. **Regression checks:** test balanced accuracy no more than 0.05 below the untouched model, with no significant paired drop; bulk `b_*` items at least 348/372.
4. **Unlabelled real-looking calls** (`real_long_*`, `v8_*`): scores keep tier order (Spearman at least 0.8).
5. **Drift:** at least 90% agreement with the untouched model on generic (custom-criteria) questions.
6. **Calibration:** ECE at most 0.10 on the test set (reported).
7. **Speed:** at most 15 s per 20-minute call on CPU.

## 5. Proposed approach

### 5.1 What is trained
- **Full fine-tune** of the English checkpoint (`convaiinnovations/laya`, revision `7b928d828b7b0e022f929d9bd2e44165aa270148`, the snapshot used locally): same architecture and 421M parameters, new values, saved as a **new checkpoint folder**. The original is never overwritten; its sha256 is verified at every stage.
- Trained with Laya's own `laya-train` (v0.4.0, commit `3cf26cb`), not custom code, on JSONL rows `{state, questions, expected | gold}`.
- Checks to train (priority from the test log): **Active listening, Confirmed resolved, Paraphrasing, Rapport, Empathy.** Regression-only (included so training does not damage them): **Ownership, Probing, Hostility, Escalation.** Rule-based checks are not touched.

### 5.2 Inputs: one source of truth
`../src/services/laya_inputs.py::build_laya_inputs(transcript)` builds every Laya input; production and the data tools both call it, so training rows contain exactly what the model sees in production. **Done:** moving it out of the evaluator changed nothing (byte-identical inputs across 80 sample calls). The frozen questions and their inputs:

| Check | Input text (cap) | Cutoff on P(pass) | yes means |
|---|---|---|---|
| Empathy | up to 2 snippets, each an upset customer turn + next 4 turns; one Laya call per snippet; one FAIL fails | 0.78 | PASS |
| Rapport | **all agent lines** in chunks of at most 8 lines / 120 words; one Laya call per chunk; one rude chunk fails | 0.50 (interim, see 7) | FAIL |
| Paraphrasing | customer problem (<=50 words) + first 10 non-setup agent lines (<=150 words) | 0.50 | PASS |
| Probing | customer problem (<=50 words) + agent question sentences (<=100 words, boilerplate removed) | 0.70 | PASS |
| Ownership | agent lines containing a deflection phrase (gate still in place) | 0.52 | FAIL |
| Active listening | up to 3 pairs: *first question / customer's answer (<=40 words) / second question*, pairs of question sentences with difflib ratio > 0.55 or that the customer answered with "like I said" | 0.19 | FAIL |
| Confirmed resolved | last 10 lines | 0.73 | PASS |
| Escalation / Hostility | whole call (windowed `predict_long` if over 512 tokens) | 0.47 / 0.79 | FAIL |

The exact question and option texts are exported to `data/frozen/checks_frozen.json` with a sha256; every training row records the hash. The Ownership phrase gate (about 30 phrases) has the same blind-spot as Rapport had; it is a known limitation and not changed in this phase.

### 5.3 Data (all synthetic; all written and labelled by Claude)
- **Authorship, stated plainly:** train, dev and test fragments are hand-written by Claude as call excerpts (`data/fragments/claude/*.txt`) in a compact pair format and turned into rows by `tools/build_rows.py`. No row was labelled by a human. The PASS/FAIL label of a row is what Claude intended when writing it.
- **Every row goes through production code:** `build_laya_inputs` cuts the snippet, the check's gate must be reached, the decision line must be in the snippet, and the snippet must fit the 512-token window with the real tokenizer. Fragments that fail are dropped and logged (`data/rows/*_dropped.json`).
- **Matched pairs** so the model learns the skill, not trigger words: the same call with only the decision line changed (restate vs echo; rude vs polite with the same trigger words such as "obviously" or "as I said"; warm vs cold reply to the same upset turn; re-asked info vs re-checked status; explicit resolution check vs a call that just ends). Same persona on both members, roughening (speech-to-text noise, about 30%) decided per pair, PASS and FAIL balanced 50/50, hard cases in most pairs.
- **Test set built to differ from training:** industries (water utility, hotel booking, food delivery, gym, university, pharmacy, travel agency, auto insurance, credit card, rental portal), personas (rambling, blunt, overly polite, robotic, sleepy, slangy) and looser wording that never occur in train or dev. It is still Claude's writing and Claude's labels, so style shared with the training data can still help the model.
- **Replay rows (drift guard):** 250 train and 37 dev rows with 1-3 generic custom-criteria questions (built exactly like `_batch_check`, over agent-only text, end of call or the full call), with the **untouched model's own probabilities as soft targets** (`gold`). No human or Claude label is involved. `tools/build_replay.py`.
- **Splits are by pair and call.** `tools/make_manifest.py` proves no pair or call appears in two splits, no identical snippet crosses splits, and it removes dev/test pairs that are near-copies (5-gram Jaccard at least 0.6) of earlier splits (13 dev pairs removed; none from test). `data/rows/manifest.json` has the counts and sha256 of each file.

**Volumes actually built** (pairs = two rows; ownership train has one unpaired row left after a gate drop):

| Check | Role | Train pairs | Dev pairs | Test pairs |
|---|---|---|---|---|
| Rapport (chunks) | train | 70 | 20 | 30 |
| Paraphrasing | train | 100 | 20 | 30 |
| Active listening | train | 80 | 20 | 30 |
| Confirmed resolved | train | 70 | 20 | 30 |
| Empathy | train | 70 | 20 | 30 |
| Ownership | regression | 30 | 4 | 12 |
| Probing | regression | 30 | 4 | 12 |
| Hostility | regression | 30 | 4 | 12 |
| Escalation | regression | 30 | 6 | 12 |
| Replay rows | drift guard | 250 rows | 37 rows | - |
| **Rows** | | **1,269** | **273** | **396** |

This is about a third of the volume first planned (3,400 train rows). It is a **first stage**: train, read the learning curve, and scale only if the checks that matter keep improving with more data. The dev slices of the four regression checks are tiny (4-6 pairs); they are a sanity check, not a measurement.

**Validation (shortcut probe, `tools/shortcut_probe.py`, bag-of-words balanced accuracy with grouped cross-validation by pair):**
- Hard-fail checks pass: Rapport 0.71 and Paraphrasing 0.79 on train (limit 0.85); Active listening 0.71.
- **Warnings (above 0.85) on train:** Empathy 0.96, Escalation 0.97, Hostility 0.95, Ownership 0.90, Probing 0.98, Resolved 0.94 (test: Probing 1.00, Resolved 0.87). In these checks the label really is carried by words ("sorry"/"thank you", "okay" vs "yes", question words), so a high lexical score is partly the task itself, but it also means **the test scores for these checks may be optimistic** relative to real calls. Length balance is reported per label; the worst gap is Probing on train (PASS 21% longer).

### 5.4 Training recipe (one self-contained notebook, `01_train_eval.ipynb`)
- The notebook embeds the data and the frozen questions (hash-checked), so the owner opens it on Colab and presses **Run all** once. It scores the untouched model, trains **two variants** (`--loss soft-ce --label-smoothing 0.05` and `--loss rlcd`), scores both on dev and test, **picks the winner by mean dev AUC over the five trained checks**, saves everything to Drive and prints a summary to paste back.
- Settings: 4 epochs, micro-batch 8 x grad-accum 2 (effective 16, chosen because 1,269 rows give only about 80 steps per epoch at the default 64), encoder lr 2.5e-5, head lr 1e-4, `max_len 512`, `head_max_len 192` (same as serving), seed 0. One seed only. No `--eval` flag (the notebook computes its own metrics).
- `laya-train` holds out min(400, 10%) of the training items and fits one temperature per question type on them; this slice includes replay rows. A shared temperature never changes which of two calls scores higher, and cutoffs are re-tuned on dev afterwards.
- **Measured (smoke test, L4):** 13.7 items/s at 367 mean state tokens; the training rows here are much shorter (about 60-90 tokens), so each variant should take well under 10 minutes. Checkpoints are fp16, about 0.84 GB.
- **Known laya 0.4.0 bug:** `finetune()` evaluates before training while the model is still on the CPU, so it crashes on any GPU ("tensors on the same device ... index_select"). `tools/laya_train_cuda.py` wraps it (moves the model to the device first; installed package not edited). Verified on CPU with a simulated device mismatch, and then on the Colab GPU.
- Output goes to `/content` and a watcher copies `checkpoint_latest/` to Drive only when its files have stopped changing for 30 s and the epoch-end log line has appeared, via a temp folder and rename.

### 5.5 Cutoffs and evaluation
- For the five trained checks the cutoff is tuned on **dev** (best balanced accuracy, ties to the one nearest 0.5), then applied to test. Regression checks keep their frozen cutoff. Because dev and test share Claude's authorship, a cutoff tuned on dev is likely to transfer better to test than it will to real calls; the final cutoffs must be re-checked on the Main and bulk calls locally.
- Reported per check on test: balanced accuracy at the tuned cutoff with a 95% bootstrap interval resampled by pair, AUC, balanced accuracy of the untouched model at the production cutoff, ECE, and replay agreement (same verdict as the untouched model on custom-criteria questions).
- After the notebook: set `LAYA_CHECKPOINT`, re-run `batch_test.py main` and `bulk` through the service, `probe_laya.py`, `compare_results.py`, and commit new cutoffs to `LAYA_CHECKS`.

### 5.6 Integration
`../src/services/laya_adapter.py` serves a fine-tuned folder when the environment variable `LAYA_CHECKPOINT` is set (served under the `english` name); unset means the stock checkpoint. **Done and tested** on CPU through the real adapter. New cutoffs are committed to `LAYA_CHECKS`.

## 6. Phases and status

| Phase | What | Status |
|---|---|---|
| Plan A | Smoke test: install, download, dry-run, 1-epoch train on 20 rows, reload, predict, save to Drive, load locally on CPU through the adapter | **Done** (passed 2026-10-16) |
| 0 | Answer key for the 4 Main calls | **Done, with a caveat**: key is Claude-written and **not human-reviewed** (section 7) |
| 1 | Remaining pipeline input changes + freeze | **Done** 2026-10-16: frozen at `qa-analysis` tag `laya-inputs-frozen-v1` (commit `53becd8`), `inputs_sha256` `66deff95a20c...` in `data/frozen/checks_frozen.json` |
| 2 | Labelling guide (PASS/FAIL per check, examples, hard-case types) | **Written** (`docs/LABELLING_GUIDE.md`); used by Claude as its own labelling rules, never approved by a human |
| 3 | Generator + 240-row pilot | **Done** (`data/rows/pilot.jsonl`, part of train) |
| 4 | Gemini test set and human labelling | **Dropped** 2026-10-16 (time); replaced by a Claude-written test set built from unseen industries, personas and wording |
| 5 | Data generation | **Done, first stage**: train 1,269 rows, dev 273, test 396 (section 5.3); scale only if the learning curve asks for it |
| 6 | Validation (incl. shortcut probe) | **Done**: warnings recorded in section 5.3, no hard fails |
| 7 | Split by pair and call; manifest | **Done** (`data/rows/manifest.json`, no leakage found) |
| 8-10 | Baseline, training, evaluation | **Done** three times (stage 1, 2, 3): `01_train_eval.ipynb`, results in `runs/` |
| 11 | Integration, re-run Main and bulk | **Done** for stage 3: `LAYA_CHECKPOINT` + `FINETUNED_CUTOFFS` in `qa-analysis`; Main 41/44, error 8.75; bulk 358/372 |
| 12 | Iteration | **Planned, direction set by AG50** (`runs/ag50/RESULT.md`): fix the snippet builders (Active listening, Empathy call-level, Ownership gate, windows for Paraphrasing/Resolved), re-tune cutoffs (Probing), regenerate affected data with a second author, retrain, keep AG50 sealed |
| 13 | Report: "measured on Claude-written synthetic data" | Written in the results paragraph above and `runs/ft3-stage3/RESULT.md`; final write-up with the owner |

The human's time is now about 1 hour (section 8).

## 7. What has been done (facts)

- **Smoke test passed**, run `smoke-20261016-0848` (details in `runs/smoke-20261016-0848/RESULT.md`): base weights downloaded and hash-matched to the local copy; 1 epoch on a Colab L4; checkpoint copied to Drive with verification; reloaded two ways with identical output; served on CPU through `laya_adapter` with a largest difference from the GPU of 0.0057 (tolerance 0.03); original weights verified unchanged.
- **Phase 1 code** (`qa-analysis`, branch `version-10.2-laya-finetune`): `fcc6869` refactor (no behaviour change, proved by byte-identical inputs on 80 calls); `9050b41` Rapport chunk scan (mean 7.9 chunks per call, max 21), Active-listening first-question/answer/second-question snippet and 0.55 similarity (calls with an Active-listening snippet rise from 8 to 19 of 80), Probing cutoff 0.60 to 0.70; `53becd8` interim Rapport cutoff, Round 3 results and docs. Tagged `laya-inputs-frozen-v1`. Self-checks pass.
- **Phase 1 baseline of the untrained model** (full detail in `../Docs/LAYA_TEST_LOG.md`, Round 3; answer key is Claude-written):

  | | Ollama | Laya v2 | Laya v3.1 (final Phase 1) |
  |---|---|---|---|
  | Main items matching (of 44) | 40 | 36 | 37 |
  | Main mean score error | 9.2 | 11.7 | 13.3 |
  | Bulk `b_*` items matching (of 372) | n/a | 348 | 351 |
  | Time per Main call (CPU) | ~6.4 min | ~8.5 s | 22.4 s |

  Probing is now 34/34 on bulk (was 30/34) and Active listening 33/33 (was 30/33). The mean score error rose although more items are right, because two wrong answers on Main call 3 used to cancel. **Rapport: the untrained model has no signal on the chunk question.** Across all 44 labelled calls the highest chunk P(rude) is 0.19-0.22 for rude and polite calls alike (rude calls 0.199-0.217, median polite 0.198), so no cutoff separates them; the first cutoff (0.81) sat on that floor and failed 29 of 33 polite bulk calls. The cutoff is therefore an interim 0.50 that never fails a call until the model is fine-tuned. Active listening has a thin margin (planted repeats 0.82-0.85, all other calls 0.55-0.81, cutoff 0.81) and still misses the genuine repeats in Main call 2.
- **The freeze:** `inputs_sha256` covers the nine question texts, which answer means PASS, the word caps, and the source of `laya_inputs.py` and `rule_engine.py`. Cutoffs are deliberately excluded because they are re-tuned after training. `tools/export_checks.py --check` fails if any of it changes; training data built before such a change must be regenerated.
- **Phases 2-3 materials (2026-10-16):**
  - `docs/LABELLING_GUIDE.md`: PASS/FAIL per check on the text the model sees, with worked examples. Active listening uses the app's definition (re-asked question) as a default pending the owner's decision.
  - Pilot: `tools/build_rows.py` turns hand-written fragments (`data/fragments/claude/pilot_*.txt`: 20 matched pairs for each of the five trained checks, 5 pairs for each regression check) into 240 rows through the frozen `build_laya_inputs`. Every row passes its production gate and fits the window (max 112 tokens). Roughening (about 30%) is decided per pair. `tools/shortcut_probe.py` already found a **length shortcut in Empathy (0.88)** and a **word shortcut in Resolved (0.93)** at pilot size; `docs/GENERATION_NOTES.md` records the rules the full generation must follow (length balance per label, hard cases that break the lexical markers).
  - Gemini workflow (scenario cards, 33 paste-ready prompts, importer): built, then **removed from the repo** on 2026-10-16 when the Gemini test set and human labelling were dropped (see the decision note in section 1). It is in git history on branch `phase-3-pilot`.
- **Data creation, first stage (2026-10-16):** train 1,269 rows, dev 273, test 396 (section 5.3), the replay builder, the split manifest and the self-contained notebook `01_train_eval.ipynb`. A local CPU run of the notebook's scoring and metric code on the untouched model passed (it is the baseline numbers the notebook will print again on Colab).
- **Phase 0 answer key is not human-reviewed.** Two review spreadsheets were produced for the 4 Main calls; both came back with notes written by an assistant that had Claude's grades ("Claude:" / "Claude (not human):"), so neither is an independent human check. Three contested items were re-read by Claude and all stood. `docs/PHASE0_ANSWER_KEY.md` and `data/review/answer_key_main.json` record this. Ollama's 9.2 and Laya's 11.7 are therefore measured against Claude-written grades. Open requirement question: should Active listening also fail an agent who ignores what the customer already said, not only one who re-asks a question?

## 8. Who does what: the steps only the human owner (Nimithra) can do

Claude (the assistant doing the build) cannot press Run in Colab. Human labelling and Gemini were dropped, so the owner's list is short:

| # | When | Action | Time |
|---|---|---|---|
| 1 | Now | Open `01_train_eval.ipynb` in Colab (L4 GPU), press **Run all**, allow the Drive prompt, and paste the block that starts `=== PASTE THIS BACK TO CLAUDE ===` | ~5 min of attention, ~30-40 min of waiting |
| 2 | After | Download `MyDrive/laya-finetuning/checkpoints/<run id>/final-<winner>` to `laya-training/checkpoints/` (zip it first) | 10 min |
| 3 | After | Go / no-go on the Main and bulk scorecards | 30 min |

Nothing in the final claim comes from human judgement. If an independent check matters later, a human-labelled sample of real calls is the thing to add.

## 9. Risks, limitations and what we want the ML engineer to challenge

1. **Full fine-tune vs something lighter.** 421M parameters on about 1,270 synthetic rows (1,020 supervised + 250 replay) for 4 epochs. Is full fine-tuning right, or would head-only (`--freeze-encoder`, which Laya documents as gaining much less), a lower encoder learning rate, fewer epochs, or early stopping on dev be safer against overfitting to synthetic style? We run soft-ce and rlcd and pick on dev, one seed only.
2. **Synthetic-to-real gap and style shortcuts.** All training text is written by one LLM family. Mitigations: variety matrix, matched pairs, speech-to-text noise, a test set of unseen industries/personas/wording, a bag-of-words shortcut probe (which warned for six checks, section 5.3). Are these enough, and is 0.85 the right probe threshold?
3. **Replay as a drift guard.** Soft targets from the untouched model on 250 train rows of generic questions. Is that adequate, or should the replay set be larger or cover more question styles? Is it sound that replay rows enter the calibration slice?
4. **The test set is not independent.** Train, dev and test were written and labelled by the same model; only industries, personas and wording differ. 24-60 test pairs per check gives a balanced-accuracy interval of about +/-0.09 or wider. A high test score shows the model learned Claude's labelling rules and generalises across Claude's styles; it does not show agreement with human graders on real calls.
5. **Rapport aggregation.** The untrained model scores every chunk 0.19-0.22, so training must create the signal first. "One rude chunk fails the call" over about 8 chunks per call multiplies false positives; we address it by tuning the cutoff at call level against full polite calls (target at most 5%, only ~20 calls). Is a better aggregation (max vs mean vs top-k, overlapping chunks, customer context in the chunk) worth trying?
6. **Latency.** Rapport now makes about 8 Laya calls per call (up to 21). Measured: 22.4 s per Main call on CPU (bulk mean 12.8 s) against a 15 s target. Batching the chunks into one forward pass is the planned fix; is that safe for ModernBERT at 512 tokens, or would you cache or shorten chunks instead?
7. **Active listening is under-defined** (re-asked question vs ignored statement) and its input is a question pair plus one customer answer, which may be too little context for "already gave in their answer".
8. **Answer key for the 4 Main calls is LLM-written** and so is the whole test set. There is currently no human-labelled number anywhere in this project.
9. **Calibration.** One temperature per question type is fitted on at most 400 held-out items (including replay). Cutoffs are re-tuned per check afterwards. Is per-check calibration needed?
10. **Reproducibility.** One seed planned for the main comparison; more seeds only if time allows. Is a seed ensemble or a paired seed comparison needed to trust a 0.02-0.05 difference?
11. **Tooling risk.** `laya-train` v0.4.0 needs a wrapper to run on a GPU (section 5.4). Anything else in it you would distrust (silent state truncation, the `--eval` path, the shared calibration clamp)?
12. **Ownership still uses a phrase gate** (the same weakness Rapport had). Out of scope for this phase; should it be fixed before generating its regression data?

## 10. Environment and reproducibility

| Where | What |
|---|---|
| **Google Colab (L4 GPU, ~23 GB)** | notebooks `00_smoke_test.ipynb` (plumbing) and `01_train_eval.ipynb` (baseline, train, evaluate). Pinned: laya commit `3cf26cb`, transformers 5.16.1 |
| **PC (CPU, Windows)** | `tools/*.py` and the `qa-analysis` service. No NVIDIA GPU |
| **Google Drive** `MyDrive/laya-finetuning/` | checkpoints, datasets, run reports (Colab's disk is wiped at session end) |
| **Git (this repo)** | notebooks, tools, prompts, docs, small data. Never weights |

Branches: this repo `plan-a-smoke-test`, `phase-0-ground-truth`; `qa-analysis` `version-10.2-laya-finetune`.

Tools in `tools/`: `build_rows.py` (fragments to rows through production code), `build_replay.py`, `make_manifest.py` (combine, de-duplicate, prove no leakage), `shortcut_probe.py`, `build_train_notebook.py` (assembles `01_train_eval.ipynb` from `train_cells/`), `export_checks.py` (freeze the production questions with a sha256; `--check` detects drift), `smoke_rows.py` / `smoke_cells/` / `build_smoke_notebook.py` (the smoke test), `check_local_load.py` (CPU check through the adapter), `laya_train_cuda.py` (GPU workaround), `make_review_sheet.py` and `pick_review_subset.py` (Phase 0 sheets). In `../Scripts/`: `dump_laya_inputs.py` records every Laya input without a model and compares two code versions.

Run the smoke test: open `00_smoke_test.ipynb` on Colab, run cells top to bottom (each starts with an "EXPECT" comment), download the `final/` folder and `smoke_preds_ft.json` from Drive into `checkpoints/<run id>/`, then

```powershell
..\qa-analysis\.venv\Scripts\python.exe tools\check_local_load.py `
  --checkpoint checkpoints\<run id>\final --preds checkpoints\<run id>\files\smoke_preds_ft.json
```

To serve any fine-tuned checkpoint in `qa-analysis`, set `LAYA_CHECKPOINT` to its folder before starting the service. `.env` is never edited.

## 11. Rules that keep the data honest
- Question wording and every extractor are **frozen** before data is generated; changing one means regenerating.
- Training inputs come only from `build_laya_inputs`, never written by hand.
- Splits are by call and by pair. The test set is written and labelled by Claude (not human) and is only used for the notebook's final scoring; cutoffs are chosen on dev.
- The original checkpoint is never modified; every checkpoint records its base revision and hashes in a manifest.
