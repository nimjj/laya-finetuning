"""Mix 2: the stage-3 rows (Claude-written) plus the Antigravity rows (AG-T) into train_all2 / dev_all2, with leakage proof.

    python laya-finetuning/tools/make_mix2.py

Reads  data/rows/train_all.jsonl, dev_all.jsonl, test*.jsonl   (stage 3; unchanged, never rewritten)
       data/rows/agt_train.jsonl, agt_dev.jsonl                (tools/build_ag_rows.py)
Writes data/rows/train_all2.jsonl, dev_all2.jsonl, manifest2.json, and data/frozen/accepted_row_hashes.json.
The test files are NOT mixed: they stay the Claude-written stage-3 tests; the independent checks are AG50 and the sealed AG-B,
run locally after training. Exits 1 on any leakage.
"""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
ROWS = os.path.join(REPO, "data", "rows")


def load(name):
    return [json.loads(l) for l in open(os.path.join(ROWS, name), encoding="utf-8") if l.strip()]


def write(name, rows):
    with open(os.path.join(ROWS, name), "w", encoding="utf-8", newline="\n") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def sha(name):
    return hashlib.sha256(open(os.path.join(ROWS, name), "rb").read()).hexdigest()


def shingles(text, n=5):
    w = text.lower().split()
    return {" ".join(w[i:i + n]) for i in range(max(1, len(w) - n + 1))}


def main():
    old_train, old_dev = load("train_all.jsonl"), load("dev_all.jsonl")
    ag_train, ag_dev = load("agt_train.jsonl"), load("agt_dev.jsonl")
    tests = {n: load(f"{n}.jsonl") for n in ("test", "test_long", "test_calls")}
    train2, dev2 = old_train + ag_train, old_dev + ag_dev
    problems = []

    # ids: an AG call must never appear in a second split; row ids must be unique
    where = {}
    for sname, rows in (("train", train2), ("dev", dev2), *tests.items()):
        for r in rows:
            for key in ("call_id", "pair_id"):
                where.setdefault(r["meta"][key], set()).add(sname)
    bad = [k for k, v in where.items() if len(v) > 1 and not k.startswith("replay")]
    if bad:
        problems.append(f"call/pair ids in more than one split: {bad[:5]} ({len(bad)})")
    ids = [r["meta"]["id"] for r in train2 + dev2]
    if len(ids) != len(set(ids)):
        problems.append("duplicate row ids")
    # identical (check, state) across splits
    states = {n: {(r["meta"]["check"], r["state"]) for r in rows if r["meta"]["check"] != "replay"}
              for n, rows in (("train", train2), ("dev", dev2), *tests.items())}
    for a in ("train", "dev"):
        for t in tests:
            same = states[a] & states[t]
            if same:
                problems.append(f"{len(same)} identical states in both {a} and {t}")
    same = states["train"] & states["dev"]
    if same:
        problems.append(f"{len(same)} identical states in both train and dev")
    # near-duplicates between the NEW rows and everything they must not resemble
    def near(a_rows, b_rows):
        out = []
        sb = [(r, shingles(r["state"])) for r in b_rows if r["meta"]["check"] != "replay"]
        for ra in a_rows:
            sa = shingles(ra["state"])
            for rb, s in sb:
                if ra["meta"]["check"] == rb["meta"]["check"] and sa and s and len(sa & s) / len(sa | s) >= 0.6:
                    out.append((ra["meta"]["id"], rb["meta"]["id"]))
        return out
    nd = {"agt_train~test": near(ag_train, [r for t in tests.values() for r in t]),
          "agt_dev~test": near(ag_dev, [r for t in tests.values() for r in t]),
          "agt_dev~train": near(ag_dev, train2)}
    for k, v in nd.items():
        if v:
            problems.append(f"{len(v)} near-duplicate rows ({k}): {v[:3]}")

    write("train_all2.jsonl", train2)
    write("dev_all2.jsonl", dev2)
    hashes = {r["meta"]["inputs_sha256"] for rows in (train2, dev2, *tests.values()) for r in rows}
    json.dump({"accepted": sorted(hashes),
               "note": "Rows carry the hash of the extractor code that built them. The stage-3 rows carry 66deff95...; the Antigravity rows "
                       "carry the current freeze. Both are accepted by the mix-2 notebook. The stage-3 rows were built with the v1 "
                       "extractors, which flow v2 left unchanged (README); this was not re-verified here."},
              open(os.path.join(REPO, "data", "frozen", "accepted_row_hashes.json"), "w"), indent=1)

    def counts(rows):
        c = {}
        for r in rows:
            lab = r["meta"].get("label", "gold")
            c.setdefault(r["meta"]["check"], {}).setdefault(f"{lab}{'' if r['meta'].get('source') != 'antigravity-agt' else ' (AG)'}", 0)
            c[r["meta"]["check"]][f"{lab}{'' if r['meta'].get('source') != 'antigravity-agt' else ' (AG)'}"] += 1
        return c
    manifest = {"rows": {"train_all2": len(train2), "dev_all2": len(dev2), **{k: len(v) for k, v in tests.items()}},
                "counts_train": counts(train2), "counts_dev": counts(dev2), "inputs_hashes": sorted(h[:12] for h in hashes),
                "sha256": {n: sha(n) for n in ("train_all2.jsonl", "dev_all2.jsonl")}, "problems": problems,
                "authorship": "Stage-3 rows: written and labelled by Claude. AG rows: written and labelled by Antigravity. Nothing is human-labelled."}
    json.dump(manifest, open(os.path.join(ROWS, "manifest2.json"), "w"), indent=2)
    print(json.dumps(manifest["rows"]))
    for c in sorted(manifest["counts_train"]):
        print(f"  train {c:17s} {manifest['counts_train'][c]}")
    print("inputs hashes in the mix:", manifest["inputs_hashes"])
    if problems:
        print("PROBLEMS:", *problems, sep="\n  ")
        sys.exit(1)
    print("mix 2 clean: no shared calls, no identical or near-identical text between train, dev and the tests")


if __name__ == "__main__":
    main()
