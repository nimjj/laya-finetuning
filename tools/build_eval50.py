"""Build the 50-call evaluation set: call payloads + Claude's expected ("ideal") scorecards.

Source: data/eval50/calls_*.txt, written and graded by Claude BEFORE any model was run on them.

    @@call id=eval_01 name=Renee
    @labels B=P H=P V=P PE=P E=P R=P PA=P AL=P O=P PR=P CR=P      (P = PASS, F = FAIL; every item required)
    @notes E: agent ignored ...; CR: call ends without a check      (optional, one reason per FAIL, for the human reviewer)
    @autofail profanity                                              (optional: agent profanity/discourtesy -> score 0)
    A: Thank you for calling S-Net ...                               (agent turn, default sentiment +8)
    C(-22): ...                                                      (customer turn with sentiment; default -5)
    @gap 45                                                          (seconds of silence before the next turn)

Timing: each turn lasts about words / 2.6 seconds (2 s minimum) and is followed by a 1-3 s pause unless @gap says
otherwise. The app ends every turn at start + 10 s when it measures dead air, so turns are kept under ~70 words.

Writes qa-analysis/laya-finetuning/inputs/Eval50/eval_NN.json, .../expected/expected_eval_NN.json and data/eval50/manifest.json (sha256 of
every file, so the key can be shown to be unchanged after the models are run). Also checks the rule-based items
(branding, dead air, verification, name) and the auto-fail words with the app's own rule code and prints any place
where Claude's label and the rule disagree, so writing slips are caught.

    python tools/build_eval50.py          (qa-analysis venv)
"""
import glob
import hashlib
import json
import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import paths  # noqa: E402
QA = paths.QA_ROOT
OUT = os.path.join(paths.INPUTS, "Eval50")
sys.path.insert(0, QA)

ITEMS = [  # code, name, category  (order of the app's scorecard)
    ("B", "Branding and Survey Check", "Soft Skills"),
    ("H", "Hold time and Dead Air", "Soft Skills"),
    ("V", "Verified customer", "Technical Knowledge"),
    ("PE", "Personalized the call/ticket appropriately", "Soft Skills"),
    ("E", "Empathy & Acknowledgment Statement", "Soft Skills"),
    ("PA", "Paraphrasing", "Technical Knowledge"),
    ("AL", "Active listening", "Technical Knowledge"),
    ("O", "Took ownership of the problem", "Technical Knowledge"),
    ("R", "Build rapport and observed professionalism", "Soft Skills"),
    ("PR", "Probing", "Technical Knowledge"),
    ("CR", "Confirmed the issue is resolved", "Technical Knowledge"),
]
FAIL_COACHING = {
    "B": "Agent missed the required opening and/or closing branding script.",
    "H": "Agent left the customer in unannounced silence (>30s) more than once.",
    "V": "Agent failed to ask for a PIN, address, or security question within the first 4 minutes of the call.",
    "PE": "Agent did not address the customer by name.",
    "E": "Failed to show empathy to customer's frustration.",
    "PA": "Failed to paraphrase core issue.",
    "AL": "Repeated questions unnecessarily.",
    "O": "Agent deflected responsibility or blamed another team instead of owning the issue.",
    "R": "Agent used rude or condescending language.",
    "PR": "Agent did not ask diagnostic questions to investigate the problem.",
    "CR": "Before closing, ask the customer to confirm the issue is fixed and state clearly that it is resolved.",
}
LINE_RE = re.compile(r"^(A|C)(?:\(([+-]?\d+(?:\.\d+)?)\))?:\s*(.*)$")


def mmss(s):
    return f"[{s // 60:02d}:{s % 60:02d}]"


def parse(path):
    calls, cur = [], None
    for n, raw in enumerate(open(path, encoding="utf-8"), 1):
        line = raw.rstrip("\n").strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("@@call"):
            attrs = dict(re.findall(r"(\w+)=(\S+)", line))
            cur = {"id": attrs["id"], "name": attrs.get("name", ""), "labels": {}, "notes": "", "autofail": None,
                   "turns": [], "src": f"{os.path.basename(path)}:{n}", "pending_gap": None}
            calls.append(cur)
        elif line.startswith("@labels"):
            cur["labels"] = dict(kv.split("=") for kv in line.split()[1:])
        elif line.startswith("@notes"):
            cur["notes"] = line[len("@notes"):].strip()
        elif line.startswith("@autofail"):
            cur["autofail"] = line[len("@autofail"):].strip() or "profanity"
        elif line.startswith("@gap"):
            cur["pending_gap"] = int(line.split()[1])
        else:
            m = LINE_RE.match(line)
            if not m:
                raise ValueError(f"{path}:{n}: cannot read: {line[:70]}")
            spk, sent, text = m.groups()
            cur["turns"].append({"spk": "Agent" if spk == "A" else "Customer", "text": text,
                                 "sent": float(sent) if sent else (8.0 if spk == "A" else -5.0),
                                 "gap": cur["pending_gap"]})
            cur["pending_gap"] = None
    for c in calls:
        missing = [code for code, _, _ in ITEMS if code not in c["labels"]]
        if missing:
            raise ValueError(f"{c['src']}: labels missing {missing}")
    return calls


def payload(call):
    rng = random.Random(int(hashlib.md5(call["id"].encode()).hexdigest()[:8], 16))
    t, out = 0, []
    for i, turn in enumerate(call["turns"]):
        if i:
            t += turn["gap"] if turn["gap"] is not None else rng.choice([1, 1, 2, 2, 3])
        dur = max(2, round(len(turn["text"].split()) / 2.6))
        out.append({"speaker": turn["spk"], "start_time": mmss(t), "end_time": mmss(t + dur), "start_time_sec": t,
                    "text": turn["text"], "sentiment_score": turn["sent"]})
        t += dur
    return {"tenant_id": "tenant-abc", "customer_name": call["name"], "transcript": out}


def main():
    from src.services.dynamic_evaluator import calculate_category_scores, check_auto_fail
    from src.services.laya_inputs import build_laya_inputs
    from src.services.rule_engine import (evaluate_branding, evaluate_hold_and_dead_air, evaluate_personalized_call,
                                          evaluate_verified_customer)
    crit = json.load(open(os.path.join(QA, "resources", "criteria_config.json"), encoding="utf-8"))["tenant-abc"]
    deductions = {li["name"]: li["deduction_value"] for cat in crit["categories"] for li in cat["line_items"]}

    calls = [c for p in sorted(glob.glob(os.path.join(REPO, "data", "eval50", "calls_*.txt"))) for c in parse(p)]
    ids = [c["id"] for c in calls]
    assert len(ids) == len(set(ids)), "duplicate ids"
    os.makedirs(os.path.join(OUT, "expected"), exist_ok=True)
    manifest, problems, fails = {}, [], {code: 0 for code, _, _ in ITEMS}
    for call in calls:
        pl = payload(call)
        long_turns = [x["text"][:40] for x in pl["transcript"] if len(x["text"].split()) > 70]
        if long_turns:
            problems.append(f"{call['id']}: turn over 70 words (app would count it as dead air): {long_turns}")
        ratings = []
        for code, name, cat in ITEMS:
            rating = "PASS" if call["labels"][code] == "P" else "FAIL"
            fails[code] += rating == "FAIL"
            ratings.append({"category": cat, "name": name, "rating": rating, "deduction_value": deductions[name]})
        af = bool(call["autofail"])
        _, score = calculate_category_scores(ratings, crit["category_weights"], af, {"Soft Skills", "Technical Knowledge"})
        scorecard = [{"category": r["category"], "name": r["name"], "rating": r["rating"],
                      "coaching": "" if r["rating"] == "PASS" else FAIL_COACHING[code]}
                     for r, (code, _, _) in zip(ratings, ITEMS)]
        expected = {"call_id": call["id"], "tenant_id": "tenant-abc", "status": "completed",
                    "result": {"final_score": score, "is_auto_fail": af,
                               "auto_fail_reason": f"Agent {call['autofail']}" if af else None, "scorecard": scorecard},
                    "grader": {"graded_by": "Claude (written and graded before any model run; not human-reviewed)",
                               "graded_on": "2026-10-17", "notes": call["notes"]}}
        # rule cross-check with the app's own code
        inp = build_laya_inputs(pl["transcript"], call["name"])
        rule = {"B": evaluate_branding(inp.turns)["rating"], "H": evaluate_hold_and_dead_air(inp.turns, inp.times)["rating"],
                "V": evaluate_verified_customer(inp.turns, inp.times)["rating"],
                "PE": evaluate_personalized_call(inp.turns, call["name"])["rating"]}
        for code, got in rule.items():
            if got[0] != call["labels"][code]:
                problems.append(f"{call['id']}: {code} labelled {call['labels'][code]} but the app's rule says {got}")
        app_af, why = check_auto_fail(inp.agent_text, [], [], [])
        if app_af != af:
            problems.append(f"{call['id']}: autofail labelled {af} but the app's word list says {app_af} ({why})")
        for name, obj in ((f"{call['id']}.json", pl), (os.path.join("expected", f"expected_{call['id']}.json"), expected)):
            path = os.path.join(OUT, name)
            text = json.dumps(obj, indent=2, ensure_ascii=False) + "\n"
            open(path, "w", encoding="utf-8", newline="\n").write(text)
            manifest[name.replace(os.sep, "/")] = hashlib.sha256(text.encode("utf-8")).hexdigest()
        mins = pl["transcript"][-1]["start_time_sec"] // 60
        print(f"{call['id']}  {len(pl['transcript']):3d} turns  {mins:2d} min  expected {score:5.1f}{'  AUTO-FAIL' if af else ''}")
    json.dump({"created": "2026-10-17", "calls": len(calls), "sha256": manifest},
              open(os.path.join(REPO, "data", "eval50", "manifest.json"), "w", encoding="utf-8"), indent=1)
    print(f"\n{len(calls)} calls. FAIL count per item:", fails)
    print("\n".join(problems) if problems else "rule cross-check: no disagreements")


if __name__ == "__main__":
    main()
