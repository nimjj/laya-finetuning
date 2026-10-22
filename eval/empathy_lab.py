"""Empathy lab: one window per distinct outburst (strict rubric: every new outburst must be handled).

Scores laya_windows.empathy_episode_windows variants with the checkpoint in LAYA_CHECKPOINT (stock when unset) on
AG50, the Main calls and the bulk b_* calls, and reports balanced accuracy per set. An item FAILs when ANY window fails.
Keys: AG50 and Main from their expected files; bulk from the defect named in the file name ("empathy" -> FAIL).
The AG50 key was written with a lenient rule (acknowledging once is enough), so its FAIL/PASS can disagree with the strict rubric.

    set LAYA_CHECKPOINT=<folder> ; python laya-finetuning/eval/empathy_lab.py out.json
"""
import glob
import json
import os
import re
import sys

import numpy as np

import _roots  # noqa: E402  (finds the QA app root; see _roots.py)
ROOT = _roots.QA_ROOT
sys.path.insert(0, ROOT)
from src.services import dynamic_evaluator as de            # noqa: E402
from src.services import laya_windows as W                  # noqa: E402
from src.services.laya_adapter import predict_yes           # noqa: E402
from src.services.laya_inputs import parse_transcript      # noqa: E402

NAME = "Empathy & Acknowledgment Statement"
VARIANTS = {"calm2": dict(calm_customer_turns=2), "calm4": dict(calm_customer_turns=4), "calm6": dict(calm_customer_turns=6),
            "calm4_gap10": dict(calm_customer_turns=4, min_gap=10)}
cache = {}


def p_pass(text):
    if text not in cache:
        c = de.LAYA_CHECKS["empathy"]
        cache[text] = float(de._p_pass(c, predict_yes(text, {"q": c["question"]}, label="empathy_lab")["q"]))
    return cache[text]


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


sets = {"AG50": [], "bulk": [], "Main": []}
for fp in sorted(glob.glob(os.path.join(ROOT, "laya-finetuning", "inputs", "AG50", "ag_*.json"))):
    c = os.path.basename(fp)[:-5]
    k = {i["name"]: i["rating"] for i in load(os.path.join(ROOT, "laya-finetuning", "inputs", "AG50", "expected", f"expected_{c}.json"))["result"]["scorecard"]}
    sets["AG50"].append((c, fp, k[NAME] == "FAIL"))
for fp in sorted(glob.glob(os.path.join(ROOT, "inputs", "Bulk tests", "b_*.json"))):
    sets["bulk"].append((os.path.basename(fp)[:-5], fp, "empathy" in os.path.basename(fp).lower()))
for fp in sorted(glob.glob(os.path.join(ROOT, "inputs", "Main tests", "gold_*.json"))):
    c = os.path.basename(fp)[:-5]
    k = {i["name"]: i["rating"] for i in load(os.path.join(ROOT, "inputs", "Main tests", "expected", f"expected_{c}.json"))["result"]["scorecard"]}
    sets["Main"].append((c, fp, k[NAME] == "FAIL"))

out = {"checkpoint": os.getenv("LAYA_CHECKPOINT") or "stock", "cutoff": de.LAYA_CHECKS["empathy"]["pass_threshold"], "sets": {}}
for sname, items in sets.items():
    out["sets"][sname] = []
    for c, fp, fail in items:
        p = load(fp)
        turns, _, _, _, _, _, sent = parse_transcript(p["transcript"], p.get("customer_name"))
        rec = {"call": c, "key_fail": fail, "variants": {}}
        for vname, kw in VARIANTS.items():
            ws = W.empathy_episode_windows(turns, sent, **kw)
            ps = [p_pass(w) for w in ws]
            rec["variants"][vname] = {"n": len(ws), "min_p": min(ps) if ps else 1.0, "p": ps}
        out["sets"][sname].append(rec)
        print(sname, c, flush=True)

cut = out["cutoff"]
for vname in VARIANTS:
    print(f"\n== {vname} (strict: fail if any window fails; cutoff {cut}) ==")
    for sname, recs in out["sets"].items():
        y = np.array([r["key_fail"] for r in recs])
        pf = np.array([r["variants"][vname]["min_p"] < cut for r in recs])
        tp, fn, fp_, tn = int((y & pf).sum()), int((y & ~pf).sum()), int((~y & pf).sum()), int((~y & ~pf).sum())
        tpr = tp / (tp + fn) if tp + fn else float("nan")
        tnr = tn / (tn + fp_) if tn + fp_ else float("nan")
        print(f"{sname:5s} faults {int(y.sum()):2d}/{len(y)}  caught {tp} missed {fn} false alarms {fp_} ok {tn}  BA {0.5 * (tpr + tnr):.2f}  windows/call {np.mean([r['variants'][vname]['n'] for r in recs]):.1f}")
path = sys.argv[1]
with open(path, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1)
print("saved", path)
