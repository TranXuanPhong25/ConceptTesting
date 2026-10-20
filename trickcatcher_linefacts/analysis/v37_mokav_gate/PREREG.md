# v37 Mokav gate: can PUT-vs-surviving-mutant differential testing reveal pilot20 bugs? (CPU only, no model call)

Written 2026-10-20 before computing anything below. User request: check whether the Mokav idea (Mokav, JSS 2025:
execution-driven differential testing of two program versions until a difference-exposing input, DET) fits our
step a/b; if not, try the next paper; then plan a fix for step a. Prior art: v7 MUTANT facts, v9 reach/infect/propagate
feedback, v31/v34 fault-template, v35 ceiling (vibepass_half, template pool only). Review that motivated this:
`analysis/fault_localization_review_2026-10-20.md`.

## Data (dev only; VibePass is not touched)
- pilot20: the 20 HumanEval PUTs of `flow_run.cohort('pilot20')` (v7 pilot split).
- Alternatives: v31 tool stage (`v34_ftplacebo.ft_run.tool_stage`, frozen code, own output root): mutmut mutants of the
  PUT, survivors = same outcome as the PUT on the public base inputs (prompt asserts). Its template pool (filtered to
  the public-example domain) is reused as the v31 comparison.
- Pool U (evaluation only, never shown to any method): all EvalPlus `base_input` + up to 300 `plus_input`, sampled
  with seed 20261020. EvalPlus inputs are contract-valid by construction. Reference = HumanEval+ canonical solution;
  output equality with the task `atol` (floats), exceptions by type, timeouts/skips excluded.

## Definitions (per task)
- Exposed: some x in U with PUT(x) != ref(x).
- Correcting survivor: survivor M with M(x) = ref(x) != PUT(x) for some x in U. **C** = task has one.
- Clean fix: survivor equal to ref on every completed x in U. **F** = task has one.
- Non-equivalent survivor: M(x) != PUT(x) for some x in U. Useful share = correcting / non-equivalent survivors.
- DET rarity: for the correcting survivor with the most correcting inputs, share of U where M != PUT.
- Template headroom **H**: tasks with C where the v31 template pool exposes no PUT != ref (same comparison).

## Go / no-go rule
Mokav-style differential search over surviving mutants is worth a model run on dev only if
- G1: C >= 10/20 (a single-edit alternative can witness the bug in at least half the tasks, given a DET), and
- G2: H >= 3 (tasks where a DET search could add over the v31 template pool).
Fails G1 → mutant alternatives are the limit; next candidate replaces them with spec-derived programs
(CASCADE / TrickCatcher style), checked the same way as a separate registered step.
Fails G2 → templates already reach what single-edit alternatives can witness; Mokav adds no headroom here.
Secondary, descriptive: F, useful share, DET rarity, exposure of the v31 template pool on pilot20.
