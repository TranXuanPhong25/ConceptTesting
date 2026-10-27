---
name: v83-reka-fullquarter
description: Running fresh full28/113 HumanEval, two actual arms combined vs concept-hybrid, K1, Reka24k cap; paired prefix currently1
metadata:
  type: project
---

2026-10-27 (Codex): user repeats request for full28-task/two-arm/K1 benchmark after
v81/v82 partials. V83 is fresh output for all28 fixed cohort tasks; no v81/v82 model
responses mixed. Reka only, reasoningenabled, max output24,000 total, no seed,
text response. Cap$3.45291084 after oldv81/v82 known bills+unresolved reservations
$.74708916; planning$3.1023104. Static max-input envelope can exceed cap by$.1859,
so provider retries/corrections may force partial prefix. User's goal remains full28;
do not claim completion early.

Independent reviewPASS, all161source hashes/PREPARED/endpoint/prepared hashes
verified; Cohort same fixed random28 (seed20261026), only arms
`concept-hybrid` and `concept-hybrid-ft`, K1. Run started 2026-10-27T07:52UTC,
PID/root/protocol in [RUN_V83](../trickcatcher_linefacts/analysis/v83_reka_fullquarter/RUN_V83.json).
At latest checkpoint task3 pair completed after11 physical calls; $.03347422 known
and$.01429360 reserved; one returned arm hit output length. No score/efficacy
result yet. See STATUS_V83.json; if terminal, watcher records CPU ref/o0/full scores.

**Why:** user explicitly directs full benchmark.
**How to apply:** inspect run PID and STATUS_V83 before action; no duplicate.
Max output cap is24k for both arms. Run through the fixed cohort while within cap;
retry only preregistered explicit shared-pool429. Incomplete stream/accounting stops;
partial output receives no efficacy conclusion. No hidden paid judges.
