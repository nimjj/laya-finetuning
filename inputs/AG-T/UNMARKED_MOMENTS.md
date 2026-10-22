# Unmarked moments in AG-T (to label)

The grading app opens a window at each moment below, but the call's `grader.markers` say nothing about it, so it cannot be used
for training. For **each** moment add exactly **one** marker to that call's key (`inputs/AG-T/expected/expected_agt_NNN.json`).
Turn numbers are 0-based positions in the `transcript` array. Do not change any dialogue.

- **Customer turn N (upset-looking moment)**: an `empathy` marker with `"customer_turn": N` exactly:
  - `no_outburst` if the line is not a real outburst (relief, a factual status report, mild annoyance that needs no acknowledgement);
  - `handled` (with `agent_turn` 1 to 4 turns later) if it is a real outburst the agent recognises in time;
  - `unhandled` if it is a real outburst with no recognition within 4 turns. Then Empathy must be FAIL: update the rating, coaching,
    grader item, evidence and final score.
- **Agent turn N (possible re-ask)**: an `active_listening` marker with `"agent_turn": N` and the `premise_turn` (the Customer turn that
  gave the information): `repeat` if it asks again for information already given clearly, else `harmless_recheck`.

| Call | Moments |
|---|---|
| agt_001 | customer turn 41 (upset-looking moment) |
| agt_002 | customer turn 19 (upset-looking moment); customer turn 45 (upset-looking moment) |
| agt_004 | customer turn 31 (upset-looking moment); customer turn 60 (upset-looking moment) |
| agt_005 | customer turn 1 (upset-looking moment) |
| agt_006 | customer turn 1 (upset-looking moment) |
| agt_007 | customer turn 1 (upset-looking moment) |
| agt_008 | customer turn 1 (upset-looking moment) |
| agt_009 | customer turn 13 (upset-looking moment); customer turn 37 (upset-looking moment) |
| agt_011 | customer turn 3 (upset-looking moment) |
| agt_012 | agent turn 30 (possible re-ask); agent turn 30 (possible re-ask) |
| agt_014 | customer turn 15 (upset-looking moment); agent turn 36 (possible re-ask) |
| agt_015 | customer turn 5 (upset-looking moment) |
| agt_016 | customer turn 1 (upset-looking moment) |
| agt_017 | customer turn 1 (upset-looking moment) |
| agt_018 | customer turn 1 (upset-looking moment) |
| agt_019 | customer turn 1 (upset-looking moment) |
| agt_020 | customer turn 1 (upset-looking moment); agent turn 4 (possible re-ask) |
| agt_021 | customer turn 1 (upset-looking moment) |
| agt_022 | customer turn 1 (upset-looking moment); customer turn 35 (upset-looking moment); agent turn 42 (possible re-ask); agent turn 40 (possible re-ask) |
| agt_025 | customer turn 23 (upset-looking moment) |
| agt_027 | customer turn 32 (upset-looking moment); agent turn 23 (possible re-ask) |
| agt_028 | customer turn 37 (upset-looking moment); agent turn 6 (possible re-ask) |
| agt_029 | customer turn 16 (upset-looking moment) |
| agt_030 | customer turn 45 (upset-looking moment) |
| agt_031 | agent turn 43 (possible re-ask); agent turn 6 (possible re-ask) |
| agt_034 | customer turn 40 (upset-looking moment); agent turn 8 (possible re-ask); agent turn 37 (possible re-ask) |
| agt_037 | agent turn 6 (possible re-ask); agent turn 49 (possible re-ask) |
| agt_038 | agent turn 8 (possible re-ask) |
| agt_039 | agent turn 8 (possible re-ask) |
| agt_042 | agent turn 8 (possible re-ask) |
| agt_044 | agent turn 6 (possible re-ask) |
| agt_045 | customer turn 37 (upset-looking moment); agent turn 40 (possible re-ask) |
| agt_047 | customer turn 47 (upset-looking moment) |
| agt_048 | customer turn 33 (upset-looking moment); agent turn 36 (possible re-ask); agent turn 8 (possible re-ask) |
| agt_050 | agent turn 6 (possible re-ask); agent turn 8 (possible re-ask) |
| agt_051 | customer turn 34 (upset-looking moment); agent turn 6 (possible re-ask) |
| agt_052 | customer turn 50 (upset-looking moment) |
| agt_054 | customer turn 33 (upset-looking moment) |
| agt_055 | customer turn 49 (upset-looking moment) |
| agt_056 | customer turn 1 (upset-looking moment); agent turn 52 (possible re-ask) |
| agt_057 | customer turn 1 (upset-looking moment); agent turn 52 (possible re-ask) |
| agt_058 | customer turn 1 (upset-looking moment) |
| agt_059 | customer turn 1 (upset-looking moment) |
| agt_060 | customer turn 1 (upset-looking moment); agent turn 52 (possible re-ask) |
| agt_061 | customer turn 1 (upset-looking moment); agent turn 50 (possible re-ask) |
| agt_062 | customer turn 1 (upset-looking moment); agent turn 48 (possible re-ask) |
| agt_063 | customer turn 1 (upset-looking moment); agent turn 4 (possible re-ask) |
| agt_064 | customer turn 1 (upset-looking moment) |
| agt_065 | customer turn 1 (upset-looking moment); agent turn 6 (possible re-ask) |
| agt_066 | customer turn 1 (upset-looking moment); agent turn 46 (possible re-ask) |
| agt_067 | customer turn 1 (upset-looking moment); agent turn 6 (possible re-ask) |
| agt_068 | customer turn 1 (upset-looking moment); agent turn 4 (possible re-ask) |
| agt_069 | customer turn 1 (upset-looking moment) |
| agt_070 | customer turn 1 (upset-looking moment) |
| agt_071 | customer turn 1 (upset-looking moment) |
| agt_072 | customer turn 1 (upset-looking moment); customer turn 12 (upset-looking moment); agent turn 4 (possible re-ask) |
| agt_073 | customer turn 1 (upset-looking moment); agent turn 6 (possible re-ask) |
| agt_074 | customer turn 1 (upset-looking moment); customer turn 12 (upset-looking moment) |
| agt_075 | customer turn 1 (upset-looking moment); agent turn 48 (possible re-ask) |
| agt_076 | customer turn 1 (upset-looking moment) |
| agt_077 | customer turn 1 (upset-looking moment); agent turn 4 (possible re-ask) |
| agt_078 | customer turn 1 (upset-looking moment); agent turn 2 (possible re-ask) |
| agt_079 | customer turn 1 (upset-looking moment) |
| agt_080 | customer turn 1 (upset-looking moment); customer turn 12 (upset-looking moment); customer turn 33 (upset-looking moment) |
| agt_081 | customer turn 1 (upset-looking moment); agent turn 6 (possible re-ask) |
| agt_082 | customer turn 1 (upset-looking moment); agent turn 2 (possible re-ask); agent turn 6 (possible re-ask) |
| agt_083 | customer turn 1 (upset-looking moment); customer turn 34 (upset-looking moment); agent turn 4 (possible re-ask) |
| agt_084 | customer turn 1 (upset-looking moment) |
| agt_085 | customer turn 1 (upset-looking moment); agent turn 44 (possible re-ask); agent turn 44 (possible re-ask); agent turn 30 (possible re-ask) |
| agt_086 | customer turn 1 (upset-looking moment); agent turn 2 (possible re-ask) |
| agt_087 | customer turn 1 (upset-looking moment) |
| agt_088 | customer turn 1 (upset-looking moment); customer turn 13 (upset-looking moment); customer turn 35 (upset-looking moment); agent turn 6 (possible re-ask) |
| agt_089 | customer turn 1 (upset-looking moment) |
| agt_090 | customer turn 1 (upset-looking moment); agent turn 50 (possible re-ask) |
| agt_091 | customer turn 1 (upset-looking moment); agent turn 6 (possible re-ask) |
| agt_092 | customer turn 1 (upset-looking moment); customer turn 13 (upset-looking moment); customer turn 37 (upset-looking moment) |
| agt_093 | customer turn 1 (upset-looking moment) |
| agt_094 | customer turn 1 (upset-looking moment) |
| agt_095 | customer turn 1 (upset-looking moment) |
| agt_096 | customer turn 1 (upset-looking moment) |
| agt_097 | customer turn 1 (upset-looking moment) |
| agt_098 | customer turn 1 (upset-looking moment); customer turn 13 (upset-looking moment); customer turn 33 (upset-looking moment) |
| agt_099 | customer turn 1 (upset-looking moment) |
| agt_100 | customer turn 1 (upset-looking moment) |

Total: 91 upset-looking moments, 50 possible re-asks, in 84 calls.
