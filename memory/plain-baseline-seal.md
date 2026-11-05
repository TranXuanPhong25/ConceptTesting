---
name: plain-baseline-seal
description: User wants fixed plain baseline reused; completed44task compiled run sealed read-only with1375originalfilehashes
metadata:
  type: project
---

2026-11-05/06 user asks whether recent runs skip unchanged plain and requests
locking the baseline. Verified latest smoke/v4/v5diagnostics contain boundary
calls only, no fresh plain calls. Latest plain is in
final/out/boundary_all_plain_bva_compiled_20261105:44tasks,840validplaininputs,
2detectedPUTs (99/124). Do not confuse with original164task baseline.

Sealed that completed run after exclusive .run.lock acquisition. Added SEALED.json;
removed all file/directory write bits. All1375originalfileSHA256s still match.
Receipt tracked candidate:final/data/baselines/plain_compiled_44tasks_20261105.seal.json
contains original file hashes/modes and generation freeze. No source changes,
new generation,model calls,scoring or historicalartifactcontentmutation.

User preference: reuse unchanged plain rather than regenerate it for each BVA
repair. Reuse requires matching task/PUT/spec/prompt/model/budget/sampling;
changed reference/scoring requires frozen-input rescore in separate output.
Existing code does not automatically assemble cross-run plain/BVA comparisons.
Readonly permissions prevent ordinary writes,not ownerchmodoverride. Do not
unseal/resume/overwrite the baseline; preserve shared execution cache separately.

**Why:** avoid unnecessary baseline generation and preserve a stable comparator.
**How to apply:** verify seal before reuse; use only intersecting matched cases.
New development outputs go to fresh directories. No commit requested for seal.
