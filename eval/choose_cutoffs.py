"""Choose a model's call-level cutoffs with a split-half check, and report cross-validated accuracy.

    python laya-finetuning/eval/choose_cutoffs.py --label ft6-softce --base laya-finetuning/runs/ft5-ag/exam_cutoffs_old.json \
        --half-a <probe agtdev> <probe ag50> --half-b <probe agb> <probe agb2> --out cutoffs.json

For each check: tune on half A and score on half B, then the reverse. A cutoff tuned on the whole pool replaces the base cutoff only
if tuning beat the base on the unseen half in BOTH directions (by at least --min-gain balanced accuracy). Otherwise the base stays:
on 50-60 calls a tuned cutoff often fits noise. Cross-validated "items right" counts each half once, scored with cutoffs from the
other half, so no number here grades its own tuning data. Keys are AI-written; never pass the sealed exam set here.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cutoff_eval as E  # noqa: E402


def rows(calls, item):
    out = []
    for stem, c in calls.items():
        key = E.key_for(stem)[0]
        if key and item in key:
            out.append((c["p"][item], key[item]))
    return out


def load_all(paths):
    calls = {}
    for p in paths:
        calls.update(E.load(p)[1])
    return calls


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--label", required=True)
    ap.add_argument("--base", required=True, help='JSON {"cutoffs": {...}}: the cutoffs to keep unless tuning holds up')
    ap.add_argument("--half-a", nargs="+", required=True)
    ap.add_argument("--half-b", nargs="+", required=True)
    ap.add_argument("--min-gain", type=float, default=0.02)
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    base = json.load(open(args.base))["cutoffs"]
    A, B = load_all(args.half_a), load_all(args.half_b)
    pool = {**A, **B}

    final, cv_right, cv_total, base_right = {}, 0, 0, 0
    print(f"[{args.label}] half A {len(A)} calls, half B {len(B)} calls")
    print(f"{'check':36s} {'base':>5s} {'pool':>6s} | {'BA on B: base / tuned on A':>27s} | {'BA on A: base / tuned on B':>27s} | decision")
    for item, (_, _, default, tkey, _, _) in E.JUDGED.items():
        b = base[tkey]
        ra, rb, rp = rows(A, item), rows(B, item), rows(pool, item)
        cut_a = E.tune(ra, default, b)[1]
        cut_b = E.tune(rb, default, b)[1]
        cut_p = E.tune(rp, default, b)[1]
        g1 = E.ba_at(rb, default, cut_a) - E.ba_at(rb, default, b)
        g2 = E.ba_at(ra, default, cut_b) - E.ba_at(ra, default, b)
        use = g1 >= args.min_gain and g2 >= args.min_gain
        final[tkey] = cut_p if use else b
        # cross-validated items right: each half scored with the cutoff chosen WITHOUT it (base, or tuned on the other half)
        ca, cb = (cut_b if use else b), (cut_a if use else b)
        cv_right += sum(E.rate(p, default, ca) == k for p, k in ra) + sum(E.rate(p, default, cb) == k for p, k in rb)
        cv_total += len(ra) + len(rb)
        base_right += sum(E.rate(p, default, b) == k for p, k in ra + rb)
        print(f"{item[:36]:36s} {b:5.2f} {cut_p:6.3f} | {E.ba_at(rb, default, b):12.2f} / {E.ba_at(rb, default, cut_a):.2f} ({g1:+.2f}) | "
              f"{E.ba_at(ra, default, b):12.2f} / {E.ba_at(ra, default, cut_b):.2f} ({g2:+.2f}) | {'TUNED ' + format(cut_p, '.3f') if use else 'keep base'}")
    print(f"items right on the pool: base cutoffs {base_right}/{cv_total} ({base_right / cv_total:.1%}); "
          f"cross-validated with this rule {cv_right}/{cv_total} ({cv_right / cv_total:.1%})")
    if args.out:
        json.dump({"cutoffs": final, "rule": f"base unless split-half tuning gained >= {args.min_gain} balanced accuracy on the unseen half "
                   "in both directions; then tuned on the pooled development calls", "base": os.path.basename(args.base),
                   "half_a": [os.path.basename(p) for p in args.half_a], "half_b": [os.path.basename(p) for p in args.half_b]},
                  open(args.out, "w"), indent=1)
        print("wrote", args.out)


if __name__ == "__main__":
    main()
