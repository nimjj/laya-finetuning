"""Assemble 01_train_eval.ipynb from tools/train_cells/*.py|md.

Embeds (so the notebook is self-contained on Colab, nothing to upload):
    {{FROZEN_JSON}}   data/frozen/checks_frozen.json
    {{DATA_B64}}      train_all / dev_all / test as gzip+base64, with {{DATA_SHA256}} to verify them
    {{LAUNCHER_PY}}   tools/laya_train_cuda.py
Run tools/make_manifest.py first (it writes the three jsonl files).

Usage (any Python 3):
    python tools/build_train_notebook.py            # writes 01_train_eval.ipynb
    python tools/build_train_notebook.py --check    # exit 1 if the notebook on disk is out of date
"""
import argparse
import base64
import glob
import gzip
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SPLITS = ("train_all", "dev_all", "test", "test_long", "test_calls")


def lines(text):
    parts = text.split("\n")
    return [p + "\n" for p in parts[:-1]] + ([parts[-1]] if parts[-1] else [])


def build(suffix="", run_prefix="ft2-", ag_oversample=0, accepted_hashes=()):
    """suffix: read train_all{suffix}.jsonl and dev_all{suffix}.jsonl instead (the embedded split names stay train_all / dev_all).
    ag_oversample N >= 2: cell 9 trains soft-ce on the rows as they are AND soft-ce with the Antigravity rows repeated N times."""
    frozen_text = open(os.path.join(REPO, "data", "frozen", "checks_frozen.json"), encoding="utf-8").read().rstrip("\n")
    launcher_text = open(os.path.join(HERE, "laya_train_cuda.py"), encoding="utf-8").read().rstrip("\n") + "\n"
    b64, sha = {}, {}
    for s in SPLITS:
        fname = f"{s}{suffix}" if s in ("train_all", "dev_all") else s
        raw = open(os.path.join(REPO, "data", "rows", f"{fname}.jsonl"), "rb").read()
        sha[s] = hashlib.sha256(raw).hexdigest()
        b64[s] = base64.b64encode(gzip.compress(raw, 9, mtime=0)).decode("ascii")
    assert '"""' not in frozen_text and "'''" not in launcher_text

    cells = []
    for i, path in enumerate(sorted(glob.glob(os.path.join(HERE, "train_cells", "*")))):
        src = open(path, encoding="utf-8").read()
        src = (src.replace("{{FROZEN_JSON}}", frozen_text).replace("{{LAUNCHER_PY}}", launcher_text)
               .replace("{{DATA_B64}}", json.dumps(b64)).replace("{{DATA_SHA256}}", json.dumps(sha))
               .replace("{{RUN_PREFIX}}", run_prefix).replace("{{AG_OVERSAMPLE}}", str(int(ag_oversample)))
               .replace("{{ACCEPTED_HASHES}}", json.dumps(sorted(accepted_hashes))))
        cell = {"id": f"ft{i:02d}", "metadata": {}, "source": lines(src.rstrip("\n"))}
        if path.endswith(".md"):
            cell["cell_type"] = "markdown"
        else:
            cell.update({"cell_type": "code", "execution_count": None, "outputs": []})
        cells.append(cell)
    return {"cells": cells, "metadata": {"language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 5}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--out", default="01_train_eval.ipynb", help="notebook file name inside laya-finetuning/")
    ap.add_argument("--rows-suffix", default="", help='e.g. "2" to embed train_all2 / dev_all2 (tools/make_mix2.py)')
    ap.add_argument("--run-prefix", default="ft2-")
    ap.add_argument("--ag-oversample", type=int, default=0)
    ap.add_argument("--accepted-hashes", default="", help="JSON file with {'accepted': [...]} (data/frozen/accepted_row_hashes.json)")
    args = ap.parse_args()
    out = os.path.join(REPO, args.out)
    accepted = json.load(open(os.path.join(REPO, args.accepted_hashes)))["accepted"] if args.accepted_hashes else []
    text = json.dumps(build(args.rows_suffix, args.run_prefix, args.ag_oversample, accepted), indent=1, ensure_ascii=False) + "\n"
    if args.check:
        same = os.path.exists(out) and open(out, encoding="utf-8").read() == text
        print("notebook up to date" if same else "notebook OUT OF DATE")
        sys.exit(0 if same else 1)
    open(out, "w", encoding="utf-8", newline="\n").write(text)
    print(f"wrote {out} ({len(text) / 1e6:.2f} MB, {len(json.loads(text)['cells'])} cells)")


if __name__ == "__main__":
    main()
