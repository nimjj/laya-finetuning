"""Where things are, for every tool in this folder.

Layout (one repository, two segments):
    <repo root>/                the QA application (segment 1): src/, frontend/, tests/, Docs/, models/final-softce-3 ...
    <repo root>/laya-finetuning/    everything about Laya (segment 2): this folder
        tools/                  row builders, the freeze check, manifests
        eval/                   testing and evaluation scripts (probes, labs, comparisons, the validator)
        inputs/                 the test sets (AG50, AG-T, AG-B, AG-B2, AG-C, Eval50 ...) and their results
        laya_eval/              the first synthetic Laya-vs-Ollama benchmark
        checkpoints/            experiment weights (git-ignored); the production weights are in <repo root>/models/

The app code the tools import (src.services.laya_inputs, ...) is the repo root, one level above this folder. Set the
environment variable QA_APP_DIR to point at another checkout of the app (for example if this folder becomes its own repo).
Older notes that say `qa-analysis/` mean the repo root, and `laya-training/` means this folder.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
FT_ROOT = os.path.dirname(HERE)                  # laya-finetuning/
QA_ROOT = os.environ.get("QA_APP_DIR") or os.path.dirname(FT_ROOT)    # the QA application (default: the repo root)
EVAL = os.path.join(FT_ROOT, "eval")             # evaluation scripts
INPUTS = os.path.join(FT_ROOT, "inputs")         # test sets and their results
PRODUCTION_CHECKPOINT = os.path.join(QA_ROOT, "models", "final-softce-3")
BASE_REVISION = "7b928d828b7b0e022f929d9bd2e44165aa270148"


def hf_home():
    """Folder holding the downloaded base Laya weights: LAYA_HF_HOME, then HF_HOME, then ../laya-test/hf_home next to
    the repo (the older sibling layout) when it exists, else None (Hugging Face's default cache)."""
    for key in ("LAYA_HF_HOME", "HF_HOME"):
        if os.environ.get(key):
            return os.environ[key]
    legacy = os.path.join(os.path.dirname(QA_ROOT), "laya-test", "hf_home")
    return legacy if os.path.isdir(legacy) else None


def base_snapshot():
    """Folder of the pinned base snapshot, or None when no cache location is known."""
    home = hf_home()
    if home is None:
        return None
    return os.path.join(home, "hub", "models--convaiinnovations--laya", "snapshots", BASE_REVISION)
