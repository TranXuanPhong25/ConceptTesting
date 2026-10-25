---
name: v65-evidencegate
description: v63 hypothesis/selection/gate repair implemented;88CPUtests pass;oracle deferred,no model run
metadata:
  type: project
---

2026-10-25 user asks to fix hypothesis, evidence selection and gate; oracle may
wait or reuse ref10 programs. Implemented isolated v65_evidencegate from packaged
v7 plus pinned v63 ports. Read its README/PREREG_V65/RESULTS_ENGINEERING_V65.
88 authored CPU regression tests passed; v7/v63 inventories unchanged. No new
model/endpoint/private scoring, no detection gain claim, no independent online
readiness issued. Separate v64 symbolic branch untouched.

**Why:** v63 admitted implausible hypotheses, omitted its sensitive construction
witness from the prompt, and allowed one sensitive case to unblock the cohort.
**How to apply:** conservative admission + spec-linked alternative rationale;
repeated public-example consistency; sensitive-first exact evidence; every fixed
case must have a non-public sensitive witness in its prepared generator context.
Public consistency/sensitivity never establishes semantic truth. Construction
still capped64candidates/256native/120s including public checks; oracle unchanged.
Ref10 exists in oracle_b01 but its combined worker reads canonical data, so do
not wire it into preparation; a separate public prediction adapter is needed.
Future model run needs fresh prospective review/readiness, not old v63 approvals.

2026-10-25 authorized diagnostic follow-up: v65token preflight blocks case66 by99
 tokens (zero completions). Isolated [[v67-evidencegate-prepare]] uses identical
 decoded writer packet with compact JSON; terminal six-writer gate0/6. Sourcev65
 unchanged. See that memory and analysis/v67_prepare6/RESULTS.md for actual blockers.
