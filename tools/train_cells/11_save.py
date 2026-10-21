# CELL 11: save to Drive (temp folder -> verify -> rename), prove the Drive copy loads, print the summary to paste back.
# EXPECT: "copied final-<name>: N files / X MB verified" per variant, "Drive copy loads; max diff ... (must be < 1e-4)",
# then a block starting "=== PASTE THIS BACK TO CLAUDE ===".
from importlib.metadata import version

for n in VARIANTS:
    src = f"{WORK}/ckpt-{n}"
    wait_stable(src, quiet_s=5, ignore=("checkpoint_latest",))
    files, size = copy_verified(src, f"{DRIVE_RUN}/final-{n}", f"final-{n}", ignore=("checkpoint_latest",))
    assert sha256_file(f"{src}/model.safetensors") == sha256_file(f"{DRIVE_RUN}/final-{n}/model.safetensors")
    print(f"copied final-{n}: {files} files / {size / 1e6:.0f} MB verified")

os.makedirs(f"{DRIVE_RUN}/files", exist_ok=True)
for n in VARIANTS:
    for fn in (f"preds_{n}.json", f"train_{n}.log"):
        shutil.copy(f"{WORK}/{fn}", f"{DRIVE_RUN}/files/{fn}")
shutil.copy(f"{WORK}/preds_base.json", f"{DRIVE_RUN}/files/preds_base.json")
for split in ("train_all", "dev_all", "test", "test_long", "test_calls"):
    shutil.copy(f"{DATA_DIR}/{split}.jsonl", f"{DRIVE_RUN}/files/{split}.jsonl")
json.dump(RES, open(f"{DRIVE_RUN}/files/results.json", "w"), indent=1)

manifest = {
    "run_id": RUN_ID, "created": datetime.datetime.now().isoformat(timespec="seconds"), "winner": WINNER,
    "gpu": subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], capture_output=True, text=True).stdout.strip(),
    "versions": {"python": sys.version.split()[0], "torch": version("torch"), "transformers": version("transformers"),
                 "laya": version("laya"), "laya_commit": LAYA_COMMIT},
    "base": {"repo": BASE_REPO, "revision": BASE_REV, "sha256": BASE_SHA256},
    "frozen_checks_sha256": FROZEN["sha256"], "inputs_sha256": FROZEN["inputs_sha256"],
    "qa_analysis_commit": FROZEN["qa_analysis_commit"], "data_sha256": DATA_SHA256,
    "authorship": "All rows written and labelled by Claude; none human-labelled; test not independent.",
    "training": TRAIN_INFO,
    "final_weights_sha256": {n: sha256_file(f"{DRIVE_RUN}/final-{n}/model.safetensors") for n in VARIANTS},
}
json.dump(manifest, open(f"{DRIVE_RUN}/manifest.json", "w"), indent=2)
os.makedirs(f"{DRIVE}/runs/{RUN_ID}", exist_ok=True)
shutil.copy(f"{DRIVE_RUN}/manifest.json", f"{DRIVE}/runs/{RUN_ID}/manifest.json")
shutil.copy(f"{DRIVE_RUN}/files/results.json", f"{DRIVE}/runs/{RUN_ID}/results.json")

# the Drive copy of the winner must predict what /content predicted
chk = laya.load(f"{DRIVE_RUN}/final-{WINNER}")
sample = DEV[:40]
P = predict_rows(chk, sample)
del chk
torch.cuda.empty_cache()
dmax = max(abs(P[k] - PRED[WINNER]["dev"][k]) for k in P)
print(f"Drive copy loads; max diff vs /content on 40 dev rows: {dmax:.6f}")
assert dmax < 1e-4, "Drive copy predicts differently: stop and tell Claude"

# compact summary
lines = [f"=== PASTE THIS BACK TO CLAUDE ===", f"run {RUN_ID} | winner {WINNER} | gpu {manifest['gpu']}",
         "rows: AI-written and AI-labelled (Claude stage-3 rows; Antigravity AG-T rows if present), nothing human-labelled. test = Claude-written, unseen industries/personas, not independent."]
for n in VARIANTS:
    lines.append(f"[{n}] wall {TRAIN_INFO[n]['wall_s']}s | losses: " + " ".join(l.split("mean loss")[-1].strip().split()[0] for l in TRAIN_INFO[n]["losses"]))
for c in TRAINED + REGRESSION:
    b = RES["base"]["checks"][c]
    parts = [f"{c:<16} base BA {b['ba_test_frozen_cut']:.2f} AUC {b['auc_test']:.2f}"]
    for n in VARIANTS:
        r = RES[n]["checks"][c]
        if c in TRAINED:
            lo, hi = r["ba_test_tuned_ci"]
            parts.append(f"{n} BA {r['ba_test_tuned']:.2f} [{lo:.2f},{hi:.2f}] AUC {r['auc_test']:.2f} cut {r['tuned_cut']:.2f}")
        else:
            parts.append(f"{n} BA {r['ba_test_frozen_cut']:.2f} AUC {r['auc_test']:.2f}")
    lines.append(" | ".join(parts))
for n in VARIANTS:
    lg = RES[n]["long"]
    lines.append(f"[{n}] LONG test BA/AUC: " + "; ".join(f"{c} {v['ba']:.2f}/{v['auc']:.2f}" for c, v in lg.items()) + " | base: " + "; ".join(f"{c} {v['ba']:.2f}/{v['auc']:.2f}" for c, v in RES["base"]["long"].items()))
    lines.append(f"[{n}] NATURAL calls BA/AUC: " + "; ".join(f"{c} {v['ba']:.2f}/{v['auc']:.2f}" for c, v in RES[n]["nat"].items()) + " | base: " + "; ".join(f"{c} {v['ba']:.2f}/{v['auc']:.2f}" for c, v in RES["base"]["nat"].items()))
    d = RES[n]["replay_dev"]
    lines.append(f"[{n}] ECE {RES[n]['ece_test']:.3f} (base {RES['base']['ece_test']:.3f}) | replay same-verdict {d['verdict_agreement'] * 100:.0f}% mean change {d['mean_abs_diff']:.3f}")
lines.append(f"checkpoints on Drive: MyDrive/laya-finetuning/checkpoints/{RUN_ID}/final-{WINNER} (download this folder)")
SUMMARY = "\n".join(lines)
open(f"{DRIVE}/runs/{RUN_ID}/summary.txt", "w").write(SUMMARY + "\n")
print("\n" + SUMMARY)
