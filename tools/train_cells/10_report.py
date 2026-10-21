# CELL 10: compare base vs tuned, pick the better variant on DEV, print the tables.
# EXPECT: WINNER line, then one table per variant with test balanced accuracy (BA) with a 95% interval (resampled by pair),
# AUC, tuned cutoff (from dev) and base BA; then replay drift and calibration error.
# Reading it: BA 0.50 = coin flip, 1.00 = perfect. AUC is cutoff-free (does the model rank PASS above FAIL?).
# Regression checks are only compared with the base model at the production cutoff; they should not drop.
VARIANTS = [n for n, _ in RUNS if n in RES]
WINNER = max(VARIANTS, key=lambda n: RES[n]["mean_auc_dev_trained"])
print("WINNER (best mean dev AUC over the 5 trained checks):", WINNER, {n: round(RES[n]["mean_auc_dev_trained"], 3) for n in VARIANTS})
print("NOTE: train and dev rows are written and labelled by AI: Claude (stage 3) and, if present (source antigravity-agt), Antigravity. The test sets are Claude-written (unseen industries/personas), NOT independent. Nothing is human-labelled.\n")

for n in VARIANTS:
    R, B = RES[n], RES["base"]
    print(f"=== {n}{'  <- winner' if n == WINNER else ''}")
    print(f"{'check':<18}{'n':>4}{'base BA':>9}{'BA':>7}{'95% interval':>16}{'AUC':>7}{'base AUC':>10}{'tuned cut':>11}")
    for c in TRAINED + REGRESSION:
        r, b = R["checks"][c], B["checks"][c]
        if c in TRAINED:
            lo, hi = r["ba_test_tuned_ci"]
            print(f"{c:<18}{r['n_test']:>4}{b['ba_test_frozen_cut']:>9.3f}{r['ba_test_tuned']:>7.3f}  [{lo:.2f}, {hi:.2f}]{r['auc_test']:>9.3f}{b['auc_test']:>10.3f}{r['tuned_cut']:>11.2f}")
        else:
            lo, hi = r["ba_test_frozen_ci"]
            print(f"{c:<18}{r['n_test']:>4}{b['ba_test_frozen_cut']:>9.3f}{r['ba_test_frozen_cut']:>7.3f}  [{lo:.2f}, {hi:.2f}]{r['auc_test']:>9.3f}{b['auc_test']:>10.3f}{'(frozen)':>11}")
    print("long snippets (padded to real-call length), BA at the same cutoff / AUC, base in brackets: " + "; ".join(
        f"{c} {v['ba']:.2f}/{v['auc']:.2f} ({B['long'][c]['ba']:.2f}/{B['long'][c]['auc']:.2f})" for c, v in R["long"].items()))
    print("natural calls (extractor snippets from 8 complete unseen-industry calls; n is small, intervals wide), BA/AUC, base in brackets: " + "; ".join(
        f"{c} {v['ba']:.2f}/{v['auc']:.2f} n={v['n']} ({B['nat'][c]['ba']:.2f}/{B['nat'][c]['auc']:.2f})" for c, v in R["nat"].items()))
    print(f"mean test BA over trained checks: {R['mean_ba_test_trained']:.3f} | ECE test: {R['ece_test']:.3f} (base {B['ece_test']:.3f})")
    d = R["replay_dev"]
    print(f"replay drift on custom-criteria questions (dev, {d['items']} items): mean |change| {d['mean_abs_diff']:.3f}, "
          f"same verdict as base {d['verdict_agreement'] * 100:.0f}%\n")
print("BA for 'base' uses the production cutoff; for trained checks the tuned model uses a cutoff chosen on DEV, so the two columns are not on identical footing.")
