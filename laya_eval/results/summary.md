# Results: Laya out of the box vs Ollama llama3.1 on a synthetic gold set

**Gold labels are synthetic (written by construction) and have not been reviewed by a human.** Treat every number as optimistic. 40 items per criterion, 18 held-out test items (9 PASS / 9 FAIL). Intervals are 95% bootstrap; differences under roughly 10-15 points are noise.

Laya checkpoints scored (complete runs only): english, multilingual.  Ollama items scored: 216/320.

## Per criterion: best Laya form (picked on dev) vs Ollama, on the held-out test half

| Criterion | Ckpt | Form | Laya test bal-acc | Laya test AUROC | Laya all-40 @0.5 | Ollama test bal-acc | Ollama all-40 | Laya minus Ollama (test) | Suggested gate |
|---|---|---|---|---|---|---|---|---|---|
| empathy | english | w1_ab | 0.83 [0.67-1.00] | 0.74 [0.46-1.00] | 0.60 [0.53-0.70] | 1.00 [1.00-1.00] | 1.00 [1.00-1.00] | -0.17 [-0.33 to +0.00] | ITERATE |
| empathy | multilingual | choice | 0.44 [0.22-0.67] | 0.33 [0.11-0.59] | 0.48 [0.40-0.55] | 1.00 [1.00-1.00] | 1.00 [1.00-1.00] | -0.56 [-0.78 to -0.33] | TRAIN |
| active_listening | english | w1 | 0.78 [0.61-0.94] | 0.84 [0.63-1.00] | 0.55 [0.47-0.65] | 0.50 [0.39-0.61] | 0.50 [0.40-0.60] | +0.28 [+0.11 to +0.44] | ADOPT (candidate) |
| active_listening | multilingual | w1_ab | 0.78 [0.61-0.94] | 0.88 [0.70-1.00] | 0.80 [0.68-0.93] | 0.50 [0.39-0.61] | 0.50 [0.40-0.60] | +0.28 [+0.06 to +0.50] | ADOPT (candidate) |
| ownership | english | w1_ab | 0.83 [0.67-0.95] | 0.96 [0.85-1.00] | 0.82 [0.72-0.93] | 0.94 [0.83-1.00] | n/a | -0.11 [-0.28 to +0.06] | ITERATE |
| ownership | multilingual | choice | 0.72 [0.50-0.89] | 0.74 [0.47-0.95] | 0.62 [0.53-0.75] | 0.94 [0.83-1.00] | n/a | -0.22 [-0.44 to +0.00] | ITERATE |
| rapport | english | w1 | 0.83 [0.67-1.00] | 0.78 [0.54-1.00] | 0.53 [0.50-0.57] | 0.56 [0.50-0.67] | n/a | +0.28 [+0.06 to +0.44] | ADOPT (candidate) |
| rapport | multilingual | choice | 0.72 [0.56-0.89] | 0.85 [0.63-1.00] | 0.57 [0.50-0.65] | 0.56 [0.50-0.67] | n/a | +0.17 [+0.00 to +0.39] | ADOPT (candidate) |
| probing | english | w1_ab | 0.83 [0.67-1.00] | 0.93 [0.80-1.00] | 0.72 [0.62-0.82] | 0.56 [0.50-0.67] | n/a | +0.28 [+0.06 to +0.44] | ADOPT (candidate) |
| probing | multilingual | w1_ab | 0.67 [0.50-0.83] | 0.72 [0.44-0.94] | 0.50 [0.40-0.60] | 0.56 [0.50-0.67] | n/a | +0.11 [-0.06 to +0.28] | ADOPT (candidate) |
| resolved | english | w1_ab | 0.83 [0.67-0.94] | 1.00 [1.00-1.00] | 0.50 [0.50-0.50] | 1.00 [1.00-1.00] | n/a | -0.17 [-0.33 to +0.00] | ITERATE |
| resolved | multilingual | w1 | 0.89 [0.72-1.00] | 0.95 [0.83-1.00] | 0.70 [0.60-0.80] | 1.00 [1.00-1.00] | n/a | -0.11 [-0.28 to +0.00] | ITERATE |
| escalation | english | w1 | 0.78 [0.56-0.94] | 0.81 [0.56-0.99] | 0.82 [0.70-0.93] | 0.83 [0.67-0.94] | 0.75 [0.65-0.88] | -0.06 [-0.28 to +0.17] | ITERATE |
| escalation | multilingual | w1 | 0.83 [0.67-1.00] | 0.96 [0.85-1.00] | 0.53 [0.50-0.57] | 0.83 [0.67-0.94] | 0.75 [0.65-0.88] | +0.00 [-0.22 to +0.22] | ADOPT (candidate) |
| hostility | english | w1 | 0.83 [0.67-1.00] | 0.81 [0.57-1.00] | 0.60 [0.47-0.75] | 0.94 [0.83-1.00] | n/a | -0.11 [-0.28 to +0.06] | ITERATE |
| hostility | multilingual | w2 | 0.83 [0.67-1.00] | 0.80 [0.57-0.96] | 0.60 [0.47-0.75] | 0.94 [0.83-1.00] | n/a | -0.11 [-0.28 to +0.06] | ITERATE |

Gate rule (proposed, to be confirmed): ADOPT if Laya test balanced accuracy is within 5 points of Ollama or better; ITERATE if it is at least 0.60 but short of that; TRAIN if below 0.60. With 18 test items the interval on the difference usually spans the 5-point bar, so ADOPT is a candidate to confirm on more data, not a proof.

## Every form, every checkpoint (test half unless stated)

| Criterion | Ckpt | Form | tuned t | dev bal-acc | test bal-acc | test AUROC | all-40 AUROC | all-40 @0.5 | mean p(pass) PASS items | mean p(pass) FAIL items |
|---|---|---|---|---|---|---|---|---|---|---|
| empathy | english | w1 | 0.57 | 0.68 | 0.72 [0.50-0.89] | 0.68 [0.38-0.94] | 0.64 | 0.62 | 0.62 | 0.56 |
| empathy | english | w2 | 0.50 | 0.82 | 0.72 [0.56-0.89] | 0.69 [0.38-0.94] | 0.78 | 0.78 | 0.59 | 0.48 |
| empathy | english | w1_ab | 0.78 | 0.82 | 0.83 [0.67-1.00] | 0.74 [0.46-1.00] | 0.84 | 0.60 | 0.82 | 0.66 |
| empathy | english | choice | 0.89 | 0.73 | 0.61 [0.44-0.78] | 0.83 [0.59-0.99] | 0.80 | 0.68 | 0.81 | 0.61 |
| empathy | multilingual | w1 | 0.37 | 0.59 | 0.44 [0.28-0.61] | 0.35 [0.09-0.63] | 0.47 | 0.50 | 0.23 | 0.25 |
| empathy | multilingual | w2 | 0.35 | 0.64 | 0.33 [0.17-0.50] | 0.27 [0.06-0.53] | 0.36 | 0.47 | 0.21 | 0.27 |
| empathy | multilingual | w1_ab | 0.50 | 0.55 | 0.61 [0.50-0.78] | 0.62 [0.33-0.88] | 0.55 | 0.57 | 0.62 | 0.61 |
| empathy | multilingual | choice | 0.35 | 0.64 | 0.44 [0.22-0.67] | 0.33 [0.11-0.59] | 0.48 | 0.48 | 0.26 | 0.27 |
| active_listening | english | w1 | 0.19 | 0.82 | 0.78 [0.61-0.94] | 0.84 [0.63-1.00] | 0.84 | 0.55 | 0.34 | 0.19 |
| active_listening | english | w2 | 0.44 | 0.77 | 0.72 [0.56-0.89] | 0.93 [0.78-1.00] | 0.84 | 0.77 | 0.61 | 0.43 |
| active_listening | english | w1_ab | 0.29 | 0.64 | 0.78 [0.56-0.94] | 0.84 [0.60-1.00] | 0.70 | 0.47 | 0.31 | 0.27 |
| active_listening | english | choice | 0.15 | 0.68 | 0.83 [0.67-1.00] | 0.86 [0.63-1.00] | 0.76 | 0.62 | 0.41 | 0.25 |
| active_listening | multilingual | w1 | 0.55 | 0.77 | 0.67 [0.44-0.83] | 0.89 [0.70-1.00] | 0.84 | 0.68 | 0.80 | 0.56 |
| active_listening | multilingual | w2 | 0.99 | 0.55 | 0.50 [0.50-0.50] | 0.40 [0.14-0.66] | 0.43 | 0.50 | 1.00 | 1.00 |
| active_listening | multilingual | w1_ab | 0.50 | 0.82 | 0.78 [0.61-0.94] | 0.88 [0.70-1.00] | 0.82 | 0.80 | 0.58 | 0.42 |
| active_listening | multilingual | choice | 0.53 | 0.77 | 0.78 [0.61-0.94] | 0.93 [0.75-1.00] | 0.83 | 0.75 | 0.73 | 0.43 |
| ownership | english | w1 | 0.50 | 0.73 | 0.67 [0.50-0.83] | 0.78 [0.52-0.98] | 0.79 | 0.70 | 0.69 | 0.55 |
| ownership | english | w2 | 0.43 | 0.82 | 0.78 [0.61-0.94] | 0.90 [0.70-1.00] | 0.88 | 0.77 | 0.55 | 0.41 |
| ownership | english | w1_ab | 0.52 | 0.91 | 0.83 [0.67-0.95] | 0.96 [0.85-1.00] | 0.97 | 0.82 | 0.72 | 0.39 |
| ownership | english | choice | 0.55 | 0.77 | 0.72 [0.56-0.89] | 0.86 [0.63-1.00] | 0.81 | 0.70 | 0.76 | 0.50 |
| ownership | multilingual | w1 | 0.67 | 0.73 | 0.61 [0.39-0.83] | 0.65 [0.37-0.91] | 0.69 | 0.57 | 0.78 | 0.67 |
| ownership | multilingual | w2 | 0.65 | 0.50 | 0.56 [0.39-0.72] | 0.64 [0.35-0.89] | 0.51 | 0.50 | 0.37 | 0.35 |
| ownership | multilingual | w1_ab | 0.41 | 0.73 | 0.67 [0.50-0.83] | 0.64 [0.36-0.88] | 0.69 | 0.53 | 0.40 | 0.34 |
| ownership | multilingual | choice | 0.63 | 0.82 | 0.72 [0.50-0.89] | 0.74 [0.47-0.95] | 0.77 | 0.62 | 0.77 | 0.59 |
| rapport | english | w1 | 0.81 | 1.00 | 0.83 [0.67-1.00] | 0.78 [0.54-1.00] | 0.90 | 0.53 | 0.83 | 0.74 |
| rapport | english | w2 | 0.67 | 0.91 | 0.56 [0.33-0.78] | 0.64 [0.35-0.89] | 0.83 | 0.60 | 0.72 | 0.60 |
| rapport | english | w1_ab | 0.64 | 0.86 | 0.89 [0.72-1.00] | 0.91 [0.75-1.00] | 0.82 | 0.70 | 0.73 | 0.56 |
| rapport | english | choice | 0.81 | 0.73 | 0.67 [0.50-0.83] | 0.95 [0.81-1.00] | 0.83 | 0.53 | 0.88 | 0.76 |
| rapport | multilingual | w1 | 0.85 | 0.77 | 0.78 [0.61-0.94] | 0.93 [0.74-1.00] | 0.84 | 0.57 | 0.89 | 0.71 |
| rapport | multilingual | w2 | 0.66 | 0.64 | 0.67 [0.44-0.83] | 0.68 [0.40-0.93] | 0.61 | 0.57 | 0.59 | 0.52 |
| rapport | multilingual | w1_ab | 0.56 | 0.77 | 0.78 [0.61-0.94] | 0.89 [0.67-1.00] | 0.83 | 0.65 | 0.76 | 0.53 |
| rapport | multilingual | choice | 0.93 | 0.82 | 0.72 [0.56-0.89] | 0.85 [0.63-1.00] | 0.81 | 0.57 | 0.95 | 0.77 |
| probing | english | w1 | 0.52 | 0.68 | 0.50 [0.28-0.72] | 0.49 [0.23-0.78] | 0.61 | 0.52 | 0.57 | 0.52 |
| probing | english | w2 | 0.43 | 0.77 | 0.72 [0.50-0.89] | 0.70 [0.42-0.94] | 0.77 | 0.62 | 0.43 | 0.27 |
| probing | english | w1_ab | 0.60 | 0.95 | 0.83 [0.67-1.00] | 0.93 [0.80-1.00] | 0.96 | 0.72 | 0.73 | 0.51 |
| probing | english | choice | 0.46 | 0.68 | 0.72 [0.56-0.89] | 0.69 [0.42-0.91] | 0.72 | 0.60 | 0.59 | 0.47 |
| probing | multilingual | w1 | 0.35 | 0.50 | 0.33 [0.11-0.56] | 0.40 [0.14-0.67] | 0.37 | 0.38 | 0.46 | 0.59 |
| probing | multilingual | w2 | 0.57 | 0.64 | 0.44 [0.22-0.67] | 0.46 [0.20-0.74] | 0.48 | 0.53 | 0.50 | 0.53 |
| probing | multilingual | w1_ab | 0.85 | 0.77 | 0.67 [0.50-0.83] | 0.72 [0.44-0.94] | 0.72 | 0.50 | 0.77 | 0.69 |
| probing | multilingual | choice | 0.86 | 0.59 | 0.50 [0.33-0.61] | 0.58 [0.30-0.85] | 0.52 | 0.50 | 0.61 | 0.63 |
| resolved | english | w1 | 0.62 | 0.86 | 0.78 [0.61-0.94] | 0.99 [0.93-1.00] | 0.96 | 0.60 | 0.78 | 0.58 |
| resolved | english | w2 | 0.86 | 0.91 | 0.89 [0.72-1.00] | 0.95 [0.81-1.00] | 0.95 | 0.57 | 0.88 | 0.63 |
| resolved | english | w1_ab | 0.80 | 0.95 | 0.83 [0.67-0.94] | 1.00 [1.00-1.00] | 0.97 | 0.50 | 0.84 | 0.74 |
| resolved | english | choice | 0.76 | 0.91 | 0.94 [0.83-1.00] | 0.96 [0.85-1.00] | 0.93 | 0.62 | 0.88 | 0.60 |
| resolved | multilingual | w1 | 0.73 | 0.95 | 0.89 [0.72-1.00] | 0.95 [0.83-1.00] | 0.97 | 0.70 | 0.86 | 0.52 |
| resolved | multilingual | w2 | 0.71 | 0.91 | 0.78 [0.61-0.94] | 0.89 [0.70-1.00] | 0.92 | 0.78 | 0.82 | 0.37 |
| resolved | multilingual | w1_ab | 0.67 | 0.82 | 0.83 [0.67-1.00] | 0.88 [0.70-1.00] | 0.88 | 0.75 | 0.77 | 0.52 |
| resolved | multilingual | choice | 0.44 | 0.91 | 0.83 [0.61-1.00] | 0.94 [0.81-1.00] | 0.93 | 0.85 | 0.71 | 0.32 |
| escalation | english | w1 | 0.47 | 0.95 | 0.78 [0.56-0.94] | 0.81 [0.56-0.99] | 0.92 | 0.82 | 0.61 | 0.39 |
| escalation | english | w2 | 0.25 | 0.86 | 0.78 [0.61-0.89] | 0.88 [0.69-1.00] | 0.88 | 0.78 | 0.50 | 0.27 |
| escalation | english | w1_ab | 0.60 | 0.68 | 0.61 [0.44-0.78] | 0.65 [0.38-0.89] | 0.64 | 0.62 | 0.52 | 0.42 |
| escalation | english | choice | 0.50 | 0.64 | 0.50 [0.28-0.72] | 0.53 [0.25-0.80] | 0.58 | 0.57 | 0.57 | 0.49 |
| escalation | multilingual | w1 | 0.09 | 0.77 | 0.83 [0.67-1.00] | 0.96 [0.85-1.00] | 0.82 | 0.53 | 0.21 | 0.10 |
| escalation | multilingual | w2 | 0.06 | 0.77 | 0.78 [0.61-0.94] | 0.94 [0.80-1.00] | 0.81 | 0.53 | 0.22 | 0.11 |
| escalation | multilingual | w1_ab | 0.41 | 0.64 | 0.67 [0.44-0.89] | 0.77 [0.52-0.96] | 0.62 | 0.57 | 0.46 | 0.38 |
| escalation | multilingual | choice | 0.36 | 0.68 | 0.67 [0.44-0.89] | 0.78 [0.52-0.98] | 0.68 | 0.53 | 0.42 | 0.30 |
| hostility | english | w1 | 0.79 | 0.82 | 0.83 [0.67-1.00] | 0.81 [0.57-1.00] | 0.81 | 0.60 | 0.72 | 0.54 |
| hostility | english | w2 | 0.50 | 0.68 | 0.67 [0.44-0.89] | 0.80 [0.52-1.00] | 0.75 | 0.68 | 0.62 | 0.43 |
| hostility | english | w1_ab | 0.32 | 0.77 | 0.61 [0.44-0.78] | 0.85 [0.63-1.00] | 0.80 | 0.70 | 0.65 | 0.42 |
| hostility | english | choice | 0.21 | 0.77 | 0.56 [0.39-0.72] | 0.81 [0.58-1.00] | 0.79 | 0.62 | 0.73 | 0.47 |
| hostility | multilingual | w1 | 0.94 | 0.73 | 0.72 [0.50-0.89] | 0.83 [0.60-0.99] | 0.77 | 0.62 | 0.87 | 0.69 |
| hostility | multilingual | w2 | 0.96 | 0.77 | 0.83 [0.67-1.00] | 0.80 [0.57-0.96] | 0.78 | 0.60 | 0.79 | 0.55 |
| hostility | multilingual | w1_ab | 0.43 | 0.64 | 0.78 [0.56-0.94] | 0.72 [0.44-0.95] | 0.64 | 0.60 | 0.49 | 0.43 |
| hostility | multilingual | choice | 0.85 | 0.77 | 0.67 [0.44-0.83] | 0.77 [0.51-0.95] | 0.74 | 0.62 | 0.83 | 0.66 |

## Macro average over the 8 criteria (best form per criterion, picked on dev)

- **english**: Laya test bal-acc 0.819, test AUROC 0.860, all-40 @0.5 0.644
- **multilingual**: Laya test bal-acc 0.736, test AUROC 0.779, all-40 @0.5 0.600
- **Ollama llama3.1** (8/8 criteria with a complete test half): test bal-acc 0.792

## Operational numbers

- Laya english: mean 1.95s per item for all 4 question forms together (CPU, excludes slowest warm-up call), median input tokens 407, max 617, truncated items 0/320.
- Laya multilingual: mean 0.57s per item for all 4 question forms together (CPU, excludes slowest warm-up call), median input tokens 406, max 580, truncated items 0/320.
- Ollama llama3.1: mean 21.1s per item, errors 0, replies that were neither PASS nor FAIL 0/216.