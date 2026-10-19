"""Check that a checkpoint trained on Colab also loads and predicts on this PC's CPU through laya_adapter.

It serves the checkpoint exactly the way qa-analysis will (LAYA_CHECKPOINT -> src/services/laya_adapter.py),
predicts the 20 smoke rows with the real frozen questions, and compares the numbers with the ones Colab
produced (smoke_preds_ft.json). It also proves the ORIGINAL base weights were not touched.

Run with the qa-analysis venv (it has laya and torch):
    ..\\qa-analysis\\.venv\\Scripts\\python.exe tools\\check_local_load.py ^
        --checkpoint checkpoints\\<run id>\\final --preds checkpoints\\<run id>\\smoke_preds_ft.json

PASS when: config says fine_tuned, every probability is within --tol (default 0.03) of Colab's, nothing is NaN,
and the base weights hash is unchanged. Exit code 0 = PASS.
"""
import argparse
import hashlib
import json
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import paths  # noqa: E402
BASE_WEIGHTS_SHA256 = "891102d372688fc2a094dac56a384bc537b87c63f21f9f3dac0be2b7cbc8d86c"   # snapshot 7b928d82...
BASE_SNAPSHOT = os.path.join("hub", "models--convaiinnovations--laya", "snapshots",
                             "7b928d828b7b0e022f929d9bd2e44165aa270148", "model.safetensors")


def sha256_file(path, chunk=1 << 24):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while block := f.read(chunk):
            h.update(block)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", required=True, help="folder with model.safetensors + rl_agent_config.json")
    ap.add_argument("--preds", required=True, help="smoke_preds_ft.json saved by the Colab notebook (cell 11)")
    ap.add_argument("--qa-root", default=paths.QA_ROOT)
    ap.add_argument("--frozen", default=os.path.join(REPO, "data", "frozen", "checks_frozen.json"))
    ap.add_argument("--tol", type=float, default=0.03)
    args = ap.parse_args()

    qa_root = os.path.abspath(args.qa_root)
    ckpt = os.path.abspath(args.checkpoint)
    problems = []

    cfg_path = os.path.join(ckpt, "rl_agent_config.json")
    if not os.path.isfile(cfg_path) or not os.path.isfile(os.path.join(ckpt, "model.safetensors")):
        sys.exit(f"FAIL: {ckpt} is not a checkpoint folder (needs model.safetensors and rl_agent_config.json)")
    cfg = json.load(open(cfg_path, encoding="utf-8"))
    print(f"config: fine_tuned={cfg.get('fine_tuned')} max_len={cfg.get('max_len')} head_max_len={cfg.get('head_max_len')}")
    if cfg.get("fine_tuned") is not True:
        problems.append("config does not say fine_tuned")

    # serve it through the production adapter, on CPU
    os.environ["LAYA_CHECKPOINT"] = ckpt
    os.environ.setdefault("LAYA_DEVICE", "cpu")
    sys.path[:0] = [qa_root, HERE]
    import smoke_rows
    from src.services import laya_adapter

    frozen = json.load(open(args.frozen, encoding="utf-8"))
    rows = smoke_rows.build_rows(frozen)
    colab = json.load(open(args.preds, encoding="utf-8"))

    local = {}
    t0 = time.time()
    for r in rows:
        probs = laya_adapter.predict_yes(r["state"], r["questions"], label="smoke")
        for qid, p in probs.items():
            local[f"{r['meta']['id']}/{qid}"] = p
    print(f"predicted {len(local)} questions on CPU in {time.time() - t0:.1f}s via laya_adapter (LAYA_CHECKPOINT)")

    missing = sorted(set(colab) ^ set(local))
    if missing:
        problems.append(f"question ids differ between Colab and local: {missing[:5]}")
    worst = 0.0
    print(f"{'row/question':<28} {'colab':>7} {'local':>7} {'diff':>7}")
    for k in sorted(set(colab) & set(local)):
        d = abs(colab[k] - local[k])
        worst = max(worst, d)
        flag = "" if d <= args.tol else "  <-- over tolerance"
        print(f"{k:<28} {colab[k]:7.3f} {local[k]:7.3f} {d:7.3f}{flag}")
    if any(math.isnan(v) for v in local.values()):
        problems.append("NaN in local predictions")
    print(f"largest difference: {worst:.4f} (tolerance {args.tol})")
    if worst > args.tol:
        problems.append(f"largest difference {worst:.4f} is over {args.tol}")

    # the original must be untouched
    hf_home = paths.hf_home() or os.path.join(os.path.expanduser("~"), ".cache", "huggingface")
    base_path = os.path.join(hf_home, BASE_SNAPSHOT)
    if os.path.isfile(base_path):
        ok = sha256_file(base_path) == BASE_WEIGHTS_SHA256
        print("original base weights unchanged:", ok)
        if not ok:
            problems.append("base weights hash changed")
    else:
        print(f"note: base snapshot not found at {base_path}; skipped the untouched-original check")

    print("\nPASS" if not problems else "\nFAIL: " + "; ".join(problems))
    sys.exit(0 if not problems else 1)


if __name__ == "__main__":
    main()
