# v10_spechint

Created with `cp -r pipelines/v7 pipelines/v10_spechint`; `config.json` sets
`VERSION="v10_spechint"`. Implements the v10_spechint registration in
`trickcatcher_linefacts/PREREG_PENDING.md` (CONCEPT_WEAKNESS plan rank 5).
The registration files are unchanged.

The added concept kind is BEHAV: an explicit specification requirement about
the relationship between input and output which none of the base tests exercises.
Round-one/round-two prompts, strategies, budgets, arms and oracle remain v7's.

## Mining and facts

`mine-behaviour` uses the existing cached `Client` and fixed prompts in
`behaviour_prompts.py`. Every prompt contains only
`preconditions.specification(task)` (signature and docstring) and prior candidate
requirements. PUT bodies, base tests, observed outputs, validators and HumanEval+
labels are never in these prompts. Workers receive base tests and the PUT only
for verification.

Each of K samples follows observation -> confirmation -> code -> verification.
Candidate quotes must be nonempty exact substrings of the supplied specification,
and confirmation must preserve the quote and approve the requirement. A failed
gate drops the item, with reasons saved per sample. Malformed replies fail closed
for that sample. Code uses the precondition miner's AST/pure-builtin gate and
original-signature wrappers. D must return a bool without crashing on every base
input; optional R must return True on **every** captured base input/output pair,
including inputs outside D. R's output is supplied as keyword-only `out`.
Failed/empty base capture aborts rather than emitting unverified requirements.

Temperature=0, top_p=1 and max_tokens=4096 match the precondition miner. Sample s
uses mining seed + task id + 100000*s (s=0 preserves the miner's seed). K defaults
to config K=3; samples are merged in sample/candidate order, deduplicating identical
quote, statement, D and R, retaining contributing sample indices. Cache identity
includes specification, base/PUT digest, model, K, seed and relevant source hashes.
Results are `behaviour/<task>/{summary.json,requirements.json,sample_*/...}`.

`behav-facts` is CPU-only. It replays the existing `facts.py` pool with exactly
the same base calls, PUT numeric constants, facts seed + task id, transformations,
caps, ordering and B5 validator. It checks the replay's size and validity stats
against the copied/reused code-fact pool. Inputs remain literal Python calls,
preserving kwargs and defaults. No base input may satisfy D; the first B5-valid
fuzz input satisfying D is the witness, as in facts.py. R is a mining gate, not a
witness or hit gate. Files are `behavfacts/<task>.json`; `witness_call` supplies
toolinput. Hint text contains only the statement and verbatim quote:

> Specification requirement (behaviour): &lt;statement&gt; ("&lt;quote&gt;"). No existing test uses an input where this matters.

BEHAV hit dispatch is additive to SPEC `input_class` dispatch. A hit requires
B5 validity and D=True, independent of the PUT's output, including a step-budget
timeout. No validator supplied means no BEHAV hit. The tracer, generator
classifier, hybrid worker, and both evaluation paths carry inputs and validity.
Generated-code execution remains in namespace-isolated, credential-free workers.

## Exactly how BEHAV takes a hint slot

Bundle first constructs **the same v7 top three**, including v7's SPEC fallback
only when there are no selected code facts. It saves these as `v7_concept_meta`.
Only those original shown candidates and the emitted BEHAV facts compete; hidden
code facts are not promoted. With no BEHAV facts the original selection/order is
returned unchanged.

With BEHAV facts, call the existing `facts.pick()` with K=3 and the additive
`extra_slots=('SPEC','BEHAV')`. Its unchanged order is:

1. Tier 0, then tier 1 (`g_demote` under G_PRIME).
2. Within each tier, round-robin kinds:
   OUTCOME, STMT, MUTANT, BOUND, NUM, DU, SPEC, BEHAV.
3. Existing deterministic within-kind shuffle, mutant boundary ordering and
   distinct-block/DU-name constraints apply. Each BEHAV gets a unique string block;
   SPEC fallback candidates get distinct string blocks. BEHAV has tier 0.

Consequently BEHAV can fill an unused slot, precede a demoted tier-1 code hint, or
take a first-cycle slot before a second hint of an already visited kind. Three
distinct tier-0 code kinds fill the three slots before BEHAV. This preserves
v7's tiering without a fitted ranker or labels. Tests explicitly cover these cases.
`concept_meta`, `concept_facts` and toolinput witnesses follow the new selection;
v7's placebo hints stay unchanged (there is no invented BEHAV placebo).
All emitted requirements remain in `behav_pool` for measurement, even if unshown.

## Offline measurement

`offline-behav` reads HumanEval+ **only for measurement**, after the bundle is
selected. It excludes pilot/design tasks and runs the official assertion labels
using the `offline.py` capture logic in isolated CPU workers. Every BEHAV fact,
including unshown ones, receives fail/pass hit counts and PF; no-hit PF is null.
The same per-input labels also score old and new selections, including mutants
and SPEC fallback hints.

`offline_behav/report.json` and `report.md` report PF, BEHAV-alone top-three
good@3, v7 versus v10 good@3, hint coverage, newly covered tasks, newly good and
lost-good tasks, all/even/odd DEV splits, and every BEHAV example with its quote,
selection status, PF and witness. Good means PF>=0.5; its task denominator excludes
tasks with zero failing plus inputs, as `offline.py` does. Coverage includes all
eligible DEV tasks; excluded-zero-fail lists and both denominators are recorded.
No outcome metric trains or changes selection.

## Commands

Run from `/home/phong/dev/ConceptTester`. Set `V4` to the existing dedicated v4
venv interpreter (the same interpreter/dependency versions as v7). Namespace
isolation via `unshare -rn` must work on the host. Outputs use the version-scoped
directory `trickcatcher_linefacts/out/pipelines/v10_spechint/humaneval`.
`--dataset /path/to/normalized/he` selects a held-out dataset instead.

```bash
P=trickcatcher_linefacts.pipelines.v10_spechint.run

# Reuse frozen v7 mining, strategies, code facts and SPEC fallback data (CPU copy).
"$V4" -B -m "$P" facts --python "$V4" \
  --reuse-from trickcatcher_linefacts/out/pipelines/v7/humaneval
"$V4" -B -m "$P" specfacts --python "$V4"

# GPU/Qwen endpoint required for new responses; operator runs these later.
"$V4" -B -m "$P" mine-behaviour --python "$V4" --k 3 --online

# CPU only; run in this order after mining.
"$V4" -B -m "$P" behav-facts --python "$V4"
"$V4" -B -m "$P" bundle --python "$V4"
"$V4" -B -m "$P" offline-behav --python "$V4"

# GPU/Qwen: run only after the separately registered offline/odd-task decision.
"$V4" -B -m "$P" arms --python "$V4" --k 3 --online
"$V4" -B -m "$P" evaluate --python "$V4"
"$V4" -B -m "$P" oracle-collect --python "$V4"
"$V4" -B -m "$P" oracle-llm --python "$V4" --online
"$V4" -B -m "$P" oracle-score --python "$V4"
"$V4" -B -m "$P" report --python "$V4"

# Optional inherited stages: mine needs GPU on a fresh dataset; strict is CPU.
"$V4" -B -m "$P" mine --python "$V4" --online
"$V4" -B -m "$P" strict --python "$V4"

# Fake LLM regression suite: no endpoint, keys, real data, or v4 venv needed.
python3 -B -m unittest trickcatcher_linefacts.pipelines.v10_spechint.test_spechint -v
```

Without `--online`, LLM stages only replay existing cache and fail on a miss;
CPU stages do not construct an endpoint client. The tests use scripted replies,
synthetic tasks and a local verification adapter; production keeps its sandbox.
The hybrid dispatch test substitutes trace-only coverage, leaving v7 coverage
measurement unchanged. No online stage or real LLM call was run for this change.
