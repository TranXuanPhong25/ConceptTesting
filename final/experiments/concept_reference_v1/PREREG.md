# Concept/reference v1 — 2026-10-30, before generated-PUT outcomes

This supersedes the initial plain-only experiment design in `final/PREREG.md` for
the user's clarified request. Preserve the original implementation and its history.
No generated PUT benchmark has run yet. A user-requested transport probe on the
selected model returned `{"ok":true}` (27 prompt + 6 completion tokens). Tokenizer
route checks before it did not send completions.

## Question and prior evidence

Question: on the SAME frozen base-passing PUTs, do concepts help produce inputs
that reveal reference-program disagreements, when output-oracle quality is fixed?

v7/v11 already implement boundary, equivalence, statement/branch and def-use hints.
v11 fair matched-placebo comparison was 26–22, not a demonstrated concept gain.
v44 generic class/boundary/coverage pools were no-go (union 21 vs random 21.36).
This experiment is not a new claim for those techniques. It isolates input targeting
from LLM expected-output errors and tests library-based evidence on a fixed cohort.
A secondary alternative uses syntactic predicate disagreements across base-passing
PUTs as concept candidates; no assertion that these differences are real bugs.
No paper is reproduced/reimplemented; existing libraries are used unchanged.

## Frozen cohort, generated once

- All original 164 HumanEval tasks. Target 10 structurally deduplicated programs/task.
- Same writer constraints as initial design: solve the full spec, never inject bugs,
  no oracle/base tests in generation prompt, AST rename/import-padding deduplication.
- User selected `qwen3.5-27b-awq`. Live server advertises 8192 context tokens.
- Up to 5 programs/request, output cap 3072; at most 10 writer requests/task.
  Keep the latest 3 full retained programs and earlier approach summaries in context.
  Temp .9; fixed seeds `20261030 + task_id*100 + round`; thinking disabled.
- Original base suite runs with seeded randomness, prompt helpers and an independent
  test namespace, timeout 3s, coverage.py branch tracing. Store all generated source,
  normalized fingerprints, raw calls, base outcomes, coverage and input identities.
- `cohort.json` is frozen with content hash after this one generation episode. Later
  experiments load it without any writer call, even when tester/concept code changes.
  Shortfall tasks are explicit and excluded from comparisons requiring 10 PUTs.
  Do not regenerate/filter the cohort based on new tests or observed detection.

## Evidence and arms

Use `python-graphs==1.2.3` for CFG, LAST_WRITE/static def-use edges; `NetworkX` for
the resulting CFG, `coverage.py` for actual base lines/arcs; stdlib AST for predicates
and base-value partitions; Hypothesis for deterministic finite candidate inputs.
The archived python-graphs package may not support every syntax node. Failures are
reported; never manufacture CFG/DFG output. Static edges are may-relations. Coverage
of both def/use lines does not prove coverage of their pair; state unknown explicitly.

Analyze only spec, base inputs and passing PUT code; no canonical implementation,
plus inputs, expected outputs or observed new-test failures enter concept extraction.

Five LLM arms, **one call per arm per task**, equal offered input budget 20, temp .7,
output cap 2048, common per-task seed `314159 + task_id`, same visible code/base/spec:

1. `plain`: no extra analysis packet.
2. `classical` (primary treatment): up to 4 grounded cards, balanced boundary,
   equivalence partition, missing static CFG arc, and def-use obligation. State
   evidence precisely; domain validity and path feasibility are not assumed.
3. `contrastive` (secondary research alternative): cross-PUT comparison-operator
   differences + up to 3 classical cards. Explicitly record tasks with no such
   contrast; fallback is not evidence of a contrastive treatment.
4. `placebo`: covered/observed facts, same maximum count as classical. This can be
   distracting; beating it alone is not proof of useful concept guidance.
5. `toolinput`: up to 8 valid novel sampler inputs, no conceptual explanation.

`witness_only`: the SAME sampler inputs, no model call. This measures direct tool
reach. Sampler uses at most 64 records from base-observed values; the trusted input
contract filters them, and a fixed random sample selects up to 8. No reference
outputs or PUT failure outcomes select witnesses.

Prompt visibility: strip repeated docstrings/comments; use a fixed SHA256 ordering
and remove whole PUTs only if needed so every arm retains the same 2048-token
completion budget. At least one PUT must fit, otherwise report a context skip.
Analyze the same visible PUTs; apply resulting input suites to ALL frozen passing
PUTs for the task. Save visible IDs and exact prompt token counts. Card text cap
800 characters; sampler hints trimmed only for the same context bound.

## Reference oracle and execution

- LLM generates input literals ONLY. No predicted output, tests made to pass PUTs,
  consensus oracle, LLM judge or post-outcome input repair.
- Freeze ALL arms' inputs before scoring. Preserve generation hashes, source and
  dependency versions. Individual malformed responses yield zero inputs; no repair
  model call. No unknown request replay, duplicate controller or automatic fallback.
- Trusted EvalPlus v0.1.10 input contracts and `atol` metadata are frozen locally.
  No EvalPlus plus-inputs are retained or supplied to generator/analyzer.
- After the generation freeze, execute the original reference on each proposed
  in-domain input twice. Discard reference errors/timeouts, unstable outputs, base
  input copies and within-suite duplicates. Never discard inputs because a PUT fails.
- Gold values come from the reference program, independent of the LLM. EvalPlus
  float convention (`atol`, fallback 1e-6, rtol 1e-7) and its `_poly` property for
  HumanEval/32 avoid treating a different valid polynomial root as a bug.
- Run union of valid inputs on every passing PUT twice, freshly loaded per input.
  A PUT is detected if one same input mismatches/errors/times out on both repeats.
  Count once per PUT, report unstable cases separately. bwrap sandbox hides host
  files/credentials/network; bounds memory/processes/time. No unsandboxed fallback.

## Metrics and fixed analysis

- Raw per-arm detected PUT count, task count, valid input yield; same frozen base-
  pass denominator. These are reference disagreements on this cohort, not recall
  of all bugs or evidence of generalization beyond HumanEval.
- **Primary:** classical vs plain, per-task equal valid input counts by independently
  seeded random subsets (never prefix selection). Task score = fraction of its
  base-pass PUTs detected. Compare macro task means; two-sided paired task-level
  sign-flip permutation test, 10000 resamples, seed 20261030. No independence claim
  for the 10 programs belonging to the same task.
- Secondary: contrastive/plain, classical/placebo, classical/toolinput. Also report
  directional task counts, exact sign test and 100 prespecified budget-matched random
  subset draws per task. These are robustness/secondary analyses, not primary swaps.
- Report shortfalls, skips, zero-valid-input pairs, per-kind card availability,
  prompt visibility, unsupported graphs, contrastive availability, input rejections,
  model calls/usage/unknown requests. Preserve full input/PUT outcome matrix.
- No adaptive run enlargement, extra arms, alternative oracle, or model substitution
  based on observed outcomes. Independent read-only review and engineering checks
  before benchmark inference; fixes must be amended here prospectively.

## Amendment 1 — independent review fixes, before any PUT generation

2026-10-30: independent read-only Codex review and engineering fixtures found and
fixed three correctness errors: filter library LAST_WRITE to real read accesses
(including implicit AugAssign reads), preserve raw source line labels when removing
prompt-only comments/docstrings, and bind positional plus keyword arguments through
the public signature for find_zero's polynomial oracle. Regression checks cover all.

Complete mandatory checks: freeze generation prompt/fingerprint/model adapter/base
worker/execution source hashes plus interpreter/dependency versions; offline score
never constructs a model; aggregate writer/tester usage, unknown calls, graph/card/
visibility/contrast availability, skips and input rejections in terminal reports.

During active generation a separate recorded observer checks model metadata and
sends at most one one-token keepalive per 20 minutes, per notebook operating rule.
Observer costs are separate from arm costs; offline scoring sends none. All added
changes are prospective; the only real model completion so far remains the 33-token
transport probe. Final engineering validation and review precede the full launch.

Final observer audit: resume starts after the highest existing observer file index;
never overwrites prior calls/usage. Regression added. Review clearance covers the
full 164-task run after this accounting fix. All changes precede PUT generation.

## Execution log — prospective protocol unchanged

Full164 detached controller PID93111 launched. A separate post-launch engineering
readiness call (not benchmark data) exercised the real input prompt/adapter through
the reference and PUT evaluator:3validnovel inputs,fixture error detected,702tokens.
Together with transportprobe33tokens this is735known diagnostic tokens outside
arm/cohort/observer costs. No source/settings or benchmark inputs were changed in
response, no cohort regenerated, and no efficacy conclusion follows from fixtures.

## User-authorized retry — 2026-10-31, before retry completion

User explicitly requests retry with the same supplied model/endpoint after the
controller stopped on task118/programs_00. Endpoint metadata again confirms the
same served model and8192context; all frozen source hashes are unchanged.

Preserve the original failed request/attempt in a sibling `calls/` directory
marked `unknown_attempt`, so final accounting retains its unknown usage. Reissue
only that missing-response slot with identical prompt/seed/sampling parameters;
resume the original run from all durable cohort/call/base checkpoints. Do not
regenerate the118 saved task cohorts, change caps, or replace saved responses.
Archive prior controller status/log and snapshot checkpoint hashes before launch.
This authorizes the explicit retry; it does not erase the historical unknown call.
