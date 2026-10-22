"""Score Laya (and the Ollama baseline) against the synthetic gold set.

Usage: python laya-finetuning/laya_eval/score.py
Writes laya-finetuning/laya_eval/results/summary.md and prints it.

Method
  * Positive class = verdict PASS. Laya gives P(true); it is converted to p_pass using the criterion polarity.
  * Threshold is tuned on the DEV half only (max balanced accuracy, ties -> closest to 0.5) and reported on the
    held-out TEST half. A fixed 0.5 threshold is also reported on all 40 items.
  * The question variant is picked by DEV balanced accuracy only, never by test results.
  * Bootstrap (1000 resamples, stratified by label, seed 0) gives 95% intervals. With 9 PASS + 9 FAIL per test half
    the intervals are wide; differences under ~10-15 points are not distinguishable from noise.
  * Gold labels are synthetic (by construction) and not human-verified.
"""
import json
from pathlib import Path

import numpy as np

import questions as Q

HERE = Path(__file__).resolve().parent
CRITERIA = ["empathy", "active_listening", "ownership", "rapport", "probing", "resolved", "escalation", "hostility"]
RNG = np.random.default_rng(0)
NBOOT = 1000

gold = {}
for c in CRITERIA:
    for l in open(HERE / "data" / f"{c}.jsonl", encoding="utf-8"):
        r = json.loads(l)
        gold[r["id"]] = r


def load(path):
    p = HERE / "results" / path
    if not p.exists():
        return {}
    return {json.loads(l)["id"]: json.loads(l) for l in open(p, encoding="utf-8")}


laya = {ck: load(f"laya_{ck}.jsonl") for ck in ("english", "multilingual")}
ollama = load("ollama.jsonl")


def bal_acc(y, pred):
    y, pred = np.asarray(y), np.asarray(pred)
    pos, neg = y == 1, y == 0
    tpr = (pred[pos] == 1).mean() if pos.any() else np.nan
    tnr = (pred[neg] == 0).mean() if neg.any() else np.nan
    return float(np.nanmean([tpr, tnr]))


def auroc(y, s):
    y, s = np.asarray(y), np.asarray(s)
    s1, s0 = s[y == 1], s[y == 0]
    if len(s1) == 0 or len(s0) == 0:
        return np.nan
    gt = (s1[:, None] > s0[None, :]).sum() + 0.5 * (s1[:, None] == s0[None, :]).sum()
    return float(gt / (len(s1) * len(s0)))


def tune(y, s):
    u = np.unique(s)
    cands = list(((u[:-1] + u[1:]) / 2)) + [0.5, 0.0, 1.0 + 1e-9]
    best = max(cands, key=lambda t: (bal_acc(y, (s >= t).astype(int)), -abs(t - 0.5)))
    return float(best)


def boot(y, fn, n=NBOOT, **arrs):
    """95% bootstrap interval of fn(y, **arrs), resampling within each label."""
    y = np.asarray(y)
    i1, i0 = np.where(y == 1)[0], np.where(y == 0)[0]
    vals = []
    for _ in range(n):
        idx = np.concatenate([RNG.choice(i1, len(i1)), RNG.choice(i0, len(i0))])
        vals.append(fn(y[idx], **{k: np.asarray(v)[idx] for k, v in arrs.items()}))
    vals = np.array(vals, dtype=float)
    return float(np.nanpercentile(vals, 2.5)), float(np.nanpercentile(vals, 97.5))


def fmt(v, ci=None):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "n/a"
    return f"{v:.2f}" + (f" [{ci[0]:.2f}-{ci[1]:.2f}]" if ci else "")


def rows_for(c, split=None):
    ids = [i for i, g in gold.items() if g["criterion"] == c and (split is None or g["split"] == split)]
    return sorted(ids)


def y_of(ids):
    return np.array([1 if gold[i]["label"] == "PASS" else 0 for i in ids])


def laya_scores(ck, v, c, ids):
    return np.array([Q.p_pass(c, laya[ck][i]["p_yes"][v]) for i in ids])


out = []
P = out.append
P("# Results: Laya out of the box vs Ollama llama3.1 on a synthetic gold set\n")
P("**Gold labels are synthetic (written by construction) and have not been reviewed by a human.** "
  "Treat every number as optimistic. 40 items per criterion, 18 held-out test items (9 PASS / 9 FAIL). "
  "Intervals are 95% bootstrap; differences under roughly 10-15 points are noise.\n")

have_laya = [ck for ck in laya if len(laya[ck]) >= 320]
P(f"Laya checkpoints scored (complete runs only): {', '.join(have_laya) or 'none'}.  "
  f"Ollama items scored: {len(ollama)}/320.\n")

summary_rows = []
full_rows = []
for c in CRITERIA:
    dev, test, allids = rows_for(c, "dev"), rows_for(c, "test"), rows_for(c)
    y_dev, y_test, y_all = y_of(dev), y_of(test), y_of(allids)

    # ----- Ollama -----
    ol = None
    if all(i in ollama for i in test):  # the test half is enough for the comparison; all-40 only if complete
        ov = {i: 1 if ollama[i]["verdict"] == "PASS" else 0 for i in test}
        o_test = np.array([ov[i] for i in test])
        ol = {"test": bal_acc(y_test, o_test), "test_ci": boot(y_test, lambda y, p: bal_acc(y, p), p=o_test),
              "all": None, "all_ci": None, "pred_test": o_test, "pass_rate": float(o_test.mean())}
        if all(i in ollama for i in allids):
            o_all = np.array([1 if ollama[i]["verdict"] == "PASS" else 0 for i in allids])
            ol["all"] = bal_acc(y_all, o_all)
            ol["all_ci"] = boot(y_all, lambda y, p: bal_acc(y, p), p=o_all)

    # ----- Laya variants -----
    for ck in have_laya:
        per_variant = {}
        for v in Q.VARIANTS:
            s_dev, s_test, s_all = (laya_scores(ck, v, c, ids) for ids in (dev, test, allids))
            t = tune(y_dev, s_dev)
            pred_test = (s_test >= t).astype(int)
            d = {"t": t, "dev_ba": bal_acc(y_dev, (s_dev >= t).astype(int)),
                 "test_ba": bal_acc(y_test, pred_test),
                 "test_ba_ci": boot(y_test, lambda y, p: bal_acc(y, p), p=pred_test),
                 "test_auc": auroc(y_test, s_test), "test_auc_ci": boot(y_test, lambda y, s: auroc(y, s), s=s_test),
                 "all_auc": auroc(y_all, s_all), "all_ba05": bal_acc(y_all, (s_all >= 0.5).astype(int)),
                 "all_ba05_ci": boot(y_all, lambda y, p: bal_acc(y, p), p=(s_all >= 0.5).astype(int)),
                 "pred_test": pred_test, "mean_s_pass": float(s_all[y_all == 1].mean()), "mean_s_fail": float(s_all[y_all == 0].mean())}
            per_variant[v] = d
            full_rows.append((c, ck, v, d))
        best_v = max(per_variant, key=lambda v: (per_variant[v]["dev_ba"], per_variant[v]["all_auc"]))
        b = per_variant[best_v]
        gate = None
        if ol:
            diff = b["test_ba"] - ol["test"]
            lo_hi = boot(y_test, lambda y, a, o: bal_acc(y, a) - bal_acc(y, o), a=b["pred_test"], o=ol["pred_test"])
            if diff >= -0.05:
                gate = "ADOPT (candidate)"
            elif b["test_ba"] >= 0.60:
                gate = "ITERATE"
            else:
                gate = "TRAIN"
        summary_rows.append((c, ck, best_v, b, ol, gate, (diff, lo_hi) if ol else None))

P("## Per criterion: best Laya form (picked on dev) vs Ollama, on the held-out test half\n")
P("| Criterion | Ckpt | Form | Laya test bal-acc | Laya test AUROC | Laya all-40 @0.5 | Ollama test bal-acc | Ollama all-40 | Laya minus Ollama (test) | Suggested gate |")
P("|---|---|---|---|---|---|---|---|---|---|")
for c, ck, v, b, ol, gate, dd in summary_rows:
    P(f"| {c} | {ck} | {v} | {fmt(b['test_ba'], b['test_ba_ci'])} | {fmt(b['test_auc'], b['test_auc_ci'])} | {fmt(b['all_ba05'], b['all_ba05_ci'])} | "
      f"{fmt(ol['test'], ol['test_ci']) if ol else 'not run yet'} | {fmt(ol['all'], ol['all_ci']) if ol and ol['all'] is not None else 'n/a'} | "
      f"{(f'{dd[0]:+.2f} [{dd[1][0]:+.2f} to {dd[1][1]:+.2f}]') if dd else 'n/a'} | {gate or 'n/a'} |")

P("\nGate rule (proposed, to be confirmed): ADOPT if Laya test balanced accuracy is within 5 points of Ollama or better; "
  "ITERATE if it is at least 0.60 but short of that; TRAIN if below 0.60. With 18 test items the interval on the difference "
  "usually spans the 5-point bar, so ADOPT is a candidate to confirm on more data, not a proof.\n")

P("## Every form, every checkpoint (test half unless stated)\n")
P("| Criterion | Ckpt | Form | tuned t | dev bal-acc | test bal-acc | test AUROC | all-40 AUROC | all-40 @0.5 | mean p(pass) PASS items | mean p(pass) FAIL items |")
P("|---|---|---|---|---|---|---|---|---|---|---|")
for c, ck, v, d in full_rows:
    P(f"| {c} | {ck} | {v} | {d['t']:.2f} | {d['dev_ba']:.2f} | {fmt(d['test_ba'], d['test_ba_ci'])} | {fmt(d['test_auc'], d['test_auc_ci'])} | "
      f"{d['all_auc']:.2f} | {d['all_ba05']:.2f} | {d['mean_s_pass']:.2f} | {d['mean_s_fail']:.2f} |")

P("\n## Macro average over the 8 criteria (best form per criterion, picked on dev)\n")
for ck in have_laya:
    rs = [r for r in summary_rows if r[1] == ck]
    P(f"- **{ck}**: Laya test bal-acc {np.mean([r[3]['test_ba'] for r in rs]):.3f}, test AUROC {np.nanmean([r[3]['test_auc'] for r in rs]):.3f}, all-40 @0.5 {np.mean([r[3]['all_ba05'] for r in rs]):.3f}")
ols = {r[0]: r[4] for r in summary_rows if r[4]}
if ols:
    P(f"- **Ollama llama3.1** ({len(ols)}/8 criteria with a complete test half): test bal-acc {np.mean([o['test'] for o in ols.values()]):.3f}")

P("\n## Operational numbers\n")
for ck in have_laya:
    lat = [laya[ck][i]["latency_s"] for i in laya[ck]]
    lat_nofirst = sorted(lat)[:-1] if len(lat) > 1 else lat
    trunc = sum(laya[ck][i]["truncated"] for i in laya[ck])
    toks = [laya[ck][i]["input_tokens"] for i in laya[ck] if laya[ck][i]["input_tokens"] is not None]
    P(f"- Laya {ck}: mean {np.mean(lat_nofirst):.2f}s per item for all 4 question forms together (CPU, excludes slowest warm-up call), "
      f"median input tokens {int(np.median(toks))}, max {max(toks)}, truncated items {trunc}/{len(lat)}.")
if ollama:
    P(f"- Ollama llama3.1: mean {np.mean([r['latency_s'] for r in ollama.values()]):.1f}s per item, errors {sum(r['error'] for r in ollama.values())}, "
      f"replies that were neither PASS nor FAIL {sum(r['unparsed'] for r in ollama.values())}/{len(ollama)}.")

text = "\n".join(out)
(HERE / "results" / "summary.md").write_text(text, encoding="utf-8")
print(text)
