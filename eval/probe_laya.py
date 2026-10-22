"""Run the Main and Bulk test calls through the evaluator in-process and record every Laya call.

For each call it saves the text Laya saw, the question(s), the yes-probabilities, the final score and the
ratings, plus the LAYA_CHECKS cutoffs in force. The ratings match /api/evaluate for the same code.
Feed the output to laya-finetuning/eval/laya_cutoffs.py to pick cutoffs from the b_* filename labels.

Usage:
    python laya-finetuning/eval/probe_laya.py "laya-finetuning/inputs/Test (results)/Laya probes/probe_laya-v3.json"
    python laya-finetuning/eval/probe_laya.py out.json --code-root ../other-checkout   # probe another version of src/
    python laya-finetuning/eval/probe_laya.py out.json --suite laya-finetuning/inputs/AG50             # probe one folder of calls

Loads Laya (~1.5 GB) and takes about 15 minutes on CPU. Don't run it while the service or Ollama is busy.
"""
import argparse
import glob
import json
import os
import sys
import time

import _roots  # noqa: E402  (finds the QA app root; see _roots.py)
ROOT = _roots.QA_ROOT

ap = argparse.ArgumentParser()
ap.add_argument("out", help="output JSON file")
ap.add_argument("--code-root", default=ROOT, help="checkout whose src/ is probed (default: this repo)")
ap.add_argument("--suite", default=None, help="probe only this folder of call payloads, e.g. laya-finetuning/inputs/AG50 (default: Main + Bulk)")
ap.add_argument("--no-text", action="store_true", help="do not store the snippet text (use for the sealed test sets AG-B / AG-B2)")
args = ap.parse_args()
sys.path[:0] = [args.code_root, os.path.join(args.code_root, "src")]

import src.services.dynamic_evaluator as de  # noqa: E402

calls_log = []
_orig = de.predict_yes


def logged(text, questions, label=None, **kw):
    t0 = time.perf_counter()
    res = _orig(text, questions, label=label, **kw)
    calls_log[-1]["laya"].append({
        "label": label,
        "words": len(text.split()),
        "text": None if args.no_text else text,
        "questions": {k: (q.get("question") if isinstance(q, dict) else q) for k, q in questions.items()},
        "p_yes": {k: round(float(v), 4) for k, v in res.items()},
        "sec": round(time.perf_counter() - t0, 2),
    })
    return res


de.predict_yes = logged

with open(os.path.join(ROOT, "resources", "criteria_config.json"), encoding="utf-8") as f:
    criteria = json.load(f)["tenant-abc"]

if args.suite:
    files = sorted(glob.glob(os.path.join(os.path.abspath(args.suite), "*.json")))
else:
    files = sorted(glob.glob(os.path.join(ROOT, "inputs", "Main tests", "gold_*.json")))
    files += sorted(glob.glob(os.path.join(ROOT, "inputs", "Bulk tests", "*.json")))
for fp in files:
    with open(fp, encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, dict) or not payload.get("transcript"):
        continue
    calls_log.append({"call": os.path.basename(fp), "laya": []})
    result = de.evaluate_interaction(payload["transcript"], criteria, "tenant-abc",
                                     caller=payload.get("customer_name") or payload.get("customerName"))
    calls_log[-1]["final_score"] = result["final_score"]
    calls_log[-1]["ratings"] = {i["name"]: i["rating"] for i in result["scorecard"]}
    print(os.path.basename(fp), result["final_score"], flush=True)

os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
with open(args.out, "w", encoding="utf-8") as f:
    json.dump({"thresholds": {k: {"yes_means": v["yes_means"], "pass_threshold": v["pass_threshold"]}
                              for k, v in de.LAYA_CHECKS.items()}, "calls": calls_log}, f, indent=2)
print("saved", args.out)
