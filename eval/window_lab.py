"""Window lab: compare what Laya is shown today with the flow-v2 windows (src/services/laya_windows.py).

Two steps, so the slow one (the model) runs once per checkpoint:

  1. Score the NEW windows with a checkpoint (stock when LAYA_CHECKPOINT is unset):
         set LAYA_CHECKPOINT=<folder>      (fine-tuned)   or leave it unset (stock)
         python laya-finetuning/eval/window_lab.py score "laya-finetuning/inputs/Test (results)/Laya probes/window_lab_laya-ft.json" --suite laya-finetuning/inputs/AG50
  2. Report old vs new (coverage of the keyed evidence, AUC, balanced accuracy, passes per call):
         python laya-finetuning/eval/window_lab.py report --suite AG50 --ft "laya-finetuning/inputs/Test (results)/Laya probes/window_lab_laya-ft.json" \
                --stock "laya-finetuning/inputs/Test (results)/Laya probes/window_lab_laya-stock.json" --out Docs/FLOW_V2_LAB.md

The OLD windows are not rescored: their probabilities come from the probe files made by laya-finetuning/eval/probe_laya.py.
Answer keys: inputs/<suite>/expected/expected_<call>.json (rating plus timestamped evidence per item).
Keys are AI-written (Antigravity), not human-reviewed. AG50 is a development set: choose variants on the odd-numbered
calls, confirm on the even-numbered ones, and never call the numbers a final result.
"""
import argparse
import glob
import json
import math
import os
import re
import sys

import numpy as np

import _roots  # noqa: E402  (finds the QA app root; see _roots.py)
ROOT = _roots.QA_ROOT
sys.path.insert(0, ROOT)

TS = re.compile(r"\[(\d{1,2}):(\d{2})\]")
ACK = re.compile(r"\b(sorry|apolog\w*|understand|frustrat\w*|annoy\w*|worr\w*|stress\w*|appreciate|that must|that sounds|"
                 r"i'd be|i would be|hate that|awful|terrible|inconvenien\w*|upsetting|disappoint\w*|feel for you|can imagine|"
                 r"not good enough|unacceptable|no fun|nightmare|ridiculous|i get it|fair enough|completely get)\b", re.I)
KEY_NAME = {"empathy": "Empathy & Acknowledgment Statement", "paraphrasing": "Paraphrasing",
            "ownership": "Took ownership of the problem", "resolved": "Confirmed the issue is resolved"}
PROBE_LABEL = {"empathy": "verify_empathy", "paraphrasing": "verify_paraphrasing", "ownership": "verify_ownership",
               "resolved": "batch_end"}


def secs(text):
    return [int(m) * 60 + int(s) for m, s in TS.findall(text)]


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def suite_calls(suite):
    return sorted(os.path.basename(p)[:-5] for p in glob.glob(os.path.join(ROOT, suite, "*.json")))


# ---------------------------------------------------------------- windows
def build_windows(payload):
    """{check: {variant: [window texts] | None}} for the new windows, plus the call's parsed pieces."""
    from src.services import laya_windows as W
    from src.services.laya_inputs import build_laya_inputs, parse_transcript
    turns, times, _, _, _, _, sent = parse_transcript(payload["transcript"], payload.get("customer_name"))
    inp = build_laya_inputs(payload["transcript"], payload.get("customer_name"))
    para_new = W.paraphrase_window(turns, times)
    para_gate = None if para_new is None else inp.paraphrasing          # cue gate, old window text
    own = W.ownership_candidates(turns)
    v = {
        "empathy": {"first6": W.empathy_windows(turns, sent, 6, second=False),
                    "first4": W.empathy_windows(turns, sent, 4, second=False),
                    "two6": W.empathy_windows(turns, sent, 6, second=True)},
        "ownership": {"v2": [own] if own else []},
        "paraphrasing": {"cue_oldwin": None if para_gate is None else [para_gate],
                         "cue_newwin": None if para_new is None else [para_new]},
        "resolved": {"tail300": [W.resolved_tail(turns, times, 300)], "tail180": [W.resolved_tail(turns, times, 180)],
                     "last14": ["\n".join(f"{s}: {t}" for s, t in turns[-14:])]},
    }
    return v, turns, times, sent, inp


def cmd_score(args):
    from src.services import dynamic_evaluator as de
    from src.services.laya_adapter import predict_yes
    out = {"checkpoint": os.getenv("LAYA_CHECKPOINT") or "stock", "calls": {}}
    cache = {}

    def p_pass(check, text):
        key = (check, text)
        if key not in cache:
            c = de.LAYA_CHECKS[check]
            cache[key] = float(de._p_pass(c, predict_yes(text, {"q": c["question"]}, label=f"lab_{check}")["q"]))
        return cache[key]

    for cid in suite_calls(args.suite):
        payload = load(os.path.join(ROOT, args.suite, f"{cid}.json"))
        v, turns, times, sent, inp = build_windows(payload)
        rec = {}
        for check, variants in v.items():
            rec[check] = {}
            for name, wins in variants.items():
                if wins is None:
                    rec[check][name] = {"windows": None, "p_pass": None}
                else:
                    rec[check][name] = {"windows": wins, "p_pass": [p_pass(check, w) for w in wins if w.strip()]}
        out["calls"][cid] = rec
        print(cid, flush=True)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    out["cutoffs"] = {k: de.LAYA_CHECKS[k]["pass_threshold"] for k in KEY_NAME}
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print("saved", args.out)


# ---------------------------------------------------------------- report
def old_p_pass(probe, cid, check):
    """Probability the OLD window gave (lowest across snippets for Empathy); None when the model was not asked."""
    for c in probe["calls"]:
        if c["call"][:-5] != cid:
            continue
        vals = []
        th = probe["thresholds"][check]
        for e in c["laya"]:
            if e["label"] == PROBE_LABEL[check] and e["p_yes"]:
                p = next(iter(e["p_yes"].values()))
                vals.append(p if th["yes_means"] == "PASS" else 1 - p)
        return (min(vals) if vals else None), len(vals)
    return None, 0


def aggregate(check, p_list):
    """Existence checks pass if ANY window passes (max); a violation check uses its single window."""
    if check == "empathy":
        return max(p_list) if p_list else 1.0
    if check == "paraphrasing":
        return p_list[0] if p_list else 0.0                  # no cue -> FAIL without asking the model
    if check == "ownership":
        return p_list[0] if p_list else 1.0                  # no candidate -> PASS
    return p_list[0]


def ba(y, pred_fail):
    tp, fn = int((y & pred_fail).sum()), int((y & ~pred_fail).sum())
    fp, tn = int((~y & pred_fail).sum()), int((~y & ~pred_fail).sum())
    tpr = tp / (tp + fn) if tp + fn else float("nan")
    tnr = tn / (tn + fp) if tn + fp else float("nan")
    return 0.5 * (tpr + tnr), (tp, fn, fp, tn)


def best_cut(y, p):
    best = (-1, 0.5)
    for t in np.unique(np.concatenate([[0.0], p, [1.01]])):
        v, _ = ba(y, p < t)
        if not math.isnan(v) and v > best[0]:
            best = (v, float(t))
    return best[1]


def metrics(y, p, cutoff, odd):
    from sklearn.metrics import roc_auc_score
    auc = float(roc_auc_score(y, 1 - p)) if 0 < y.sum() < len(y) else float("nan")
    b, cm = ba(y, p < cutoff)
    # tune the cutoff on one half, test on the other
    cv = []
    for tr, te in ((odd, ~odd), (~odd, odd)):
        t = best_cut(y[tr], p[tr])
        v, _ = ba(y[te], p[te] < t)
        if not math.isnan(v):
            cv.append(v)
    b_odd, _ = ba(y[odd], p[odd] < cutoff)
    b_even, _ = ba(y[~odd], p[~odd] < cutoff)
    return {"auc": auc, "ba": b, "cm": cm, "ba_odd": b_odd, "ba_even": b_even, "cv": float(np.mean(cv)) if cv else float("nan")}


def evidence_turn_text(turns, ts, speaker):
    cands = [(abs(t["start_time_sec"] - ts), t["text"]) for t in turns if t["speaker"] == speaker]
    return min(cands)[1] if cands else ""


def cmd_report(args):
    suite = args.suite
    calls = suite_calls(os.path.relpath(_roots.suite_dir(suite), ROOT))
    keys, payloads = {}, {}
    for c in calls:
        e = load(os.path.join(_roots.suite_dir(suite), "expected", f"expected_{c}.json"))
        keys[c] = {i["name"]: (i["rating"], i.get("evidence", "")) for i in e["grader"]["items"]}
        payloads[c] = load(os.path.join(_roots.suite_dir(suite), f"{c}.json"))
    models = {"fine-tuned": (load(os.path.join(ROOT, args.ft)), load(os.path.join(ROOT, args.ft_probe))),
              "stock": (load(os.path.join(ROOT, args.stock)), load(os.path.join(ROOT, args.stock_probe)))}
    odd = np.array([int(re.sub(r"\D", "", c)) % 2 == 1 for c in calls])
    L = [f"# Flow v2 window lab on {suite}", "",
         "Old windows: probabilities from the probe files. New windows: scored by `laya-finetuning/eval/window_lab.py`. Key = Antigravity, not human-reviewed. "
         "AG50 is a development set, so every number below is for choosing variants, not a final result.", ""]
    for check in KEY_NAME:
        full = KEY_NAME[check]
        y = np.array([keys[c][full][0] == "FAIL" for c in calls])
        L += [f"## {check.capitalize()}", ""]
        # coverage of keyed evidence by the new windows (model independent)
        cov = {}
        ft_calls = models["fine-tuned"][0]["calls"]
        variants = list(next(iter(ft_calls.values()))[check].keys())
        for vname in variants:
            n = k = 0
            wcount = []
            for c in calls:
                r, ev = keys[c][full]
                rec = ft_calls[c][check][vname]
                wins = rec["windows"]
                wcount.append(0 if not wins else len(wins))
                s = secs(ev)
                if not s:
                    continue
                text = "\n".join(wins) if wins else ""
                if check == "resolved" and r == "PASS":
                    n += 1
                    conf = evidence_turn_text(payloads[c]["transcript"], max(s), "Customer")
                    k += conf[:40] in text
                elif check == "paraphrasing" and r == "PASS":
                    n += 1
                    k += evidence_turn_text(payloads[c]["transcript"], min(s), "Agent")[:40] in text
                elif check == "ownership" and r == "FAIL":
                    n += 1
                    k += evidence_turn_text(payloads[c]["transcript"], s[0], "Agent")[:40] in text
                elif check == "empathy" and r == "PASS":
                    T = payloads[c]["transcript"]
                    ack = next((x["text"] for x in T if x["speaker"] == "Agent" and ACK.search(x["text"])), "")
                    n += 1
                    k += ack[:40] in text
            cov[vname] = (k, n, float(np.mean(wcount)))
        L += ["| Variant | Keyed evidence inside the window | Windows per call |", "|---|---|---|"]
        for vname, (k, n, w) in cov.items():
            L.append(f"| {vname} | {k}/{n} | {w:.1f} |")
        L.append("")
        for mname, (lab, probe) in models.items():
            cut = lab["cutoffs"][check]
            rows = []
            # old
            po = []
            for c in calls:
                p, _ = old_p_pass(probe, c, check)
                po.append(1.0 if p is None else p)       # no model call = default PASS (Paraphrasing/Empathy/Resolved always ask)
            rows.append(("old (today)", metrics(y, np.array(po), cut, odd)))
            for vname in variants:
                pn = []
                for c in calls:
                    rec = lab["calls"][c][check][vname]
                    pl = rec["p_pass"]
                    pn.append(aggregate(check, pl) if pl is not None else 0.0)
                rows.append((vname, metrics(y, np.array(pn), cut, odd)))
            L += [f"**{mname}** (deployed cutoff {cut:.2f}; faults in key {int(y.sum())} of {len(y)})", "",
                  "| Window | AUC | Balanced accuracy | TP/FN/FP/TN | BA odd calls | BA even calls | BA with cutoff tuned on the other half |",
                  "|---|---|---|---|---|---|---|"]
            for name, m in rows:
                L.append(f"| {name} | {m['auc']:.2f} | {m['ba']:.2f} | {'/'.join(map(str, m['cm']))} | {m['ba_odd']:.2f} | {m['ba_even']:.2f} | {m['cv']:.2f} |")
            L.append("")
    text = "\n".join(L) + "\n"
    if args.out:
        with open(os.path.join(ROOT, args.out), "w", encoding="utf-8") as f:
            f.write(text)
    sys.stdout.reconfigure(encoding="utf-8")
    print(text)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("score")
    s.add_argument("out")
    s.add_argument("--suite", default="laya-finetuning/inputs/AG50")
    r = sub.add_parser("report")
    r.add_argument("--suite", default="AG50")
    r.add_argument("--ft", required=True)
    r.add_argument("--stock", required=True)
    r.add_argument("--ft-probe", default="laya-finetuning/inputs/Test (results)/Laya probes/probe_AG50_laya-ft.json")
    r.add_argument("--stock-probe", default="laya-finetuning/inputs/Test (results)/Laya probes/probe_AG50_laya-stock.json")
    r.add_argument("--out")
    a = ap.parse_args()
    if a.cmd == "score":
        cmd_score(a)
    else:
        cmd_report(a)


if __name__ == "__main__":
    main()
