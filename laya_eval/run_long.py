"""Long-transcript stress test for the full-call criteria (Escalation, Hostility; pipeline batch B3).

Each gold call is inserted into the MIDDLE of a real, neutral, professional S-Net call
(inputs/Bulk tests/b_00_perfect.json, no escalation request and no hostility), giving ~900 tokens.
Modes:
  en_long   english checkpoint, router.predict_long (overlapping windows, strongest window per noul question)
  ml_8192   multilingual checkpoint, router.predict(max_len=8192) (one window)
Controls: the filler alone (label PASS for both criteria) to measure how far P(violation) drifts with no signal.

Usage: python laya-finetuning/laya_eval/run_long.py
Writes laya-finetuning/laya_eval/results/long.jsonl (resumable).
"""
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import questions as Q  # noqa: E402

from laya import Router  # noqa: E402

QA_ROOT = HERE.parents[1]  # repo root (the QA app); this folder is laya-finetuning/laya_eval
filler_turns = json.load(open(QA_ROOT / "inputs" / "Bulk tests" / "b_00_perfect.json", encoding="utf-8"))["transcript"]
filler = [f"{t['speaker']}: {t['text']}" for t in filler_turns]
mid = len(filler) // 2

CRITERIA = ["escalation", "hostility"]
items = []
for c in CRITERIA:
    items += [json.loads(l) for l in open(HERE / "data" / f"{c}.jsonl", encoding="utf-8")]
jobs = [{"id": it["id"], "criterion": it["criterion"], "label": it["label"],
         "text": "\n".join(filler[:mid] + it["lines"] + filler[mid:])} for it in items]
jobs += [{"id": f"control-{c}", "criterion": c, "label": "PASS", "text": "\n".join(filler)} for c in CRITERIA]

out = HERE / "results" / "long.jsonl"
done = {(json.loads(l)["id"], json.loads(l)["mode"]) for l in open(out, encoding="utf-8")} if out.exists() else set()
router = Router()
MODES = [("en_long", "english"), ("ml_8192", "multilingual")]

with open(out, "a", encoding="utf-8") as f:
    for mode, ck in MODES:
        todo = [j for j in jobs if (j["id"], mode) not in done]
        print(f"[{mode}] {len(todo)} to run", flush=True)
        t_all = time.time()
        for n, j in enumerate(todo, 1):
            qs = Q.build_questions(j["criterion"])
            t0 = time.perf_counter()
            if mode == "en_long":
                res = router.predict_long(j["text"], qs, model=ck)
            else:
                res = router.predict(j["text"], qs, model=ck, max_len=8192)
            dt = time.perf_counter() - t0
            row = {"id": j["id"], "criterion": j["criterion"], "label": j["label"], "mode": mode,
                   "latency_s": round(dt, 3), "windows": res["usage"].get("windows"),
                   "input_tokens": res["usage"].get("input_tokens"), "truncated": bool(res["usage"].get("truncated")),
                   "p_yes": {v: Q.p_yes(res["answers"][v], v) for v in Q.VARIANTS}}
            f.write(json.dumps(row) + "\n")
            f.flush()
            if n % 10 == 0:
                print(f"[{mode}] {n}/{len(todo)}  {time.time()-t_all:.0f}s", flush=True)
print("done", flush=True)
