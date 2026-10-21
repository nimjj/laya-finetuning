# CELL 4: unpack the embedded data and the frozen production questions, and check their hashes.
# EXPECT: "data sha OK" for train_all/dev_all/test/test_long/test_calls, "frozen checks sha OK", row counts (see the table),
# and a table of rows per check. Every row must carry the same inputs hash as the frozen questions.
import base64
import gzip

FROZEN = json.loads(r"""{{FROZEN_JSON}}""")
DATA_B64 = {{DATA_B64}}
DATA_SHA256 = {{DATA_SHA256}}


def canonical_sha(obj):
    text = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


assert canonical_sha(FROZEN["frozen"]) == FROZEN["sha256"], "frozen checks were altered"
CHECKS = FROZEN["frozen"]["checks"]
print("frozen checks sha OK:", FROZEN["sha256"][:12] + "...", "|", len(CHECKS), "questions")

DATA_DIR = f"{WORK}/data"
os.makedirs(DATA_DIR, exist_ok=True)
SPLIT = {}
for name, b64 in DATA_B64.items():
    raw = gzip.decompress(base64.b64decode(b64))
    assert hashlib.sha256(raw).hexdigest() == DATA_SHA256[name], f"{name}: embedded data was altered"
    open(f"{DATA_DIR}/{name}.jsonl", "wb").write(raw)
    SPLIT[name] = [json.loads(l) for l in raw.decode("utf-8").splitlines() if l.strip()]
    print(f"data sha OK: {name:<10} {len(SPLIT[name])} rows")
ACCEPTED = set({{ACCEPTED_HASHES}}) | {FROZEN["inputs_sha256"]}     # rows record the extractor hash that built them
for s in SPLIT.values():
    assert all(r["meta"]["inputs_sha256"] in ACCEPTED for r in s), "rows were built from inputs that are not in the accepted list"
print("row input hashes (accepted):", sorted({r["meta"]["inputs_sha256"][:12] for s in SPLIT.values() for r in s}))

import collections
tbl = collections.defaultdict(lambda: collections.Counter())
for name, rows in SPLIT.items():
    for r in rows:
        tbl[r["meta"]["check"]][name] += 1
print(f"{'check':<18}" + "".join(f"{n:>12}" for n in SPLIT))
for c, cnt in tbl.items():
    print(f"{c:<18}" + "".join(f"{cnt[n]:>12}" for n in SPLIT))
