# v65 evidence gate repair — 2026-10-25

User authorizes repairing hypothesis, selection and gate; oracle may wait. This is
an engineering successor on already seen dev cases, not a new efficacy result.
Prior work: v31/v34 fault templates (18/33 vs plain15; placebo FA gate failed),
v35 fixed-pool ceiling, v63 runnable hypotheses but concept0/6 with provisional
labels. Preserve all previous sources, responses, scoring and vendor code.

Start with the packaged v7 base and pinned v63 ports (PARENT_V65.json). v64 is an
independent symbolic-construction branch and is not edited or claimed complete.

## Changes fixed before validation

1. Writer must state an actual claimed required/observed contrast and explain a
   non-null alternative using the selected source-bound spec clause. Reject exact
   normalized duplicate claims, constant-false/nonboolean predicates, no-op
   replacements, expression `None` placeholders and unsupported module sites.
   Abstention uses JSON null/empty hypotheses. These are necessary checks, never
   semantic proof; differently worded wrong claims can still pass.
2. Before search, replay original and replacement independently on ALL public
   examples using two seeds and two repetitions. Both must match typed public
   expected values. Failure/unknown blocks that hypothesis. This checks public
   consistency only; it is neither a private oracle nor full spec validation.
3. Keep construction budgets at64 candidates,256 native executions,120s; public checks
   count against the native/time budgets. Existing generator probes and final
   audits (at most96native executions per arm) are separate and unchanged. Divide remaining resources across
   remaining hypotheses to avoid first-hypothesis starvation. Unsupported or
   exhausted searches remain explicit failures, not full-program UNSAT.
4. Select at most two distinct realized witnesses per hypothesis, prioritizing
   sensitive witnesses outside public examples, then other sensitive witnesses.
   Concept/raw receive identical evidence; inputs-only gets the identical union.
   Persist selection IDs/hash and dropped counts. No private labels select inputs.
5. Each of the SIX fixed cases must deliver at least one non-public sensitive
   witness from a public-consistent alternative in the exact generator context.
   No aggregate single-case escape hatch. Block ALL arm generation if any case
   fails, preserving denominators and diagnostics. Direct per-case entry also
   enforces this gate. Semantic truth and input validity remain unverified.

## Validation and execution boundary

Authored offline regression tests cover the known failure modes, public regression,
unknown execution, typed outputs, budget accounting, witness ranking, parity and
gate bypass/resume. No generated benchmark outcomes or paid/model requests are
needed for this implementation task. Online entry requires a new
prospective reviewed run identity; --prepare-only stops before generator calls; old v63 readiness/continuation
must never authorize this changed protocol. CPU results do not demonstrate gain.

Oracle unchanged. v7 `oracle_b01.py` has NREF=10, base-pass filtering and >=3
unanimous survivors; its combined worker also reads canonical scoring data.
Do not import that worker into this public-only path. A future ref adapter must
separate prediction from private scoring and bind programs to this cohort/spec.
