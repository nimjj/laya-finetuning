"""Pick the items of the 4 Main calls that a human must grade (focused Phase 0), and record why.

Selected:
  1. every item where Ollama or a Laya run (laya, laya-v2) disagreed with Claude's expected grade
  2. items Claude's own grading flagged as borderline (listed in BORDERLINE below)
  3. SPOT_CHECKS random judgment items from the rest, seeded, to estimate how often Claude's unreviewed
     grades are wrong. They are not marked in the sheet the reviewer sees.
Rule-based criteria (Branding, Hold/Dead air, Personalized, Verified) are never spot-checked: they are facts a
script can verify against the transcript.

Writes data/review/subset_main.json (item ids + reasons). The reviewer's workbook never contains the reasons or
Claude's grades.

Usage:  python tools/pick_review_subset.py
"""
import argparse
import glob
import json
import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from make_review_sheet import CRITERIA  # noqa: E402

SHORT = {name: short for name, short, _ in CRITERIA}
JUDGMENT = {"EMP", "RAPPORT", "PARA", "PROBE", "OWN", "AL", "RESOLVED"}
BORDERLINE = {
    "2-BRAND": "Claude: closing says 'Thanks for calling S-Net', not the required script; a lenient grader might pass it",
    "4-AL": "Claude: no careless repeat by this app's definition, but the agent clearly does not listen; a stricter grader could fail it",
}
SPOT_CHECKS, SEED = 5, 20261016


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--qa-root", default=os.path.join(REPO, "..", "QA-system"))
    ap.add_argument("--out", default=os.path.join(REPO, "data", "review", "subset_main.json"))
    ap.add_argument("--engines", default="ollama,laya,laya-v2")
    args = ap.parse_args()
    qa = os.path.abspath(args.qa_root)

    expected = {}
    for p in sorted(glob.glob(os.path.join(qa, "inputs", "Main tests", "expected", "*.json"))):
        call = re.search(r"gold_(\d\d)", os.path.basename(p)).group(1).lstrip("0")
        d = json.load(open(p, encoding="utf-8"))
        expected[call] = {i["name"]: i["rating"] for i in d["grader"]["items"]}

    reasons = {}
    for engine in args.engines.split(","):
        for p in glob.glob(os.path.join(qa, "inputs", "Test (results)", f"Main tests ({engine})", "*.json")):
            call = re.search(r"gold_(\d\d)", os.path.basename(p)).group(1).lstrip("0")
            d = json.load(open(p, encoding="utf-8"))
            for item in d.get("result", d)["scorecard"]:
                name = item["name"]
                if name in expected[call] and expected[call][name] != item["rating"]:
                    reasons.setdefault(f"{call}-{SHORT[name]}", []).append(f"{engine} says {item['rating']} (Claude {expected[call][name]})")
    for item_id, why in BORDERLINE.items():
        reasons.setdefault(item_id, []).append(why)

    rest = [f"{c}-{SHORT[n]}" for c in sorted(expected) for n in expected[c] if SHORT[n] in JUDGMENT
            and f"{c}-{SHORT[n]}" not in reasons]
    spot = sorted(random.Random(SEED).sample(rest, SPOT_CHECKS))
    for item_id in spot:
        reasons[item_id] = ["spot check (random, all engines agreed with Claude)"]

    order = {short: i for i, (_, short, _) in enumerate(CRITERIA)}
    ids = sorted(reasons, key=lambda x: (int(x.split("-")[0]), order[x.split("-")[1]]))
    out = {"seed": SEED, "n_items": len(ids), "items": ids, "reasons": {i: reasons[i] for i in ids}}
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(out, open(args.out, "w", encoding="utf-8"), indent=1)
    print(f"{len(ids)} items -> {args.out}")
    for i in ids:
        print(f"  {i:<12} {'; '.join(reasons[i])}")


if __name__ == "__main__":
    main()
