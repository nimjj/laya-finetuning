# Fine-tuned Laya checkpoints: what each folder is

The weights live in `laya-finetuning/checkpoints/` (git-ignored, never pushed). Each folder has a hash record in `runs/`; check a copy
with `python tools/checkpoint_manifest.py verify <folder> --manifest <record>`. To serve one, set
`LAYA_CHECKPOINT=laya-finetuning/checkpoints/<folder>` in `.env` (and `LAYA_AL_SOURCE2=1` for ft5/ft6, which were trained with the
Active-listening second source). Every result below is measured against AI-written keys, none human-reviewed.

| Folder | Trained on | Status | Hash record |
|---|---|---|---|
| `final-softce-3` | Stage 3: Claude-written rows only (17 Oct). Flow v2, no Active-listening second source | **Current reference ("old model").** Sealed exam AG-B+AG-B2: 317/434 judged items, score error 9.8 | `runs/ft3-stage3/final-softce-3.manifest.json` |
| `ft4-20261021-1331/final-softce`, `final-softce_ag3` | Stage 3 + AG-T **with the author's filler padding** | **Do not use.** Trained on contaminated data; kept only as a record | `runs/ft4-ag/` |
| `ft5-20261021-1621/final-softce` | Stage 3 + clean AG-T (padding removed) | Tested. Sealed exam: 323/434, score error 11.9. Rapport much better, Empathy and Probing worse | `runs/ft5-ag/`, result `runs/ft5-ag/RESULT.md` |
| `ft5-20261021-1621/final-softce_ag3` | Same, AG-T rows x3 | Not chosen (lost to `softce` on development data) | `runs/ft5-ag/` |
| `ft6-20261022-0453/final-softce` | Stage 3 + AG-T with all moments labelled, Probing rows, Empathy length-balanced | Tested on AG-C: 272/350 (old 273, ft5 276), score error 10.8 (best), fewest Empathy false fails; not significantly different. Result `runs/ft6/RESULT.md` | `runs/ft6/` |
| `ft6-20261022-0453/final-softce_ag2` | Same, AG-T rows x2 | Not chosen (lost on development data, 670 vs 704 of 882) | `runs/ft6/` |

Round 8 (AG-C): old, ft5 and ft6 are statistically indistinguishable (77.7% to 78.9% of judged items). Production choice: see the owner's decision in Docs/LAYA_TEST_LOG.md.
