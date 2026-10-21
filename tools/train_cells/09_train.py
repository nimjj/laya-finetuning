# CELL 9: train two variants on train_all (soft-ce and rlcd), 4 epochs each, and score each on dev and test.
# laya-train writes to /content (local disk); a watcher copies checkpoint_latest/ to Drive once it is fully written.
# EXPECT per variant (about 7-10 min, ~1,270 rows x 4 epochs at roughly 14 rows/s): "train items ..., calibration items ...",
# "epoch N/4 mean loss ..." with the loss falling, "Training complete!", watcher lines, then "exit code 0".
# A RuntimeWarning about calibration is fine. If one variant fails the other still runs; paste the error.
AG_OVERSAMPLE = {{AG_OVERSAMPLE}}     # 0: the original two loss variants. N >= 2: soft-ce on the rows as they are, and soft-ce with the Antigravity rows repeated N times
SOFT = ["--loss", "soft-ce", "--label-smoothing", "0.05"]
if AG_OVERSAMPLE:
    RUNS = [("softce", SOFT), (f"softce_ag{AG_OVERSAMPLE}", SOFT)]
    _rows = [l.rstrip("\n") + "\n" for l in open(f"{DATA_DIR}/train_all.jsonl", encoding="utf-8") if l.strip()]
    _ag = [l for l in _rows if json.loads(l)["meta"].get("source") == "antigravity-agt"]
    with open(f"{DATA_DIR}/train_all_ag{AG_OVERSAMPLE}.jsonl", "w", encoding="utf-8", newline="\n") as _fh:
        _fh.writelines(_rows + _ag * (AG_OVERSAMPLE - 1))
    DATA_FOR = {"softce": f"{DATA_DIR}/train_all.jsonl", f"softce_ag{AG_OVERSAMPLE}": f"{DATA_DIR}/train_all_ag{AG_OVERSAMPLE}.jsonl"}
    print(f"{len(_ag)} Antigravity rows; the second variant sees {len(_rows) + len(_ag) * (AG_OVERSAMPLE - 1)} rows ({AG_OVERSAMPLE}x Antigravity)")
else:
    RUNS = [("softce", SOFT), ("rlcd", ["--loss", "rlcd"])]
    DATA_FOR = {n: f"{DATA_DIR}/train_all.jsonl" for n, _ in RUNS}
COMMON = ["--epochs", "4", "--micro-batch", "8", "--grad-accum", "2", "--seed", "0", "--max-len", "512", "--head-max-len", "192"]
DRIVE_RUN = f"{DRIVE}/checkpoints/{RUN_ID}"
os.makedirs(DRIVE_RUN, exist_ok=True)

# dry run first: prints how many items laya-train builds and skips (should skip none)
rc, ev = run_logged([sys.executable, "-u", LAUNCHER, "--data", f"{DATA_DIR}/train_all.jsonl", "--base", BASE, "--dry-run",
                     "--max-len", "512", "--head-max-len", "192"], f"{WORK}/dry_run.log")
assert rc == 0, "dry run failed: paste the output above"

TRAIN_INFO = {}
for name, loss_args in RUNS:
    OUT = f"{WORK}/ckpt-{name}"
    shutil.rmtree(OUT, ignore_errors=True)
    cmd = [sys.executable, "-u", LAUNCHER, "--data", DATA_FOR[name], "--base", BASE, "--out", OUT] + loss_args + COMMON
    print(f"\n===== {name}: {' '.join(cmd[3:])}")
    watcher = CkptWatcher(f"{OUT}/checkpoint_latest", f"{DRIVE_RUN}/checkpoint_latest-{name}", quiet_s=30)
    t0 = time.time()
    rc, events = run_logged(cmd, f"{WORK}/train_{name}.log", on_item=lambda it: ((watcher.feed(it) if it else None), watcher.flush()))
    (watcher.finish if rc == 0 else watcher.stop)()
    watcher.thread.join(timeout=300)
    watcher.flush()
    wall = time.time() - t0
    print(f"{name}: exit code {rc} | wall {wall:.0f}s | watcher copies {len(watcher.copies)} | watcher errors {watcher.errors}")
    TRAIN_INFO[name] = {"rc": rc, "wall_s": round(wall), "cmd": " ".join(cmd), "watcher_errors": watcher.errors,
                        "losses": [l for _, l in events if "mean loss" in l]}
    if rc != 0:
        print(f"{name} FAILED: skipping it, the error is in the output above")
        continue
    t1 = time.time()
    agent = laya.load(OUT)
    PRED[name] = {"dev": predict_rows(agent, DEV), "test": predict_rows(agent, TEST), "test_long": predict_rows(agent, TEST_LONG),
                 "test_calls": predict_rows(agent, TEST_CALLS)}
    del agent
    torch.cuda.empty_cache()
    json.dump(PRED[name], open(f"{WORK}/preds_{name}.json", "w"))
    RES[name] = evaluate(DEV, PRED[name]["dev"], TEST, PRED[name]["test"])
    RES[name]["long"] = evaluate_long(TEST_LONG, PRED[name]["test_long"], RES[name])
    RES[name]["nat"] = evaluate_long(TEST_CALLS, PRED[name]["test_calls"], RES[name])
    print(f"{name}: scored in {time.time() - t1:.0f}s | mean dev AUC (trained checks) {RES[name]['mean_auc_dev_trained']:.3f}")
assert any(n in RES for n, _ in RUNS), "no variant trained successfully: paste the errors above"
