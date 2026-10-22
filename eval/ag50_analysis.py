"""Statistics for the AG50 test (50 long calls, answer keys written by Antigravity) -> laya-finetuning/docs/ag50_stats.json.

Run from the repo root after the three engines have run and (optionally) after laya-finetuning/eval/probe_laya.py has been run
on laya-finetuning/inputs/AG50 for the fine-tuned and stock checkpoints:

    python laya-finetuning/eval/ag50_analysis.py        (needs scipy and scikit-learn, which are not in requirements.txt: pip install scipy scikit-learn)

What it computes (all confidence intervals resample whole calls, 5000 times, seed 0):
  - items matching the key per engine, overall and for the 7 model-judged items
  - paired differences between engines with a McNemar exact test on the judged items
  - per-item confusion counts and balanced accuracy (FAIL = positive class)
  - Cohen's kappa against the key, score error and bias, rank correlation of final scores
  - accuracy by call length and by call tier
  - pipeline attribution: for every judged item, how many keyed faults never reached the model
  - if probe files exist: AUC per item (ranking ability without a cutoff) and a cross-validated re-tune of the cutoff
"""
import glob
import json
import math
import os
import re
import sys

import numpy as np
from scipy.stats import binomtest, spearmanr
from sklearn.metrics import roc_auc_score

import _roots  # noqa: E402  (finds the QA app root; see _roots.py)
ROOT = _roots.QA_ROOT
sys.path.insert(0, ROOT)
from src.services.laya_inputs import build_laya_inputs  # noqa: E402

INPUTS = _roots.DATA
RES = os.path.join(INPUTS, "Test (results)")
ENGINES = ["laya-stock", "laya-ft", "laya-ft-v2b", "ollama"]
NICE = {"laya-stock": "Stock Laya", "laya-ft": "Fine-tuned Laya", "laya-ft-v2b": "Fine-tuned Laya + flow v2", "ollama": "Ollama"}
ITEMS = ["Branding and Survey Check", "Hold time and Dead Air", "Verified customer",
         "Personalized the call/ticket appropriately", "Empathy & Acknowledgment Statement", "Paraphrasing",
         "Active listening", "Took ownership of the problem", "Build rapport and observed professionalism",
         "Probing", "Confirmed the issue is resolved"]
SHORT = {"Branding and Survey Check": "Branding", "Hold time and Dead Air": "Dead air", "Verified customer": "Verified",
         "Personalized the call/ticket appropriately": "Personalized", "Empathy & Acknowledgment Statement": "Empathy",
         "Paraphrasing": "Paraphrasing", "Active listening": "Active listening",
         "Took ownership of the problem": "Ownership", "Build rapport and observed professionalism": "Rapport",
         "Probing": "Probing", "Confirmed the issue is resolved": "Resolved"}
JUDGED = ["Empathy & Acknowledgment Statement", "Paraphrasing", "Active listening", "Took ownership of the problem",
          "Build rapport and observed professionalism", "Probing", "Confirmed the issue is resolved"]
B = 5000
rng = np.random.default_rng(0)


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def ratings(doc):
    return {i["name"]: i["rating"] for i in doc["result"]["scorecard"]}


# ---------------------------------------------------------------- data
calls = sorted(os.path.basename(p)[:-5] for p in glob.glob(os.path.join(INPUTS, "AG50", "ag_*.json")))
N = len(calls)
key, kdoc, payload = {}, {}, {}
for c in calls:
    kdoc[c] = load(os.path.join(INPUTS, "AG50", "expected", f"expected_{c}.json"))
    key[c] = ratings(kdoc[c])
    payload[c] = load(os.path.join(INPUTS, "AG50", f"{c}.json"))
got, score, secs, af = {}, {}, {}, {}
for e in ENGINES:
    got[e], score[e], secs[e], af[e] = {}, {}, {}, {}
    for fp in glob.glob(os.path.join(RES, f"AG50 ({e})", "result_*.json")):
        c = re.sub(r"^result_\d{8}_\d{6}_", "", os.path.basename(fp))[:-5]
        d = load(fp)
        got[e][c], score[e][c], secs[e][c] = ratings(d), d["result"]["final_score"], d.get("elapsed_sec")
        af[e][c] = bool(d["result"].get("is_auto_fail"))
    assert len(got[e]) == N, (e, len(got[e]))
key_score = {c: kdoc[c]["result"]["final_score"] for c in calls}
dur = {c: kdoc[c]["grader"].get("duration_sec") for c in calls}
tier = {c: kdoc[c]["grader"].get("tier") for c in calls}

# correct[e][item] -> array over calls of 0/1
correct = {e: {it: np.array([got[e][c][it] == key[c][it] for c in calls], float) for it in ITEMS} for e in ENGINES}


def acc(e, items, idx):
    return float(np.mean([correct[e][it][idx].mean() for it in items]))


def boot_idx():
    return rng.integers(0, N, N)


def ci(vals):
    return [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))]


out = {"n_calls": N, "engines": ENGINES, "nice": NICE, "short": SHORT, "items": ITEMS, "judged": JUDGED}
allidx = np.arange(N)
boots = [boot_idx() for _ in range(B)]

# ---------------------------------------------------------------- headline
head = {}
for e in ENGINES:
    a_all = [acc(e, ITEMS, ix) for ix in boots]
    a_j = [acc(e, JUDGED, ix) for ix in boots]
    errs = np.array([abs(score[e][c] - key_score[c]) for c in calls])
    bias = np.array([score[e][c] - key_score[c] for c in calls])
    mae_b = [float(errs[ix].mean()) for ix in boots]
    rho = spearmanr([score[e][c] for c in calls], [key_score[c] for c in calls]).statistic
    head[e] = {
        "items_all": [int(sum(correct[e][it].sum() for it in ITEMS)), len(ITEMS) * N],
        "acc_all": acc(e, ITEMS, allidx), "acc_all_ci": ci(a_all),
        "items_judged": [int(sum(correct[e][it].sum() for it in JUDGED)), len(JUDGED) * N],
        "acc_judged": acc(e, JUDGED, allidx), "acc_judged_ci": ci(a_j),
        "mae": float(errs.mean()), "mae_ci": ci(mae_b), "bias": float(bias.mean()),
        "spearman": float(rho),
        "sec_per_call": float(np.mean([v for v in secs[e].values() if v is not None])),
        "autofail_ok": int(sum(af[e][c] == bool(kdoc[c]["result"].get("is_auto_fail")) for c in calls)),
    }
out["headline"] = head

# ---------------------------------------------------------------- paired differences (judged items)
pairs = {}
for a, b in (("laya-ft", "ollama"), ("laya-ft", "laya-stock"), ("ollama", "laya-stock"), ("laya-ft-v2b", "laya-ft"), ("laya-ft-v2b", "ollama")):
    d_boot = [acc(a, JUDGED, ix) - acc(b, JUDGED, ix) for ix in boots]
    d_all = [acc(a, ITEMS, ix) - acc(b, ITEMS, ix) for ix in boots]
    only_a = int(sum(((correct[a][it] == 1) & (correct[b][it] == 0)).sum() for it in JUDGED))
    only_b = int(sum(((correct[a][it] == 0) & (correct[b][it] == 1)).sum() for it in JUDGED))
    p = binomtest(only_a, only_a + only_b, 0.5).pvalue if only_a + only_b else 1.0
    pairs[f"{a} vs {b}"] = {
        "diff_judged": acc(a, JUDGED, allidx) - acc(b, JUDGED, allidx), "diff_judged_ci": ci(d_boot),
        "diff_all": acc(a, ITEMS, allidx) - acc(b, ITEMS, allidx), "diff_all_ci": ci(d_all),
        "only_a_right": only_a, "only_b_right": only_b, "mcnemar_p": float(p)}
out["pairs"] = pairs

# ---------------------------------------------------------------- per item
def bal_acc(tp, fn, fp, tn):
    tpr = tp / (tp + fn) if tp + fn else float("nan")
    tnr = tn / (tn + fp) if tn + fp else float("nan")
    return 0.5 * (tpr + tnr)


per_item = {}
for it in ITEMS:
    kfail = np.array([key[c][it] == "FAIL" for c in calls])
    row = {"key_fail": int(kfail.sum())}
    for e in ENGINES:
        gfail = np.array([got[e][c][it] == "FAIL" for c in calls])
        tp, fn = int((kfail & gfail).sum()), int((kfail & ~gfail).sum())
        fp, tn = int((~kfail & gfail).sum()), int((~kfail & ~gfail).sum())
        bs = []
        for ix in boots:
            k, g = kfail[ix], gfail[ix]
            a, b_, c_, d_ = (k & g).sum(), (k & ~g).sum(), (~k & g).sum(), (~k & ~g).sum()
            v = bal_acc(a, b_, c_, d_)
            if not math.isnan(v):
                bs.append(v)
        row[e] = {"tp": tp, "fn": fn, "fp": fp, "tn": tn, "acc": (tp + tn) / N, "ba": bal_acc(tp, fn, fp, tn),
                  "ba_ci": ci(bs)}
    per_item[SHORT[it]] = row
out["per_item"] = per_item

# ---------------------------------------------------------------- kappa on judged items (pooled)
def kappa(e):
    kv = np.array([key[c][it] == "FAIL" for c in calls for it in JUDGED])
    gv = np.array([got[e][c][it] == "FAIL" for c in calls for it in JUDGED])
    po = (kv == gv).mean()
    pe = kv.mean() * gv.mean() + (1 - kv.mean()) * (1 - gv.mean())
    return float((po - pe) / (1 - pe))


out["kappa_judged"] = {e: kappa(e) for e in ENGINES}

# ---------------------------------------------------------------- by length and by tier
bins = [(600, 720, "10-12 min"), (720, 900, "12-15 min"), (900, 1080, "15-18 min"), (1080, 1201, "18-20 min")]
by_len = []
for lo, hi, name in bins:
    ix = np.array([i for i, c in enumerate(calls) if lo <= dur[c] < hi])
    by_len.append({"bucket": name, "n": int(len(ix)), **{e: acc(e, JUDGED, ix) for e in ENGINES}})
out["by_length"] = by_len
by_tier = []
for t in ["excellent", "good", "okay", "poor", "very_poor", "auto_fail"]:
    ix = np.array([i for i, c in enumerate(calls) if tier[c] == t])
    if len(ix):
        by_tier.append({"tier": t, "n": int(len(ix)), "key_mean": float(np.mean([key_score[calls[i]] for i in ix])),
                        **{e: float(np.mean([score[e][calls[i]] for i in ix])) for e in ENGINES}})
out["by_tier"] = by_tier
out["scores"] = [{"call": c, "key": key_score[c], "dur": dur[c], **{e: score[e][c] for e in ENGINES}} for c in calls]

# ---------------------------------------------------------------- pipeline attribution
inputs = {c: build_laya_inputs(payload[c]["transcript"], payload[c]["customer_name"]) for c in calls}
shown_fn = {
    "Empathy": lambda I: len(I.empathy) > 0,
    "Active listening": lambda I: bool(I.active_listening),
    "Ownership": lambda I: bool(I.ownership),
    "Probing": lambda I: I.probing is not None,
    "Paraphrasing": lambda I: True,
    "Rapport": lambda I: len(I.rapport) > 0,
    "Resolved": lambda I: True,
}
funnel = {}
for it in JUDGED:
    s = SHORT[it]
    shown = np.array([shown_fn[s](inputs[c]) for c in calls])
    kfail = np.array([key[c][it] == "FAIL" for c in calls])
    row = {"key_fail": int(kfail.sum()), "never_shown": int((kfail & ~shown).sum()), "shown": int((kfail & shown).sum())}
    for e in ENGINES:
        gfail = np.array([got[e][c][it] == "FAIL" for c in calls])
        row[e] = {"caught": int((kfail & gfail).sum()), "caught_when_shown": int((kfail & shown & gfail).sum()),
                  "missed_when_shown": int((kfail & shown & ~gfail).sum()),
                  "false_alarms": int((~kfail & gfail).sum())}
    funnel[s] = row
out["funnel"] = funnel
tot_words = [sum(len(t.split()) for sp, t in inputs[c].turns) for c in calls]
out["window"] = {
    "call_words_mean": float(np.mean(tot_words)),
    "agent_lines_mean": float(np.mean([sum(1 for sp, t in inputs[c].turns if sp == "Agent") for c in calls])),
    "paraphrase_words_seen_mean": float(np.mean([len(inputs[c].paraphrasing.split()) for c in calls])),
    "resolved_words_seen_mean": float(np.mean([len(inputs[c].resolved.split()) for c in calls])),
    "probing_words_seen_mean": float(np.mean([len((inputs[c].probing or "").split()) for c in calls])),
    "rapport_chunks_mean": float(np.mean([len(inputs[c].rapport) for c in calls])),
    "rapport_chunks_min": int(min(len(inputs[c].rapport) for c in calls)),
    "rapport_chunks_max": int(max(len(inputs[c].rapport) for c in calls)),
}

# ---------------------------------------------------------------- probes: AUC and cross-validated cutoff re-tune
LABEL_ITEM = {}  # filled from the probe's own labels, see below


PROBE_LABEL = {"empathy": "verify_empathy", "paraphrasing": "verify_paraphrasing", "active_listening": "verify_al",
               "ownership": "verify_ownership", "rapport": "verify_rapport", "probing": "verify_probing",
               "resolved": "batch_end"}
LABEL_CHECK = {v: k for k, v in PROBE_LABEL.items()}


def probe_scores(path):
    """{call: {check: lowest P(pass) among the Laya calls for that check}} from a probe_laya.py output.
    A check with no Laya call on a call is missing from the dict (the app then defaults to PASS)."""
    doc = load(path)
    th = doc["thresholds"]
    res = {}
    for cdoc in doc["calls"]:
        c = cdoc["call"][:-5]
        res[c] = {}
        for entry in cdoc["laya"]:
            check = LABEL_CHECK.get(entry["label"])
            if check is None or not entry["p_yes"]:
                continue
            p_yes = next(iter(entry["p_yes"].values()))       # the first question of the call (one per check here)
            p_pass = p_yes if th[check]["yes_means"] == "PASS" else 1 - p_yes
            res[c][check] = min(res[c].get(check, 1.0), p_pass)
    return res, th


QID = {"Empathy": "empathy", "Paraphrasing": "paraphrasing", "Active listening": "active_listening",
       "Ownership": "ownership", "Rapport": "rapport", "Probing": "probing", "Resolved": "resolved"}
probe_out = {}
_arr = {}
for e, fname in (("laya-ft", "probe_AG50_laya-ft.json"), ("laya-stock", "probe_AG50_laya-stock.json")):
    pth = os.path.join(RES, "Laya probes", fname)
    if not os.path.exists(pth):
        continue
    ps, th = probe_scores(pth)
    rows = {}
    for it in JUDGED:
        s, q = SHORT[it], QID[SHORT[it]]
        y = np.array([key[c][it] == "FAIL" for c in calls])
        p_pass = np.array([ps[c].get(q, 1.0) for c in calls])     # no Laya call = default PASS = 1.0
        called = np.array([q in ps[c] for c in calls])
        auc = float(roc_auc_score(y, 1 - p_pass)) if 0 < y.sum() < N else float("nan")
        auc_called = float(roc_auc_score(y[called], 1 - p_pass[called])) if called.sum() > 3 and 0 < y[called].sum() < called.sum() else float("nan")
        cut = th[q]["pass_threshold"]
        dep = p_pass >= cut                                   # deployed cutoff: PASS when P(pass) >= cutoff
        dep_ba = bal_acc(int((y & ~dep).sum()), int((y & dep).sum()), int((~y & ~dep).sum()), int((~y & dep).sum()))

        def best_cut(idx):
            cands = np.unique(np.concatenate([[0.0], p_pass[idx], [1.01]]))
            best = (-1, 0.5)
            for t in cands:
                pred_fail = p_pass[idx] < t
                yy = y[idx]
                v = bal_acc(int((yy & pred_fail).sum()), int((yy & ~pred_fail).sum()),
                            int((~yy & pred_fail).sum()), int((~yy & ~pred_fail).sum()))
                if not math.isnan(v) and v > best[0]:
                    best = (v, float(t))
            return best

        ins_ba, ins_cut = best_cut(allidx)
        cv = []
        for _ in range(200):                                  # repeated 2-fold: tune on one half, score on the other
            perm = rng.permutation(N)
            a_idx, b_idx = perm[: N // 2], perm[N // 2:]
            for tr, te in ((a_idx, b_idx), (b_idx, a_idx)):
                _, t = best_cut(tr)
                pf = p_pass[te] < t
                yy = y[te]
                v = bal_acc(int((yy & pf).sum()), int((yy & ~pf).sum()), int((~yy & pf).sum()), int((~yy & ~pf).sum()))
                if not math.isnan(v):
                    cv.append(v)
        _arr.setdefault(e, {})[s] = (y, p_pass)
        rows[s] = {"auc": auc, "auc_when_called": auc_called, "n_called": int(called.sum()),
                   "deployed_cutoff": cut, "deployed_ba": dep_ba, "insample_best_ba": ins_ba,
                   "insample_best_cutoff": ins_cut, "cv_ba": float(np.mean(cv))}
    probe_out[e] = rows


def _auc_boot(y, p_pass, ixs):
    vals = []
    for ix in ixs:
        yy = y[ix]
        if 0 < yy.sum() < len(yy):
            vals.append(roc_auc_score(yy, 1 - p_pass[ix]))
    return vals


if "laya-ft" in _arr and "laya-stock" in _arr:
    ixs = boots[:2000]
    for s_name in probe_out["laya-ft"]:
        for e in ("laya-ft", "laya-stock"):
            y, pp = _arr[e][s_name]
            probe_out[e][s_name]["auc_ci"] = ci(_auc_boot(y, pp, ixs))
        y, pf = _arr["laya-ft"][s_name]
        _, ps_ = _arr["laya-stock"][s_name]
        d = []
        for ix in ixs:
            yy = y[ix]
            if 0 < yy.sum() < len(yy):
                d.append(roc_auc_score(yy, 1 - pf[ix]) - roc_auc_score(yy, 1 - ps_[ix]))
        probe_out["laya-ft"][s_name]["auc_minus_stock"] = probe_out["laya-ft"][s_name]["auc"] - probe_out["laya-stock"][s_name]["auc"]
        probe_out["laya-ft"][s_name]["auc_minus_stock_ci"] = ci(d)
out["probe"] = probe_out

path = os.path.join(ROOT, "laya-finetuning", "docs", "ag50_stats.json")
with open(path, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1)
print("wrote", path)
for e in ENGINES:
    h = head[e]
    print(f"{NICE[e]:16s} all {h['acc_all']:.3f} {h['acc_all_ci']}  judged {h['acc_judged']:.3f} "
          f"{h['acc_judged_ci']}  MAE {h['mae']:.1f} bias {h['bias']:+.1f} rho {h['spearman']:.2f}")
for k, v in pairs.items():
    print(k, f"judged diff {v['diff_judged']:+.3f} {v['diff_judged_ci']}  McNemar p={v['mcnemar_p']:.3f} "
          f"({v['only_a_right']} vs {v['only_b_right']})")
print("kappa", out["kappa_judged"])
