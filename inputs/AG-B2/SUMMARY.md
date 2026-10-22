# Summary of AG-B2 Sealed Test Set (12 Calls)

This test set was authored and verified independently for S-Net customer support QA analysis. All 12 calls are realistic, unpadded conversations lasting between 10 and 20 minutes, with noisy, per-turn customer sentiment scores, rigorous rule item verification, expert QA answer keys, and exact `grader.markers`.

---

## 1. Call-by-Call Summary Table

| Call ID | Customer | Agent | Duration | Group | Failed Items | Final Score | Outbursts & Notes | Hard Cases |
|---|---|---|---|---|---|---|---|---|
| `agb2_01` | Tariq | Chloe | 16m 31s (991s) | Long excellent | None (All PASS) | 100.0 | Turn 13 (late handled, +3 turns). DFS radar 5GHz channel scanning; locked to clean channel 40. | Empathy, Hold time, Paraphrasing |
| `agb2_02` | Eleanor | Nathan | 17m 52s (1072s) | Long excellent | None (All PASS) | 100.0 | Turn 13 (handled, +1 turn). Home move fibre booking, 4G emergency mini-hub, and Hub 5 upgrade. STT roughness. | Empathy, Hold time, Paraphrasing |
| `agb2_03` | Marcus | Maya | 15m 40s (940s) | Long excellent | None (All PASS) | 100.0 | Turn 13 (late handled, +3 turns). Heathrow airport emergency roaming bar removal and Worldwide Pass activation. | Empathy, Hold time, Paraphrasing |
| `agb2_04` | Fiona | Oliver | 15m 16s (916s) | Long excellent | None (All PASS) | 100.0 | Turn 11 (handled, +1 turn). 4K TV remote Bluetooth re-pairing, infrared Samsung TV volume programming, HDMI-CEC sync. | Empathy, Hold time, Paraphrasing |
| `agb2_05` | Declan | Darren | 11m 48s (708s) | Short poor | Empathy, Paraphrasing, Active listening, Probing, Confirmed resolved (5 fails) | 45.0 | Turn 9 (unhandled). Direct debit bounce fee & unallocated payment dispute; repeated bank details query. STT roughness. | Empathy, Active listening |
| `agb2_06` | Soraya | Kieran | 11m 42s (702s) | Short poor | Branding, Verified customer, Empathy, Took ownership, Build rapport, Confirmed resolved (6 fails) | 33.3 | Turn 9 (unhandled). Care alarm line static & broadband drop; rude line at turn 34, deflected ownership to Openreach. | Empathy, Rapport, Ownership |
| `agb2_07` | Graham | Hayley | 11m 11s (671s) | Short poor | Hold time / dead air, Personalized, Empathy, Paraphrasing, Probing, Confirmed resolved (6 fails) | 41.7 | Turn 9 (unhandled). Wi-Fi dead zones in Victorian house; 2 dead air gaps (>30s), never says Graham, echo paraphrasing. STT roughness. | Hold time, Personalized, Empathy |
| `agb2_08` | Nadia | Sophie | 17m 22s (1042s) | Several upset moments | Empathy (1 fail) | 88.3 | Turn 11 (handled), Turn 71 (unhandled, last third). Business static IP reverse DNS PTR record & public DNS cache flush. | Empathy, Hold time |
| `agb2_09` | Callum | Jason | 18m 22s (1102s) | Several upset moments | Empathy, Active listening (2 fails) | 81.7 | Turn 11 (handled), Turn 71 (unhandled, last third). Fraudulent SIM swap freeze & PAC revocation; re-asked contact email at turn 51. | Empathy, Active listening, Hold time |
| `agb2_10` | Beatrice | Ryan | 16m 24s (984s) | Several upset moments | Empathy, Paraphrasing, Took ownership (3 fails) | 61.7 | Turn 11 (handled), Turn 67 (unhandled, last third). CPI price rise dispute; ownership deflected to head office retentions. | Empathy, Ownership, Paraphrasing |
| `agb2_11` | Liam | Amber | 17m 32s (1052s) | Several upset moments | Empathy, Confirmed resolved (2 fails) | 78.3 | Turn 13 (unhandled), Turn 69 (handled, last third). Severed FTTP drop cable; Openreach civils booking & priority courier 4G hub. STT roughness. | Empathy, Confirmed resolved, Hold time |
| `agb2_12` | Yasmin | Hannah | 16m 25s (985s) | Several upset moments | Branding, Active listening (2 fails) | 88.3 | Turn 11 (handled), Turn 71 (handled, last third). Legacy email SSL port migration & app-specific passwords; missed closing script. | Empathy, Active listening, Branding |

---

## 2. Coverage and Mix Verification

| Target Metric | Required | Actual in AG-B2 | Status |
|---|---|---|---|
| **Total Calls** | 12 | 12 | PASS |
| **Long Excellent Calls (15+ min, score 100)** | 4 | 4 (`agb2_01`–`agb2_04`) | PASS |
| **Short Poor Calls (10–12 min, 5+ failed items, not auto-fail)** | 3 | 3 (`agb2_05`–`agb2_07`) | PASS |
| **Calls with 2+ Distinct Outbursts** | 5 | 5 (`agb2_08`–`agb2_12`) | PASS |
| **Calls: Handled Outburst followed by Unhandled Outburst** | 3 | 3 (`agb2_08`, `agb2_09`, `agb2_10`) | PASS |
| **Calls: First Outburst Unhandled, Later Handled** | 1 | 1 (`agb2_11`) | PASS |
| **Outbursts in the Last Third of the Call** | ≥ 3 | 5 (`agb2_08`, `agb2_09`, `agb2_10`, `agb2_11`, `agb2_12`) | PASS |
| **Distinct Customer First Names** | 12 | 12 (Tariq, Eleanor, Marcus, Fiona, Declan, Soraya, Graham, Nadia, Callum, Beatrice, Liam, Yasmin) | PASS |
| **Calls with Speech-to-Text Roughness** | ~4 | 4 (`agb2_02`, `agb2_05`, `agb2_07`, `agb2_11`) | PASS |
| **Auto-Fail Calls** | 0 | 0 (No auto-fail words in any Agent lines) | PASS |
| **Borderline Items in Answer Keys** | ≤ 2 | 0 (All items graded with clear-cut confidence) | PASS |

---

## 3. Per-Criterion Fail / Pass Summary

| Criterion | FAIL Count | PASS Count |
|---|---|---|
| Branding and Survey Check | 2 | 10 |
| Hold time and Dead Air | 1 | 11 |
| Verified customer | 1 | 11 |
| Personalized the call/ticket appropriately | 1 | 11 |
| Empathy & Acknowledgment Statement | 7 | 5 |
| Paraphrasing | 3 | 9 |
| Active listening | 3 | 9 |
| Took ownership of the problem | 2 | 10 |
| Build rapport and observed professionalism | 1 | 11 |
| Probing | 2 | 10 |
| Confirmed the issue is resolved | 4 | 8 |

---

## 4. Final Sealing Statement
This test set (`inputs/AG-B2/`) is now completely finalized, validated against the official `Scripts/validate_calls.py` validator with zero errors and zero warnings, and SEALED. No further edits will be made.
