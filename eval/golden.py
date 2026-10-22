"""Golden-set harness: where does pipeline v3 differ from v2, call by call?

    python laya-finetuning/eval/golden.py rules            # the four rule checks + auto-fail, no model, seconds

The AI-written answer keys for the rule items were computed with the v2 rule code (validate_calls.py enforces it), so a key cannot say
whether a v3 change is right. This script lists every call where v3 and v2 disagree, per rule and direction, so each can be reviewed.
For the sealed-style sets (AG-B, AG-B2, AG-C) it prints call ids only, never dialogue.
"""
import argparse
import collections
import glob
import json
import os
import sys

import _roots  # noqa: E402  (finds the QA app root; see _roots.py)
ROOT = _roots.QA_ROOT
sys.path.insert(0, ROOT)

SETS = [("AG-T", "laya-finetuning/inputs/AG-T", "agt_*.json"), ("AG50", "laya-finetuning/inputs/AG50", "ag_*.json"), ("AG-B", "laya-finetuning/inputs/AG-B", "agb_*.json"),
        ("AG-B2", "laya-finetuning/inputs/AG-B2", "agb2_*.json"), ("AG-C", "laya-finetuning/inputs/AG-C", "agc_*.json"), ("Main", "inputs/Main tests", "gold_*.json"),
        ("Bulk", "inputs/Bulk tests", "*.json")]
SEALED = {"AG-B", "AG-B2", "AG-C"}
RULES = ["Branding", "Dead air", "Verified", "Personalized", "Auto-fail"]


def v2_results(payload):
    from src.services.dynamic_evaluator import check_auto_fail
    from src.services.laya_inputs import parse_transcript
    from src.services.rule_engine import (evaluate_branding, evaluate_hold_and_dead_air, evaluate_personalized_call, evaluate_verified_customer)
    turns, times, _, agent_lines, _, name, _ = parse_transcript(payload["transcript"], payload.get("customer_name"))
    agent_text = "\n".join(f"Agent: {x}" for x in agent_lines)
    return {"Branding": evaluate_branding(turns)["rating"], "Dead air": evaluate_hold_and_dead_air(turns, times)["rating"],
            "Verified": evaluate_verified_customer(turns, times)["rating"],
            "Personalized": evaluate_personalized_call(turns, payload.get("customer_name") or "")["rating"],
            "Auto-fail": "FAIL" if check_auto_fail(agent_text, [], [], [])[0] else "PASS"}


def v3_results(payload):
    from src.v3 import rules
    from src.v3.normalise import normalise
    c = normalise(payload["transcript"], payload.get("customer_name"))
    return {"Branding": rules.evaluate_branding(c)["rating"], "Dead air": rules.evaluate_dead_air(c)["rating"],
            "Verified": rules.evaluate_verified(c)["rating"], "Personalized": rules.evaluate_personalized(c)["rating"],
            "Auto-fail": "FAIL" if rules.check_auto_fail(c)[0] else "PASS"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["rules"])
    ap.add_argument("--show", type=int, default=15, help="ids listed per rule and direction")
    args = ap.parse_args()
    total = collections.Counter()
    for label, folder, pattern in SETS:
        files = [f for f in sorted(glob.glob(os.path.join(ROOT, folder, pattern))) if "expected" not in f and "result" not in os.path.basename(f).lower()]
        diffs = collections.defaultdict(lambda: collections.defaultdict(list))
        n = errors = 0
        for fp in files:
            try:
                payload = json.load(open(fp, encoding="utf-8"))
                if not isinstance(payload, dict) or not payload.get("transcript"):
                    continue
                a, b = v2_results(payload), v3_results(payload)
            except Exception as e:                                     # a v2 crash is itself a finding
                errors += 1
                print(f"  {label}: {os.path.basename(fp)} raised {type(e).__name__}: {e}")
                continue
            n += 1
            for r in RULES:
                if a[r] != b[r]:
                    diffs[r][f"v2 {a[r]} -> v3 {b[r]}"].append(os.path.basename(fp)[:-5])
        print(f"\n{label}: {n} calls" + (f", {errors} errors" if errors else "") + ("   (ids only: sealed-style set)" if label in SEALED else ""))
        if not diffs:
            print("   v3 and v2 agree on every rule")
        for r in RULES:
            for direction, ids in diffs[r].items():
                total[(r, direction)] += len(ids)
                print(f"   {r:13s} {direction:24s} {len(ids):3d}  {', '.join(ids[:args.show])}{' ...' if len(ids) > args.show else ''}")
    print("\nTotals over all sets:")
    for (r, d), k in sorted(total.items()):
        print(f"   {r:13s} {d:24s} {k}")


if __name__ == "__main__":
    main()
