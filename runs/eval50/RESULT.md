# Eval50: 50 calls graded by Claude, run through three engines (2026-10-17)

Key: `data/eval50/` (written and graded by Claude before any engine ran; not human-reviewed). Full tables: generate them with `python Scripts/compare_eval.py Eval50 laya-ft laya-stock ollama --out Docs/EVAL50_RESULTS.md` (the generated file was removed from the repo on 2026-10-22; the last copy is in commit `8a6842b`).

| | Fine-tuned Laya | Stock Laya | Ollama |
|---|---|---|---|
| All 550 items matching the key | **506 (92%)** | 458 (83%) | 448 (81%) |
| The 350 model-judged items matching | **306 (87%)** | 258 (74%) | 251 (72%) |
| Mean absolute final-score error | **6.0** | 12.2 | 9.3 |
| Auto-fail decisions matching | 50/50 | 50/50 | 50/50 |
| Mean time per call (CPU) | 7.8 s | 7.7 s | 122.6 s |

Fine-tuned right and Ollama wrong on 74 items; Ollama right and fine-tuned wrong on 19. Fine-tuned errors: 31 missed FAILs (called PASS) and 13 false FAILs.
Weakest items for the fine-tuned model (balanced accuracy): Ownership 0.68, Active listening 0.70, Rapport 0.83, Resolved 0.82.
22 model-judged items are ones where all three engines agree with each other but contradict the key (mostly Ownership and Active listening FAILs the engines pass): either the key is too strict or these are shared blind spots. Many of them are cases the pipeline's phrase gates (Ownership deflection phrases, Active-listening question similarity) never send to the model. A human should look at these first.
The Ollama copy of the service (`qa-analysis-ollama`) uses an older rule engine, so it also differs on Dead air (47/50); compare engines on the 7 model-judged items.
