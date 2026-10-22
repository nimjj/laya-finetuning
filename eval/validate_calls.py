"""Validate a set of written test or training calls and their answer keys. Prints counts and error messages, never dialogue.

    python laya-finetuning/eval/validate_calls.py --suite agt                 # laya-finetuning/inputs/AG-T  (100 training calls, with markers)
    python laya-finetuning/eval/validate_calls.py --suite agb                 # laya-finetuning/inputs/AG-B  (50 sealed test calls)
    python laya-finetuning/eval/validate_calls.py --suite ag50                # laya-finetuning/inputs/AG50  (the first set; checks this script against it)
    python laya-finetuning/eval/validate_calls.py --suite agt --subset agt_001,agt_002    # a batch while you are still writing

Run it from the repo root after every batch and fix every error before writing more. WARN lines do not fail the run.
Exit code 0 = no errors. The key format is described in Docs/CODEBASE_GUIDE.md (section 5); the original brief and format document are in git history.

The four rule-based items are recomputed with the application's own functions (src/services/rule_engine.py), so the key
must match the code exactly. Judged items are your reading of the call; the markers must agree with your ratings.
"""
import argparse
import glob
import json
import os
import re
import sys
from collections import Counter

import _roots  # noqa: E402  (finds the QA app root; see _roots.py)
ROOT = _roots.QA_ROOT
sys.path.insert(0, ROOT)
from src.services.rule_engine import (  # noqa: E402  the application's own rule functions
    _is_managed_hold, evaluate_branding, evaluate_hold_and_dead_air, evaluate_personalized_call, evaluate_verified_customer,
)

SPEC = [  # (category, name, deduction) in the order the scorecard must have
    ("Soft Skills", "Branding and Survey Check", 15),
    ("Soft Skills", "Hold time and Dead Air", 15),
    ("Technical Knowledge", "Verified customer", 25),
    ("Soft Skills", "Personalized the call/ticket appropriately", 15),
    ("Soft Skills", "Empathy & Acknowledgment Statement", 35),
    ("Technical Knowledge", "Paraphrasing", 15),
    ("Technical Knowledge", "Active listening", 10),
    ("Technical Knowledge", "Took ownership of the problem", 25),
    ("Soft Skills", "Build rapport and observed professionalism", 20),
    ("Technical Knowledge", "Probing", 25),
    ("Technical Knowledge", "Confirmed the issue is resolved", 15),
]
NAMES = [n for _, n, _ in SPEC]
AUTO_FAIL_STRINGS = ["fuck", "shut up", "idiot", "get lost", "stupid", "hang up"]
# Stock clauses a generator once appended to reach a word count (AG-T, Oct 2026). Length must come from real support work.
FILLER_PHRASES = [
    "to ensure your S-Net service operates reliably without unexpected dropped packets or connection faults",
    "in accordance with our standard telecommunications network diagnostic procedures",
    "so that your account records and provisioning parameters remain completely up to date",
    "across all your connected household devices including laptops, mobile phones, and streaming hardware",
    "to maintain optimal throughput and low latency across the regional distribution network",
    "because having a reliable home broadband connection is absolutely essential for our daily household work",
    "since we depend heavily on this service for remote working and family communications every day",
    "so I really appreciate you taking the time to look into these technical details with me today",
]
TIME_RE = re.compile(r"^\[(\d{2}):(\d{2})\]$")

AG50_MIN_FAIL = {"Branding and Survey Check": 8, "Hold time and Dead Air": 8, "Verified customer": 8,
                 "Personalized the call/ticket appropriately": 8, "Empathy & Acknowledgment Statement": 12,
                 "Paraphrasing": 12, "Active listening": 12, "Took ownership of the problem": 12,
                 "Build rapport and observed professionalism": 10, "Probing": 10, "Confirmed the issue is resolved": 12}
AGT_MIN_FAIL = {"Branding and Survey Check": 10, "Hold time and Dead Air": 10, "Verified customer": 10,
                "Personalized the call/ticket appropriately": 10, "Empathy & Acknowledgment Statement": 30,
                "Paraphrasing": 35, "Active listening": 30, "Took ownership of the problem": 15,
                "Build rapport and observed professionalism": 30, "Probing": 15, "Confirmed the issue is resolved": 15}

SUITES = {
    "ag50": dict(dir="laya-finetuning/inputs/AG50", prefix="ag_", n=50, width=2, groups={"excellent": 8, "1-2": 15, "3-4": 12, "5+": 11, "auto_fail": 4},
                 group_tol=0, min_fail=AG50_MIN_FAIL, min_pass=25, borderline_max=5, names_min=50, markers="optional",
                 agent_sentiment=True, hard_ratio=True),
    "agb": dict(dir="laya-finetuning/inputs/AG-B", prefix="agb_", n=50, width=2, groups={"excellent": 8, "1-2": 15, "3-4": 12, "5+": 11, "auto_fail": 4},
                group_tol=0, min_fail=AG50_MIN_FAIL, min_pass=25, borderline_max=5, names_min=50, markers="required",
                agent_sentiment=False, hard_ratio=True),
    "agt": dict(dir="laya-finetuning/inputs/AG-T", prefix="agt_", n=100, width=3, min_words=700, groups={"excellent": 20, "1-2": 30, "3-4": 25, "5+": 20, "auto_fail": 5},
                group_tol=5,  # a writing guide, not a labelling target: honest relabelling moved 2 calls into 5+ (Oct 2026)
                min_fail=AGT_MIN_FAIL, min_pass=40, borderline_max=10, names_min=90, markers="required",
                agent_sentiment=False, hard_ratio=False),
    # 12 sealed calls that fill AG-B's gaps (its task brief is in git history); its own mix targets are checked below
    "agb2": dict(dir="laya-finetuning/inputs/AG-B2", prefix="agb2_", n=12, width=2, groups={}, group_tol=0, min_fail={}, min_pass=0,
                 borderline_max=2, names_min=12, markers="required", agent_sentiment=False, hard_ratio=False),
}
SUITES["agc"] = dict(dir="laya-finetuning/inputs/AG-C", prefix="agc_", n=50, width=2, groups={"excellent": 8, "1-2": 15, "3-4": 12, "5+": 11, "auto_fail": 4},
                     group_tol=1, min_fail=AG50_MIN_FAIL, min_pass=25, borderline_max=5, names_min=50, markers="required",
                     agent_sentiment=False, hard_ratio=True)
AGB2_MIX = {"long excellent calls (15+ min, every item PASS)": 4, "short poor calls (10-12 min, 5+ failed items, not auto-fail)": 3,
            "calls with 2+ outbursts": 5, "calls where a handled outburst is followed by an unhandled one": 3,
            "outbursts in the last third of the call": 3}
AGC_MIX = {"long excellent calls (15+ min, every item PASS)": 3, "short poor calls (10-12 min, 5+ failed items, not auto-fail)": 3,
           "calls with 2+ outbursts": 8, "calls where a handled outburst is followed by an unhandled one": 4,
           "outbursts in the last third of the call": 5}
AGC_NO_OUTBURST_MIN = 15          # upset-looking but fine customer lines, marked no_outburst
AGC_MAX_LENGTH_QUALITY_R = 0.30   # |correlation| between call length and number of failed items

# marker kinds per check, and the minimum totals over a full AG-T set
MARKER_KINDS = {
    "active_listening": {"repeat", "harmless_recheck"},
    "paraphrasing": {"restatement", "not_a_restatement"},
    "rapport": {"rude", "blunt_but_ok"},
    "empathy": {"handled", "unhandled", "no_outburst"},
}
AGT_MARKER_MIN = {
    ("active_listening", "repeat"): 30, ("active_listening", "harmless_recheck"): 70,
    ("paraphrasing", "restatement"): 60, ("paraphrasing", "not_a_restatement"): 50,
    ("rapport", "rude"): 30, ("rapport", "blunt_but_ok"): 60,
    ("empathy", "handled"): 40, ("empathy", "unhandled"): 35,
}
AGT_TAG_MIN = {"reworded repeats": 12, "repeats 5+ minutes apart": 10, "late acknowledgements (3-4 turns after)": 15,
               "acknowledgement then refusal": 15, "rude lines in calls of 12+ minutes": 20,
               # spread: events must not all sit at the start of the call, and the look-alikes must not all be adjacent turns
               "outbursts after the first third of the call": 30, "calls with 2+ outbursts": 15,
               "harmless rechecks 10+ turns after the premise": 25, "rude lines in the middle third": 8,
               "events in the last third of the call": 25}      # outbursts, rude lines, repeats and rechecks in the final third


def mmss(val):
    m = TIME_RE.match(val.strip()) if isinstance(val, str) else None
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


def is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def final_score(scorecard, auto_fail):
    if auto_fail:
        return 0.0
    ded = {n: d for _, n, d in SPEC}
    soft = tech = 0
    for it in scorecard:
        if it["rating"] == "FAIL":
            if it["category"] == "Soft Skills":
                soft += ded[it["name"]]
            else:
                tech += ded[it["name"]]
    return round(0.333 * max(0, 100 - soft) + 0.667 * max(0, 100 - tech), 1)


def check_markers(cid, turns, markers, ratings, duration, err, tally):
    """markers: {check: [ {kind, ...turn indices...} ]}. Turn index = 0-based position in the transcript array."""
    if not isinstance(markers, dict):
        err("markers", f"{cid}: grader.markers must be an object with keys {sorted(MARKER_KINDS)}")
        return
    for extra in set(markers) - set(MARKER_KINDS):
        err("markers", f"{cid}: unknown markers key '{extra}'")
    n = len(turns)

    def turn_of(m, field, speaker, where):
        v = m.get(field)
        if not is_int(v) or not 0 <= v < n:
            err("markers", f"{cid} {where}: '{field}' must be a turn index 0..{n - 1}, got {v!r}")
            return None
        if turns[v]["speaker"] != speaker:
            err("markers", f"{cid} {where}: turn {v} ('{field}') is {turns[v]['speaker']}, expected {speaker}")
            return None
        return v

    for check, kinds in MARKER_KINDS.items():
        lst = markers.get(check)
        if lst is None:
            err("markers", f"{cid}: grader.markers.{check} is missing (use [] when there is nothing to mark)")
            continue
        if not isinstance(lst, list):
            err("markers", f"{cid}: grader.markers.{check} must be a list")
            continue
        found = Counter()
        for k, m in enumerate(lst):
            where = f"{check}[{k}]"
            kind = m.get("kind") if isinstance(m, dict) else None
            if kind not in kinds:
                err("markers", f"{cid} {where}: kind must be one of {sorted(kinds)}, got {kind!r}")
                continue
            found[kind] += 1
            tally[(check, kind)] += 1
            if check == "active_listening":
                p = turn_of(m, "premise_turn", "Customer", where)
                a = turn_of(m, "agent_turn", "Agent", where)
                if a is not None and a / n >= 0.66:
                    tally["events in the last third of the call"] += 1
                if p is not None and a is not None:
                    if p >= a:
                        err("markers", f"{cid} {where}: premise_turn must come before agent_turn")
                    elif kind == "harmless_recheck":
                        tally["_rechecks"] += 1
                        if a - p >= 10:
                            tally["harmless rechecks 10+ turns after the premise"] += 1
                    elif kind == "repeat":
                        if turns[a]["start_time_sec"] - turns[p]["start_time_sec"] >= 300:
                            tally["repeats 5+ minutes apart"] += 1
                        if m.get("reworded") is True:
                            tally["reworded repeats"] += 1
            elif check == "paraphrasing":
                turn_of(m, "agent_turn", "Agent", where)
            elif check == "rapport":
                a = turn_of(m, "agent_turn", "Agent", where)
                if a is not None and kind == "rude" and duration >= 720:
                    tally["rude lines in calls of 12+ minutes"] += 1
                if a is not None and kind == "rude" and 0.33 <= a / n < 0.66:
                    tally["rude lines in the middle third"] += 1
                if a is not None and kind == "rude" and a / n >= 0.66:
                    tally["events in the last third of the call"] += 1
            elif check == "empathy":
                c = turn_of(m, "customer_turn", "Customer", where)
                if c is not None and kind != "no_outburst":       # no_outburst = looks upset to a classifier but is not an outburst
                    tally["_outbursts"] += 1
                    if c / n >= 0.33:
                        tally["outbursts after the first third of the call"] += 1
                    if c / n >= 0.66:
                        tally["events in the last third of the call"] += 1
                if kind == "handled":
                    a = turn_of(m, "agent_turn", "Agent", where)
                    if c is not None and a is not None:
                        if not 1 <= a - c <= 4:
                            err("markers", f"{cid} {where}: a handled outburst needs the agent turn 1 to 4 turns after the customer turn "
                                           f"(got {a - c}); a later acknowledgement is 'unhandled' for that outburst")
                        elif a - c >= 3:
                            tally["late acknowledgements (3-4 turns after)"] += 1
                    if m.get("with_refusal") is True:
                        tally["acknowledgement then refusal"] += 1
        # the markers must agree with the rating you gave
        rating = ratings.get(check)
        if check == "active_listening" and rating is not None and (rating == "FAIL") != (found["repeat"] > 0):
            err("markers", f"{cid}: Active listening is {rating} but there are {found['repeat']} 'repeat' markers (FAIL needs at least one, PASS none)")
        if check == "paraphrasing" and rating is not None and (rating == "PASS") != (found["restatement"] > 0):
            err("markers", f"{cid}: Paraphrasing is {rating} but there are {found['restatement']} 'restatement' markers (PASS needs at least one, FAIL none)")
        if check == "rapport" and rating is not None and (rating == "FAIL") != (found["rude"] > 0):
            err("markers", f"{cid}: Rapport is {rating} but there are {found['rude']} 'rude' markers (FAIL needs at least one, PASS none)")
        if check == "empathy" and found["handled"] + found["unhandled"] >= 2:
            tally["calls with 2+ outbursts"] += 1
        if check == "empathy" and rating is not None and (rating == "FAIL") != (found["unhandled"] > 0):
            err("markers", f"{cid}: Empathy is {rating} but there are {found['unhandled']} 'unhandled' markers (FAIL needs at least one, PASS none)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--suite", required=True, choices=sorted(SUITES))
    ap.add_argument("--dir", default=None, help="folder with the payloads (default depends on --suite)")
    ap.add_argument("--subset", default="", help="comma-separated call ids to check while the set is incomplete")
    args = ap.parse_args()
    cfg = SUITES[args.suite]
    base = os.path.abspath(args.dir) if args.dir else os.path.join(ROOT, cfg["dir"])
    if args.subset:
        ids = [c.strip() for c in args.subset.split(",") if c.strip()]
        full = False
    else:
        ids = [f"{cfg['prefix']}{i:0{cfg['width']}d}" for i in range(1, cfg["n"] + 1)]
        full = True

    checks = ["files", "turns", "length", "padding", "rule_items", "sentiment", "auto_fail", "final_score", "scorecard", "markers", "coverage"]
    all_text = {}
    dur_fail = []          # (duration, failed items) per call, for the length/quality check
    errors = {c: [] for c in checks}
    warns = []

    def err(check, msg):
        errors[check].append(msg)

    fails, passes, groups, durations, names = Counter(), Counter(), Counter(), [], []
    tally, borderline, hard_f, hard_p, tot_f, tot_p = Counter(), 0, 0, 0, 0, 0

    for cid in ids:
        rp, ep = os.path.join(base, f"{cid}.json"), os.path.join(base, "expected", f"expected_{cid}.json")
        if not os.path.isfile(rp) or not os.path.isfile(ep):
            err("files", f"{cid}: missing {'payload' if not os.path.isfile(rp) else 'key'} file")
            continue
        try:
            req = json.load(open(rp, encoding="utf-8"))
            exp = json.load(open(ep, encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            err("files", f"{cid}: cannot parse JSON ({e})")
            continue

        if req.get("tenant_id") != "tenant-abc" or exp.get("tenant_id") != "tenant-abc":
            err("files", f"{cid}: tenant_id must be 'tenant-abc' in the payload and the key")
        if exp.get("call_id") != cid:
            err("files", f"{cid}: key call_id is {exp.get('call_id')!r}")
        if exp.get("status") != "completed":
            err("files", f"{cid}: key status must be 'completed'")
        cname = req.get("customer_name")
        if not isinstance(cname, str) or not cname.strip() or " " in cname.strip():
            err("files", f"{cid}: customer_name must be one first name")
        else:
            names.append(cname.strip().lower())
        turns = req.get("transcript")
        if not isinstance(turns, list) or not turns:
            err("turns", f"{cid}: transcript is empty or not a list")
            continue

        # ---- turns, timing, sentiment
        prev_end, words, cust_scores = 0, 0, []
        for i, t in enumerate(turns):
            for key in ("speaker", "start_time", "end_time", "start_time_sec", "text"):
                if key not in t:
                    err("turns", f"{cid} turn {i}: missing '{key}'")
            spk = t.get("speaker")
            if spk not in ("Agent", "Customer"):
                err("turns", f"{cid} turn {i}: speaker must be 'Agent' or 'Customer'")
            s, e = mmss(t.get("start_time")), mmss(t.get("end_time"))
            if s is None or e is None:
                err("turns", f"{cid} turn {i}: start_time/end_time must look like [MM:SS]")
                continue
            if not is_int(t.get("start_time_sec")) or t["start_time_sec"] != s:
                err("turns", f"{cid} turn {i}: start_time_sec must be the integer seconds of start_time ({s})")
            if e < s:
                err("turns", f"{cid} turn {i}: end_time is before start_time")
            if e - s > 30:
                err("turns", f"{cid} turn {i}: lasts {e - s}s, the limit is 30s")
            if s < prev_end:
                err("turns", f"{cid} turn {i}: starts before the previous turn ends")
            prev_end = e
            if not isinstance(t.get("text"), str) or not t["text"].strip():
                err("turns", f"{cid} turn {i}: empty text")
            else:
                words += len(t["text"].split())
            sc = t.get("sentiment_score")
            if spk == "Customer":
                if not isinstance(sc, float) or not -100.0 <= sc <= 100.0:
                    err("sentiment", f"{cid} turn {i}: a Customer turn needs a float sentiment_score between -100 and 100")
                else:
                    cust_scores.append((i, sc, len(t["text"].split())))
            elif spk == "Agent":
                if cfg["agent_sentiment"]:
                    if not isinstance(sc, float):
                        err("sentiment", f"{cid} turn {i}: sentiment_score must be a float on every turn in this suite")
                elif "sentiment_score" in t and sc not in (None, 0, 0.0):
                    err("sentiment", f"{cid} turn {i}: Agent turns carry NO sentiment (leave the field out)")
        last_end = mmss(turns[-1].get("end_time", ""))
        if last_end is None or not 600 <= last_end <= 1200:
            err("length", f"{cid}: the call must end between [10:00] and [20:00]")
            last_end = last_end or 0
        else:
            durations.append(last_end)
        if not 55 <= len(turns) <= 170:
            err("length", f"{cid}: {len(turns)} turns, expected about 60-160")
        if not cfg.get("min_words", 1100) <= words <= 3000:
            err("length", f"{cid}: {words} words, expected {cfg.get('min_words', 1100)}-3000. Add real support work, never filler or repeated turns")
        # ---- padding: repeated turns inside one call, stock filler clauses
        reps = Counter(t.get("text", "").strip().lower() for t in turns if len(str(t.get("text", "")).split()) >= 8)
        for text, k in reps.items():
            if k >= 3:
                err("padding", f"{cid}: the same {len(text.split())}-word turn appears {k} times (padding by repetition is not allowed)")
            elif k == 2:
                warns.append(f"{cid}: one {len(text.split())}-word turn appears twice word for word; fine only if a real agent would repeat it")
        filler = sum(ph.lower() in t.get("text", "").lower() for t in turns for ph in FILLER_PHRASES)
        if filler:
            err("padding", f"{cid}: {filler} turn(s) contain a stock filler clause (length must come from real support work)")
        all_text[cid] = " ".join(t.get("text", "") for t in turns)
        if len(cust_scores) >= 10 and not cfg["agent_sentiment"]:
            steps = [abs(b[1] - a[1]) for a, b in zip(cust_scores, cust_scores[1:])]
            if sum(1 for d in steps if d >= 3.0) / len(steps) < 0.5:
                warns.append(f"{cid}: customer sentiment is too smooth (fewer than half of the turn-to-turn changes are 3+ points)")
            loud = [i for i, sc, w in cust_scores if w <= 3 and abs(sc) > 12]
            if loud:
                warns.append(f"{cid}: {len(loud)} one-to-three word customer turns score beyond +/-12 (a text classifier gives them about 0)")

        res, grader = exp.get("result", {}), exp.get("grader", {})
        if grader.get("duration_sec") != last_end:
            err("length", f"{cid}: grader.duration_sec must equal the last end_time in seconds ({last_end})")

        # ---- scorecard structure
        scorecard = res.get("scorecard", [])
        if len(scorecard) != 11:
            err("scorecard", f"{cid}: the scorecard has {len(scorecard)} entries, expected 11")
            continue
        rating = {}
        for i, (it, (cat, nm, _)) in enumerate(zip(scorecard, SPEC)):
            if it.get("category") != cat or it.get("name") != nm:
                err("scorecard", f"{cid} scorecard[{i}]: expected ({cat}, {nm})")
            r, co = it.get("rating"), it.get("coaching")
            if r not in ("PASS", "FAIL"):
                err("scorecard", f"{cid} '{nm}': rating must be PASS or FAIL")
            if r == "PASS" and co != "":
                err("scorecard", f"{cid} '{nm}': PASS needs empty coaching")
            if r == "FAIL" and not (isinstance(co, str) and co.strip()):
                err("scorecard", f"{cid} '{nm}': FAIL needs one coaching sentence")
            rating[nm] = r
        hard = grader.get("hard_cases", [])
        for h in hard if isinstance(hard, list) else []:
            if h not in rating:
                err("scorecard", f"{cid}: unknown criterion {h!r} in hard_cases")
        items = grader.get("items", [])
        if len(items) != 11:
            err("scorecard", f"{cid}: grader.items has {len(items)} entries, expected 11")
        else:
            for i, (gi, nm) in enumerate(zip(items, NAMES)):
                if gi.get("name") != nm or gi.get("rating") != rating.get(nm):
                    err("scorecard", f"{cid} grader.items[{i}]: name or rating differs from the scorecard")
                if gi.get("confidence") not in ("clear", "borderline"):
                    err("scorecard", f"{cid} grader.items[{i}]: confidence must be 'clear' or 'borderline'")
                borderline += gi.get("confidence") == "borderline"
                if (gi.get("rating") == "FAIL" or nm in hard) and not str(gi.get("evidence", "")).strip():
                    err("scorecard", f"{cid} grader.items[{i}] '{nm}': needs timestamped evidence")

        # ---- the four rule items, with the application's own functions
        tl = [(t["speaker"], t["text"]) for t in turns]
        tm = [(t["start_time_sec"], t["start_time_sec"] + 10) for t in turns]
        calc = {
            "Branding and Survey Check": evaluate_branding(tl)["rating"],
            "Hold time and Dead Air": evaluate_hold_and_dead_air(tl, tm)["rating"],
            "Verified customer": evaluate_verified_customer(tl, tm)["rating"],
            "Personalized the call/ticket appropriately": evaluate_personalized_call(tl, cname or "")["rating"],
        }
        for nm, r in calc.items():
            if r != rating.get(nm):
                err("rule_items", f"{cid} {nm}: the application gives {r}, the key says {rating.get(nm)}")
        gaps = [i for i in range(1, len(tm)) if tm[i][0] - tm[i - 1][1] > 30 and not _is_managed_hold(tl, i, tm[i][0] - tm[i - 1][1])]
        if calc["Hold time and Dead Air"] == "PASS" and gaps and "Hold time and Dead Air" not in (hard or []):
            warns.append(f"{cid}: {len(gaps)} unmanaged gap(s) over 30s by the app formula but Dead Air is PASS; add 'Hold time and Dead Air' to hard_cases if intended")

        # ---- auto-fail
        hits = [(i, w) for i, t in enumerate(turns) if t.get("speaker") == "Agent" for w in AUTO_FAIL_STRINGS if w in t.get("text", "").lower()]
        af, reason = res.get("is_auto_fail"), res.get("auto_fail_reason")
        if af and not hits:
            err("auto_fail", f"{cid}: is_auto_fail is true but no Agent line contains one of {AUTO_FAIL_STRINGS}")
        if af and not (isinstance(reason, str) and reason.strip()):
            err("auto_fail", f"{cid}: is_auto_fail needs an auto_fail_reason")
        if not af and hits:
            err("auto_fail", f"{cid}: Agent turn(s) {[i for i, _ in hits]} contain an auto-fail word but is_auto_fail is false")
        if not af and reason is not None:
            err("auto_fail", f"{cid}: auto_fail_reason must be null when is_auto_fail is false")

        # ---- final score
        if res.get("final_score") != final_score(scorecard, bool(af)):
            err("final_score", f"{cid}: final_score is {res.get('final_score')}, recomputed {final_score(scorecard, bool(af))}")

        # ---- markers
        if "markers" in grader:
            check_markers(cid, turns, grader["markers"], {"active_listening": rating.get("Active listening"),
                          "paraphrasing": rating.get("Paraphrasing"), "rapport": rating.get("Build rapport and observed professionalism"),
                          "empathy": rating.get("Empathy & Acknowledgment Statement")}, last_end, err, tally)
        elif cfg["markers"] == "required":
            err("markers", f"{cid}: grader.markers is required in this suite")

        # ---- coverage numbers
        nfail = sum(1 for it in scorecard if it["rating"] == "FAIL")
        groups["auto_fail" if af else "excellent" if nfail == 0 else "1-2" if nfail <= 2 else "3-4" if nfail <= 4 else "5+"] += 1
        dur_fail.append((last_end, nfail))
        if args.suite in ("agb2", "agc"):
            emp = sorted((m for m in (grader.get("markers") or {}).get("empathy", []) if isinstance(m, dict)
                          and m.get("kind") in ("handled", "unhandled") and is_int(m.get("customer_turn"))), key=lambda m: m["customer_turn"])
            mix = tally
            mix["long excellent calls (15+ min, every item PASS)"] += last_end >= 900 and nfail == 0 and not af
            mix["short poor calls (10-12 min, 5+ failed items, not auto-fail)"] += last_end <= 720 and nfail >= 5 and not af
            mix["calls where a handled outburst is followed by an unhandled one"] += any(
                a["kind"] == "handled" and b["kind"] == "unhandled" for k, a in enumerate(emp) for b in emp[k + 1:])
            mix["outbursts in the last third of the call"] += sum(m["customer_turn"] / len(turns) >= 0.66 for m in emp)
        for it in scorecard:
            if it["rating"] == "FAIL":
                fails[it["name"]] += 1
                tot_f += 1
                hard_f += it["name"] in (hard or [])
            else:
                passes[it["name"]] += 1
                tot_p += 1
                hard_p += it["name"] in (hard or [])

    # ---- coverage (a full run only)
    if full and all_text:
        df = Counter()
        for text in all_text.values():
            w = re.findall(r"[a-z0-9']+", text.lower())
            df.update({" ".join(w[i:i + 12]) for i in range(len(w) - 11)})
        common = [g for g, k in df.items() if k > 0.4 * len(all_text) and "s-net" not in g]
        if common:
            warns.append(f"{len(common)} twelve-word phrase(s) appear in more than 40% of the calls, e.g. '{common[0]}'. "
                         "Scripted lines are fine; copy-pasted dialogue is not")
    if full:
        if len(set(names)) < cfg["names_min"]:
            err("files", f"only {len(set(names))} different customer names, need at least {cfg['names_min']}")
        for g, target in cfg["groups"].items():
            if abs(groups[g] - target) > cfg["group_tol"]:
                err("coverage", f"group '{g}' has {groups[g]} calls, target {target}" + (f" (+/-{cfg['group_tol']})" if cfg["group_tol"] else ""))
        for nm, mn in cfg["min_fail"].items():
            if fails[nm] < mn:
                err("coverage", f"'{nm}' has {fails[nm]} FAILs, minimum {mn}")
            if passes[nm] < cfg["min_pass"]:
                err("coverage", f"'{nm}' has {passes[nm]} PASSes, minimum {cfg['min_pass']}")
        if borderline > cfg["borderline_max"]:
            err("coverage", f"{borderline} borderline items, maximum {cfg['borderline_max']}")
        if cfg["hard_ratio"]:
            if tot_f and hard_f / tot_f < 0.40:
                err("coverage", f"hard FAILs are {hard_f}/{tot_f}, need at least 40%")
            if tot_p and not 0.22 <= hard_p / tot_p <= 0.40:
                err("coverage", f"hard PASSes are {hard_p}/{tot_p}, need about 30%")
        if args.suite in ("agb2", "agc"):
            for key, mn in (AGB2_MIX if args.suite == "agb2" else AGC_MIX).items():
                if tally[key] < mn:
                    err("coverage", f"{key}: {tally[key]} found, minimum {mn}")
        if args.suite == "agc":
            if tally[("empathy", "no_outburst")] < AGC_NO_OUTBURST_MIN:
                err("coverage", f"no_outburst markers (upset-looking but fine customer lines): {tally[('empathy', 'no_outburst')]}, "
                                f"minimum {AGC_NO_OUTBURST_MIN}")
            if len(dur_fail) >= 10:
                d, f = [x for x, _ in dur_fail], [y for _, y in dur_fail]
                md, mf = sum(d) / len(d), sum(f) / len(f)
                den = (sum((x - md) ** 2 for x in d) * sum((y - mf) ** 2 for y in f)) ** 0.5
                r = sum((x - md) * (y - mf) for x, y in zip(d, f)) / den if den else 0.0
                if abs(r) > AGC_MAX_LENGTH_QUALITY_R:
                    err("coverage", f"call length and number of failed items correlate r = {r:+.2f} (limit +/-{AGC_MAX_LENGTH_QUALITY_R}): "
                                    "quality must not show in length; give some good calls long durations and some poor calls short ones")
        if args.suite == "agt":
            for key, mn in AGT_MARKER_MIN.items():
                if tally[key] < mn:
                    err("coverage", f"markers {key[0]}/{key[1]}: {tally[key]} found, minimum {mn}")
            for key, mn in AGT_TAG_MIN.items():
                if tally[key] < mn:
                    err("coverage", f"{key}: {tally[key]} found, minimum {mn}")

    if args.suite == "agt" and not full:      # early feedback while the set is still being written
        if tally["_outbursts"] >= 5 and tally["outbursts after the first third of the call"] / tally["_outbursts"] < 0.25:
            warns.append(f"SPREAD: only {tally['outbursts after the first third of the call']} of {tally['_outbursts']} outbursts are after the "
                         "first third of the call. Put upset moments in the middle and last thirds too, not only in the customer's opening line")
        if tally["_rechecks"] >= 5 and tally["harmless rechecks 10+ turns after the premise"] / tally["_rechecks"] < 0.25:
            warns.append(f"SPREAD: only {tally['harmless rechecks 10+ turns after the premise']} of {tally['_rechecks']} harmless rechecks are 10+ turns "
                         "after the premise. Most should look like a real repeat: the information given minutes earlier, a similar question later")
        if len(ids) >= 5 and tally["calls with 2+ outbursts"] == 0:
            warns.append("SPREAD: no call has two or more outbursts yet (first handled, a later one missed is the case we most need)")
        if len(ids) >= 5 and tally["events in the last third of the call"] < len(ids) // 5:
            warns.append(f"SPREAD: only {tally['events in the last third of the call']} events (outburst, rude line, repeat, recheck) in the last third "
                         f"of {len(ids)} calls; put some there")
        handled = tally[("empathy", "handled")]
        if handled >= 8 and tally["late acknowledgements (3-4 turns after)"] == 0:
            warns.append("MISSING: no late acknowledgement yet (agent recognises the feeling 3 or 4 turns after the outburst, after a procedural answer)")
        if handled >= 8 and tally["acknowledgement then refusal"] == 0:
            warns.append("MISSING: no 'acknowledgement then refusal' yet (handled outburst with \"with_refusal\": true)")
        for kind, label in ((("paraphrasing", "not_a_restatement"), "not_a_restatement"), (("rapport", "blunt_but_ok"), "blunt_but_ok")):
            if len(ids) >= 5 and tally[kind] < 0.4 * len(ids):
                warns.append(f"MARKERS: only {tally[kind]} '{label}' markers in {len(ids)} calls (expected about one per call). Mark every such line you wrote")

    labels = {"files": "payloads and keys exist, ids and names valid", "turns": "turn fields, time order, no overlaps, turns of 30s or less",
              "length": "10-20 minute calls, turn and word counts, duration_sec",
              "padding": "no repeated turns, no stock filler clauses", "rule_items": "four rule items match the application's code",
              "sentiment": "sentiment rules (customer float on every turn, no agent sentiment)", "auto_fail": "auto-fail words only where intended",
              "final_score": "final score recomputed from the ratings", "scorecard": "11 scorecard and grader entries, coaching, evidence",
              "markers": "markers valid and consistent with the ratings", "coverage": "set-level coverage targets"}
    print("=" * 74)
    print(f"{args.suite.upper()} VALIDATION: {len(ids)} calls" + ("" if full else " (subset: set-level coverage not checked)"))
    print("=" * 74)
    ok = True
    for c in checks:
        errs = errors[c]
        print(f"[{'PASS' if not errs else f'FAIL ({len(errs)})':9s}] {labels[c]}")
        for m in errs[:12]:
            print(f"            -> {m}")
        if len(errs) > 12:
            print(f"            -> ... and {len(errs) - 12} more")
        ok &= not errs
    for w in warns[:12]:
        print(f"WARN {w}")
    if len(warns) > 12:
        print(f"WARN ... and {len(warns) - 12} more")
    if durations:
        b = [sum(1 for d in durations if lo <= d < hi) for lo, hi in ((600, 720), (720, 900), (900, 1080), (1080, 1201))]
        print("-" * 74)
        print(f"Lengths: 10-12m={b[0]}  12-15m={b[1]}  15-18m={b[2]}  18-20m={b[3]}   Groups: {dict(groups)}")
        print("Per criterion (FAIL / PASS):")
        for nm in NAMES:
            print(f"  {nm:45s} {fails[nm]:3d} / {passes[nm]:3d}   (minimum FAIL {cfg['min_fail'].get(nm, 0)}, PASS {cfg['min_pass']})")
        if tally:
            print("Markers: " + ", ".join(f"{k[0]}/{k[1]}={v}" for k, v in sorted(tally.items(), key=str) if isinstance(k, tuple)))
            print("Tags   : " + ", ".join(f"{k}={v}" for k, v in sorted(tally.items(), key=str) if isinstance(k, str) and not k.startswith("_")))
    print("=" * 74)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
