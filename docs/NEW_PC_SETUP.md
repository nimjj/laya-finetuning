# Setting up the Laya project (and the QA app it works with) on a new PC

The work is in **two git repos that sit side by side**: the QA application `QA-system` (`https://github.com/nimjj/QA-system`) and this Laya project `laya-finetuning` (`https://github.com/nimjj/laya-finetuning`). The QA app runs on its own. This project needs the app next to it: its tools import the app's code and run the app's model, and find the app at `../QA-system` (or wherever the environment variable `QA_APP_DIR` points). So set up both.

## 1. What is in git and what is not

| Item | Where | How it moves |
|---|---|---|
| App code, app docs, tests, the sample calls `inputs/Main tests` and `Bulk tests` | repo `QA-system` | `git clone` |
| Fine-tuning data, tools, evaluation scripts, Colab notebooks, all test sets with keys and results, run notes, hash records | repo `laya-finetuning` (this one) | `git clone` |
| **Production weights** (808 MB folder `final-softce-3`) | **Google Drive, folder `final-softce-3`** (`model.safetensors`, `rl_agent_config.json`, `questions.json`, `tokenizer/`, `encoder/`); live in `QA-system/models/final-softce-3` | Download into `QA-system/models/` (step 4) |
| Experiment weights (ft5, ft6; 1.6 GB each) | Google Drive; live in `laya-finetuning/checkpoints/` | Only if you need to re-test them |
| Laya library | GitHub `NandhaKishorM/laya`, pinned commit `3cf26cb` (v0.4.0) | Installed automatically by `pip install -r requirements.txt` in `QA-system` |
| Stock Laya weights (1.5 GB) | Hugging Face `convaiinnovations/laya`, revision `7b928d82...` | Only for stock-Laya runs and the training-data tools. Optional (step 5) |
| `.env` of the app | git-ignored | Recreate from `QA-system/.env.example` |
| Old Ollama copy of the app (`qa-analysis-ollama`) | a git worktree of commit `3035269` of the QA repo | Only to re-run Ollama; its results are in the repos. Recreate in the QA folder with `git worktree add ..\qa-analysis-ollama 3035269`, run it with `SERVER_PORT=8007` and `ollama serve` |
| Claude Code chat and notes | `C:\Users\<you>\.claude\projects\...` | Section 4 |

## 2. Setup (PowerShell; needs Git and Python 3.14, about 4 GB of disk)
```powershell
# 1. clone both repos next to each other (any parent folder; D:\CIAP\QA is what the owner uses)
mkdir D:\CIAP\QA; cd D:\CIAP\QA
git clone --branch app-v3 https://github.com/nimjj/QA-system.git QA-system
git clone --branch separated-from-qa-system https://github.com/nimjj/laya-finetuning.git laya-finetuning

# 2. one environment, in the app folder; it installs the app's packages and Laya from GitHub
cd QA-system
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\pip install "transformers==5.16.1"      # the version everything was tested with
.\.venv\Scripts\python -c "import laya, transformers, torch; print(transformers.__version__, torch.__version__)"

# 3. settings (copy the real values from the old PC's .env; only paths change)
copy .env.example .env
# then set in .env:   LAYA_CHECKPOINT=models/final-softce-3
```
4. **Production weights.** From Google Drive, download the folder `final-softce-3` **file by file** (`model.safetensors`, `rl_agent_config.json`, `questions.json`, and the `tokenizer` and `encoder` subfolders), not as one zip: a big folder download is split into several zips and a half-unpacked folder fails to load. Put it at `QA-system\models\final-softce-3`.
5. **Stock weights (optional).** Needed for stock-Laya runs and for rebuilding training data (the tokenizer comes from them):
   ```powershell
   $env:HF_HOME = "D:\somewhere\hf_home"        # also set LAYA_HF_HOME to this in .env
   .\.venv\Scripts\python -c "from huggingface_hub import snapshot_download; snapshot_download('convaiinnovations/laya', revision='7b928d828b7b0e022f929d9bd2e44165aa270148')"
   ```

## 3. Check that it worked
Use the app's Python for everything: `D:\CIAP\QA\QA-system\.venv\Scripts\python` (written `python` below once that environment is active).
1. **Weights are bit-identical to the ones tested** (run in `laya-finetuning`):
   ```powershell
   python tools\checkpoint_manifest.py verify ..\QA-system\models\final-softce-3 --manifest runs\ft3-stage3\final-softce-3.manifest.json
   ```
   Must print `ALL FILES MATCH` (`model.safetensors` starts `fc6a3f1b793a`). Stock weights: `... verify <hf_home>\hub\models--convaiinnovations--laya\snapshots\7b928d82... --manifest data\frozen\base_laya_7b928d82.manifest.json`.
2. **Extractors unchanged** (run in `laya-finetuning`): `python tools\export_checks.py --check` prints two `MATCH` lines (inputs hash `4021ce6d6740`, tag `laya-inputs-frozen-v4`).
3. **End to end on the 4 golden calls (2 minutes)**, in `QA-system`:
   ```powershell
   Start-Process python -ArgumentList main.py -WindowStyle Hidden
   Start-Sleep 60
   python Scripts\batch_test.py main --label newpc
   python Scripts\compare_results.py laya-ft-v2b newpc
   ```
   Expected: **42 of 44** items; scores about **100 / 88.3 / 50.0 / 30.0** (key 100 / 88.3 / 56.7 / 13.3). A point or two of difference on another CPU is normal. A database warning at start is expected; the service runs without one. Stop the service afterwards.
4. **The evaluation scripts find the app** (run in `laya-finetuning`): `python eval\validate_calls.py --suite ag50` exits with code 0, and `python eval\golden.py rules` lists one difference (`agc_42`, Dead air).

## 4. Carrying the Claude Code conversation and notes
The chat is not in git. It lives in `C:\Users\<you>\.claude\projects\<folder-name>\` on the old PC (the folder name is the working directory's path with separators turned into dashes): the session files (`*.jsonl`) and a `memory\` folder of notes that load automatically.

- **Recommended: start a fresh session.** Sign in to Claude Code on the new PC, open the folder `D:\CIAP\QA` (the parent of both repos), run Claude once, then copy the old `memory\` folder into the new `...\.claude\projects\<new-folder-name>\memory\` (the new folder name appears there after the first run). Paste the first message below.
- **Or resume the exact session:** copy the `.jsonl` files and `memory\` into that same new folder and use `/resume`. If the folder name does not match the new path the session will not be listed. A fresh start is cleaner.

**First message:**
> There are two repos side by side here: `QA-system` (the S-Net QA call-grading service) and `laya-finetuning` (training, fine-tuning and evaluating the Laya model for it). Read `QA-system/CLAUDE.md`, `QA-system/Docs/AI_HANDOVER.md`, `QA-system/Docs/CODEBASE_GUIDE.md`, `laya-finetuning/README.md` and `laya-finetuning/docs/NEW_PC_SETUP.md`. Then check my setup with section 3 of the setup guide. Rules: describe all results as measured against AI-written keys (not human-labelled); never modify the original checkpoint; never touch `.env` or the `bitbucket` remote; commit or push only when I ask; production sentiment is customer-side only; keep replies short.

## 5. What depends on paths
The tools find the app by themselves (`../QA-system`); the app finds its own files. Only these settings are per machine:

| Setting | Purpose |
|---|---|
| `LAYA_CHECKPOINT` (`.env` of the app) | Folder of the fine-tuned weights, relative to the app: `models/final-softce-3`. When set, the app uses the fine-tuned cutoffs and flow v2 |
| `QA_APP_DIR` (environment) | Where the QA app is, if it is not the sibling folder `QA-system` |
| `LAYA_HF_HOME` (`.env`) | Folder of the stock weights. Empty means `../laya-test/hf_home` if it exists, else the Hugging Face default cache |
| `LAYA_FLOW` (environment) | `v3` for the new pipeline; `v1` or `v2` to override the snippet-cutting flow (unset: v2 with a fine-tuned checkpoint, v1 for stock) |

Older notes in this project say `qa-analysis/` (meaning the QA app) and `laya-training/` (meaning this folder).

## 6. Facts to keep
- Base checkpoint: `convaiinnovations/laya`, revision `7b928d828b7b0e022f929d9bd2e44165aa270148`; laya v0.4.0, commit `3cf26cbcb18725dbc2d127bb8bb2c4c43243ae63`; transformers 5.16.1.
- Train only through `tools/laya_train_cuda.py` (`laya-train` crashes on GPU), on a Colab L4, with the notebooks `01_train_eval.ipynb` to `04_train_eval_ft6.ipynb`.
- Frozen inputs: tag `laya-inputs-frozen-v4` (in the QA repo), `inputs_sha256` `4021ce6d6740...`. It covers the question wording and the source of `laya_inputs.py` and `rule_engine.py` (and `laya_windows.py`), all in the QA app. If it stops matching, training data built earlier must be regenerated. (The older tags `-v2` and `-v3` are superseded; ignore them.)
- Latest results: `runs/CHECKPOINTS.md`, `docs/LAYA_TEST_LOG.md`, and `../QA-system/Docs/V3.md`.
- Never push to the `bitbucket` remote; the weights never go to GitHub.

## 7. Do not keep the repos inside a Google Drive synced folder
On the old PC the project folder was mirrored by Google Drive for desktop, and edits to tracked files were silently reverted twice (flow-v2 code was lost before a commit and had to be redone). A synced folder can also corrupt the `.git` folder. On the new PC keep both repos in a plain local folder (for example `C:\dev\`), and use `git push` as the backup. If you must keep Drive, exclude the repo folders from sync. Always check `git status` and `git diff` before committing.
