# v68 results — v57 four-arm protocol with v66 CrossHair evidence (Qwen2.5-Coder-32B, ngrok), 2026-10-25

Scores: `analysis/v68_symbolicgen/out_v68/score.json` (pinned scorer), baseline `out_v57_historical/score.json` (v57 generation_v2,
same writer/plain, empty evidence; descriptive). Mechanism audit: `analysis/v68_symbolicgen/mechanism_evidence.json`.

| arm | tasks confirmed (/6) | confirmed slots | input-discrepancy tasks | FA | invalid | attack rate (valid) |
|---|---|---|---|---|---|---|
| plain (reused v57) | 1 (85) | 2 | 5 | 8 | 7 | .34 |
| concept | 1 (85) | 2 | 2 | 9 | 4 | .16 |
| equal_evidence_raw | 1 (85) | 3 | 5 | 6 | 6 | .33 |
| inputs_only | 0 | 0 | 3 | 2 | 9 | .22 |
| v57 concept (empty evidence) | 1 (85) | 2 | 4 | 9 | 0 | .14 |

**Decision (PREREG_V68): NOT PROMISING** — concept 1 = plain 1 = raw 1 > inputs_only 0. Only case 85 is ever confirmed, by all
arms, from the public-spec route (its constructed inputs were all spec-invalid). Concept framing lowered the attack rate
(.16 vs .34): the model wrote more passing tests around the shown obligations.

Mechanism:
- Constructed evidence is mostly valid but rarely bug-revealing: contract-valid / bug-revealing verified inputs —
  61 10/0, 66 11/0, 124 11 of 35/0, 58 0/0, 131 19/3, 85 0 of 6/0.
- Case 131: two bug-revealing witnesses (`'081107'`, `'067'`) were shown; concept and inputs_only both reused them but wrote the
  displayed **PUT output** as expected (9, 2; reference 11, 3) → input_discrepancy, not confirmed. The alternative's output (10, 4)
  was also wrong: the source edit (`range(n)`→`range(n-1)`) is not the fix, the input revealed the bug incidentally.
- Validity judge vs EvalPlus contract: 61/66/131 all correct (33 TP); 85 all 6 correctly rejected; 124 TP 0, FP 2, FN 3, TN 7.
- Interface: 59 new slots (5 validity — case 58 had no candidates — + 54 arm calls), 60 attempts (one in-flight call charged unknown
  during the endpoint switch, retried once), 0 new errors; 195,001 input + 28,992 output = 223,993 tokens. Reused: 6 writer + 18 plain
  (v57 plain 61 probe1 was `incomplete_completion` historically).

Reading: the constructor fixes v57's input-construction gap, but the bottleneck moves to (a) the source-edit catalogue rarely
matching the real fault and (b) the oracle — the model copies observed PUT output. Consistent with v41/v48 (oracle/selection binds).
