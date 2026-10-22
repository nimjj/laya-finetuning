#!/usr/bin/env python3
"""
selfcheck.py — Independent validator for the AG50 S-Net QA benchmark dataset.
Uses Python standard library only.
"""

import argparse
import json
import os
import re
import sys
from collections import Counter

EXPECTED_SCORECARD_SPEC = [
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

MIN_FAIL_COUNTS = {
    "Branding and Survey Check": 8,
    "Hold time and Dead Air": 8,
    "Verified customer": 8,
    "Personalized the call/ticket appropriately": 8,
    "Empathy & Acknowledgment Statement": 12,
    "Paraphrasing": 12,
    "Active listening": 12,
    "Took ownership of the problem": 12,
    "Build rapport and observed professionalism": 10,
    "Probing": 10,
    "Confirmed the issue is resolved": 12,
}

AUTO_FAIL_STRINGS = ["fuck", "shut up", "idiot", "get lost", "stupid", "hang up"]

HOLD_MAX_EXEMPT_SEC = 120
_HOLD_ANNOUNCE_RE = re.compile(
    r"\b(place|put) you on (a )?(brief |short |quick )?hold\b|\bbear with me\b"
    r"|\b(one|a) moment while\b|\bgive me (a|one) (moment|minute|second|sec) while\b",
    re.IGNORECASE,
)
_HOLD_RETURN_RE = re.compile(
    r"\bthank(s| you)( so much)? for (holding|waiting|your patience|bearing with me)\b|\bsorry for the wait\b",
    re.IGNORECASE,
)
_CUSTOMER_CHASING_RE = re.compile(
    r"\bhello\?|\b(are )?you still there\b|\banyone there\b", re.IGNORECASE
)
_TIME_RE = re.compile(r"^\[(\d{2}):(\d{2})\]$")


def parse_mmss(val: str):
    if not isinstance(val, str):
        return None
    m = _TIME_RE.match(val.strip())
    if not m:
        return None
    return int(m.group(1)) * 60 + int(m.group(2))


def eval_branding(turns):
    agent_lines = [t["text"] for t in turns if t["speaker"].lower() == "agent"]
    if not agent_lines:
        return "FAIL"
    first_4 = " ".join(agent_lines[:4]).lower()
    last_4 = " ".join(agent_lines[-4:]).lower()
    greeting_ok = "thank you for calling s-net" in first_4
    closing_ok = "thank you for choosing s-net" in last_4
    return "PASS" if (greeting_ok and closing_ok) else "FAIL"


def is_managed_hold(turns, i, gap):
    if gap > HOLD_MAX_EXEMPT_SEC:
        return False
    prev_spk, prev_txt = turns[i - 1]["speaker"], turns[i - 1]["text"]
    spk, txt = turns[i]["speaker"], turns[i]["text"]
    if spk.lower() == "customer" and _CUSTOMER_CHASING_RE.search(txt):
        return False
    return (
        (spk.lower() == "agent" and bool(_HOLD_RETURN_RE.search(txt)))
        or (prev_spk.lower() == "agent" and bool(_HOLD_ANNOUNCE_RE.search(prev_txt)))
    )


def eval_hold_and_dead_air(turns):
    unmanaged_gaps = []
    managed_gaps = []
    for i in range(1, len(turns)):
        prev_end = turns[i - 1]["start_time_sec"] + 10
        curr_start = turns[i]["start_time_sec"]
        gap = curr_start - prev_end
        if gap > 30:
            if is_managed_hold(turns, i, gap):
                managed_gaps.append((i, gap))
            else:
                unmanaged_gaps.append((i, gap))
    rating = "FAIL" if len(unmanaged_gaps) >= 2 else "PASS"
    return rating, unmanaged_gaps, managed_gaps


def eval_verified_customer(turns):
    for t in turns:
        if t["speaker"].lower() == "agent" and t["start_time_sec"] <= 240:
            if re.search(r"\b(pin|address|security question)\b", t["text"], re.IGNORECASE):
                return "PASS"
    return "FAIL"


def eval_personalized(turns, customer_name):
    if not customer_name or not customer_name.strip():
        return "PASS"
    name_lower = customer_name.lower().strip()
    for t in turns:
        if t["speaker"].lower() == "agent" and name_lower in t["text"].lower():
            return "PASS"
    return "FAIL"


def compute_final_score(scorecard, is_auto_fail):
    if is_auto_fail:
        return 0.0
    deductions = {name: ded for _, name, ded in EXPECTED_SCORECARD_SPEC}
    soft_ded = 0
    tech_ded = 0
    for item in scorecard:
        if item["rating"] == "FAIL":
            if item["category"] == "Soft Skills":
                soft_ded += deductions[item["name"]]
            elif item["category"] == "Technical Knowledge":
                tech_ded += deductions[item["name"]]
    soft = max(0, 100 - soft_ded)
    tech = max(0, 100 - tech_ded)
    return round(0.333 * soft + 0.667 * tech, 1)


def main():
    parser = argparse.ArgumentParser(description="Validate AG50 calls and expected keys.")
    parser.add_argument("--dir", default=os.path.dirname(os.path.abspath(__file__)), help="AG50 directory")
    parser.add_argument("--subset", default="", help="Comma-separated call IDs (e.g. ag_01,ag_02) for batch check")
    args = parser.parse_args()

    base_dir = args.dir
    expected_dir = os.path.join(base_dir, "expected")
    if args.subset:
        call_ids = [c.strip() for c in args.subset.split(",") if c.strip()]
        is_full_run = len(call_ids) == 50
    else:
        call_ids = [f"ag_{i:02d}" for i in range(1, 51)]
        is_full_run = True

    errors_by_check = {
        "files_and_ids": [],
        "turn_fields_and_timing": [],
        "duration_and_length": [],
        "rule_items": [],
        "auto_fail": [],
        "final_score": [],
        "scorecard_and_grader_structure": [],
        "coverage": [],
    }

    durations = []
    customer_names = []
    fail_counter = Counter()
    pass_counter = Counter()
    group_counter = Counter()
    hard_fail_count = 0
    total_fail_count = 0
    hard_pass_count = 0
    total_pass_count = 0
    borderline_count = 0

    for cid in call_ids:
        req_path = os.path.join(base_dir, f"{cid}.json")
        exp_path = os.path.join(expected_dir, f"expected_{cid}.json")

        if not os.path.isfile(req_path):
            errors_by_check["files_and_ids"].append(f"Missing request payload: {req_path}")
            continue
        if not os.path.isfile(exp_path):
            errors_by_check["files_and_ids"].append(f"Missing expected payload: {exp_path}")
            continue

        try:
            with open(req_path, "r", encoding="utf-8") as f:
                req = json.load(f)
        except Exception as e:
            errors_by_check["files_and_ids"].append(f"{cid}: Failed to parse request JSON: {e}")
            continue

        try:
            with open(exp_path, "r", encoding="utf-8") as f:
                exp = json.load(f)
        except Exception as e:
            errors_by_check["files_and_ids"].append(f"{cid}: Failed to parse expected JSON: {e}")
            continue

        # 1. File / ID / top-level checks
        if req.get("tenant_id") != "tenant-abc":
            errors_by_check["files_and_ids"].append(f"{cid}: req tenant_id != 'tenant-abc'")
        if exp.get("tenant_id") != "tenant-abc":
            errors_by_check["files_and_ids"].append(f"{cid}: exp tenant_id != 'tenant-abc'")
        if exp.get("call_id") != cid:
            errors_by_check["files_and_ids"].append(f"{cid}: exp call_id is '{exp.get('call_id')}', expected '{cid}'")
        if exp.get("status") != "completed":
            errors_by_check["files_and_ids"].append(f"{cid}: exp status != 'completed'")

        cname = req.get("customer_name")
        if not isinstance(cname, str) or not cname.strip() or " " in cname.strip():
            errors_by_check["files_and_ids"].append(f"{cid}: invalid customer_name '{cname}' (must be single first name)")
        else:
            customer_names.append(cname.strip().lower())

        turns = req.get("transcript", [])
        if not isinstance(turns, list) or len(turns) == 0:
            errors_by_check["turn_fields_and_timing"].append(f"{cid}: empty or invalid transcript list")
            continue

        # 2. Turn fields and timing
        prev_end_sec = 0
        total_words = 0
        for idx, t in enumerate(turns):
            for req_key in ("speaker", "start_time", "end_time", "start_time_sec", "text", "sentiment_score"):
                if req_key not in t:
                    errors_by_check["turn_fields_and_timing"].append(f"{cid} turn {idx}: missing '{req_key}'")
            spk = t.get("speaker")
            if spk not in ("Agent", "Customer"):
                errors_by_check["turn_fields_and_timing"].append(f"{cid} turn {idx}: invalid speaker '{spk}'")
            st_sec = parse_mmss(t.get("start_time", ""))
            et_sec = parse_mmss(t.get("end_time", ""))
            if st_sec is None or et_sec is None:
                errors_by_check["turn_fields_and_timing"].append(
                    f"{cid} turn {idx}: invalid timestamp format ({t.get('start_time')} - {t.get('end_time')})"
                )
                continue
            if not isinstance(t.get("start_time_sec"), int) or isinstance(t.get("start_time_sec"), bool):
                errors_by_check["turn_fields_and_timing"].append(f"{cid} turn {idx}: start_time_sec not int")
            elif t["start_time_sec"] != st_sec:
                errors_by_check["turn_fields_and_timing"].append(
                    f"{cid} turn {idx}: start_time_sec ({t['start_time_sec']}) != start_time ({st_sec})"
                )
            if et_sec < st_sec:
                errors_by_check["turn_fields_and_timing"].append(f"{cid} turn {idx}: end_time < start_time")
            if et_sec - st_sec > 30:
                errors_by_check["turn_fields_and_timing"].append(
                    f"{cid} turn {idx}: turn duration {et_sec - st_sec}s > 30s"
                )
            if st_sec < prev_end_sec:
                errors_by_check["turn_fields_and_timing"].append(
                    f"{cid} turn {idx}: overlaps previous turn ({st_sec} < {prev_end_sec})"
                )
            prev_end_sec = et_sec

            sent = t.get("sentiment_score")
            if not isinstance(sent, float) or isinstance(sent, bool):
                errors_by_check["turn_fields_and_timing"].append(
                    f"{cid} turn {idx}: sentiment_score ({sent!r}) is not a float"
                )
            txt = t.get("text", "")
            if not isinstance(txt, str) or not txt.strip():
                errors_by_check["turn_fields_and_timing"].append(f"{cid} turn {idx}: empty text")
            else:
                total_words += len(txt.split())

        # 3. Last end_time between 10:00 and 20:00 & turn/word counts
        last_end_sec = parse_mmss(turns[-1].get("end_time", ""))
        if last_end_sec is None or not (600 <= last_end_sec <= 1200):
            errors_by_check["duration_and_length"].append(
                f"{cid}: last end_time {turns[-1].get('end_time')} ({last_end_sec}s) not in [600, 1200]"
            )
        else:
            durations.append(last_end_sec)

        if not (55 <= len(turns) <= 170):
            errors_by_check["duration_and_length"].append(
                f"{cid}: turn count {len(turns)} outside expected ~60-160 range"
            )
        if not (1100 <= total_words <= 3000):
            errors_by_check["duration_and_length"].append(
                f"{cid}: word count {total_words} outside expected ~1200-2800 range"
            )

        res = exp.get("result", {})
        grader = exp.get("grader", {})
        if grader.get("duration_sec") != last_end_sec:
            errors_by_check["duration_and_length"].append(
                f"{cid}: grader.duration_sec ({grader.get('duration_sec')}) != last end_time ({last_end_sec})"
            )

        # 4. Scorecard & Grader structure
        scorecard = res.get("scorecard", [])
        if len(scorecard) != 11:
            errors_by_check["scorecard_and_grader_structure"].append(
                f"{cid}: scorecard has {len(scorecard)} items, expected 11"
            )
            continue

        sc_map = {}
        for idx, (sc_item, (exp_cat, exp_name, _)) in enumerate(zip(scorecard, EXPECTED_SCORECARD_SPEC)):
            if sc_item.get("category") != exp_cat or sc_item.get("name") != exp_name:
                errors_by_check["scorecard_and_grader_structure"].append(
                    f"{cid} scorecard[{idx}]: got ({sc_item.get('category')}, {sc_item.get('name')}), "
                    f"expected ({exp_cat}, {exp_name})"
                )
            rating = sc_item.get("rating")
            coaching = sc_item.get("coaching")
            if rating not in ("PASS", "FAIL"):
                errors_by_check["scorecard_and_grader_structure"].append(
                    f"{cid} '{exp_name}': invalid rating '{rating}'"
                )
            if rating == "PASS" and coaching != "":
                errors_by_check["scorecard_and_grader_structure"].append(
                    f"{cid} '{exp_name}': PASS must have empty coaching, got '{coaching}'"
                )
            if rating == "FAIL" and (not isinstance(coaching, str) or not coaching.strip()):
                errors_by_check["scorecard_and_grader_structure"].append(
                    f"{cid} '{exp_name}': FAIL must have non-empty coaching"
                )
            sc_map[exp_name] = rating

        hard_cases = grader.get("hard_cases", [])
        if not isinstance(hard_cases, list):
            errors_by_check["scorecard_and_grader_structure"].append(f"{cid}: grader.hard_cases not a list")
            hard_cases = []
        for hc in hard_cases:
            if hc not in sc_map:
                errors_by_check["scorecard_and_grader_structure"].append(
                    f"{cid}: unknown criterion '{hc}' in grader.hard_cases"
                )

        g_items = grader.get("items", [])
        if len(g_items) != 11:
            errors_by_check["scorecard_and_grader_structure"].append(
                f"{cid}: grader.items has {len(g_items)} entries, expected 11"
            )
        else:
            for idx, (gi, (_, exp_name, _)) in enumerate(zip(g_items, EXPECTED_SCORECARD_SPEC)):
                if gi.get("name") != exp_name:
                    errors_by_check["scorecard_and_grader_structure"].append(
                        f"{cid} grader.items[{idx}]: name '{gi.get('name')}' != '{exp_name}'"
                    )
                if gi.get("rating") != sc_map.get(exp_name):
                    errors_by_check["scorecard_and_grader_structure"].append(
                        f"{cid} grader.items[{idx}] '{exp_name}': rating '{gi.get('rating')}' != scorecard '{sc_map.get(exp_name)}'"
                    )
                conf = gi.get("confidence")
                if conf not in ("clear", "borderline"):
                    errors_by_check["scorecard_and_grader_structure"].append(
                        f"{cid} grader.items[{idx}] '{exp_name}': invalid confidence '{conf}'"
                    )
                if conf == "borderline":
                    borderline_count += 1
                ev = gi.get("evidence", "")
                if gi.get("rating") == "FAIL" and (not isinstance(ev, str) or not ev.strip()):
                    errors_by_check["scorecard_and_grader_structure"].append(
                        f"{cid} grader.items[{idx}] '{exp_name}': FAIL must have timestamped evidence"
                    )
                if exp_name in hard_cases and (not isinstance(ev, str) or not ev.strip()):
                    errors_by_check["scorecard_and_grader_structure"].append(
                        f"{cid} grader.items[{idx}] '{exp_name}': hard_case item must have timestamped evidence"
                    )

        # 5. Rule-based items recomputed from transcript
        b_calc = eval_branding(turns)
        h_calc, unmanaged_gaps, managed_gaps = eval_hold_and_dead_air(turns)
        v_calc = eval_verified_customer(turns)
        p_calc = eval_personalized(turns, cname)

        if b_calc != sc_map["Branding and Survey Check"]:
            errors_by_check["rule_items"].append(
                f"{cid} Branding: rule_engine={b_calc}, key={sc_map['Branding and Survey Check']}"
            )
        if h_calc != sc_map["Hold time and Dead Air"]:
            errors_by_check["rule_items"].append(
                f"{cid} Dead Air: rule_engine={h_calc} (unmanaged={unmanaged_gaps}, managed={managed_gaps}), "
                f"key={sc_map['Hold time and Dead Air']}"
            )
        if v_calc != sc_map["Verified customer"]:
            errors_by_check["rule_items"].append(
                f"{cid} Verified customer: rule_engine={v_calc}, key={sc_map['Verified customer']}"
            )
        if p_calc != sc_map["Personalized the call/ticket appropriately"]:
            errors_by_check["rule_items"].append(
                f"{cid} Personalized: rule_engine={p_calc}, key={sc_map['Personalized the call/ticket appropriately']}"
            )

        # Also check no unintended unmanaged gaps > 30s when Dead Air is PASS (unless H is in hard_cases)
        if h_calc == "PASS" and len(unmanaged_gaps) > 0 and "Hold time and Dead Air" not in hard_cases:
            errors_by_check["turn_fields_and_timing"].append(
                f"{cid}: has {len(unmanaged_gaps)} unmanaged gap(s) >30s ({unmanaged_gaps}) without Dead Air in hard_cases"
            )

        # 6. Auto-fail check
        found_af = []
        for idx, t in enumerate(turns):
            if t["speaker"].lower() == "agent":
                low = t["text"].lower()
                for trig in AUTO_FAIL_STRINGS:
                    if trig in low:
                        found_af.append((idx, t["start_time"], trig, t["text"]))

        is_af = res.get("is_auto_fail")
        af_reason = res.get("auto_fail_reason")
        if is_af:
            if not found_af:
                errors_by_check["auto_fail"].append(
                    f"{cid}: marked is_auto_fail=True but no auto-fail string found in Agent lines"
                )
            if not isinstance(af_reason, str) or not af_reason.strip():
                errors_by_check["auto_fail"].append(
                    f"{cid}: marked is_auto_fail=True but auto_fail_reason is empty"
                )
        else:
            if found_af:
                errors_by_check["auto_fail"].append(
                    f"{cid}: marked is_auto_fail=False but Agent line contains auto-fail trigger: {found_af}"
                )
            if af_reason is not None:
                errors_by_check["auto_fail"].append(
                    f"{cid}: marked is_auto_fail=False but auto_fail_reason is not null ({af_reason!r})"
                )

        # 7. Final score check
        calc_score = compute_final_score(scorecard, bool(is_af))
        if res.get("final_score") != calc_score:
            errors_by_check["final_score"].append(
                f"{cid}: final_score={res.get('final_score')}, expected {calc_score}"
            )

        # 8. Accumulate coverage stats
        num_fails = sum(1 for item in scorecard if item["rating"] == "FAIL")
        if is_af:
            group_counter["auto_fail"] += 1
        elif num_fails == 0:
            group_counter["excellent"] += 1
        elif num_fails in (1, 2):
            group_counter["1-2"] += 1
        elif num_fails in (3, 4):
            group_counter["3-4"] += 1
        else:
            group_counter["5+"] += 1

        for item in scorecard:
            nm = item["name"]
            if item["rating"] == "FAIL":
                fail_counter[nm] += 1
                total_fail_count += 1
                if nm in hard_cases:
                    hard_fail_count += 1
            else:
                pass_counter[nm] += 1
                total_pass_count += 1
                if nm in hard_cases:
                    hard_pass_count += 1

    # Coverage checks (only enforced on full 50-call run)
    if is_full_run:
        if len(set(customer_names)) != 50:
            errors_by_check["files_and_ids"].append(
                f"Expected 50 unique customer names, found {len(set(customer_names))}"
            )
        expected_groups = {"excellent": 8, "1-2": 15, "3-4": 12, "5+": 11, "auto_fail": 4}
        for g, exp_cnt in expected_groups.items():
            if group_counter[g] != exp_cnt:
                errors_by_check["coverage"].append(
                    f"Group '{g}' has {group_counter[g]} calls, expected {exp_cnt}"
                )
        for nm, min_f in MIN_FAIL_COUNTS.items():
            if fail_counter[nm] < min_f:
                errors_by_check["coverage"].append(
                    f"Criterion '{nm}' has {fail_counter[nm]} FAILs, minimum is {min_f}"
                )
            if pass_counter[nm] < 25:
                errors_by_check["coverage"].append(
                    f"Criterion '{nm}' has {pass_counter[nm]} PASSes, minimum is 25"
                )
        if total_fail_count > 0 and (hard_fail_count / total_fail_count) < 0.40:
            errors_by_check["coverage"].append(
                f"Hard FAIL ratio {hard_fail_count}/{total_fail_count} ({100*hard_fail_count/total_fail_count:.1f}%) < 40%"
            )
        if total_pass_count > 0 and not (0.22 <= (hard_pass_count / total_pass_count) <= 0.40):
            errors_by_check["coverage"].append(
                f"Hard PASS ratio {hard_pass_count}/{total_pass_count} ({100*hard_pass_count/total_pass_count:.1f}%) not ~30%"
            )
        if borderline_count > 5:
            errors_by_check["coverage"].append(
                f"Borderline item count {borderline_count} exceeds maximum of 5"
            )

    # Print Pass/Fail report
    print("=" * 72)
    print(f"AG50 SELF-CHECK REPORT ({len(call_ids)} calls checked)")
    print("=" * 72)
    check_labels = [
        ("files_and_ids", "1. 50 payloads & 50 keys exist, names match, call_id & customer_name valid"),
        ("turn_fields_and_timing", "2. Turn fields valid, time order, no overlaps, turn <= 30s, gaps valid"),
        ("duration_and_length", "3. Call duration in [10:00, 20:00], turn/word counts & duration_sec match"),
        ("rule_items", "4. Four deterministic rule items (7.1) match answer keys exactly"),
        ("auto_fail", "5. Auto-fail triggers only in intended auto-fail calls & named in reason"),
        ("final_score", "6. Final score recomputed from ratings (7.4) matches answer keys"),
        ("scorecard_and_grader_structure", "7. 11 scorecard & grader items in exact order, coaching & evidence valid"),
        ("coverage", "8. Coverage: group counts, FAIL/PASS minimums (9.1), hard cases, borderline <= 5"),
    ]

    all_passed = True
    for key, label in check_labels:
        errs = errors_by_check[key]
        status = "PASS" if not errs else f"FAIL ({len(errs)} error(s))"
        print(f"[{status:16s}] {label}")
        if errs:
            all_passed = False
            for e in errs[:15]:
                print(f"                   -> {e}")
            if len(errs) > 15:
                print(f"                   -> ... and {len(errs) - 15} more errors")

    if durations:
        b1 = sum(1 for d in durations if 600 <= d < 720)
        b2 = sum(1 for d in durations if 720 <= d < 900)
        b3 = sum(1 for d in durations if 900 <= d < 1080)
        b4 = sum(1 for d in durations if 1080 <= d <= 1200)
        print("-" * 72)
        print(f"Length distribution: 10-12m={b1}, 12-15m={b2}, 15-18m={b3}, 18-20m={b4} (total={len(durations)})")
        print(f"Group distribution : {dict(group_counter)}")
        if total_fail_count > 0 and total_pass_count > 0:
            print(
                f"Hard cases         : FAIL={hard_fail_count}/{total_fail_count} ({100*hard_fail_count/total_fail_count:.1f}%), "
                f"PASS={hard_pass_count}/{total_pass_count} ({100*hard_pass_count/total_pass_count:.1f}%), "
                f"Borderline={borderline_count}"
            )
        print("-" * 72)
        print("Per-criterion FAIL / PASS counts:")
        for _, nm, _ in EXPECTED_SCORECARD_SPEC:
            print(
                f"  {nm:45s}: FAIL={fail_counter[nm]:2d} (min {MIN_FAIL_COUNTS[nm]:2d}) | PASS={pass_counter[nm]:2d} (min 25)"
            )
    print("=" * 72)
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
