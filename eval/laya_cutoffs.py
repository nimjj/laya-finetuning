"""Pick a pass cutoff per Laya check from the defects named in the b_* filenames.

Reads a probe file from laya-finetuning/eval/probe_laya.py. For each check, a b_* call whose filename names that defect
(b_15_noconfirm -> Resolved) should FAIL and every other b_* call should PASS. Prints the spread of P(pass)
for both groups and the cutoff with the best balanced accuracy. Auto-fail calls are skipped.

Usage:
    python laya-finetuning/eval/laya_cutoffs.py "laya-finetuning/inputs/Test (results)/Laya probes/probe_laya-v2.json"
"""
import argparse
import json
import re

# probe label -> filename tokens that mean "this check should FAIL"
LABEL_TO_TOKEN = {"batch_end": {"noconfirm"}, "verify_empathy": {"empathy"}, "verify_rapport": {"rapport"},
                  "verify_paraphrasing": {"nopara", "nopa"}, "verify_probing": {"noprobe"},
                  "verify_ownership": {"ownership"}, "verify_al": {"al"}}
# for these labels a yes answer means PASS; for the rest (violation checks) yes means FAIL
YES_MEANS_PASS = {"batch_end", "verify_empathy", "verify_paraphrasing", "verify_probing"}

ap = argparse.ArgumentParser()
ap.add_argument("probe", help="probe JSON from laya-finetuning/eval/probe_laya.py")
ap.add_argument("--list", default="batch_end", help="label whose calls are listed one by one (default: batch_end)")
args = ap.parse_args()

with open(args.probe, encoding="utf-8") as f:
    d = json.load(f)
for label, tokens in LABEL_TO_TOKEN.items():
    rows = []  # (p_pass, should_pass, call)
    for c in d["calls"]:
        m = re.match(r"^(b_\d+)_(.*)\.json$", c["call"])
        if not m or "autofail" in c["call"]:
            continue
        should_fail = bool(tokens & set(m.group(2).split("_")))
        for x in c["laya"]:
            if x["label"] != label:
                continue
            p = list(x["p_yes"].values())[0]
            rows.append((p if label in YES_MEANS_PASS else 1 - p, not should_fail, c["call"]))
    if not rows:
        print(f"{label}: no Laya calls on b_* files\n")
        continue
    good = sorted(r[0] for r in rows if r[1])
    bad = sorted(r[0] for r in rows if not r[1])
    print(f"{label}: {len(good)} should-pass, {len(bad)} should-fail (P(pass) values)")
    print(f"  should PASS: min {good[0]:.3f} median {good[len(good)//2]:.3f} max {good[-1]:.3f}" if good else "  should PASS: none")
    print(f"  should FAIL: min {bad[0]:.3f} median {bad[len(bad)//2]:.3f} max {bad[-1]:.3f}" if bad else "  should FAIL: none")
    best = None
    for cut in sorted({round(r[0], 3) for r in rows} | {0.5, 0.6, 0.7, 0.8}):
        tp = sum(1 for p, sp, _ in rows if sp and p >= cut)
        tn = sum(1 for p, sp, _ in rows if not sp and p < cut)
        bal = ((tp / len(good) if good else 1) + (tn / len(bad) if bad else 1)) / 2
        if best is None or bal > best[0] + 1e-9:
            best = (bal, cut, tp, tn)
    print(f"  best cutoff {best[1]:.3f}: balanced accuracy {best[0]:.2f} ({best[2]}/{len(good)} pass, {best[3]}/{len(bad)} fail)")
    if label == args.list:
        for p, sp, call in sorted(rows):
            print(f"    {p:.3f} {'PASS' if sp else 'FAIL'}-label {call}")
    print()
