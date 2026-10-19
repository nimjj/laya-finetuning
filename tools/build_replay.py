"""Replay rows: protect custom tenant criteria while the 9 frozen checks are fine-tuned.

Customer-defined criteria reach Laya as generic questions ("Did the agent do this: X?") over the batch texts
(agent-only text, end of call, full call), built exactly the way qa-analysis/_batch_check builds them. The fine-tune must
not change how the model answers those, so each replay row asks 1-3 such questions and its target (`gold`) is the
UNTOUCHED base model's own probability. No human or Claude label is involved.

Usage (qa-analysis venv, CPU, scores ~3 items/s):
    python tools/build_replay.py --fragments "data/fragments/claude/train_*.txt" --n 250 --seed 1 --out data/rows/replay_train.jsonl
    python tools/build_replay.py --fragments "data/fragments/claude/dev_*.txt"   --n 50  --seed 2 --out data/rows/replay_dev.jsonl
"""
import argparse
import glob
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import paths  # noqa: E402
from build_rows import Builder, parse_file, to_transcript  # noqa: E402

# (name, description, violation_based) -- the kind of custom line items tenants configure
CRITERIA = [
    ("Greeted the customer", "The agent greeted the customer at the start of the call.", False),
    ("Offered further assistance", "The agent asked whether there was anything else they could help with.", False),
    ("Used the customer's name", "The agent addressed the customer by name during the call.", False),
    ("Explained next steps", "The agent explained what would happen next and when.", False),
    ("Thanked the customer", "The agent thanked the customer for calling or for their patience.", False),
    ("Gave a reference number", "The agent gave the customer a case or reference number.", False),
    ("Summarised the call", "The agent summarised what was done before ending the call.", False),
    ("Apologised for the inconvenience", "The agent apologised for the problem or the wait.", False),
    ("Set a clear timeframe", "The agent gave a specific timeframe for the fix or the follow-up.", False),
    ("Asked permission before a hold", "The agent asked the customer before placing them on hold.", False),
    ("Promising refunds", "VIOLATION-BASED: The agent must not promise a refund or credit without approval.", True),
    ("Sharing personal opinions", "VIOLATION-BASED: The agent must not give personal opinions about the company or other customers.", True),
    ("Interrupting the customer", "VIOLATION-BASED: The agent must not interrupt or talk over the customer.", True),
    ("Using slang", "VIOLATION-BASED: The agent must not use slang or informal language.", True),
    ("Blaming the customer", "VIOLATION-BASED: The agent must not blame the customer for the problem.", True),
    ("Disclosing internal policy", "VIOLATION-BASED: The agent must not disclose internal procedures or staff details.", True),
    ("Making guarantees", "VIOLATION-BASED: The agent must not guarantee an outcome that is not certain.", True),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fragments", required=True)
    ap.add_argument("--n", type=int, required=True)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    b = Builder(source="replay")
    qa = paths.QA_ROOT
    from src.services.dynamic_evaluator import _batch_check
    from src.services.laya_adapter import predict_yes
    if os.getenv("LAYA_CHECKPOINT"):
        sys.exit("STOP: LAYA_CHECKPOINT is set. Replay targets must come from the UNTOUCHED base model.")

    frags = []
    for path in sorted(glob.glob(os.path.join(REPO, args.fragments))):
        frags += parse_file(path)
    # one member per pair, so the same call is not used twice
    seen, uniq = set(), []
    for f in frags:
        key = f.get("pair") or f["id"]
        if key not in seen:
            seen.add(key)
            uniq.append(f)
    rng = random.Random(args.seed)
    rng.shuffle(uniq)

    rows, tried = [], 0
    for f in uniq:
        if len(rows) >= args.n:
            break
        tried += 1
        transcript, _, rough = to_transcript(f)
        inp = b.build_laya_inputs(transcript, f.get("name"))
        kind = rng.choice(["batch_agent_only", "batch_agent_only", "resolved", "batch_full"])
        text = getattr(inp, kind)
        if not text:
            continue
        picks = rng.sample(CRITERIA, rng.choice([1, 2, 3]))
        questions = {}
        for n, (name, desc, _) in enumerate(picks):
            questions[f"item_{n}"] = _batch_check({"name": name, "description": desc})["question"]
        p = predict_yes(text, questions, label="replay")
        gold = {qid: {"probabilities": {"false": round(1 - v, 6), "true": round(v, 6)}} for qid, v in p.items()}
        # keep it inside the window with the real tokenizer (largest question head included)
        n_tok = len(b.lt.encode_state(b.tok, text, 10 ** 6))
        room = min(b.lc.state_room(b.tok, b.lt.to_internal(qid, q), b.max_len, b.head_max_len) for qid, q in questions.items())
        if n_tok > room:
            continue
        rows.append({"state": text, "questions": questions, "gold": gold,
                     "meta": {"id": f"rp_{f['id']}", "call_id": f["id"], "pair_id": f.get("pair", f["id"]), "check": "replay",
                              "text_kind": kind, "criteria": [c[0] for c in picks], "source": "replay", "tokens": n_tok,
                              "room": room, "inputs_sha256": b.frozen["inputs_sha256"]}})
        if len(rows) % 25 == 0:
            print(f"  {len(rows)} replay rows", flush=True)

    with open(os.path.join(REPO, args.out), "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    ps = [v["probabilities"]["true"] for r in rows for v in r["gold"].values()]
    print(f"wrote {len(rows)} replay rows from {tried} fragments; base P(yes) mean {sum(ps)/len(ps):.2f}, "
          f"share >0.5: {sum(p > 0.5 for p in ps)/len(ps):.2f}")


if __name__ == "__main__":
    main()
