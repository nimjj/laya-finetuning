# Setting this project up on a new PC

One repository now holds everything: **`https://github.com/nimjj/QA-system`, branch `laya-finetuning`**. The app is at the repo root and the fine-tuning work is in `laya-finetuning/`. (The separate `laya-finetuning` GitHub repo is no longer needed.)

## 1. What is in git and what is not

| Item | Where | How it moves |
|---|---|---|
| App code, docs, tests, all test calls, answer keys and results from every engine | the repo (`inputs/`, `Docs/`, `Scripts/`, `src/`) | `git clone` |
| Fine-tuning data, tools, Colab notebook, run notes, hash records | `laya-finetuning/` in the repo | `git clone` |
| **Fine-tuned weights** (808 MB folder) | **Google Drive, folder `final-softce-3`** (it has `model.safetensors`, `rl_agent_config.json`, `questions.json`, `tokenizer/`, `encoder/`); also on the old PC at `laya-training\checkpoints\final-softce-3` | Download it into `laya-finetuning/checkpoints/final-softce-3`, then verify (section 3) |
| Laya library | GitHub `NandhaKishorM/laya`, pinned commit `3cf26cb` (v0.4.0) | Installed automatically by `pip install -r requirements.txt` |
| Stock Laya weights (1.5 GB) | Hugging Face `convaiinnovations/laya`, revision `7b928d82...` | Only for stock-Laya runs and the training-data tools. Optional (section 2, step 5) |
| `.env` | git-ignored | Recreate from `.env.example` |
| Old Ollama copy of the app (`qa-analysis-ollama`) | not a repo | Only to re-run Ollama; its results are in the repo. Skip |
| Claude Code chat and notes | `C:\Users\<you>\.claude\projects\...` | Section 4 |

## 2. Setup (PowerShell; needs Git and Python 3.14, about 4 GB of disk)
```powershell
# 1. clone the one repo, on the right branch (the default branch is NOT this one)
git clone --branch laya-finetuning https://github.com/nimjj/QA-system.git qa-analysis
cd qa-analysis

# 2. environment; installs the app's packages and Laya from GitHub
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\pip install "transformers==5.16.1"      # the version everything was tested with
.\.venv\Scripts\python -c "import laya, transformers, torch; print(transformers.__version__, torch.__version__)"

# 3. settings (copy the real values from the old PC's .env; only paths change)
copy .env.example .env
```
4. **Fine-tuned weights.** From Google Drive, download the folder `final-softce-3` **file by file** (`model.safetensors`, `rl_agent_config.json`, `questions.json`, and the `tokenizer` and `encoder` subfolders), not as one zip: a big folder download is split into several zips. Put them in `laya-finetuning\checkpoints\final-softce-3\`. Or copy that folder from the old PC.
5. **Stock weights (optional).** Needed for stock-Laya runs and for rebuilding training data (the tokenizer comes from them):
   ```powershell
   $env:HF_HOME = "D:\somewhere\hf_home"        # also set LAYA_HF_HOME to this in .env
   .\.venv\Scripts\python -c "from huggingface_hub import snapshot_download; snapshot_download('convaiinnovations/laya', revision='7b928d828b7b0e022f929d9bd2e44165aa270148')"
   ```

## 3. Check that it worked
Run these from the repo root.
1. **Weights are bit-identical to the ones tested:**
   ```powershell
   .\.venv\Scripts\python laya-finetuning\tools\checkpoint_manifest.py verify laya-finetuning\checkpoints\final-softce-3 --manifest laya-finetuning\runs\ft3-stage3\final-softce-3.manifest.json
   ```
   Must print `ALL FILES MATCH` (`model.safetensors` starts `fc6a3f1b793a`). Stock weights: `... verify <hf_home>\hub\models--convaiinnovations--laya\snapshots\7b928d82... --manifest laya-finetuning\data\frozen\base_laya_7b928d82.manifest.json` (starts `891102d37268`).
2. **Extractors unchanged:** `.\.venv\Scripts\python laya-finetuning\tools\export_checks.py --check` prints two `MATCH` lines (inputs hash `49e61755fdb6`).
3. **End to end on the 4 golden calls (2 minutes):**
   ```powershell
   $env:LAYA_CHECKPOINT = "$PWD\laya-finetuning\checkpoints\final-softce-3"
   Start-Process .\.venv\Scripts\python -ArgumentList main.py -WindowStyle Hidden
   Start-Sleep 60
   .\.venv\Scripts\python Scripts\batch_test.py main --label newpc
   .\.venv\Scripts\python Scripts\compare_results.py laya-ft-v2b newpc
   ```
   Expected: **42 of 44** items; scores about **100 / 88.3 / 50.0 / 30.0** (key 100 / 88.3 / 56.7 / 13.3). A point or two of difference on another CPU is normal. A database warning at start is expected; the service runs without one. Stop the service afterwards.
4. Optional, 15 minutes: `batch_test.py inputs\AG50 --label newpc`, then `python Scripts\compare_eval.py AG50 laya-ft-v2b newpc`.

## 4. Carrying the Claude Code conversation and notes
The chat is not in git. It lives in `C:\Users\adept\.claude\projects\D--Projects--Tests--QA-2-laya-training\` on the old PC: this session (`f99a48a2-...jsonl`), the earlier one (`1e06a8c6-...jsonl`) and a `memory\` folder of notes that load automatically. The folder name is the working directory's path with separators turned into dashes.

- **Recommended: start a fresh session.** Sign in to Claude Code on the new PC, open the repo folder, run Claude once, then copy the old `memory\` folder into the new `...\.claude\projects\<new-folder-name>\memory\` (the new folder name appears there after the first run). Paste the first message below.
- **Or resume this exact session:** copy the two `.jsonl` files and `memory\` into that same new folder and use `/resume`. If the folder name does not match the new path the session will not be listed. It is a very long session, so a fresh start is cleaner.

**First message:**
> This repo fine-tunes Laya to replace Ollama in the S-Net QA call-grading service. Read `laya-finetuning/README.md`, `laya-finetuning/runs/ag50/RESULT.md`, `Docs/FLOW_V2.md`, `Docs/AG50_REPORT.md`, `Docs/LAYA_TEST_LOG.md` and `laya-finetuning/docs/NEW_PC_SETUP.md`. Then check my setup with section 3 of the setup guide and continue with the next steps in `Docs/FLOW_V2.md`. Rules: describe all results as measured against AI-written keys (not human-labelled); never modify the original checkpoint; never touch `.env` or the `bitbucket` remote; commit or push only when I ask; production sentiment is customer-side only; keep replies short.

## 5. What depends on paths
Everything finds the repo root by itself. Only these settings are per machine:

| Setting | Purpose |
|---|---|
| `LAYA_CHECKPOINT` (environment) | Folder of the fine-tuned weights. When set, the app uses the fine-tuned cutoffs and flow v2 |
| `LAYA_HF_HOME` (`.env`) | Folder of the stock weights. Empty means `../laya-test/hf_home` if it exists, else the Hugging Face default cache |
| `LAYA_FLOW` (environment) | `v1` or `v2` to override the flow (unset: v2 with a fine-tuned checkpoint, v1 for stock) |

Older notes in this folder say `qa-analysis/` (meaning the repo root) and `laya-training/` (meaning `laya-finetuning/`). Renaming the folders above the repo is safe.

## 6. Facts to keep
- Base checkpoint: `convaiinnovations/laya`, revision `7b928d828b7b0e022f929d9bd2e44165aa270148`; laya v0.4.0, commit `3cf26cbcb18725dbc2d127bb8bb2c4c43243ae63`; transformers 5.16.1.
- Train only through `laya-finetuning/tools/laya_train_cuda.py` (`laya-train` crashes on GPU), on a Colab L4, with `01_train_eval.ipynb`.
- Frozen inputs: tag `laya-inputs-frozen-v3`, `inputs_sha256` `49e61755fdb692f5...`. It covers `laya_inputs.py`, `rule_engine.py` and `laya_windows.py`. If it stops matching, training data built earlier must be regenerated. (The older tag `laya-inputs-frozen-v2` was made at a commit that lacked the flow-v2 switch; ignore it.)
- Latest results: `Docs/FLOW_V2.md`. Next steps: sealed test set and new training data from Antigravity, retrain, human review, shadow mode.
- Never push to the `bitbucket` remote; the weights never go to GitHub.
