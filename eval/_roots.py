"""Roots and path helpers for the evaluation scripts in this folder (imported as `import _roots`; Python finds it because it sits beside the script).

    QA_ROOT   the QA application (the sibling folder QA-system): src/ (code the scripts import), .env, resources/criteria_config.json, models/
    FT_ROOT   laya-finetuning/ (this project)
    DATA      laya-finetuning/inputs: the test sets AG50, AG-T, AG-B, AG-B2, AG-C, Eval50, Tough checks, and their results
    DOCS      laya-finetuning/docs: where generated reports are written

The app keeps its own sample calls (QA-system/inputs/Main tests, Bulk tests) and their result folders; suite_dir() and results_root() look
in DATA first and then in the app, so a script can be given any suite name.

Scripts can be run from any folder:
    resolve(p)   an INPUT path: absolute as is; otherwise the first place it exists among the current folder, laya-finetuning/, then the app
    out_path(p)  an OUTPUT path: absolute as is; starting with "." (./x, ../x) from the current folder; anything else inside laya-finetuning/
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


def resolve(path: str) -> str:
    """Find an input file or folder given on the command line (see the module docstring). If it exists nowhere, the laya-finetuning/ spelling."""
    if os.path.isabs(path):
        return path
    for base in (os.getcwd(), FT_ROOT, QA_ROOT):
        cand = os.path.normpath(os.path.join(base, path))
        if os.path.exists(cand):
            return cand
    return os.path.normpath(os.path.join(FT_ROOT, path))


def out_path(path: str) -> str:
    """Where an output file goes (see the module docstring)."""
    if os.path.isabs(path):
        return path
    base = os.getcwd() if path.startswith(".") else FT_ROOT
    return os.path.normpath(os.path.join(base, path))
