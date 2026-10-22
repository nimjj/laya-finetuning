"""Small shared helpers for analyze.py (kept separate so score.py stays a plain script)."""
import json
from pathlib import Path

import numpy as np

import questions as Q

HERE = Path(__file__).resolve().parent
CRITERIA = ["empathy", "active_listening", "ownership", "rapport", "probing", "resolved", "escalation", "hostility"]

gold = {}
for _c in CRITERIA:
    for _l in open(HERE / "data" / f"{_c}.jsonl", encoding="utf-8"):
        _r = json.loads(_l)
        gold[_r["id"]] = _r

laya = {ck: {json.loads(l)["id"]: json.loads(l) for l in open(HERE / "results" / f"laya_{ck}.jsonl", encoding="utf-8")}
        for ck in ("english", "multilingual")}


def ids_for(c, split=None):
    return sorted(i for i, g in gold.items() if g["criterion"] == c and (split is None or g["split"] == split))


def bal_acc(y, pred):
    y, pred = np.asarray(y), np.asarray(pred)
    return float(np.mean([(pred[y == 1] == 1).mean(), (pred[y == 0] == 0).mean()]))


def auroc(y, s):
    y, s = np.asarray(y), np.asarray(s)
    s1, s0 = s[y == 1], s[y == 0]
    if len(s1) == 0 or len(s0) == 0:
        return float("nan")
    return float(((s1[:, None] > s0[None, :]).sum() + 0.5 * (s1[:, None] == s0[None, :]).sum()) / (len(s1) * len(s0)))


def tune(y, s):
    u = np.unique(s)
    cands = list((u[:-1] + u[1:]) / 2) + [0.5, 0.0, 1.0 + 1e-9]
    return float(max(cands, key=lambda t: (bal_acc(y, (s >= t).astype(int)), -abs(t - 0.5))))


def best_form_by_dev(ck, c):
    dev = ids_for(c, "dev")
    y = np.array([1 if gold[i]["label"] == "PASS" else 0 for i in dev])
    best = None
    for v in Q.VARIANTS:
        s = np.array([Q.p_pass(c, laya[ck][i]["p_yes"][v]) for i in dev])
        ba = bal_acc(y, (s >= tune(y, s)).astype(int))
        allids = ids_for(c)
        auc_all = auroc(np.array([1 if gold[i]["label"] == "PASS" else 0 for i in allids]),
                        np.array([Q.p_pass(c, laya[ck][i]["p_yes"][v]) for i in allids]))
        if best is None or (ba, auc_all) > best[0]:
            best = ((ba, auc_all), v)
    return best[1]
