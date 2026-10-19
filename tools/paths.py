"""Where things are, for every tool in this folder.

Layout (one repository):
    <repo root>/                the QA application: src/, Scripts/, inputs/, Docs/, resources/ ...
    <repo root>/laya-finetuning/    this folder: data, tools, notebooks, run notes
        checkpoints/            fine-tuned weights (git-ignored; see docs/NEW_PC_SETUP.md)

The app code the tools import (src.services.laya_inputs, ...) is therefore the repo root, one level above this folder.
Older notes in this folder that say `qa-analysis/` mean the repo root, and `laya-training/` means this folder.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
FT_ROOT = os.path.dirname(HERE)                  # laya-finetuning/
QA_ROOT = os.path.dirname(FT_ROOT)               # repo root
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
