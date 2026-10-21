"""Undo the AG-T author's filler padding, exactly, and write clean copies of the calls.

The author's generator (inputs/AG-T/batch_engine.py, enrich_turns) lengthened 77 of the 100 calls by stripping a turn's final
punctuation and appending one of 10 stock phrases plus ".". That turned questions into statements (the app finds questions by "?")
and put the same phrases into many calls, correlated with the labels. The generator scripts keep each call's original turns as a
literal list (`raw = [...]` inside get_call_NNN()). This tool reads those lists by parsing the scripts (it never runs them),
checks that every turn of the published call is either identical to the original or exactly "original minus final punctuation +
stock phrase + '.'", and only then writes the original text back. Anything that does not line up is reported, never guessed.

    python laya-finetuning/tools/unpad_agt.py            # writes inputs/AG-T-clean/ (calls + copied keys) and a report

Keys, markers, timestamps and sentiment are kept as they are: the author graded the original dialogue, and turn indices are unchanged.

Run once on 2026-10-21: 45 calls restored exactly and copied back into inputs/AG-T; 23 were never padded; 33 (agt_023..agt_055,
padded with repeated turns as well) could not be restored and are being rewritten. The generator scripts were then removed from
the working tree; they are in commit e81c8f1 (`git checkout e81c8f1 -- inputs/AG-T` to re-run this on the original files).
"""
import ast
import glob
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
QA_ROOT = os.path.dirname(os.path.dirname(HERE))
SRC = os.path.join(QA_ROOT, "inputs", "AG-T")
DST = os.path.join(QA_ROOT, "inputs", "AG-T-clean")


def padding_phrases():
    tree = ast.parse(open(os.path.join(SRC, "batch_engine.py"), encoding="utf-8").read())
    return [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)
            and n.value.startswith(" ") and len(n.value) > 25]


def raw_candidates():
    """cid -> list of original turn lists found in the generator scripts (a call may be defined in more than one script)."""
    out = {}
    for path in sorted(glob.glob(os.path.join(SRC, "*.py"))):
        try:
            tree = ast.parse(open(path, encoding="utf-8").read())
        except SyntaxError:
            continue
        for fn in ast.walk(tree):
            m = re.fullmatch(r"get_call_(\d+)", getattr(fn, "name", "") or "")
            if not (isinstance(fn, ast.FunctionDef) and m):
                continue
            for node in ast.walk(fn):
                if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "raw" for t in node.targets):
                    try:
                        raw = ast.literal_eval(node.value)
                    except ValueError:
                        continue
                    out.setdefault(f"agt_{int(m.group(1)):03d}", []).append((os.path.basename(path), raw))
    return out


def aligns(turns, raw, phrases):
    """Original texts if every published turn is the original or original + one stock phrase, else None."""
    if len(turns) != len(raw):
        return None
    texts, padded = [], 0
    for t, r in zip(turns, raw):
        spk, txt = r[0], r[1]
        if t["speaker"] != spk:
            return None
        if t["text"] == txt:
            texts.append(txt)
        elif any(t["text"] == txt.rstrip(".!?") + p + "." for p in phrases):
            texts.append(txt)
            padded += 1
        else:
            return None
    return texts, padded


def main():
    phrases = padding_phrases()
    cands = raw_candidates()
    if os.path.exists(DST):
        shutil.rmtree(DST)
    os.makedirs(os.path.join(DST, "expected"))
    report = {"phrases": phrases, "restored": {}, "unchanged": [], "unresolved": []}
    for path in sorted(glob.glob(os.path.join(SRC, "agt_*.json"))):
        cid = os.path.basename(path)[:-5]
        payload = json.load(open(path, encoding="utf-8"))
        has_pad = any(p.strip() in t["text"] for t in payload["transcript"] for p in phrases)
        fixed = None
        for script, raw in cands.get(cid, []):
            fixed = aligns(payload["transcript"], raw, phrases)
            if fixed:
                break
        if fixed and fixed[1]:
            for t, txt in zip(payload["transcript"], fixed[0]):
                t["text"] = txt
            report["restored"][cid] = {"turns_restored": fixed[1], "from": script}
        elif has_pad:
            report["unresolved"].append(cid)
            continue                                   # padded but not restorable exactly: leave it out of the clean set
        else:
            report["unchanged"].append(cid)
        json.dump(payload, open(os.path.join(DST, f"{cid}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        shutil.copy(os.path.join(SRC, "expected", f"expected_{cid}.json"), os.path.join(DST, "expected", f"expected_{cid}.json"))
    left = sum(p.strip() in t["text"] for f in glob.glob(os.path.join(DST, "agt_*.json"))
               for t in json.load(open(f, encoding="utf-8"))["transcript"] for p in phrases)
    report["padding_left_in_clean_set"] = left
    json.dump(report, open(os.path.join(DST, "UNPAD_REPORT.json"), "w"), indent=1)
    print(f"restored exactly: {len(report['restored'])} calls ({sum(v['turns_restored'] for v in report['restored'].values())} turns); "
          f"unchanged (never padded): {len(report['unchanged'])}; unresolved, left out: {len(report['unresolved'])} {report['unresolved']}; "
          f"padding phrases left in the clean set: {left}")
    sys.exit(0 if left == 0 else 1)


if __name__ == "__main__":
    main()
