"""Build and validate the synthetic gold set.

Run:  python laya-finetuning/laya_eval/build_gold.py
Writes laya-finetuning/laya_eval/data/<criterion>.jsonl and prints validation + a real-vs-synthetic snippet length check.

Snippets for Empathy / Ownership / Rapport are produced by the REAL extractors in
src/services/rule_engine.py, so format matches what the pipeline sends to the LLM, and any
item the real gate would have filtered out is rejected here.
"""
import difflib
import glob
import importlib.util
import json
import re
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
QA_ROOT = HERE.parents[1]  # repo root (the QA app); this folder is laya-finetuning/laya_eval

import gold_a, gold_b, gold_c, gold_d  # noqa: E402

spec = importlib.util.spec_from_file_location("rule_engine", QA_ROOT / "src" / "services" / "rule_engine.py")
rule_engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rule_engine)

APOLOGY = ["sorry", "apologize", "understand", "frustrating", "apologies", "let me help"]
errors = []


def err(cid, msg):
    errors.append(f"{cid}: {msg}")


def words(s):
    return len(re.findall(r"\w+", s))


def parse_prefixed(lines):
    out = []
    for ln in lines:
        m = re.match(r"^(C|A):\s*(.*)$", ln)
        out.append(("Customer" if m.group(1) == "C" else "Agent", m.group(2)))
    return out


def build_empathy(cid, payload):
    turns = parse_prefixed(payload)
    if turns[0][0] != "Customer":
        err(cid, "first turn must be the customer")
    for j in range(1, min(4, len(turns))):
        spk, txt = turns[j]
        if spk == "Agent" and any(k in txt.lower() for k in APOLOGY):
            err(cid, f"agent turn {j} contains an apology keyword, real gate would skip it: {txt!r}")
    scores = [-20.0] + [0.0] * (len(turns) - 1)
    snip = rule_engine.extract_empathy_snippets(turns, scores)
    if not snip:
        err(cid, "real extractor produced no snippet")
    if "\n---\n" in snip:
        err(cid, "extractor produced more than one snippet")
    return {"turns": [list(t) for t in turns], "text": snip}


def build_al(cid, payload, k):
    q1, q2 = payload
    ratio = difflib.SequenceMatcher(None, q1.lower(), q2.lower()).ratio()
    if ratio <= 0.60:
        err(cid, f"difflib ratio {ratio:.2f} <= 0.60, real gate would not form this pair: {q1!r} / {q2!r}")
    i1 = 6 + 2 * (k % 5)
    i2 = i1 + 8 + 2 * (k % 7)
    return {"q1": q1, "q2": q2, "difflib_ratio": round(ratio, 3), "text": f"Turn {i1}: {q1}\n... Turn {i2}: {q2}"}


def build_lines_extractor(cid, payload, fn):
    turns = [("Agent", ln) for ln in payload]
    snip = fn(turns)
    got = [ln for ln in snip.split("\n") if ln]
    if len(got) != len(payload):
        err(cid, f"only {len(got)}/{len(payload)} lines hit the real phrase list, so the rest would never reach the LLM")
    return {"lines": payload, "text": snip}


def build_probing(cid, payload):
    problem, qs = payload
    q_txt = "\n".join(f"- {q}" for q in qs)
    if not any("?" in q for q in qs):
        err(cid, "no question mark; real pipeline auto-FAILs without calling the LLM")
    return {"problem": problem, "questions": qs,
            "text": f"CUSTOMER PROBLEM: {problem}\n\nThe agent asked these questions during the call:\n{q_txt}"}


def build_lines(cid, payload):
    return {"lines": payload, "text": "\n".join(payload)}


CRITERIA = [
    ("empathy", gold_a.EMPATHY, lambda cid, p, k: build_empathy(cid, p)),
    ("active_listening", gold_a.ACTIVE_LISTENING, build_al),
    ("ownership", gold_b.OWNERSHIP, lambda cid, p, k: build_lines_extractor(cid, p, rule_engine.extract_ownership_snippets)),
    ("rapport", gold_b.RAPPORT, lambda cid, p, k: build_lines_extractor(cid, p, rule_engine.extract_rapport_snippets)),
    ("probing", gold_c.PROBING, lambda cid, p, k: build_probing(cid, p)),
    ("resolved", gold_c.RESOLVED, lambda cid, p, k: build_lines(cid, p)),
    ("escalation", gold_d.ESCALATION, lambda cid, p, k: build_lines(cid, p)),
    ("hostility", gold_d.HOSTILITY, lambda cid, p, k: build_lines(cid, p)),
]

out_dir = HERE / "data"
out_dir.mkdir(exist_ok=True)
seen_text = {}
summary = []

for name, items, builder in CRITERIA:
    rows = []
    stratum_counter = {}
    for k, (label, hard, payload) in enumerate(items):
        cid = f"{name}-{k:03d}"
        if label not in ("PASS", "FAIL"):
            err(cid, f"bad label {label!r}")
        built = builder(cid, payload, k)
        key = (label, bool(hard))
        n = stratum_counter.get(key, 0)
        stratum_counter[key] = n + 1
        split = "dev" if n % 2 == 0 else "test"
        row = {"id": cid, "criterion": name, "label": label, "hard": bool(hard), "split": split}
        row.update(built)
        if built["text"] in seen_text:
            err(cid, f"duplicate text, same as {seen_text[built['text']]}")
        seen_text[built["text"]] = cid
        rows.append(row)
    with open(out_dir / f"{name}.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    c = lambda **kw: sum(all(r[a] == b for a, b in kw.items()) for r in rows)
    wc = [words(r["text"]) for r in rows]
    summary.append((name, len(rows), c(label="PASS"), c(label="FAIL"), c(hard=True), c(split="dev"), c(split="test"),
                    c(split="test", label="PASS"), c(split="test", label="FAIL"), statistics.mean(wc), max(wc)))

print(f"{'criterion':17s} {'n':>3s} {'PASS':>4s} {'FAIL':>4s} {'hard':>4s} {'dev':>3s} {'test':>4s} {'t.P':>3s} {'t.F':>3s} {'meanW':>6s} {'maxW':>5s}")
for s in summary:
    print(f"{s[0]:17s} {s[1]:3d} {s[2]:4d} {s[3]:4d} {s[4]:4d} {s[5]:3d} {s[6]:4d} {s[7]:3d} {s[8]:3d} {s[9]:6.1f} {s[10]:5d}")
print("total items:", sum(s[1] for s in summary))

# --- real-vs-synthetic snippet length check on the repo's real inputs (list-style transcripts with sentiment) ---
real = {"empathy": [], "ownership": [], "rapport": []}
n_files = 0
for fp in sorted(glob.glob(str(QA_ROOT / "inputs" / "**" / "*.json"), recursive=True)
                 + glob.glob(str(QA_ROOT / "laya-finetuning" / "inputs" / "**" / "*.json"), recursive=True)):
    if "result" in Path(fp).name.lower() or "results" in fp.lower():
        continue
    try:
        d = json.load(open(fp, encoding="utf-8"))
    except Exception:
        continue
    tr = d.get("transcript") if isinstance(d, dict) else None
    if not isinstance(tr, list) or not tr or not isinstance(tr[0], dict) or "speaker" not in tr[0]:
        continue
    if "sentiment_score" not in tr[0]:
        continue
    n_files += 1
    turns = [(t.get("speaker", ""), t.get("text", "")) for t in tr]
    sc = [t.get("sentiment_score", 0.0) for t in tr]
    e = rule_engine.extract_empathy_snippets(turns, sc)
    o = rule_engine.extract_ownership_snippets(turns)
    r = rule_engine.extract_rapport_snippets(turns)
    if e:
        real["empathy"] += [words(s) for s in e.split("\n---\n")]
    if o:
        real["ownership"].append(words(o))
    if r:
        real["rapport"].append(words(r))
print(f"\nReal-pipeline snippets from {n_files} input files with sentiment (word counts):")
for k, v in real.items():
    gold_wc = [words(json.loads(l)["text"]) for l in open(out_dir / f"{k}.jsonl", encoding="utf-8")]
    if v:
        print(f"  {k:10s} real n={len(v):3d} mean={statistics.mean(v):5.1f} median={statistics.median(v):5.1f} max={max(v):3d} | gold mean={statistics.mean(gold_wc):5.1f} max={max(gold_wc):3d}")
    else:
        print(f"  {k:10s} real n=0")

if errors:
    print(f"\nVALIDATION FAILED: {len(errors)} problem(s)")
    for e in errors:
        print("  -", e)
    sys.exit(1)
print("\nValidation OK")
