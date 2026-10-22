"""Run v2 and v3 side by side on a folder of calls with the real model, and list every item where they disagree.

    python laya-finetuning/eval/v3_compare.py laya-finetuning/inputs/AG-T --out runs/v3_compare_agt.jsonl --limit 20

Model results are memoised by (window text, question), so v3 only pays for windows that differ from v2's. Output is one JSON line per call
(resumable: calls already in --out are skipped). Sealed-style sets (AG-B, AG-B2, AG-C) are summarised by id only, never dialogue.
Both flows use the checkpoint in .env (LAYA_CHECKPOINT). The comparison is v3 vs v2 on AI-written calls: it shows where they differ,
not which one is right.
"""
import argparse
import collections
import glob
import hashlib
import json
import os
import sys
import time

import _roots  # noqa: E402  (finds the QA app root; see _roots.py)
ROOT = _roots.QA_ROOT
sys.path.insert(0, ROOT)
from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(ROOT, ".env"))

import src.services.dynamic_evaluator as de  # noqa: E402
from src.v3.pipeline import evaluate_v3  # noqa: E402

SEALED = ("AG-B", "AG-B2", "AG-C")
_memo, _stats = {}, collections.Counter()
_orig = de.predict_yes


def memo_predict(text, questions, label=None, **kw):
    key = hashlib.sha1(json.dumps([text, label, {k: (q.get("question") if isinstance(q, dict) else q) for k, q in questions.items()}],
                                  sort_keys=True, default=str).encode()).hexdigest()
    if key in _memo:
        _stats["hits"] += 1
        return _memo[key]
    t0 = time.perf_counter()
    res = _orig(text, questions, label=label, **kw)
    _stats["model_seconds"] += time.perf_counter() - t0
    _stats["misses"] += 1
    _memo[key] = res
    return res


de.predict_yes = memo_predict


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--show", type=int, default=12)
    args = ap.parse_args()
    with open(os.path.join(ROOT, "resources", "criteria_config.json"), encoding="utf-8") as f:
        criteria = json.load(f)["tenant-abc"]
    files = [f for f in sorted(glob.glob(os.path.join(os.path.abspath(args.folder), "*.json")))
             if "expected" not in f and "result" not in os.path.basename(f).lower()]
    if args.limit:
        files = files[:args.limit]
    done = set()
    if os.path.exists(args.out):
        with open(args.out, encoding="utf-8") as f:
            done = {json.loads(line)["call"] for line in f if line.strip()}
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "a", encoding="utf-8") as out:
        for fp in files:
            name = os.path.basename(fp)[:-5]
            if name in done:
                continue
            payload = json.load(open(fp, encoding="utf-8"))
            if not isinstance(payload, dict) or not payload.get("transcript"):
                continue
            caller = payload.get("customer_name") or payload.get("customerName")
            t0 = time.perf_counter()
            a = de.evaluate_interaction(payload["transcript"], criteria, "tenant-abc", caller=caller)
            t1 = time.perf_counter()
            b = evaluate_v3(payload["transcript"], criteria, "tenant-abc", caller=caller)
            t2 = time.perf_counter()
            key_path = os.path.join(os.path.dirname(fp), "expected", f"expected_{name}.json")
            key = None
            if os.path.exists(key_path):
                ke = json.load(open(key_path, encoding="utf-8"))
                key = {i["name"]: i["rating"] for i in ke["result"]["scorecard"]}
                key_score = ke["result"]["final_score"]
            rec = {"key": key, "key_score": key_score if key else None, "call": name, "v2_score": a["final_score"], "v3_score": b["final_score"], "v2_af": a["is_auto_fail"], "v3_af": b["is_auto_fail"],
                   "v2": {i["name"]: i["rating"] for i in a["scorecard"]}, "v3": {i["name"]: i["rating"] for i in b["scorecard"]},
                   "v3_rows": b["meta"]["model_rows"], "v3_words": b["meta"]["model_words"], "v2_sec": round(t1 - t0, 1), "v3_sec": round(t2 - t1, 1)}
            out.write(json.dumps(rec) + "\n")
            out.flush()
            print(f"{name}: v2 {a['final_score']} v3 {b['final_score']}  ({rec['v2_sec']}s, {rec['v3_sec']}s)", flush=True)
    summarise(args.out, args.folder, args.show)
    print(f"model windows computed {_stats['misses']}, reused {_stats['hits']}, {_stats['model_seconds']:.0f} s in the model")


def summarise(path, folder, show):
    recs = [json.loads(line) for line in open(path, encoding="utf-8") if line.strip()]
    sealed = any(s in folder for s in SEALED)
    diffs = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in recs:
        for item, v in r["v2"].items():
            w = r["v3"].get(item)
            if w != v:
                diffs[item][f"v2 {v} -> v3 {w}"].append(r["call"])
    gap = [abs(r["v2_score"] - r["v3_score"]) for r in recs]
    print(f"\n{len(recs)} calls{' (ids only: sealed-style set)' if sealed else ''}; mean |score change| {sum(gap) / max(1, len(gap)):.1f}; "
          f"calls with any change {sum(g > 0 for g in gap)}; auto-fail v2 {sum(r['v2_af'] for r in recs)} v3 {sum(r['v3_af'] for r in recs)}")
    if recs:
        print(f"mean seconds per call: v2 {sum(r['v2_sec'] for r in recs) / len(recs):.1f}, v3 {sum(r['v3_sec'] for r in recs) / len(recs):.1f} "
              f"(v3 is faster here because it reuses v2's model answers); mean model rows {sum(r['v3_rows'] for r in recs) / len(recs):.1f}, "
              f"words {sum(r['v3_words'] for r in recs) / len(recs):.0f}")
    for item, d in sorted(diffs.items()):
        for direction, ids in d.items():
            print(f"  {item[:42]:42s} {direction:20s} {len(ids):3d}  {', '.join(ids[:show])}{' ...' if len(ids) > show else ''}")
    keyed = [r for r in recs if r.get("key")]
    if keyed:
        print(f"\nAgainst the AI-written keys ({len(keyed)} calls): items matching the key, v2 vs v3, and calls only one flow got right (v3 better / v3 worse)")
        tot = [0, 0, 0, 0]
        for item in keyed[0]["v2"]:
            a = sum(r["v2"].get(item) == r["key"].get(item) for r in keyed)
            b = sum(r["v3"].get(item) == r["key"].get(item) for r in keyed)
            better = sum(r["v3"].get(item) == r["key"].get(item) and r["v2"].get(item) != r["key"].get(item) for r in keyed)
            worse = sum(r["v3"].get(item) != r["key"].get(item) and r["v2"].get(item) == r["key"].get(item) for r in keyed)
            flag = "" if (a, b) == (b, a) and better == worse == 0 else "  <-- differs"
            print(f"  {item[:44]:44s} v2 {a:3d}  v3 {b:3d}   {better} / {worse}{flag}")
            tot = [tot[0] + a, tot[1] + b, tot[2] + better, tot[3] + worse]
        n = len(keyed) * len(keyed[0]["v2"])
        print(f"  {'ALL ITEMS':44s} v2 {tot[0]:3d}  v3 {tot[1]:3d}  of {n}   {tot[2]} / {tot[3]}")
        e2 = sum(abs(r["v2_score"] - r["key_score"]) for r in keyed) / len(keyed)
        e3 = sum(abs(r["v3_score"] - r["key_score"]) for r in keyed) / len(keyed)
        print(f"  mean |final score - key score|: v2 {e2:.1f}, v3 {e3:.1f}")


if __name__ == "__main__":
    main()
