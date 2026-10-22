"""Turn Antigravity-written calls plus their markers into training rows, cut by the production extractors (flow v2, with the
Active-listening second source), so the model sees exactly what it sees in production.

    python laya-finetuning/tools/build_ag_rows.py --calls inputs/AG-T --out-prefix laya-finetuning/data/rows/agt
    python laya-finetuning/tools/build_ag_rows.py --calls inputs/AG-T --ids agt_001,agt_002 --out-prefix <scratch>/test   # a trial

Writes <prefix>_train.jsonl, <prefix>_dev.jsonl (split BY CALL, about 1 in 5 calls to dev) and <prefix>_dropped.json, and prints a report.

How a row is labelled (markers come from grader.markers in each key; see Docs/ANTIGRAVITY_V2_COMMON.md):
  rapport            one row per chunk the extractor builds. FAIL: the chunk holds a `rude` line. PASS: chunks holding a `blunt_but_ok`
                     line (the hard negatives, all kept) plus at most one other clean chunk per call.
  empathy            one row per outburst window the extractor builds. Matched to the nearest marker within 2 turns:
                     handled -> PASS (its acknowledgement must lie inside the window), unhandled -> FAIL. Unmatched windows are dropped.
  paraphrasing       the window the extractor builds (none = production fails the item without the model, so no row).
                     Key FAIL -> FAIL. Key PASS -> PASS only when a `restatement` line is inside the window, else dropped.
  active_listening   one row per block the extractor builds. Its later question is a `repeat` -> FAIL, a `harmless_recheck` -> PASS,
                     any other block in a call whose Active listening is PASS -> PASS, otherwise dropped (unlabelled).
  probing            the app's one window per call, labelled with the call's Probing grade (added for ft6).
Ownership, Resolved and the rest are not built here (no turn-level markers, and their windows often miss the evidence); the earlier
rows and the replay rows cover them.

Never point this at AG50 (development set) or AG-B (sealed test): the script refuses.
"""
import argparse
import collections
import hashlib
import json
import os
import re
import subprocess
import sys

os.environ["LAYA_FLOW"] = "v2"            # the windows production uses with a fine-tuned checkpoint
os.environ["LAYA_AL_SOURCE2"] = "1"       # Active listening: customer statement vs later agent question blocks too

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)              # laya-finetuning/
sys.path.insert(0, HERE)
import paths  # noqa: E402

BLOCK_LATER = re.compile(r"^Turn (\d+) Agent later asked:", re.M)


def norm(s):
    return re.sub(r"\s+", " ", s.strip().lower())


def in_text(line, text, n=45):
    """True when the start of an agent/customer line appears in a snippet (extractors may trim long lines)."""
    return norm(line)[:n] in norm(text)


def load_tokenizer(checkpoint):
    """The stock tokenizer when the base weights are on this PC, else the fine-tuned checkpoint's own copy. The fallback is
    verified: it must reproduce the token counts recorded in the existing training rows, exactly."""
    sys.path.insert(0, paths.QA_ROOT)
    from laya.agent import _load_tokenizer
    snap = paths.base_snapshot()
    if snap and os.path.isdir(snap):
        src = snap
    else:
        src = os.path.join(paths.QA_ROOT, checkpoint)
        if not os.path.isdir(src):
            sys.exit(f"STOP: neither the stock weights nor the checkpoint {checkpoint} are available for the tokenizer")
    cfg = json.load(open(os.path.join(src, "rl_agent_config.json"), encoding="utf-8"))
    return _load_tokenizer(os.path.join(src, "tokenizer"), cfg), cfg, src


class AgBuilder:
    def __init__(self, checkpoint):
        sys.path.insert(0, paths.QA_ROOT)
        chk = subprocess.run([sys.executable, os.path.join(HERE, "export_checks.py"), "--check"], capture_output=True, text=True)
        print(chk.stdout.strip())
        if chk.returncode != 0:
            sys.exit("STOP: the application no longer matches data/frozen/checks_frozen.json. Re-freeze deliberately, then rebuild.")
        self.frozen = json.load(open(os.path.join(REPO, "data", "frozen", "checks_frozen.json"), encoding="utf-8"))
        self.checks = self.frozen["frozen"]["checks"]
        import laya.common as lc
        import laya.train as lt
        from src.services import laya_windows as W
        from src.services.laya_inputs import build_laya_inputs, parse_transcript
        self.lc, self.lt, self.W, self.build_laya_inputs, self.parse_transcript = lc, lt, W, build_laya_inputs, parse_transcript
        self.tok, cfg, src = load_tokenizer(checkpoint)
        self.max_len, self.head_max_len = cfg["max_len"], cfg["head_max_len"]
        print(f"tokenizer from {src}")
        self.verify_tokenizer()

    def verify_tokenizer(self, n=400):
        path = os.path.join(REPO, "data", "rows", "train_all.jsonl")
        rows = [json.loads(l) for l in open(path, encoding="utf-8")][:n]
        bad = [r["meta"]["id"] for r in rows if len(self.lt.encode_state(self.tok, r["state"], 10 ** 6)) != r["meta"]["tokens"]]
        if bad:
            sys.exit(f"STOP: this tokenizer disagrees with the recorded token counts on {len(bad)}/{len(rows)} existing rows, e.g. {bad[:3]}")
        print(f"tokenizer check: identical token counts on {len(rows)} existing training rows")

    def fits(self, check, snippet):
        q = self.checks[check]["question"]
        room = self.lc.state_room(self.tok, self.lt.to_internal(check, q), self.max_len, self.head_max_len)
        n_tok = len(self.lt.encode_state(self.tok, snippet, 10 ** 6))
        return n_tok <= room, n_tok, room

    def row(self, call_id, check, label, snippet, hard, turn, dropped):
        ok, n_tok, room = self.fits(check, snippet)
        if not ok:
            dropped.append({"call": call_id, "check": check, "reason": f"{n_tok} tokens > window room {room}"})
            return None
        q = self.checks[check]["question"]
        return {"state": snippet, "questions": {check: q}, "expected": {check: label == self.checks[check]["yes_means"]},
                "meta": {"id": f"{call_id}_{check}_{hard}_{turn}", "call_id": call_id, "pair_id": call_id, "check": check, "label": label,
                         "industry": None, "persona": None, "hard": hard, "rough": None, "source": "antigravity-agt", "tokens": n_tok,
                         "room": room, "inputs_sha256": self.frozen["inputs_sha256"]}}


def rows_for_call(b, cid, payload, key, dropped):
    T = payload["transcript"]
    turns = [(t["speaker"], t["text"]) for t in T]
    sent = [t.get("sentiment_score", 0.0) for t in T]
    mk = key["grader"]["markers"]
    rating = {s["name"]: s["rating"] for s in key["result"]["scorecard"]}
    inp = b.build_laya_inputs(T, payload.get("customer_name"))
    out = []

    def drop(check, reason, turn=None, kind=None):
        dropped.append({"call": cid, "check": check, "reason": reason, "turn": turn, "kind": kind})

    # ---- rapport
    rude = [m["agent_turn"] for m in mk["rapport"] if m["kind"] == "rude"]
    blunt = [m["agent_turn"] for m in mk["rapport"] if m["kind"] == "blunt_but_ok"]
    has = lambda chunk, idxs: any(in_text(turns[i][1], chunk) for i in idxs)          # noqa: E731
    fail_chunks = [c for c in inp.rapport if has(c, rude)]
    if rude and not fail_chunks:
        drop("rapport", "a rude line is in no chunk")
    for k, c in enumerate(fail_chunks):
        out.append(b.row(cid, "rapport", "FAIL", c, "rude", k, dropped))
    clean = [c for c in inp.rapport if not has(c, rude)]
    hard_neg = [c for c in clean if has(c, blunt)][:3]
    other = sorted((c for c in clean if c not in hard_neg), key=lambda c: hashlib.md5((cid + c[:40]).encode()).hexdigest())[:1]
    for k, c in enumerate(hard_neg):
        out.append(b.row(cid, "rapport", "PASS", c, "blunt_but_ok", k, dropped))
    for k, c in enumerate(other):
        out.append(b.row(cid, "rapport", "PASS", c, "clean_chunk", k, dropped))

    # ---- empathy
    W = b.W
    starts = W.outburst_starts(turns, sent, 4)
    if len(starts) > 4:
        starts = starts[:3] + starts[-1:]
    windows = [W._span(turns, i, 4) for i in starts]
    if windows != inp.empathy:
        drop("empathy", "could not reproduce the windows the extractor builds")
    else:
        for s, w in zip(starts, windows):
            near = [m for m in mk["empathy"] if abs(m["customer_turn"] - s) <= 2]
            if not near:
                drop("empathy", f"window at turn {s} matches no marker", s, "unmarked_outburst")
                continue
            m = min(near, key=lambda m: abs(m["customer_turn"] - s))
            if m["kind"] == "no_outburst":
                out.append(b.row(cid, "empathy", "PASS", w, "no_outburst_trigger", s, dropped))
            elif m["kind"] == "handled":
                if not (s <= m["agent_turn"] <= s + 4):
                    drop("empathy", f"the acknowledgement (turn {m['agent_turn']}) is outside the window starting at {s}")
                    continue
                late = m["agent_turn"] - m["customer_turn"] >= 3
                hard = "handled_with_refusal" if m.get("with_refusal") else "handled_late" if late else "handled"
                out.append(b.row(cid, "empathy", "PASS", w, hard, s, dropped))
            else:
                out.append(b.row(cid, "empathy", "FAIL", w, "unhandled", s, dropped))

    # ---- paraphrasing
    if inp.paraphrasing is None:
        drop("paraphrasing", "no restatement cue in the first 300 s: production fails the item without the model")
    elif rating["Paraphrasing"] == "FAIL":
        out.append(b.row(cid, "paraphrasing", "FAIL", inp.paraphrasing, "no_restatement", 0, dropped))
    else:
        rs = [m["agent_turn"] for m in mk["paraphrasing"] if m["kind"] == "restatement"]
        if any(in_text(turns[i][1], inp.paraphrasing) for i in rs):
            out.append(b.row(cid, "paraphrasing", "PASS", inp.paraphrasing, "restatement", 0, dropped))
        else:
            drop("paraphrasing", "the restatement is outside the window production shows")

    # ---- active listening
    rep = {m["agent_turn"] for m in mk["active_listening"] if m["kind"] == "repeat"}
    harm = {m["agent_turn"] for m in mk["active_listening"] if m["kind"] == "harmless_recheck"}
    seen = set()
    for blk in (inp.active_listening.split("\n\n") if inp.active_listening else []):
        if blk in seen:
            continue
        seen.add(blk)
        mt = BLOCK_LATER.search(blk)
        aj = int(mt.group(1)) if mt else None
        if aj in rep:
            out.append(b.row(cid, "active_listening", "FAIL", blk, "repeat", aj, dropped))
        elif aj in harm:
            out.append(b.row(cid, "active_listening", "PASS", blk, "harmless_recheck", aj, dropped))
        elif rating["Active listening"] == "PASS":
            out.append(b.row(cid, "active_listening", "PASS", blk, "good_call_block", aj, dropped))
        else:
            drop("active_listening", f"block at turn {aj} in a faulty call matches no marker", aj, "unmarked_al_candidate")

    # ---- probing: the app's single window (customer problem + every agent question) stands for the whole call, so the call's
    # grade is the label. Added after ft5, which had no Probing rows from AG-T and drifted on Probing.
    if inp.probing is None:
        drop("probing", "the agent asked no questions: production fails the item without the model")
    else:
        out.append(b.row(cid, "probing", rating["Probing"], inp.probing, "call_grade", 0, dropped))
    out = [r for r in out if r]
    seen = collections.Counter()                 # two blocks can end at the same later question: keep every row id unique
    for r in out:
        base = r["meta"]["id"]
        seen[base] += 1
        if seen[base] > 1:
            r["meta"]["id"] = f"{base}_{seen[base]}"
    return out


def is_dev(cid):
    return int(hashlib.md5(cid.encode()).hexdigest()[:8], 16) % 5 == 0


HARD_KINDS = {"harmless_recheck", "blunt_but_ok", "handled_late", "handled_with_refusal", "no_outburst_trigger", "restatement", "repeat",
              "rude", "unhandled", "no_restatement"}


def cap_pass_ratio(rows, ratio):
    """Keep every FAIL row of a check and at most ratio x as many PASS rows, hard negatives first, so one label cannot dominate."""
    keep = []
    for chk in sorted({r["meta"]["check"] for r in rows}):
        fails = [r for r in rows if r["meta"]["check"] == chk and r["meta"]["label"] == "FAIL"]
        passes = sorted((r for r in rows if r["meta"]["check"] == chk and r["meta"]["label"] == "PASS"),
                        key=lambda r: (r["meta"]["hard"] not in HARD_KINDS, hashlib.md5(r["meta"]["id"].encode()).hexdigest()))
        keep += fails + passes[:max(1, int(ratio * len(fails) + 0.5))]
    order = {id(r): i for i, r in enumerate(rows)}
    return sorted(keep, key=lambda r: order[id(r)])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--calls", required=True, help="folder with agt_NNN.json and expected/expected_agt_NNN.json")
    ap.add_argument("--out-prefix", required=True)
    ap.add_argument("--ids", default="", help="comma-separated call ids (default: every call in the folder)")
    ap.add_argument("--checkpoint", default="laya-finetuning/checkpoints/final-softce-3", help="tokenizer fallback")
    ap.add_argument("--max-pass-ratio", type=float, default=2.0, help="train split only: at most this many PASS rows per FAIL row for each check (0 = no cap)")
    args = ap.parse_args()
    calls_dir = os.path.abspath(os.path.join(paths.QA_ROOT, args.calls)) if not os.path.isabs(args.calls) else args.calls
    if re.search(r"AG50|AG-B|agb_", calls_dir, re.I):
        sys.exit("STOP: AG50 is a development set and AG-B is the sealed test set. Never build training rows from them.")
    ids = [c for c in args.ids.split(",") if c] or sorted(f[:-5] for f in os.listdir(calls_dir) if re.fullmatch(r"agt_\d+\.json", f))
    b = AgBuilder(args.checkpoint)
    rows, dropped, skipped = [], [], []
    for cid in ids:
        try:
            payload = json.load(open(os.path.join(calls_dir, f"{cid}.json"), encoding="utf-8"))
            key = json.load(open(os.path.join(calls_dir, "expected", f"expected_{cid}.json"), encoding="utf-8"))
            rows += rows_for_call(b, cid, payload, key, dropped)
        except (OSError, json.JSONDecodeError, KeyError) as e:
            skipped.append(f"{cid}: {type(e).__name__} {e}")
    train = [r for r in rows if not is_dev(r["meta"]["call_id"])]
    dev = [r for r in rows if is_dev(r["meta"]["call_id"])]
    n_before = len(train)
    if args.max_pass_ratio:
        train = cap_pass_ratio(train, args.max_pass_ratio)
    unmarked = collections.defaultdict(list)
    for d in dropped:
        if d.get("kind"):
            unmarked[d["call"]].append(f"{'customer' if d['kind'] == 'unmarked_outburst' else 'agent'} turn {d['turn']} "
                                       f"({'upset-looking moment' if d['kind'] == 'unmarked_outburst' else 'possible re-ask'})")
    with open(f"{args.out_prefix}_unmarked.txt", "w", encoding="utf-8", newline="\n") as fh:
        for cid in sorted(unmarked):
            fh.write(f"{cid}: " + "; ".join(unmarked[cid]) + "\n")
    for name, rs in (("train", train), ("dev", dev)):
        with open(f"{args.out_prefix}_{name}.jsonl", "w", encoding="utf-8", newline="\n") as fh:
            for r in rs:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    json.dump({"dropped": dropped, "skipped": skipped}, open(f"{args.out_prefix}_dropped.json", "w", encoding="utf-8"), indent=1)

    print(f"\n{len(ids)} calls -> {len(rows)} rows before the PASS cap; train {len(train)} (was {n_before}), dev {len(dev)}; "
          f"dropped {len(dropped)}, skipped {len(skipped)}; {sum(len(v) for v in unmarked.values())} unmarked moments in {len(unmarked)} calls "
          f"(listed in {os.path.basename(args.out_prefix)}_unmarked.txt)")
    rows = train + dev
    cnt = collections.Counter((r["meta"]["check"], r["meta"]["label"], r["meta"]["hard"]) for r in rows)
    for k in sorted(cnt):
        print(f"  {k[0]:17s} {k[1]:5s} {k[2]:22s} {cnt[k]:4d}")
    ln = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in rows:
        ln[r["meta"]["check"]][r["meta"]["label"]].append(r["meta"]["tokens"])
    print("mean tokens per label (PASS / FAIL):")
    for c in sorted(ln):
        mp, mf = (sum(ln[c][k]) / len(ln[c][k]) if ln[c][k] else 0 for k in ("PASS", "FAIL"))
        flag = "   <-- length gap over 15%: a shortcut the model could learn" if mp and mf and abs(mp - mf) / max(mp, mf) > 0.15 else ""
        print(f"  {c:17s} {mp:6.1f} / {mf:6.1f}{flag}")
    why = collections.Counter((d["check"], d["reason"].split(" at turn")[0].split(" (turn")[0][:70]) for d in dropped)
    print("dropped, by reason:")
    for (c, r), n in why.most_common(12):
        print(f"  {n:3d}  {c:17s} {r}")
    for s in skipped:
        print("  SKIPPED", s)


if __name__ == "__main__":
    main()
