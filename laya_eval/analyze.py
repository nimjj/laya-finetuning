"""Error analysis for the short-snippet Laya runs.

Usage: python laya-finetuning/laya_eval/analyze.py
For each criterion and checkpoint, take the form with the best DEV balanced accuracy (same rule as score.py), then:
  * AUROC on clear vs hard items (all 40; threshold-free)
  * the most confidently wrong items (FAIL scored as passing, PASS scored as failing)
"""
import json
from pathlib import Path

import numpy as np

import questions as Q
import score_lib as S

HERE = Path(__file__).resolve().parent
for ck in ("english", "multilingual"):
    print(f"\n===== {ck} =====")
    print(f"{'criterion':17s} {'form':7s} {'AUROC clear':>11s} {'AUROC hard':>10s}   worst misses (gold label, p_pass, text)")
    for c in S.CRITERIA:
        ids = S.ids_for(c)
        form = S.best_form_by_dev(ck, c)
        s = np.array([Q.p_pass(c, S.laya[ck][i]["p_yes"][form]) for i in ids])
        y = np.array([1 if S.gold[i]["label"] == "PASS" else 0 for i in ids])
        hard = np.array([S.gold[i]["hard"] for i in ids])
        a_clear = S.auroc(y[~hard], s[~hard])
        a_hard = S.auroc(y[hard], s[hard])
        print(f"{c:17s} {form:7s} {a_clear:11.2f} {a_hard:10.2f}")
        # rank-based misses: FAIL items with highest p_pass, PASS items with lowest p_pass
        order_f = [k for k in np.argsort(-s) if y[k] == 0][:2]
        order_p = [k for k in np.argsort(s) if y[k] == 1][:2]
        for k in order_f + order_p:
            g = S.gold[ids[k]]
            txt = g["text"].replace("\n", " | ")[:110]
            print(f"      {'FAIL-scored-high' if y[k]==0 else 'PASS-scored-low ':16s} p_pass={s[k]:.2f} hard={int(g['hard'])}  {txt}")
