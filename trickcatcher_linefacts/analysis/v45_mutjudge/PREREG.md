# v45 (renumbered from v43 on 2026-10-22; v43 is also used by v43_concept_identify) binary judge on v42 mutant-disagreement questions (Qwen2.5-Coder-32B) — diagnostic

Written 2026-10-21 before any model call. v42 was **no-go** by its rule (D1 15/33, lift 0.62), so this is not the
registered follow-up step; the user asked to try the GPU endpoint anyway ("xong rồi thì chạy thử nhé"). It is a
diagnostic of the one thing v42 cannot measure on CPU: whether a model can answer the binary question at all (v42: on
valid package inputs the mutant output is right in 52 questions, the PUT in 335, neither in 46).

## Prior art
Open expected-value oracle with Qwen: v21/v23/v26 (bottleneck, 19% unsound properties); Codex oracle v27/v28 (strong,
ceiling). Mutant alternatives shown to the model as concepts: v31/v34 (input side). New here: the oracle question is
binary (two concrete outputs on one input), and the concept arm explains the difference as a fault concept.

## Material (frozen)
All 607 questions of the v42 package (`out/analysis/v42_mutoracle/packages.json`): (input, surviving mutant), with the
PUT and mutant outcomes from the v42 batch. Frozen to `questions.json` before any call.

## Arms (one call per question per arm; temperature 0, seed 20261021, max_tokens 300, JSON mode)
- `binary`: signature, spec, public tests, the input, two results labelled A/B (order fixed per question by a hash),
  "two candidate implementations disagree; decide from the spec which result is correct". Choices: A, B, neither,
  invalid (input violates the spec constraints), unsure.
- `concept`: the same plus the numbered code and the fault concept: fault type (v31 types from the mutmut operator,
  `ft_concepts.fault_type`) with its meaning, the edit `line L: before -> after`, and which label is the code as
  written and which is the code with the edit.
A choice of the mutant's label = a flag (a test asserting the mutant output would be written).

## Scoring (references only here; v41/v42 reference batch + official re-check as in v42)
- Confirmed task: some flag on a question whose input is confirmed exposing and whose mutant output = reference.
- False-alarm question: a flag where the input is contract-invalid, or the PUT output = reference, or neither is right.
- Reported per arm: confirmed tasks, FA questions, FA tasks, flag precision (questions), sensitivity on mutant-right
  questions, specificity (PUT chosen) on PUT-right questions, choice distribution, parse failures.
- Context only (different generator, not comparable as a gate): v31 plain Qwen3.5-35B 15/33 confirmed, 32 FA tests.

## Decision (diagnostic)
The mutant-oracle route is worth a registered follow-up iff the `concept` arm has **confirmed tasks ≥ 8 AND flag
precision ≥ 0.5 AND confirmed tasks ≥ binary with FA questions ≤ binary**. Otherwise close the route (v42 + v43).

## Amendment 1 (2026-10-21, after an independent read-only review, before any model call)
- `questions.json` sha256 `3b4f48378d8c78cfae6f782715fd96681a22d9500cbb5ee9bf256a069b7cabca`, asserted by generate/score.
- New arm `code` (code + which label is the code as written / with one small edit, no fault type, meaning or edit
  text) to separate the fault concept from "code shown + PUT identified" (PUT right in 77% of valid questions, so
  defaulting to the PUT would pass an FA comparison against `binary` alone). Decision rule now requires `concept` ≥
  both `binary` and `code` on confirmed tasks with FA questions ≤ both (other conditions unchanged).
- Neutral wording for `code`/`concept`: the code and the edited code both pass the public tests.
- Parse: choice is stripped and case-folded; a truncated JSON falls back to a `"choice": "..."` regex.
- generate: preflight that the model is served; per-call errors are counted, the run exits non-zero if any call is
  missing (rerun resumes from the cache).
- A flag on a batch-only exposure (official disagrees) counts in flags (lowers precision) but neither as true nor FA.
