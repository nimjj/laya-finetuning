# laya_eval: synthetic gold set for the Laya checks

This is the out-of-the-box benchmark behind the starting `pass_threshold` values in `LAYA_CHECKS` (`src/services/dynamic_evaluator.py`). The results and caveats are in [`RESULTS.md`](RESULTS.md).

The gold set has 8 criteria × 40 short snippets, each with an intended PASS/FAIL. **I wrote the labels; no human has reviewed them.**

For checks on full-length calls, see `laya-finetuning/docs/LAYA_TEST_LOG.md`, `inputs/Main tests` and `inputs/Bulk tests`.

| File | What it does |
|---|---|
| `gold_a.py` … `gold_d.py` | The hand-written snippets per criterion |
| `build_gold.py` | Builds and validates `data/<criterion>.jsonl` through the pipeline's own extractors in `src/services/rule_engine.py` |
| `questions.py` | The question wordings asked of Laya (four forms per criterion) |
| `run_laya.py` | Runs Laya on the gold set → `results/laya_<checkpoint>.jsonl` |
| `run_long.py` | Escalation/Hostility on long padded transcripts → `results/long.jsonl` (stopped early, not scored) |
| `run_ollama.py` | Ollama llama3.1 baseline → `results/ollama.jsonl`; needs a version-10 checkout (`QA_OLLAMA_ROOT`) |
| `score.py`, `score_lib.py`, `analyze.py` | Dev/test-split scoring → `results/summary.md`, error analysis |
| `smoke_test.py` | Checks that Laya loads and answers |

Run from the repo root with the `.venv` active, one model job at a time (see the end of `RESULTS.md`).

`build_gold.py` uses the *current* `rule_engine.py` extractors, so a rebuild after the Round 2 rule changes may produce slightly different items from the committed `data/`.
