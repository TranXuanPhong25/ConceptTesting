# v30_flowcontract — 2026-10-19

- Parent: fresh best-v7 source copy, PARENT.json hashes. Ports: separately hashed v21_flowtools source; no output/cache.
- Design: analysis/v21_failure_audit/CONTRACT_FIX_PLAN.md; two independent read-only reviewers before code.
- Central per-action schemas disclose4-ID/name caps,64-step paths, exact integer types and required/optional fields.
  Prompt disclosure and charged dispatcher use the same contract; tolerant whole-response envelope preserved.
- Structured errors preserve slot/replay charging and bounded corrective linkage; no auto-truncation/splitting/repair.
- Feedback after slot3 retains compact errors when legacy history projection omits detailed records.
- Online transports/inherited generation CLIs disabled; explicit hand-authored offline fixture API retained for integration checks.
- No semantic extraction, hypothesis policy, CFG semantics, oracle/scoring or shared witness changes. No model calls.
- CPU tests/code-review status will be recorded in CPU_VALIDATION.md after checks.

## Copied best-v7 history

- 10f991c (2026-10-13): self-contained copy of the v7 pipeline (B5 preconditions + v4c Hypothesis strategies, v6 code
  facts, spec input-class facts, 7 arms, v4 evaluation, B1/ref/full oracle, optional strict construction).
  Verified: bundles equal, 0 cache misses, report reproduced (EQUIVALENCE.md).
- Status: current best on dev (v8-strict construction: concept-hybrid 61.0 vs plain-hybrid 55.7, per task 29/20 n.s.).
  Base for every new copy. Never edited in place.
