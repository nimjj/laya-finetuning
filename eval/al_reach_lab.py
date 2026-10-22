"""Active-listening reach lab: does the real fault reach the model? No model is loaded.

For each call it builds the Active-listening candidates two ways and reports how often the keyed fault (the agent question
the key's evidence names) is inside them:
  current  extract_active_listening_snippets (rule_engine): agent question vs an earlier agent question
  second   W.active_listening_pairs_from_customer (laya_windows): agent question vs an earlier CUSTOMER statement
  union    either source

Run (from the repo root):
    python laya-finetuning/eval/al_reach_lab.py laya-finetuning/inputs/AG50            # reach on faults + snippets on good calls (AG50 key)
    python laya-finetuning/eval/al_reach_lab.py "inputs/Bulk tests"    # snippet counts only (bulk keys are in the file names)
    python laya-finetuning/eval/al_reach_lab.py "inputs/Main tests"

Keys are AI-written (Antigravity for AG50), not human-reviewed. AG50 is a development set.
"""
import argparse
import glob
import json
import os
import re
import sys

import _roots  # noqa: E402  (finds the QA app root; see _roots.py)
ROOT = _roots.QA_ROOT
sys.path.insert(0, ROOT)

TS = re.compile(r"\[(\d{1,2}):(\d{2})\]")
BLOCK_LATER = re.compile(r"^Turn (\d+) Agent later asked:", re.M)


def evidence_agent_turns(turns, times, evidence):
    """Indices of agent turns containing a question whose start time matches a timestamp quoted in the evidence."""
    stamps = [int(m) * 60 + int(s) for m, s in TS.findall(evidence)]
    out = set()
    for i, ((spk, txt), (start, _)) in enumerate(zip(turns, times)):
        if spk.lower() == "agent" and "?" in txt and any(abs(start - t) <= 3 for t in stamps):
            out.add(i)
    return out


def candidates(payload):
    from src.services import laya_windows as W
    from src.services.laya_inputs import parse_transcript
    from src.services.rule_engine import AL_MAX_PAIRS, extract_active_listening_snippets
    turns, times = parse_transcript(payload["transcript"], payload.get("customer_name"))[:2]
    snippet = extract_active_listening_snippets(turns)
    cur = {int(i) for i in BLOCK_LATER.findall(snippet)}
    sec = {j for _, _, j, _ in W.active_listening_pairs_from_customer(turns)}
    # what the model would really be sent with LAYA_AL_SOURCE2 on: current blocks first, then the new ones, at most AL_MAX_PAIRS
    combined_text = W.active_listening_with_customer_pairs(turns, snippet, AL_MAX_PAIRS)
    both = {int(i) for i in BLOCK_LATER.findall(combined_text)}
    n_blocks = len([b for b in combined_text.split("\n\n") if b])
    return turns, times, cur, sec, both, n_blocks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("suite", help="folder with call JSONs (AG50 also needs expected/expected_<call>.json)")
    ap.add_argument("--show-misses", action="store_true", help="print the evidence of faults no source reaches")
    args = ap.parse_args()
    suite = args.suite if os.path.isabs(args.suite) else os.path.join(ROOT, args.suite)

    faults = {"current": 0, "second": 0, "union": 0, "combined": 0, "n": 0}
    good = {"n": 0, "current": 0, "second": 0, "union": 0, "combined": 0}
    counts, blocks_sent = [], []
    for path in sorted(glob.glob(os.path.join(suite, "*.json"))):
        cid = os.path.basename(path)[:-5]
        with open(path, encoding="utf-8") as f:
            payload = json.load(f)
        if "transcript" not in payload:
            continue
        turns, times, cur, sec, both, n_blocks = candidates(payload)
        blocks_sent.append(n_blocks)
        key_path = os.path.join(suite, "expected", f"expected_{cid}.json")
        if os.path.exists(key_path):
            with open(key_path, encoding="utf-8") as f:
                item = next(i for i in json.load(f)["grader"]["items"] if i["name"] == "Active listening")
            if item["rating"] == "FAIL":
                ev = evidence_agent_turns(turns, times, item["evidence"])
                faults["n"] += 1
                hit_cur, hit_sec = bool(ev & cur), bool(ev & sec)
                faults["current"] += hit_cur
                faults["second"] += hit_sec
                faults["union"] += hit_cur or hit_sec
                hit_both = bool(ev & both)
                faults["combined"] += hit_both
                print(f"FAULT {cid}: evidence turns {sorted(ev) or 'NONE MATCHED'}  current={hit_cur} second={hit_sec} combined={hit_both}")
                if args.show_misses and not (hit_cur or hit_sec):
                    print("   ", item["evidence"][:300])
            else:
                good["n"] += 1
                good["current"] += bool(cur)
                good["second"] += bool(sec)
                good["union"] += bool(cur or sec)
                good["combined"] += bool(both - cur)      # a new block beyond what the current extractor already sends
        counts.append((cid, len(cur), len(sec)))

    if faults["n"]:
        print(f"\nFaults reaching the model (of {faults['n']}): current {faults['current']}, "
              f"second source {faults['second']}, either {faults['union']}, "
              f"REAL combined snippet (capped) {faults['combined']}")
        print(f"Good calls that produce at least one snippet (of {good['n']}): current {good['current']}, "
              f"second source {good['second']}, either {good['union']}, new blocks in combined {good['combined']}")
    print(f"Model calls per call with the switch on (one per block): mean {sum(blocks_sent) / max(len(blocks_sent), 1):.2f}, "
          f"max {max(blocks_sent, default=0)}")
    print(f"\nSnippet pairs per call ({len(counts)} calls): current mean {sum(c for _, c, _ in counts) / max(len(counts), 1):.2f}, "
          f"second-source mean {sum(s for _, _, s in counts) / max(len(counts), 1):.2f}")
    if not faults["n"]:
        for cid, c, s in counts:
            print(f"  {cid}: current {c}, second {s}")


if __name__ == "__main__":
    main()
