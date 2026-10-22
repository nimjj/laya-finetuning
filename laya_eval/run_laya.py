"""Run Laya on the gold set. Resumable.

Usage: python laya_eval/run_laya.py [english|multilingual ...] [--limit N]
Writes laya_eval/results/laya_<checkpoint>.jsonl, one line per item with P(true) for each question variant.
"""
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import questions as Q  # noqa: E402

from laya import Router  # noqa: E402

args = [a for a in sys.argv[1:] if not a.startswith("--")]
limit = None
if "--limit" in sys.argv:
    limit = int(sys.argv[sys.argv.index("--limit") + 1])
    args = [a for a in args if a != str(limit)]
checkpoints = args or ["english", "multilingual"]

CRITERIA = ["empathy", "active_listening", "ownership", "rapport", "probing", "resolved", "escalation", "hostility"]
items = []
for c in CRITERIA:
    with open(HERE / "data" / f"{c}.jsonl", encoding="utf-8") as f:
        items += [json.loads(l) for l in f]
if limit:
    items = items[:limit]

(HERE / "results").mkdir(exist_ok=True)
router = Router()

for ck in checkpoints:
    out = HERE / "results" / f"laya_{ck}.jsonl"
    done = set()
    if out.exists():
        done = {json.loads(l)["id"] for l in open(out, encoding="utf-8")}
    todo = [it for it in items if it["id"] not in done]
    print(f"[{ck}] {len(done)} done, {len(todo)} to run", flush=True)
    t_all = time.time()
    with open(out, "a", encoding="utf-8") as f:
        for n, it in enumerate(todo, 1):
            qs = Q.build_questions(it["criterion"])
            t0 = time.perf_counter()
            res = router.predict(it["text"], qs, model=ck)
            dt = time.perf_counter() - t0
            row = {"id": it["id"], "criterion": it["criterion"], "ckpt": ck, "latency_s": round(dt, 4),
                   "routed_model": res.get("routing", {}).get("model"),
                   "input_tokens": res["usage"].get("input_tokens"),
                   "truncated": bool(res["usage"].get("truncated")),
                   "p_yes": {}, "conf": {}}
            for v in Q.VARIANTS:
                a = res["answers"][v]
                row["p_yes"][v] = Q.p_yes(a, v)
                row["conf"][v] = a.get("answer_confidence")
            f.write(json.dumps(row) + "\n")
            f.flush()
            if n % 40 == 0:
                print(f"[{ck}] {n}/{len(todo)}  {time.time()-t_all:.0f}s", flush=True)
    print(f"[{ck}] finished in {time.time()-t_all:.0f}s", flush=True)
