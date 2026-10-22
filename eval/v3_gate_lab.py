"""Window lab: which lines should the model be shown for one check? Scores every candidate window against the AI-written answer keys.

    python laya-finetuning/eval/v3_gate_lab.py resolved                      # all variants, all sets
    python laya-finetuning/eval/v3_gate_lab.py resolved --variants tail10,cue

tail10 is today's v2 behaviour. Development sets (AG-T, AG50) are where a variant and its cutoff are chosen; the hold-out sets (AG-B, AG-B2,
AG-C) are looked at only to confirm, and are never used to pick anything. Model answers are cached by a hash of the window text, so a
re-run only pays for windows it has not seen. Prints counts only, never dialogue. Keys are AI-written, not human-labelled.
"""
import argparse
import glob
import hashlib
import json
import math
import os
import sys
import time

import _roots  # noqa: E402  (finds the QA app root; see _roots.py)
ROOT = _roots.QA_ROOT
sys.path.insert(0, ROOT)
from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(ROOT, ".env"))

import src.services.dynamic_evaluator as de  # noqa: E402
from src.v3.candidates import empathy as EMP  # noqa: E402
from src.v3.candidates import ownership as OWN  # noqa: E402
from src.v3.candidates import paraphrase as PARA  # noqa: E402
from src.v3.candidates import resolved as RES  # noqa: E402
from src.v3.normalise import normalise  # noqa: E402

CHECKS = {"resolved": {"item": "Confirmed the issue is resolved", "key": "resolved", "label": "batch_end", "variants": RES.VARIANTS, "combine": "single"},
          "paraphrasing": {"item": "Paraphrasing", "key": "paraphrasing", "label": "verify_paraphrasing", "variants": PARA.VARIANTS, "combine": "single"},
          # no window = nothing to object to = PASS (empty_score 1.0); the model answers "does the agent deflect?", so p_pass = 1 - p_yes
          "ownership": {"item": "Took ownership of the problem", "key": "ownership", "label": "verify_ownership", "variants": OWN.VARIANTS, "combine": "single", "empty_score": 1.0},
          # one model call per window, the item fails if ANY window fails (min of the scores); no window = no outburst = PASS
          "empathy": {"item": "Empathy & Acknowledgment Statement", "key": "empathy", "label": "verify_empathy", "variants": EMP.VARIANTS, "combine": "min", "empty_score": 1.0}}
DEV = ["AG-T", "AG50"]
HOLD = ["AG-B", "AG-B2", "AG-C"]
FOLDERS = {"AG-T": "laya-finetuning/inputs/AG-T", "AG50": "laya-finetuning/inputs/AG50", "AG-B": "laya-finetuning/inputs/AG-B", "AG-B2": "laya-finetuning/inputs/AG-B2", "AG-C": "laya-finetuning/inputs/AG-C"}
CACHE_PATH = os.path.join(ROOT, "laya-finetuning", "runs", "v3", "lab_cache.json")


def load_set(name, item):
    out = []
    for fp in sorted(glob.glob(os.path.join(ROOT, FOLDERS[name], "*.json"))):
        stem = os.path.basename(fp)[:-5]
        ef = os.path.join(ROOT, FOLDERS[name], "expected", f"expected_{stem}.json")
        if not os.path.exists(ef):
            continue
        d = json.load(open(fp, encoding="utf-8"))
        e = json.load(open(ef, encoding="utf-8"))
        rating = {i["name"]: i["rating"] for i in e["result"]["scorecard"]}.get(item)
        if rating in ("PASS", "FAIL") and isinstance(d, dict) and d.get("transcript"):
            out.append((stem, d, rating))
    return out


def auc(pos, neg):
    """P(a random PASS call scores above a random FAIL call); ties count half."""
    if not pos or not neg:
        return float("nan")
    wins = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg)
    return wins / (len(pos) * len(neg))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("check", choices=sorted(CHECKS))
    ap.add_argument("--variants", default="")
    ap.add_argument("--sets", default=",".join(DEV + HOLD))
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    cfg = CHECKS[args.check]
    check = de.LAYA_CHECKS[cfg["key"]]
    variants = {k: v for k, v in cfg["variants"].items() if not args.variants or k in args.variants.split(",")}
    cache = json.load(open(CACHE_PATH, encoding="utf-8")) if os.path.exists(CACHE_PATH) else {}
    stats = {"model": 0, "cached": 0, "sec": 0.0}

    ckpt = os.path.basename((os.getenv("LAYA_CHECKPOINT") or "").replace("\\", "/").rstrip("/"))      # the model's folder name, wherever it lives

    def p_pass(text):
        question = de.LAYA_CHECKS[cfg["key"]]["question"]["instructions"]
        key = hashlib.sha1(f"{args.check}|{question}|{ckpt}|{text}".encode()).hexdigest()
        # answers cached before 2026-10-22 were keyed with the old location of the production weights; still honour them
        legacy = hashlib.sha1(f"{args.check}|{question}|laya-finetuning/checkpoints/{ckpt}|{text}".encode()).hexdigest()
        if key in cache or legacy in cache:
            stats["cached"] += 1
            return cache[key] if key in cache else cache[legacy]
        t0 = time.perf_counter()
        p = de._p_pass(check, de.predict_yes(text, {"q": check["question"]}, label=cfg["label"])["q"])
        stats["sec"] += time.perf_counter() - t0
        stats["model"] += 1
        cache[key] = p
        return p

    rows = []
    for sname in args.sets.split(","):
        for stem, d, rating in load_set(sname, cfg["item"]):
            try:
                call = normalise(d["transcript"], d.get("customer_name") or d.get("customerName"))
            except Exception as e:
                print("skip", sname, stem, type(e).__name__)
                continue
            row = {"set": sname, "call": stem, "key": rating, "score": {}}
            for vname, fn in variants.items():
                windows = fn(call)
                row["score"][vname] = min(p_pass(w) for w in windows) if windows else cfg.get("empty_score", 0.0)
            if args.check == "resolved":                          # the end-of-call mood signal, alone and blended 50/50 with each model score
                mood = 1.0 / (1.0 + math.exp(-RES.end_mood(call) / 10.0))
                row["score"]["mood"] = mood
                for vname in list(variants):
                    row["score"][vname + "+mood"] = 0.5 * row["score"][vname] + 0.5 * mood
            rows.append(row)
        json.dump(cache, open(CACHE_PATH, "w", encoding="utf-8"))
        print(f"{sname}: scored ({stats['model']} model calls, {stats['cached']} cached, {stats['sec']:.0f} s)", flush=True)

    cut0 = check["pass_threshold"]
    base = "tail10" if "tail10" in variants else next(iter(variants))
    groups = {"dev": [r for r in rows if r["set"] in DEV], "hold": [r for r in rows if r["set"] in HOLD]}

    def acc(rs, v, cut):
        return sum((r["score"][v] >= cut) == (r["key"] == "PASS") for r in rs)

    print(f"\nCheck: {cfg['item']}   current cutoff {cut0}   dev = {', '.join(DEV)} ({len(groups['dev'])} calls), hold = {', '.join(HOLD)} ({len(groups['hold'])} calls)")
    print(f"{'variant':10s} {'dev@cut':>8s} {'hold@cut':>9s} {'devAUC':>7s} {'holdAUC':>8s} {'bestcut':>8s} {'dev@best':>9s} {'hold@best':>10s}   hold vs {base}: better/worse")
    for v in (list(rows[0]["score"]) if rows else []):
        dev, hold = groups["dev"], groups["hold"]
        cands = sorted({round(r["score"][v], 3) for r in dev})
        best = max(cands, key=lambda c: (acc(dev, v, c), -abs(c - cut0))) if cands else cut0
        aucs = []
        for rs in (dev, hold):
            aucs.append(auc([r["score"][v] for r in rs if r["key"] == "PASS"], [r["score"][v] for r in rs if r["key"] == "FAIL"]))
        b = sum((r["score"][v] >= cut0) == (r["key"] == "PASS") and (r["score"][base] >= cut0) != (r["key"] == "PASS") for r in hold)
        w = sum((r["score"][v] >= cut0) != (r["key"] == "PASS") and (r["score"][base] >= cut0) == (r["key"] == "PASS") for r in hold)
        print(f"{v:10s} {acc(dev, v, cut0):>4d}/{len(dev):<3d} {acc(hold, v, cut0):>5d}/{len(hold):<3d} {aucs[0]:>7.3f} {aucs[1]:>8.3f} {best:>8.3f} "
              f"{acc(dev, v, best):>5d}/{len(dev):<3d} {acc(hold, v, best):>6d}/{len(hold):<3d}   {b} / {w}")
    if args.out:
        json.dump({"check": args.check, "cutoff": cut0, "rows": rows}, open(args.out, "w", encoding="utf-8"))
    print(f"\nmodel calls {stats['model']}, cached {stats['cached']}, model time {stats['sec']:.0f} s")


if __name__ == "__main__":
    main()
