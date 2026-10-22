"""Where things are, for every tool in this folder.

Layout (two folders side by side, each its own git repo):
    QA-system/        the QA application: src/, frontend/, tests/, Docs/, models/final-softce-3 ...
    laya-finetuning/  this folder: everything about Laya (it sits next to QA-system/)
        tools/                  row builders, the freeze check, manifests
        eval/                   testing and evaluation scripts (probes, labs, comparisons, the validator)
        inputs/                 the test sets (AG50, AG-T, AG-B, AG-B2, AG-C, Eval50 ...) and their results
        laya_eval/              the first synthetic Laya-vs-Ollama benchmark
        checkpoints/            experiment weights (git-ignored); the production weights are in QA-system/models/

The app code the tools import (src.services.laya_inputs, ...) is the sibling folder QA-system. Set the environment variable
QA_APP_DIR to point at another checkout of the app. (If this folder is still nested inside the app, as it was until 2026-10-22,
its parent is used.) Older notes that say `qa-analysis/` mean the app, and `laya-training/` means this folder.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
FT_ROOT = os.path.dirname(HERE)                  # laya-finetuning/


def _find_app():
    explicit = os.environ.get("QA_APP_DIR")
    if explicit:
        return os.path.abspath(explicit)
    sibling = os.path.join(os.path.dirname(FT_ROOT), "QA-system")
    return sibling if os.path.isdir(os.path.join(sibling, "src")) else os.path.dirname(FT_ROOT)


QA_ROOT = _find_app()                            # the QA application
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
