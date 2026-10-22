"""Tune the call-level pass cutoffs of a checkpoint on one set of calls, then score it on a different set.

    python laya-finetuning/eval/cutoff_eval.py --tune "<probe agtdev>" "<probe mainbulk>" --eval "<probe ag50>" --label softce --out cutoffs.json

Inputs are probe files from laya-finetuning/eval/probe_laya.py (every Laya probability of every call, plus the ratings the app gave at the cutoffs
in force). The call-level value for a check is the lowest P(pass) over its windows (one weak window fails the call), exactly as
dynamic_evaluator does. Where the model is never asked, the app's fixed answer is used (no restatement cue or no question: FAIL; no
upset moment, no repeat candidate, no deflection: PASS).

Keys: AG-T and AG50 expected files, Main expected files, and the defects named in Bulk file names (compare_results.bulk_labels).
Every key is AI-written, none is human-reviewed. AG50 is a development set. Never pass AG-B to --tune, and use it for --eval only once.
"""
import argparse
import json
import os
import statistics
import sys

import _roots  # noqa: E402  (finds the QA app root; see _roots.py)
ROOT = _roots.QA_ROOT
sys.path.insert(0, os.path.join(ROOT, "Scripts"))
from compare_results import bulk_labels  # noqa: E402

# item -> (probe label, does "yes" mean PASS, answer when the model is never asked, thresholds key, deduction, category)
JUDGED = {
    "Empathy & Acknowledgment Statement": ("verify_empathy", True, "PASS", "empathy", 35, "Soft"),
    "Build rapport and observed professionalism": ("verify_rapport", False, "PASS", "rapport", 20, "Soft"),
    "Paraphrasing": ("verify_paraphrasing", True, "FAIL", "paraphrasing", 15, "Tech"),
    "Active listening": ("verify_al", False, "PASS", "active_listening", 10, "Tech"),
    "Took ownership of the problem": ("verify_ownership", False, "PASS", "ownership", 25, "Tech"),
    "Probing": ("verify_probing", True, "FAIL", "probing", 25, "Tech"),
    "Confirmed the issue is resolved": ("batch_end", True, "PASS", "resolved", 15, "Tech"),
}
RULE_DED = {"Branding and Survey Check": (15, "Soft"), "Hold time and Dead Air": (15, "Soft"),
            "Personalized the call/ticket appropriately": (15, "Soft"), "Verified customer": (25, "Tech")}


def key_for(stem):
    """(item -> rating, final_score or None) for a call, or (None, None)."""
    for prefix, folder in (("agc_", "AG-C"), ("agb2_", "AG-B2"), ("agb_", "AG-B"), ("agt_", "AG-T"), ("ag_", "AG50"), ("gold_", "Main tests")):
        if stem.startswith(prefix):
            p = os.path.join(_roots.suite_dir(folder), "expected", f"expected_{stem}.json")
            if os.path.exists(p):
                k = json.load(open(p, encoding="utf-8"))
                return {s["name"]: s["rating"] for s in k["result"]["scorecard"]}, k["result"]["final_score"]
            return None, None
    b = bulk_labels(stem)
    return (b, None) if b else (None, None)


def load(path):
    d = json.load(open(path, encoding="utf-8"))
    calls = {}
    for c in d["calls"]:
        per = {}
        for item, (label, yes_pass, _, _, _, _) in JUDGED.items():
            ps = [(lambda y: y if yes_pass else 1 - y)(list(x["p_yes"].values())[0]) for x in c["laya"] if x["label"] == label]
            per[item] = min(ps) if ps else None
        calls[c["call"][:-5]] = {"p": per, "ratings": c["ratings"], "final": c["final_score"]}
    return d["thresholds"], calls


def rate(p, default, cut):
    if p is None:
        return default
    return "PASS" if p >= cut else "FAIL"


def check_consistency(thr, calls):
    return sum(rate(c["p"][i], JUDGED[i][2], thr[JUDGED[i][3]]["pass_threshold"]) != c["ratings"].get(i)
               for c in calls.values() for i in JUDGED)


def ba_at(rows, default, cut):
    tp = fn = tn = fp = 0
    for p, key in rows:
        pred = rate(p, default, cut)
        if key == "FAIL":
            tp += pred == "FAIL"
            fn += pred == "PASS"
        else:
            tn += pred == "PASS"
            fp += pred == "FAIL"
    return ((tp / (tp + fn) if tp + fn else 1.0) + (tn / (tn + fp) if tn + fp else 1.0)) / 2


def tune(rows, default, current):
    """Best balanced accuracy; among equally good cutoffs, the middle of the plateau (the most margin on both sides)."""
    vals = sorted({p for p, _ in rows if p is not None})
    cands = sorted({round((a + b) / 2, 4) for a, b in zip(vals, vals[1:])} | {0.5, current})
    scored = [(ba_at(rows, default, c), c) for c in cands]
    best = max(s for s, _ in scored)
    plateau = [c for s, c in scored if s >= best - 1e-9]
    return best, round(statistics.median(plateau), 3)


def auc(rows, default):
    def s(p):
        return (2.0 if default == "FAIL" else -1.0) if p is None else 1 - p
    pos = [s(p) for p, k in rows if k == "FAIL"]
    neg = [s(p) for p, k in rows if k == "PASS"]
    if not pos or not neg:
        return None
    return sum((a > b) + 0.5 * (a == b) for a in pos for b in neg) / (len(pos) * len(neg))


def final_score(c, preds):
    soft = tech = 0
    for item, (_, _, _, _, ded, cat) in JUDGED.items():
        if preds[item] == "FAIL":
            soft, tech = (soft + ded, tech) if cat == "Soft" else (soft, tech + ded)
    for item, (ded, cat) in RULE_DED.items():
        if c["ratings"].get(item) == "FAIL":
            soft, tech = (soft + ded, tech) if cat == "Soft" else (soft, tech + ded)
    return 0.0 if c["final"] == 0.0 else round(0.333 * max(0, 100 - soft) + 0.667 * max(0, 100 - tech), 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tune", nargs="+", default=[])
    ap.add_argument("--eval", nargs="+", required=True)
    ap.add_argument("--cutoffs", default="", help='score at FIXED cutoffs from this JSON ({"cutoffs": {check: value}}); no tuning')
    ap.add_argument("--label", default="")
    ap.add_argument("--out", default="", help="write the tuned cutoffs here (JSON)")
    args = ap.parse_args()

    thr, tune_calls, ev_calls = None, {}, {}
    for p in args.tune:
        t, c = load(p)
        thr = thr or t
        tune_calls.update(c)
    for p in args.eval:
        t, c = load(p)
        thr = thr or t
        ev_calls.update(c)
    if not args.tune and not args.cutoffs:
        ap.error("give --tune (tune the cutoffs) or --cutoffs (score at fixed cutoffs)")
    fixed = json.load(open(args.cutoffs))["cutoffs"] if args.cutoffs else None
    bad = check_consistency(thr, {**tune_calls, **ev_calls})
    print(f"[{args.label}] consistency: ratings recomputed from the probabilities at the cutoffs in force differ from the app's in {bad} of "
          f"{7 * (len(tune_calls) + len(ev_calls))} judged items" + ("" if bad == 0 else "   <-- CHECK before trusting anything below"))
    print(f"tuning set: {len(tune_calls)} calls   evaluation set: {len(ev_calls)} calls\n")

    tuned = {}
    print(f"{'check':36s} {'tune F/P':>9s} {'in force':>9s} {'tuned':>7s} {'tuneBA':>7s} | {'eval F/P':>9s} {'AUC':>5s} {'BA@force':>9s} {'BA@tuned':>9s}")
    total = {"force": [0, 0], "tuned": [0, 0]}
    for item, (label, yes_pass, default, tkey, _, _) in JUDGED.items():
        cur = thr[tkey]["pass_threshold"]
        trows = [(c["p"][item], key_for(s)[0][item]) for s, c in tune_calls.items() if key_for(s)[0] and item in key_for(s)[0]]
        erows = [(c["p"][item], key_for(s)[0][item]) for s, c in ev_calls.items() if key_for(s)[0] and item in key_for(s)[0]]
        if fixed is not None:
            best, cut = float("nan"), fixed.get(tkey, cur)
        else:
            best, cut = tune(trows, default, cur) if trows else (float("nan"), cur)
        tuned[tkey] = cut

        def nf(r):
            return f"{sum(k == 'FAIL' for _, k in r)}/{sum(k == 'PASS' for _, k in r)}"
        for name, cc in (("force", cur), ("tuned", cut)):
            total[name][0] += sum(rate(p, default, cc) == k for p, k in erows)
            total[name][1] += len(erows)
        a = auc(erows, default)
        print(f"{item[:36]:36s} {nf(trows):>9s} {cur:9.2f} {cut:7.3f} {best:7.2f} | {nf(erows):>9s} {(f'{a:.2f}' if a is not None else '-'):>5s} "
              f"{ba_at(erows, default, cur):9.2f} {ba_at(erows, default, cut):9.2f}")
    print(f"\nitems matching the key on the evaluation set: cutoffs in force {total['force'][0]}/{total['force'][1]} "
          f"({total['force'][0] / max(total['force'][1], 1):.1%}); {'fixed' if fixed is not None else 'tuned'} cutoffs {total['tuned'][0]}/{total['tuned'][1]} "
          f"({total['tuned'][0] / max(total['tuned'][1], 1):.1%})")
    for name, cuts in (("in force", {k: v["pass_threshold"] for k, v in thr.items()}),
                       ("fixed" if fixed is not None else "tuned", {**{k: v["pass_threshold"] for k, v in thr.items()}, **tuned})):
        errs = []
        for s, c in ev_calls.items():
            fs = key_for(s)[1]
            if fs is None:
                continue
            preds = {i: rate(c["p"][i], JUDGED[i][2], cuts[JUDGED[i][3]]) for i in JUDGED}
            errs.append(final_score(c, preds) - fs)
        if errs:
            print(f"final score vs key, {name} cutoffs: mean absolute error {statistics.mean(abs(e) for e in errs):.1f}, "
                  f"bias {statistics.mean(errs):+.1f} ({len(errs)} calls)")
    if args.out:
        json.dump({"cutoffs": tuned, "tuned_on": [os.path.basename(p) for p in args.tune],
                   "note": "AI-written keys; call-level cutoffs; AG50 is a development set"}, open(args.out, "w"), indent=1)
        print("wrote", args.out)


if __name__ == "__main__":
    main()
