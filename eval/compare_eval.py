"""Compare batch_test.py result folders for a suite against that suite's expected scorecards.

Usage (from the repo root):
    python laya-finetuning/eval/compare_eval.py Eval50 laya-ft laya-stock ollama
    python laya-finetuning/eval/compare_eval.py Eval50 laya-ft ollama --out laya-finetuning/docs/EVAL50_RESULTS.md

Expected files: inputs/<suite>/expected/expected_<call>.json. Results: inputs/Test (results)/<suite> (<label>)/result_*.json.
Reports per engine: items matching the expected rating (overall and per item), balanced accuracy per item
(FAIL is the positive class), mean absolute final-score error, auto-fail agreement, and mean time per call. Then lists
every item where the engines disagree with each other, for human review.
"""
import argparse
import glob
import json
import os
import re
import sys

import _roots  # noqa: E402  (finds the QA app root; see _roots.py)
ROOT = _roots.QA_ROOT
ITEMS = [
    "Branding and Survey Check", "Hold time and Dead Air", "Verified customer",
    "Personalized the call/ticket appropriately", "Empathy & Acknowledgment Statement", "Paraphrasing",
    "Active listening", "Took ownership of the problem", "Build rapport and observed professionalism",
    "Probing", "Confirmed the issue is resolved",
]
SHORT = {"Branding and Survey Check": "Branding", "Hold time and Dead Air": "Dead air", "Verified customer": "Verified",
         "Personalized the call/ticket appropriately": "Personalized", "Empathy & Acknowledgment Statement": "Empathy",
         "Paraphrasing": "Paraphrasing", "Active listening": "Active listening",
         "Took ownership of the problem": "Ownership", "Build rapport and observed professionalism": "Rapport",
         "Probing": "Probing", "Confirmed the issue is resolved": "Resolved"}
LAYA_DECIDED = {"Empathy & Acknowledgment Statement", "Paraphrasing", "Active listening", "Took ownership of the problem",
                "Build rapport and observed professionalism", "Probing", "Confirmed the issue is resolved"}


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def ratings(doc):
    return {i["name"]: i["rating"] for i in doc["result"]["scorecard"]}


def load_results(suite, label):
    out = {}
    for fp in sorted(glob.glob(os.path.join(_roots.results_root(suite), f"{suite} ({label})", "result_*.json"))):
        stem = re.sub(r"^result_\d{8}_\d{6}_", "", os.path.basename(fp))[:-len(".json")]
        out[stem] = load(fp)
    return out


def bal_acc(pairs):
    """pairs of (expected, got); FAIL is the positive class."""
    pos = [g for e, g in pairs if e == "FAIL"]
    neg = [g for e, g in pairs if e == "PASS"]
    if not pos or not neg:
        return None
    return 0.5 * (sum(g == "FAIL" for g in pos) / len(pos) + sum(g == "PASS" for g in neg) / len(neg))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("suite")
    ap.add_argument("labels", nargs="+")
    ap.add_argument("--out")
    args = ap.parse_args()
    exp = {os.path.basename(f)[len("expected_"):-len(".json")]: load(f)
           for f in sorted(glob.glob(os.path.join(_roots.suite_dir(args.suite), "expected", "expected_*.json")))}
    res = {lb: load_results(args.suite, lb) for lb in args.labels}
    L = []
    author = "Antigravity" if args.suite.upper().startswith("AG") else "Claude"      # who wrote the keys of this suite
    L += [f"# {args.suite}: engines vs {author}'s expected scorecards", "",
          f"{len(exp)} calls. Expected scorecards were written by {author}" + (" before any engine ran" if author == "Claude" else "") + " (not human-reviewed).", ""]
    for lb in args.labels:
        missing = [c for c in exp if c not in res[lb]]
        if missing:
            L.append(f"**{lb}: {len(missing)} calls have no result** ({', '.join(missing[:8])}{'...' if len(missing) > 8 else ''})")
    L.append("")

    # summary
    L += ["## Summary", "", "| | " + " | ".join(args.labels) + " |", "|---|" + "---|" * len(args.labels)]
    rows = {k: [] for k in ("items", "laya_items", "err", "af", "time", "calls")}
    per_item = {lb: {it: [] for it in ITEMS} for lb in args.labels}
    for lb in args.labels:
        n = m = nl = ml = af_ok = 0
        errs, times = [], []
        for c, e in exp.items():
            if c not in res[lb]:
                continue
            got, want = ratings(res[lb][c]), ratings(e)
            for it in ITEMS:
                if it in got and it in want:
                    n += 1
                    m += got[it] == want[it]
                    per_item[lb][it].append((want[it], got[it]))
                    if it in LAYA_DECIDED:
                        nl += 1
                        ml += got[it] == want[it]
            errs.append(abs(res[lb][c]["result"]["final_score"] - e["result"]["final_score"]))
            af_ok += bool(res[lb][c]["result"].get("is_auto_fail")) == bool(e["result"].get("is_auto_fail"))
            if res[lb][c].get("elapsed_sec") is not None:
                times.append(res[lb][c]["elapsed_sec"])
        rows["calls"].append(f"{len(errs)}")
        rows["items"].append(f"{m}/{n} ({100 * m / n:.0f}%)" if n else "-")
        rows["laya_items"].append(f"{ml}/{nl} ({100 * ml / nl:.0f}%)" if nl else "-")
        rows["err"].append(f"{sum(errs) / len(errs):.1f}" if errs else "-")
        rows["af"].append(f"{af_ok}/{len(errs)}")
        rows["time"].append(f"{sum(times) / len(times):.1f} s" if times else "-")
    for key, title in (("calls", "Calls scored"), ("items", "All items matching expected"),
                       ("laya_items", "Model-judged items matching (7 items: empathy ... resolved)"),
                       ("err", "Mean absolute final-score error"), ("af", "Auto-fail decision matching"),
                       ("time", "Mean time per call")):
        L.append(f"| {title} | " + " | ".join(rows[key]) + " |")
    L.append("")

    # per item
    L += ["## Per item: matching expected / balanced accuracy (FAIL = positive)", "",
          "| Item | expected FAILs | " + " | ".join(args.labels) + " |", "|---|---|" + "---|" * len(args.labels)]
    for it in ITEMS:
        nf = sum(ratings(e).get(it) == "FAIL" for e in exp.values())
        cells = []
        for lb in args.labels:
            p = per_item[lb][it]
            ba = bal_acc(p)
            cells.append(f"{sum(a == b for a, b in p)}/{len(p)}" + (f" / {ba:.2f}" if ba is not None else ""))
        L.append(f"| {SHORT[it]} | {nf} | " + " | ".join(cells) + " |")
    L.append("")

    # per call scores
    L += ["## Final scores per call", "", "| Call | expected | " + " | ".join(args.labels) + " |",
          "|---|---|" + "---|" * len(args.labels)]
    for c, e in exp.items():
        cells = []
        for lb in args.labels:
            r = res[lb].get(c)
            cells.append("-" if r is None else f"{r['result']['final_score']}{' AF' if r['result'].get('is_auto_fail') else ''}")
        ee = e["result"]
        L.append(f"| {c} | {ee['final_score']}{' AF' if ee.get('is_auto_fail') else ''} | " + " | ".join(cells) + " |")
    L.append("")

    # disagreements for review
    L += ["## Items where the engines and the expected key do not all agree", "",
          "| Call | Item | expected | " + " | ".join(args.labels) + f" | {author}'s note |", "|---|---|---|" + "---|" * len(args.labels) + "---|"]
    for c, e in exp.items():
        want = ratings(e)
        for it in ITEMS:
            vals = [ratings(res[lb][c]).get(it, "-") if c in res[lb] else "-" for lb in args.labels]
            if any(v != want.get(it) for v in vals):
                note = e.get("grader", {}).get("notes", "")
                L.append(f"| {c} | {SHORT[it]} | {want.get(it)} | " + " | ".join(vals) + f" | {note[:160]} |")
    text = "\n".join(L) + "\n"
    if args.out:
        with open(os.path.join(ROOT, args.out), "w", encoding="utf-8") as f:
            f.write(text)
    sys.stdout.reconfigure(encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
