"""Roots for the evaluation scripts in this folder (imported as `import _roots`; Python finds it because it sits beside the script).

    QA_ROOT   the QA application: src/ (code the scripts import), .env, resources/criteria_config.json, models/
    FT_ROOT   laya-finetuning/
    DATA      laya-finetuning/inputs: the test sets AG50, AG-T, AG-B, AG-B2, AG-C, Eval50, Tough checks, and their results
    DOCS      laya-finetuning/docs: where generated reports are written

The app keeps its own sample calls (inputs/Main tests, inputs/Bulk tests) and their result folders; suite_dir() and results_dir()
look in DATA first and then in the app, so a script can be given any suite name.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "tools"))
import paths  # noqa: E402

QA_ROOT = paths.QA_ROOT
FT_ROOT = paths.FT_ROOT
DATA = paths.INPUTS
DOCS = os.path.join(FT_ROOT, "docs")
APP_INPUTS = os.path.join(QA_ROOT, "inputs")

if QA_ROOT not in sys.path:
    sys.path.insert(0, QA_ROOT)               # so `import src.services...` finds the app


def suite_dir(name: str) -> str:
    """Folder of a test set: laya-finetuning/inputs/<name>, else the app's inputs/<name> (Main tests, Bulk tests)."""
    first = os.path.join(DATA, name)
    return first if os.path.isdir(first) else os.path.join(APP_INPUTS, name)


def results_root(suite: str) -> str:
    """Folder holding '<suite> (<label>)' result folders: next to the suite's data, either in laya-finetuning/inputs or in the app's inputs."""
    return os.path.join(DATA if os.path.isdir(os.path.join(DATA, suite)) else APP_INPUTS, "Test (results)")
