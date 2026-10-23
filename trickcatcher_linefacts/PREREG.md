# Pre-registration: line-fact concepts for LLM test generation (pilot)

Written 2026-10-10 before any LLM call; amended that day for ranking v2 and vocabulary v3.
V3 templates, operators, fuzzing, gates and ranking choices are derived on DEV. The fixed even/odd split
is a robustness check. The gate plan was written before opening v3 offline results. The final generator and settings are frozen before the
one-time offline pilot confirmation; later deviations are recorded separately.

## Question

The tool runs the base tests and states, at the line level, what they never exercised. Each statement uses a
fixed, human-defined vocabulary and is rendered from a template. Does giving these facts to an LLM make its tests
find more bugs than (a) the same number of facts about behaviour the tests already cover, (b) a one-line
"leave the tested region" hint, (c) the tool's own inputs with the LLM only writing the oracle, and (d) no extra hint?

## Material

- **PUTs:** TrickCatcher EvalPlus (`vendor/TrickCatcher`, commit `a0d285a`). These are LLM-written HumanEval
  solutions that pass the HumanEval base tests and fail HumanEval+. `tasks.txt` lists 139 of them.
- **Method-visible inputs:** PUT source (with the spec docstring) and the HumanEval base `check`.
  `facts.py` never reads HumanEval+.
- **Evaluation-only:** the HumanEval+ canonical solution, used as the oracle in `evaluate.py`.

## Concepts (v3 vocabulary)

All concept and placebo templates begin with a course criterion. `VOCAB.md` maps each kind to chapters
03/04/05/08, mutation-tool sources, a concrete DEV example and its gate result. OUTCOME-q is removed.

| Kind | Criterion and missing behaviour |
|---|---|
| OUTCOME | Branch coverage C2: an unseen True/False decision branch; condition coverage C3 for BoolOp operands |
| STMT | Statement coverage C1: unexecuted statement lines |
| BOUND | Boundary value: a comparison constant or its immediate neighbour is unobserved |
| NUM / SHAPE | Input equivalence class: an unobserved numeric/structural class or its complement |
| REL | Decision table / dependent inputs: equality, order, prefix and length relations |
| MUTANT | Mutation ROR/AOR/COR/UOI-negation/CRP: surviving change, fuzz-confirmed output/status distinction |
| MUTANT-X | SDL, call-result removal, SIR, BCR, ZIL/OIL/RIL; separately gated, joins MUTANT on pass |
| LOOP | Loop coverage: 0, 1 or 2 iterations in one dynamic loop execution |
| LOOP-MAX | Loop coverage: more iterations than the largest count observed in base |
| OUTPUT | Output equivalence class: a class missing from successful top-level returns |
| DU | Def-use pair: a local definition (parameters at entry included) reaches an unseen c-use/p-use |
| DECISION | Decision table: an unseen T/F outcome combination of non-nested decisions in one call |

**Fuzz confirmation.** The generator reads only PUT source, prompt and HumanEval base tests. It uses at
most 400 seeded variants, reserving 100 for relation targets: equal same-type arguments, swapped order,
equal lists, prefixes, equal lengths and integer/container 0/len/len±1. Unused reserve goes to generic
variants. Seed is 20261010 plus task id. Numeric source constants provide boundary candidates.

**Bounded operators.** Keep v2's 80 legacy mutation points, add up to 80 extended points in a separate
seeded sample. Call-result removal requires method-visible type evidence. Reverse iteration applies to
list/tuple/string/range; unsupported iterables retain their order and equivalent mutants are filtered.
One-iteration mutation allows at most the first iteration, including loops with continue. Mutant testing
compares plain PUT and mutant under the existing deterministic step budgets. A survivor with no fuzz
distinction is dropped as likely equivalent, without claiming a proof of equivalence.

**Dynamic criteria.** Loop counts are per execution of a loop in a call, including nested/recursive
executions and interruption. LOOP-MAX may be reached before a step-budget failure; offline failures
include STEP. DU emits at most 64 distinct missing pairs per task, using actual reaching definitions;
comprehension-local variables are outside this DU implementation. At most 32 same-function non-nested
condition pairs are probed; both outcomes must be evaluated in one call, possibly across loop iterations.
These bounded observed pairs support the course all-defs/all-uses vocabulary without an exhaustive claim.

**Fixed gate.** For each candidate slot independently, BOTH even and odd folds must satisfy (1) fact-level
mean PF > matched task base and (2) per-task better > worse among tasks with scored reached facts. PF is
fail_hits/(fail_hits+pass_hits), strong is PF≥.5, zero-hit PF is undefined. Comparisons use tolerance 1e−12;
empty slots/folds fail. SHAPE and REL are re-gated by the identical rule. Failed slots remain recorded but
never enter the concept/placebo display pool. Gate numbers and frozen decisions appear in `VOCAB.md`.

**Ranking v3.** Core round-robin slots: OUTCOME, STMT, MUTANT, BOUND, NUM. Passing MUTANT-X merges into
MUTANT. Other passing slots follow NUM in order LOOP, LOOP-MAX, OUTPUT, DU, REL, DECISION, SHAPE. K=3;
K=5 is a dev sensitivity analysis. Keep v2's short-exit-guard blocks, one selected fact per block, boundary
mutants last within MUTANT, and fresh `random.Random(20261010 + task_id)` tie-breaking. G′ stays on:
base-seen exit-guard outcomes are forced while preserving condition evaluation; same/necessary facts
are demoted, header mutants exempt. Changed outputs or removal of an original error classify as differ;
original success/forced error (including timeout) classifies as necessary; equal outputs/two errors as same.

**Docstring pre-check.** Store plain-PUT mismatches with literal prompt examples in `doc_fail`, with numeric
rounding tolerance 1e−6. These flags stay outside prompts. Pilot tasks **108, 116, 131** have docstring-example
failures and are reported both included and excluded in the single frozen offline pilot analysis.
Paid LLM generation remains deferred. The post-freeze prompt bundle change is recorded below.

**Placebo.** Use the same course wording for covered behaviour: branches taken, statements executed,
classes exercised, loop counts observed, def-use pairs exercised and mutants killed. Preserve seeded
same-kind matching where available. Concept and placebo arms receive the same neutral FACTS header sentence.

**Human understandability.** After freeze, sample 30 K=3 shown facts from DEV only, seeded and stratified by
kind without PF-based selection. Each item includes docstring, PUT code and fact. The rating sheet asks
Q1 "I understand what this fact says" (1–5) and Q2 "an input that satisfies it" (a literal Python call).
A sandboxed checker reuses `evaluate.py`'s shared hit logic. Vietnamese instructions explain that reach
is evaluated separately from input-domain validity and oracle correctness.

## Arms (`prompts.py`)

Every arm is white-box. Every arm sees the code, the docstring spec and the base tests, and gets the same
instruction: up to 10 `assert f(args) == expected` lines, with the expected value taken from the spec.

| Arm | Extra section |
|---|---|
| plain | none (HEAD + TAIL) |
| concept | top-3 facts |
| placebo | matched covered-behaviour facts |
| coverage | "Target behaviour that the existing tests do not exercise." |
| toolinput | the fuzz witness input for each concept fact (no output); the LLM writes the assertions |

## Tasks

**Eligible PUTs.** A PUT is eligible if it has at least 1 fuzz-confirmed fact. The following are excluded:
- the 6 PUTs used to design the concepts: 22, 33, 111, 122, 123, 139;
- 66, which has no failing HumanEval+ input on this toolchain;
- 50, which is spec-ambiguous.

The original v1 eligibility and the fixed pilot are recorded in `out/pilot_tasks.json`. Recompute v3 coverage
from final `facts_v3f` before generation; the original eligibility count is not a v3 result. Fixed pilot tasks for
which the tool has nothing to say remain in all task denominators and are reported as a coverage limit.

**Pilot sample.** Keep the 20 ids in `out/pilot_tasks.json` → `pilot`: 0, 7, 18, 43, 44, 65, 70, 77, 82, 84,
87, 90, 105, 108, 116, 120, 131, 143, 151, 157. Do not resample after the v3 dev analysis. Do not compute or
open their HumanEval+ offline results before freezing. The six design tasks are excluded from that analysis too.

**Dev analysis.** 139 tasks minus those 26 exclusions, dropping tasks with zero failing HumanEval+ inputs.
Fix folds by even/odd task id before looking at outcomes. At K=3 and K=5 report strong-fact coverage (PF≥.5),
fact-weighted mean PF vs a matched task base rate, per-task better/worse counts and a two-sided sign test.
Include no-fact tasks in coverage denominators and omit zero-hit facts from PF means. Compare frozen v2, final v3,
2000 uniform random draws from the same v3 pool and the oracle v3 pool ceiling.
This entire selection procedure is development-derived; pilot confirmation is run once after freezing.

## Generation

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct` from Hugging Face, on Kaggle T4 GPUs, float16.
- K = 3 independently seeded samples per (task, arm), giving 20 x 5 x 3 = 300 requests.
- Temperature 0.7, top_p 0.95, max output 1024, context limit 8192; tokenizer chat template with system + user.
- Seed = 20261010 + ((task_id x 5 + arm_index) x 1000 + sample), with plain/concept/placebo/coverage/toolinput
  indexed 0–4 and sample indexed 0–2. This is independent of Python's randomized hash and row order.
- Gemini 2.5 Flash on Vertex is optional later, separately authorized; thinking budget 0, temperature 0.7,
  max output 2048. Preserve `out/gen.jsonl` and `out/eval.jsonl` for that run.

## Metrics (`evaluate.py`)

For each assertion:
- **canon_ok:** the assertion passes when the canonical solution replaces the PUT.
- **detects:** canon_ok, and the assertion fails, errors or times out on the PUT (5 s).
- **false alarm:** not canon_ok.

For each (task, arm, sample):
- **detected:** any assertion detects.

Three measures:
- **Primary:** tasks detected per sample, averaged over K.
- **Paired:** per task, the number of detecting samples (0–3). Concept is compared with each other arm by a
  sign test (plain first, then placebo, coverage, toolinput).
- **Delivery (manipulation check):** the fraction of concept facts that the arm's assertions reach. It is
  measured in every arm, against the concept arm's facts.

## Decision rules

**Pilot go/no-go (n = 20, descriptive; it has no power for significance):**
- **G1, delivery.** The concept arm reaches at least 50% of its facts, and at least 15 points more than the
  coverage arm. If G1 fails, the facts are not being used. Stop and fix the delivery, not the concepts.
- **G2, detection.** Concept is at least coverage + 1 task per sample (5% of 20), and concept is at least placebo.
- **G3, precision.** The concept false-alarm rate is at most the coverage false-alarm rate + 10 points.

G1, G2 and G3 must all pass before the full run.

**Full-run kill criterion (final v3 eligible PUTs, K = 3).** Two conditions, both required:
- Concept beats coverage by at least 5% of the tasks.
- Concept beats placebo with a paired sign test, p < 0.05.

Otherwise the line-fact concept is declared not useful in this setting.

**Reading toolinput.** If toolinput is at least as good as concept, the LLM's contribution is writing the oracle.
The concept then works through the tool, not through the LLM's reasoning, and the thesis has to report it that way.

## Historical v1/v2 notes (no LLM output seen; superseded by v3)

- **OUTCOME-q** was added after HumanEval/122 (a design PUT) produced no plain OUTCOME fact. The bug there
  needs "never False when x is negative".
- **Ranking** was changed from "one fact per line" to "one per (kind, line)" with OUTCOME-q last, after the
  facts for pilot PUT 0 were inspected. The boundary mutant `<=`→`<` had been crowded out by an OUTCOME-q fact
  on the same line. Only facts were inspected; no HumanEval+ result for this ranking was computed.

## Frozen v3 gate decisions

Passing candidates: MUTANT-X, DU. Failed candidates: LOOP, LOOP-MAX, OUTPUT, REL, DECISION, SHAPE.
Display round-robin: OUTCOME, STMT, MUTANT, BOUND, NUM, DU. K=3; G′ stays enabled. Full fold numbers are in `VOCAB.md`.

## Final v3 freeze with DU readability rule (v3f)

Final v3 = v3 + at most one selected DU fact per variable, keyed by `("DU", variable)`.
This rule was fixed before viewing its DEV delta and is retained regardless of that delta.
Generation, templates, gates, blocks, boundary-mutant ordering (R2), G′, seeded tie-breaking,
round-robin slots and K=3 remain unchanged; K=5 is diagnostic only. The existing passing gates
remain MUTANT-X and DU. The 139 fresh outputs are in `out/facts_v3f/`; 113 DEV-only offline
outputs are in `out/offline_v3f/`. Old v2/v3 outputs remain untouched.

The freeze manifest is `codex_freeze_v3/freeze.json` in the task scratch folder. It records
SHA256 of facts.py, tracer.py, offline.py, evaluate.py, prompts.py, generate.py and every one
of the 139 facts_v3f JSON files. It is written after the fixed 20 DEV tasks agree across
two fresh generations ignoring only secs, and before any pilot HumanEval+ label is computed.

`codex_freeze_v3/pilot_plan.json` fixes one $0 offline confirmation on the original 20 pilot
ids, using frozen facts_v3f and HumanEval+ labels. Drop zero-failing-plus tasks, include
no-fact tasks in task denominators, report strong@3/@5, mean PF versus matched base, per-task
better/worse and exact two-sided sign p, placebo-3, 2000 uniform random-3/5 draws from the same
reached display pool, pool ceiling and per-kind reach/PF/strong counts. Report all pilot tasks
and separately with doc_fail tasks 108/116/131 excluded, alongside unchanged DEV metrics.
Random/oracle diagnostics retain the prior unconstrained same-pool definitions. No generator,
ranking, gate or setting change follows from any pilot result. No design-task offline results
are computed or inspected. The saved `out/pilot_tasks.json` prompt material is preserved,
and generate.py was not run during that freeze task. This offline confirmation is separate from the deferred paid
LLM-arm experiment and its G1/G2/G3 rules above.

## Post-freeze, pre-generation amendment (2026-10-10)

Before any LLM output exists, add the plain arm to measure the effect of extra guidance against code/spec/base
tests alone. Prepare the free Kaggle Qwen2.5-Coder-7B-Instruct pilot with K=3 and temperature 0.7 to avoid paid
API use and obtain batched throughput measurements. This amendment changes only the LLM-side bundle, prompts,
generation, evaluator plumbing and documentation; facts.py, tracer.py, offline.py and all facts_v3f files stay frozen.
It follows the final freeze report and does not select or tune facts from pilot labels. No further pilot offline
result files are opened and no pilot ids are reselected.

`generate.py bundle` copies final v3f top3 records (including exact shared fact_hit selectors), matched placebo3,
witness calls and doc_fail into `out/pilot_tasks_v3.json`, using the existing 20 ids from `out/pilot_tasks.json`.
The original file stays untouched. Empty-top3 tasks 77 and 151 stay in the pilot; their concept/placebo/toolinput
sections are empty and exactly match plain. Coverage keeps its generic hint. doc_fail remains outside prompts.

The Qwen export contains 300 rows in `kaggle/data/prompts.jsonl`; samples differ only by seed, never prompt text.
Qwen outputs use `out/gen_qwen7b.jsonl` and `out/eval_qwen7b.jsonl`. All five arms are reported, and concept is
paired against every other arm. The delivery denominator includes shown concept facts for samples with zero
assertions (zero hits), so an empty response cannot inflate delivery. No-fact tasks contribute to task metrics,
with no facts added to the delivery denominator. Evaluation worker failures stop evaluation before output is
written, preventing a silently reduced cohort. G1/G2/G3 thresholds and detection/oracle/hit definitions stay fixed.

The kernel submits all pending valid rows in one vLLM batched call. If vLLM installation/import fails, a
transformers fallback attempts one batch and splits failed batches until they fit or individual rows fail;
it applies the same sampling parameters with a separate seeded RNG for each row. Backend and timing are
recorded. Errors produce empty text plus error metadata; successful rows resume only when model, prompt hash
and seed match. Throughput totals cover successful new rows and timed generation calls (including retries),
excluding resumed rows and model load. No kernel, model generation or paid call is run during preparation.

## gen arms (post-pilot design)

Fact set = v3c (spec-valid fuzz evidence), using `out/tasks_v3c_all.json`; the v3f bundle remains preserved.
Registered before any new real or canned LLM response is collected. This design follows the Qwen pilot.
Six arms, in fixed order: plain, concept, toolinput, gen-plain, gen-concept, gen-placebo. Plain/concept retain
the existing direct assertion prompts. Toolinput uses frozen fuzz witnesses. The three gen arms use the
verbatim pinned TrickCatcher generator system/user templates; gen-concept/gen-placebo append the identical
FACTS_HEAD, their up-to-three frozen facts, and construction instruction. No-fact tasks use gen-plain's prompt.
Stage 2 for every input arm is the existing toolinput oracle prompt, without facts and with selected inputs.

N=100 sample_one() calls in one unshare -rn isolated generator process, random.seed(sample_seed) before
the loop; 1 second per call, 120 seconds total. Only correct-arity lists/tuples with JSON and repr roundtrips
are retained, deduped by repr. EvalPlus v0.1.10 contract assertions alone decide validity; the same filter
applies to toolinput witnesses. No canonical solution or HumanEval+ inputs enter generation or selection.
Trace the PUT with frozen tracer.fact_hit; measure concept-fact hits for all input arms, and shown placebo
fact hits for gen-placebo. One correction request at most if the generator crashes or yields zero valid
inputs; gen-concept/gen-placebo also retry when any shown fact has zero valid hits. Feedback format is
shared by all gen arms. Use the corrected attempt when requested, including if it is empty.

Select up to three distinct valid inputs: gen-concept/gen-placebo choose one seeded hitting input per
shown fact where possible, then pad with seeded random valid inputs; gen-plain chooses seeded random valid
inputs; toolinput keeps valid distinct witnesses in frozen order (up to three). Empty pools still receive
stage 2 with an empty input list. Keep the frozen v3c facts and tasks regardless of generated hit counts;
do not revise them based on this condition. Rates use unique retained candidates,
with raw 100-call success/valid/duplicate counts also retained.

K=3; Qwen/Qwen2.5-Coder-7B-Instruct float16 (same checkpoint as pilot, no AWQ), vLLM 0.7.3 served on
Kaggle T4 x2 with tensor parallelism 2, served name qwen2.5-coder-7b-instruct. Chat sampling: temperature
0.7, top_p 0.95, max_tokens 1024; 16 client workers by default. Base seed 20261010; seed =
20261010 + (((task*6 + arm_index)*1000 + sample)*8 + stage*2 + retry), stages direct=0, generator=1,
oracle=2, input sampling/selection=3; retry=0/1. Model calls use on-disk message+parameter SHA256 caching.

All 139 method tasks minus design IDs {22,33,111,122,123,139}: 133 tasks, comprising 113 dev and the
20 original pilot IDs from out/pilot_tasks.json. Keep no-fact, task 50 and task 66; do not filter using
HumanEval+ labels. Primary analysis is dev; pilot is reported separately because design follows its LLM
outputs. Within each split report all, without doc_fail, and doc_fail-only cohorts separately. Task 157 is
a pilot ID: the explicitly requested Pythagorean harness check is an illustrative pilot smoke, in addition
to three genuine dev tasks (2,3,4), and does not change the primary dev cohort or smoke driver selection.

Primary: gen-concept vs gen-plain, per-task detected samples (0..3), exact two-sided sign test on dev tasks.
Secondary: gen-concept vs gen-placebo, toolinput, concept; gen-plain vs plain. Preserve detection, false-alarm
and delivery definitions. Also report valid-input rate, concept fact-hit rate by kind, oracle-free
bug-revealing-input rate (selected valid input with PUT output != canonical output, evaluation only), LLM
calls and input/output tokens per arm, plus throughput. Canonical use occurs only after selection in evaluation.

Caveat: fact kinds were gated on dev offline PF on HumanEval+, so dev favours fact arms over non-fact arms;
gen-concept vs gen-placebo controls for that only partly. This is a post-pilot design, not a new untouched
confirmation cohort. No real LLM output is collected during build/smoke verification.

## v3c (spec-valid fuzz evidence)

Decided after the v3f pilot offline confirmation and before any gen-run output. The rule is retained whatever
the DEV delta. Prior shown witnesses violated EvalPlus contracts: 44/154 witnesses on DEV (31/113 tasks)
and 8/31 on pilot; e.g. greatest_common_divisor(144, -1), string_sequence(-1), and task 157's negative-b fact
despite the contract requiring all sides > 0. These were specification-forbidden gaps.

Every fuzz input must pass the task's EvalPlus v0.1.10 `prompt + contract` assertions before contributing
reachability, witnesses, mutant kills/equivalence filtering, relation/loop/DU/OUTPUT observations, G′ evidence
or any fuzz-based placebo check. Base-test inputs are taken as given. Contract code executes only under
`unshare -rn python3 -I -B`, with one-second per-check safety timeouts. The validator interface is
`valid(task, args) -> bool`: evalplus is the v3c default; none reproduces v3f, and mined is reserved for future work.

Seed and type-aware candidate construction stay fixed. Collect up to 400 distinct valid non-base inputs,
with a fixed cap of 2000 candidate draws (including duplicate/nonliteral draws). The relation-targeted share
collects up to 100 valid inputs from its shuffled pool, with a cap of 500 draws or pool exhaustion; unused
capacity is filled by the existing scalar/sequence and second-level variations. Log attempts, valid count
and valid/draw rate, plus distinct contract-check counts/pass rate and the same relation-share statistics.

No re-gating: MUTANT-X and DU remain the only passing candidates. Fact kinds, templates, R1/R2/G′,
ranking v3, block and per-variable DU dedupe, seeded tie-breaking, K=3 and placebo construction remain
unchanged; K=5 stays diagnostic. Regenerate 133 non-design tasks in `out/facts_v3c/`, DEV-only offline
results in `out/offline_v3c/` with OFFLINE_SKIP_PILOT=1, and the gen bundle in `out/tasks_v3c_all.json`.
Pilot offline results remain those of v3f; no v3c pilot/design offline results are computed or inspected.
All previous outputs stay byte-identical. CPU verification uses canned responses only; no gen run starts here.

## v3m (mined preconditions, inline)

Registered before any real mining output. The gen run now uses v3m as its primary fact set;
v3c remains the EvalPlus contract upper bound, offline only unless the user requests its arms.
This is adapted from RBCTest (Huynh et al., ICSE'26, arXiv:2504.17287), which mines REST API
output oracles; this adaptation mines Python input preconditions, not a reimplementation.

Once per task, shared by all arms/samples: AST-strip the PUT body and provide only its signature
and docstring to Qwen2.5-Coder-7B-Instruct through the existing cached QWEN_BASE_URL client.
Use temperature 0, top_p 1, seed 20261010+task for all three mining calls. Exact prompts live
in precond_prompts.py: observation enumerates atomic specified or necessarily implied input
conditions; one batched confirmation requires a keep decision and exact docstring quote;
whitespace-normalized evidence must be a nonempty substring of the specification text sent
(signature + docstring; amended below). One code call
emits builtin-only predicates, without try/except. No imports, I/O, or parameter mutation.

Semantic verification uses only base-test argument tuples captured by the existing tracer and
literal AST-parsable docstring >>> calls. Reject any predicate that returns other than True,
raises, or times out on any known-valid input; log each rejection. No survivors means always
valid. All generated code executes under unshare -rn python3 -I -B with stripped environment
and timeouts, never in the parent. Persist prompts, raw replies, candidates, confirmation,
code, verifier log, valid.py and hash-bearing summary per task in out/precond_qwen7b/.

Per task, inline: mine/cache -> facts with validity=mined in out/facts_v3m -> bundle -> arms.
Concurrent tasks share the same client/cache and bounded call pool. The same mined valid.py
filters stage-1 and toolinput inputs; no EvalPlus contract enters this generation path.
Record facts_version=v3m and every validator SHA256 in manifests. --precond-only stops after
mining/facts/bundling. Real arms use the separate out/gen2_qwen7b_v3m directory.
No vocabulary, fuzz caps, ranking, G-prime, seeds, placebo rules or frozen gates change.

Evaluation is fixed in eval_plan_v3m.json before mining: all 133 non-design tasks, raw seeded
validity=none fuzz inputs, per-task and pooled valid-precision/recall versus EvalPlus contracts,
and tasks accepting/rejecting every draw; candidate/confirmed/surviving counts and dropped
hallucination examples. DEV-only HumanEval+ input rejection is evaluation only, never feedback.
OFFLINE_SKIP_PILOT=1: compare v3m/v3c/v3f in out/offline_v3m using the v3c overall/even/odd
K=3/5, placebo, random, ceiling and per-kind tables. No pilot/design offline results. No change
follows from evaluation numbers. All older outputs and freeze manifests remain unchanged.
Build verification uses canned local HTTP replies for DEV 2/3/4 and contract-only task 157;
no real LLM, paid API, Kaggle, commit or push in the preparation session.

### v3m amendment (2026-10-11, during the first real mining run, before any evaluation)

The first real mining run showed the evidence check rejected type conditions quoted from the
signature (task 13: `a: int`, `b: int` -> "evidence not in docstring"), although the signature
is part of the specification text sent to the model. Fix: evidence must be a substring of the
signature + docstring text that was sent. Prompts are unchanged. The partial run (19 tasks
mined, 8 facts files, no offline evaluation, no arm output) was moved unchanged to the session
scratch folder as `v3m_run1_evidence_bug/`; mining restarted in fresh directories. No other
setting changed.


### v3m amendment 2 (2026-10-11, second real mining run aborted, before any evaluation)

Qwen writes each predicate with only the parameters it uses (`def P1(a)` for `f(a, b)`), and some
replies were malformed (output conditions on `result`, a `lambda`), which made the strict code check
abort the whole run. Fix, decided from these failures only: (1) a predicate may take any subset of the
specification's parameter names; it is wrapped in a function with the original signature that passes
that subset; (2) a predicate that fails the safety/shape checks is dropped alone with a recorded reason
(`code_rejected`, `no_code`, `code_unparsable`) instead of failing the task; top-level statements in
the code reply (e.g. `from typing import List`) are ignored and never executed; (3) a malformed
observation/confirmation reply leaves that task unconstrained (always valid) and is recorded as
`mining_failure`. Prompts, model, seeds and the verifier are unchanged. The aborted run (33 task
dirs, no offline evaluation, no arm output) was moved unchanged to the session scratch folder as
`v3m_run2_strict_code/`; its LLM response cache is reused (identical prompts and seeds).

### gen-run amendment (2026-10-11, first v3m arms run aborted at 78/133 tasks, before any evaluation)

A gen-plain generator for task 68 returned lists of up to 10,000 elements; classifying 100 such inputs
exceeded the 900 s sandbox budget and the RuntimeError aborted the run. Inputs of that size also
cannot be written into the stage-2 oracle prompt (16k context). Rule added for every input arm:
a candidate whose repr exceeds 1000 characters is marked `oversize`, never traced or selected,
and counted separately (the feedback message names it). Per-input tracing has a 10 s alarm
(`trace_error` recorded), and a failed classification sandbox yields an empty pool instead of
aborting. Checked before rerunning: no toolinput witness exceeds 152 characters and none of the 1810
inputs selected in the aborted run exceeded 1000 characters. Because the pool for seeded selection
can change, all 133 tasks are rerun into a fresh directory; identical LLM requests come from the
cache. The aborted run was moved unchanged to the session scratch folder as `v3m_arms_run1_aborted/`.
No result of the aborted run was evaluated or inspected beyond the failure.

### v3m2 (2026-10-11): confirmation accepts necessarily implied conditions

Decided after the v3m mining-quality/offline report and after the v3m arms finished generating, but
before any arm output was evaluated. Problem found by inspecting mining artifacts (no bug labels):
the confirmation prompt asked for "exact docstring evidence", so the model rejected implied conditions
that have no literal quote. Task 157: observation proposed a > 0, b > 0, c > 0 ("the lengths of the three
sides"), confirmation returned keep=false; 212 of 432 candidates were dropped for evidence. Change: the
CONFIRMATION prompt now accepts conditions necessarily implied by the meaning of the words (generic
examples: lengths/counts/sizes are non-negative, indices lie within their sequence) and asks for the
exact words the condition is based on, which need not state the condition. The evidence must still be
a substring of the signature + docstring sent; observation/code prompts, verifier, model, seeds, fact
generation, arms and evaluation are unchanged. Outputs: out/precond_qwen7b_v2, out/facts_v3m2,
out/tasks_v3m2_all.json, out/offline_v3m2, out/gen2_qwen7b_v3m2 (the LLM response cache is copied from
the v3m run, so unchanged requests are not re-sent). v3m2 is the primary analysis; v3m (registered
first) is reported in full next to it.

### v4 (2026-10-11; before any real v4 output)

User-approved replacement of the home-made fuzz, mutation and C1/C2 measurements with
Hypothesis 6.169.0, mutmut 3.8.0 (libcst 1.9.0), and coverage.py 7.16.2. All run in a new
scratch venv; --python/V4_PYTHON names its interpreter, including every v4 sandbox worker.
mutmut.mutation.file_mutation.create_mutations(filename, source) returns a parsed module
and individual original/mutated CST node pairs; each full mutant uses module.deep_replace.
This avoids mutmut 2.5.1's stateful incremental source-string mutation API. Only mutmut
supplies mutants. Coverage.Coverage(branch=True) gives line/arc data; PythonParser provides
measurable function-body statements and possible branch exits. The tracer remains for C3
subconditions, boundaries, equivalence classes, dynamic DU, loops, output and decision pairs.
Frozen v3 templates, slots, gates, G-prime, ranking, DU dedupe, K=3 and placebo rules remain.
Old outputs and commands retain their historical behaviour.

The user approved re-implementing parts of TrickCatcher (DPP-style reference panel) and
DeCon (postconditions) under AGENTS rule 2 on 2026-10-11. This build does not implement a
new oracle: stage-2 assertions remain o0. The main session subsequently re-oracles every
input of every arm with oracle_b01.py; that file is protected. V4 bundles preserve the full
source of every shown MUTANT, including placebo_meta mutants. tasks.json and eval.jsonl
retain the existing assertion schema src/canon/put/hits.

V4 uses B5 preconditions: re-mine into out/precond_qwen7b_v4 using the unchanged v3m2
observation/confirmation/code prompts, with evidence-substring filtering disabled. Keep
evidence for reporting; semantic base/doctest verification is unchanged. Never add mined
predicates or conditions to the assertion/oracle/paper prompts. Enforce them mechanically
with assume(valid) and the stage-1 filter. Only domain strategy mining receives the surviving
condition text. Domain mining gets the signature/docstring, without PUT body or base tests.

Once per task, shared by facts/toolinput/hybrids: cached Qwen2.5-Coder-7B-Instruct strategy
at temperature 0, top_p 1, max_tokens 4096, seed 20261010+task. Persist prompts, replies,
code, verification, failures, fallback flag and hashes in out/strategy_qwen7b/<task>.
The following domain prompts are verbatim (v4_prompts.py):

SYSTEM:
```text
Write a Python Hypothesis input strategy from the supplied specification.
```
DOMAIN:
```text
Write def strategy(): returning a hypothesis.strategies strategy whose draws are positional argument tuples for the supplied function. Describe the input domain in the specification. The surviving mined conditions below are domain information; the harness applies the validator mechanically. Use only hypothesis.strategies (available as st), pure builtins and pure string methods. No other imports, I/O, global state, decorators, mutation, or execution of the function. You may use local variables, lambdas, st.map/filter/flatmap and st.builds. Every draw must have the correct arity and be literal-roundtrippable. Reply with Python code only.
```
Append exactly `\n\nSPECIFICATION:\n` + AST signature/docstring and
`\n\nSURVIVING CONDITIONS:\n` + JSON condition-text list. A syntax allowlist permits only
st strategies and pure operations; generated code executes only under unshare -rn python -I -B
with stripped environment. Verify up to 100 distinct valid draws / cap 500: all encountered
draws must have the right arity and roundtrip through literal_eval(repr(...)); at least one
must pass B5. Oversize draws (>1000 repr characters) are rejected. One correction request
with the error; after a second failure use st.tuples(st.from_type(annotation), ...).
Unannotated parameters use object; record missing annotations and fallback verification,
including no-valid-draw cases. A domain can be finite, so fewer than 100/400 draws is recorded.

Facts: explicit task seed 20261010+task; database=None, deadline=None, generate phase only,
suppress too_slow/filter_too_much; assume(B5 valid), at most 400 distinct valid inputs and
2000 body-level candidate attempts, excluding positional base inputs. Hypothesis can stop
early for finite domains or internal filtering exhaustion. Record attempts, checked, accepted,
invalid, duplicate, oversize, nonliteral, wrong arity, errors and validity/yield. Base tests stay
unchanged. Store all 133 non-design tasks in out/facts_v4, without method-side plus labels.

| Arm | Round 1 | Round 2 |
|---|---|---|
| plain | Existing direct plain assertion prompt | none |
| concept | Existing concept assertion prompt | none |
| toolinput | B5-valid Hypothesis witnesses of shown facts -> existing shared o0 oracle prompt | none |
| gen-plain | Verbatim TrickCatcher generator prompt, same v4 venv cyaron sandbox and retry -> B5 filter -> shared o0 oracle | none |
| concept-hybrid | Exact concept round-1 request/result, shared cache | Missed shown facts -> targeted Hypothesis strategies -> up to 2 hitting inputs/fact -> shared o0 oracle -> merged assertions |
| placebo-hybrid | Existing placebo assertion prompt | Same missed-fact procedure for placebo facts |
| plain-hybrid | Exact plain round-1 request/result, shared cache | Exactly as many round-2 strategy requests (including corrections) as concept-hybrid for the task/sample; unguided strategy and up to 2 seeded valid inputs/request -> shared o0 oracle -> merged assertions |

Round-1 fact_hit uses only B5-valid assertion calls. Targeted requests see fact text, PUT,
spec, original tests, round-1 assertions and the task's shared domain strategy. Draw up to
100 distinct valid inputs with cap 500, retain hitting inputs, retry once on none/error.
Control requests see no fact; no extra control retry beyond the matched request count.
Strategy completions use temperature 0/top_p 1/max_tokens 4096. Assertion and oracle calls
keep the previous temperature .7/top_p .95/max_tokens 1024. Seeds are deterministic by
(task, arm, sample, stage, request, retry). The same oracle prompt is used for every injected
input. One oracle completion per active round 2; no round 2 if all facts were hit. Merge
round 1 then round 2 with exact-source dedupe; cap each completion at 10 assertions and
retain the full merged sequence. Shared round-1 calls are attributed logically to each arm;
physical cache misses remain visible in cache/calls.jsonl. Record assertions, distinct inputs,
valid inputs, logical calls, tokens and strategy requests for every task/sample/arm.

Evaluate o0 with canonical pass/PUT pass, detection, any-of-K, false alarm, fact delivery,
valid inputs, input-only bug revelation, per-kind reach, calls/tokens/timing, assertions/sample
and detection/assertion. For concept vs plain and concept-hybrid vs plain-hybrid,
placebo-hybrid, concept, toolinput and gen-plain: report raw paired task detection and
budget-matched paired detection, truncating BOTH ordered assertion sequences to
m=min(the two counts) for that task/sample (including m=0); save every m. No selection by
assertion success. False alarms are classified in this priority: contract-invalid,
mined-invalid, canonical-raises; then literal expected==PUT output (copied-the-bug),
type/format mismatch (including explicit spec-unordered sequence ordering and quote
format), float tolerance (isclose rel_tol=abs_tol=1e-6), other wrong oracle. These are
heuristic diagnostic classes, never an oracle rewrite. Preserve assertion src/canon/put/hits
and annotate class/input validity. Report DEV as primary, pilot separately and each split
all/without doc_fail/doc_fail-only.

Primary comparisons: concept-hybrid vs plain-hybrid (method vs generate-more control),
concept-hybrid vs gen-plain (paper baseline), concept-hybrid vs placebo-hybrid (content),
and concept-hybrid vs toolinput. Also concept vs plain and hybrid vs concept. Existing
dev-gating/post-pilot-design caveats continue to apply. No new gates follow from these results.

DEV-only offline: out/offline_v4, frozen offline_v3m2 metric definitions, overall/even/odd,
selected K=3/5, random 2000 draws, ceiling, placebo, per-kind and per-task tables, v4 vs
v3m2 vs v3c vs v3f; fuzz validity v4/B5 vs v3c/contract and reach by kind; explicit string-format
tasks 17/19. Exclude pilot/design before scheduling plus workers. Warn on version-label
mismatches (hash-order-dependent list(set(...)) on 34/58) and keep all per-version labels.
CPU build verification uses canned fake HTTP replies only for DEV 2/3/4/17 and method-only
157. No paid API, real LLM, Kaggle, commit/push or index mutation in this preparation.


## tc-full (TrickCatcher re-run with Qwen)

Registered 2026-10-11 before this arm's canned smoke. The user approved a faithful
TrickCatcher reimplementation under AGENTS rule 2 on 2026-10-11. Primary source:
Liu et al., ACL 2025, Sec. 4, Algorithm 1, App. A/B; released artifact commit
`a0d285a77efff7c93fc280d606497d9de5e1defe`. The method's only intentional change is
Qwen2.5-Coder-7B-Instruct, served through the existing llm_client.Client and
QWEN_BASE_URL. The dataset is our 133 non-design tasks (113 DEV, 20 pilot), with
unchanged PUTs, base check(candidate) tests and splits. Prefer
out/tasks_v4_all.json when present, otherwise out/tasks_v3m_all.json; persist the
selected source and its SHA256. Exclude design IDs 22/33/111/122/123/139.

Ten independent PUT-guided variants per task use the artifact genprog_tc_sys/usr
verbatim, substituting the complete PUT source for {function_and_docstring}.
Keep exactly the variants passing HumanEval check(candidate). Four independent
input generators use geninput_generator_sys + geninput_usr verbatim with the
same PUT source. Each sample_one is seeded and called 100 times in the v4 venv
with cyaron 0.7.0. Combine up to 400 successfully returned inputs. Preserve
multiplicities (the artifact input file contains duplicates); the reused worker's
occurrence counts are expanded. Do not filter by contracts, mined predicates,
base inputs or facts. There are no semantic retries, repair calls or fallback
generators/variants. Syntax/generation failures and pool shortages are recorded.

The paper does not specify sampling parameters: choose API defaults temperature
1.0/top_p 1.0 and max_tokens 2048 for both stages. Each request has a deterministic
32-bit seed from the first eight hex digits of SHA256 of
`tc-full/20261011/{task}/{rq2}/{stage}/{index}`. Distinct streams are used for
variant, generator, draw and resample stages and for canonical RQ2 runs. One LLM
generation per task (10+4 calls); K=3 independently seeded samples of 100 pool
positions without replacement. If the pool has fewer than 100 positions, use all
positions without padding and report the shortage. Repeated values at separate
positions remain separate observations. All variants surviving base tests are
used (k=n). No extra LLM calls are made for K or subset analyses.

Algorithm 1: run PUT and every surviving variant on each input; drop crashed or
timed-out executions. Discard input when PUT has no output. Ignore all variant
outputs equal to PUT's. Among the remaining outputs select the most frequent;
if none remain, discard input. Exact equality uses Analysis/utils.py:to_hashable
(recursive lists/tuples -> tuples, dicts -> frozenset of key/value pairs), without
float tolerance. Ties for emitted assertions choose the first generated surviving
variant's group. The paper does not specify an emission tie-break. Container
assertion sources include a self-contained _tc_output normalizer to express the
artifact equality; scalar assertions are `assert f(args) == expected`.

Operational bounds: source loading 5 seconds, base check 20 seconds, each call
1 second; namespace worker total timeout is bounded by the worst-case call
budget, and generator workers have 120-second total timeout. All generated code
runs only under `unshare -rn <v4-venv-python> -I -B`, with no credentials in its
environment and worker resource limits. Reuse the existing generator worker's
literal/JSON roundtrip, arity and 65536-character transport checks; these are
representation/execution bounds, not an input-validity filter. Nonliteral output
expectations cannot be serialized as assertions and are recorded as serialization
errors. Use fresh output directories if source/configuration hashes change.

Labels only: HumanEvalPlus-v0.1.10 prompt+canonical_solution gives the canonical
output; prompt+contract validates input. These never select inputs, filter
variants or choose main-run expected values. TP = contract-valid and canonical
output equals selected expected output; FP = otherwise (including invalid inputs
and canonical failure). Persist src/canon/put/hits plus validity in eval.jsonl.
Our metrics: detecting samples, detection/sample, any-of-K, assertions/sample,
false alarm fraction, logical generation calls/tokens and physical cache-miss/
transport counts; DEV and pilot remain separate, with an all-task summary.
Each task/sample also records emitted precision TP/(TP+FP), undefined if no tests.

Paper analysis is recorded separately from the single-tie emission metrics.
Reproduce ep_compute_res(tc): for each subset among C(n,min(k,n)), k=2..10,
include every tied maximal-vote disagreeing group per sampled input; let p be
TP/(TP+FP) among those reports, then add p to weighted TP and 1-p to weighted FP.
A subset with no reports contributes zero to both. Divide each sum by the total
number of subsets for TP_rate/FP_rate. Per-PUT paper precision is weighted
TP/(TP+FP); notebook recall is sum(TP_rate)/number of PUTs, precision is the mean
among emitting PUTs, and F1 is their harmonic mean. Repeat-level metrics are
averaged across K. Also record expected FP-program count = sum(FP_rate), matching
RQ2's notebook. These artifact-weighted quantities are not binary detection.

RQ2 repeats exactly the same 10-variant/4-generator method, generating BOTH from
canonical code, with its own seeds/cache/output out/tcfull_qwen7b_rq2 and K=1.
Report the count out of 133 canonical programs with >=1 reported test, plus
invalid-input reports and expected FP-program counts by k. Main output:
out/tcfull_qwen7b. Expected logical requests: 1330 variants + 532 generators =
1862 main, another 1862 RQ2, 3724 combined (transport retries counted separately).
No real LLM call, paid API, Kaggle action, commit/push or git-index mutation is
part of build/CPU smoke verification. Fixtures: DEV 2/3/4 and pilot 157, including
a canned correct and buggy variant, crashes, a majority agreeing with PUT,
contract-invalid reported inputs, RQ2, reader compatibility and paper metrics.

Verbatim templates follow. They are byte-identical files copied using git show
from the pinned artifact; all four SHA256 values are checked on every gen/run.

### genprog_tc_sys (SHA256 5d38456f5861453a96ebb691f1794876913f08688392fd3a5626907cba5471ad)

```text
**INSTRCUTION**:
You are a professional developer, skilled at identifying bugs and logic flaws in code.
You will receive a Python function, and the comments below the function signature is the docstring that specifies the requirement of the function.
Please carefully check if the function has correctly implemented the requirements of the docstring. if there is any bug in the existing code, please reply a repaired correct implementation.
Please reply with ONLY the whole completed function code without any other content.
```

### genprog_tc_usr (SHA256 ce7b4adbf8d6c00a4f855191256c76ef7bf7dbad18362a8e0f73b1d3e3129317)

```text
**Function and Docstring**:
{function_and_docstring}
```

### geninput_generator_sys (SHA256 4c9164d6fabaebe04301471c690cfa927eef4b2e39d80561b6125da06c35017d)

```text
**INSTRCUTION**:
You are a professional software testing engineer. 
You will get a Program Under Test (PUT), and the comments below the function signature is the docstring that specifies the requirement of the PUT.

Please write an input generator in Python for generating test input for THE PUT (DO NOT generate outputs).
The generator should be a single Python function named 'sample_one()' and return a list of input parameters for PUT.
Each parameter of the generated inputs must adhere to the type and format according to the function signature of PUT. And the format of return value should be list of parameters and should NOT be dict.

You can use the python library random to generate random float and int, for example:
from random import *
# Generate a random integer between 0 and 9
random_number = randint(0, 9)
# Generate a random floating-point number between -1.0 and 1.0
random_float = uniform(-1.0, 1.0)

You can use the python library cyaron to generate random string, for example:
from cyaron import *
ALPHABET_SMALL = string.ascii_lowercase
ALPHABET_CAPITAL = string.ascii_uppercase
ALPHABET = ALPHABET_SMALL + ALPHABET_CAPITAL
NUMBERS = string.digits
str = String.random(5) # Generate a random string with 5 letters consisting of lowercase letters
str = String.random(10, charset=ALPHABET_SMALL) # Generate a random string with 10 letters consisting of lowercase letters
str = String.random(10, charset=ALPHABET_CAPITAL) # Generate a random string with 10 letters consisting of uppercase letters
str = String.random(10, charset=NUMBERS) # Generate a random string with 10 letters consisting of digits letters
str = String.random(10, charset='#.') # Generate a random string with 10 letters consisting of '#' and '.'

Please reply with ONLY the code of the input generator without any other content.

**EXAMPLE**:
Here is an example of how to write input generator:

If the given function and docstring is like:
```python
def has_close_elements(numbers: List[float], threshold: float) -> bool:
    """ Check if in given list of numbers, are any two numbers closer to each other than
    given threshold.
    >>> has_close_elements([1.0, 2.0, 3.0], 0.5)
    False
    >>> has_close_elements([1.0, 2.8, 3.0, 4.0, 5.0, 2.0], 0.3)
    True
    """
    for i in range(len(numbers)):
        for j in range(i + 1, len(numbers)):
            if abs(numbers[i] - numbers[j]) <= threshold:
                return True
    return False
```

Then your reply should be like the following content:
```python
from random import *
from cyaron import *
def sample_one():
    numbers=[]
    length_of_numbers=randint(0,10)
    for i in range(length_of_numbers):
      numbers.append(uniform(-5,5))
    threshold=uniform(-10,10)
    generated_input=[numbers,threshold]
    return generated_input
```
```

### geninput_usr (SHA256 ce7b4adbf8d6c00a4f855191256c76ef7bf7dbad18362a8e0f73b1d3e3129317)

```text
**Function and Docstring**:
{function_and_docstring}
```

### v4 amendment (2026-10-11, facts stage, before any v4 arm output)
Six tasks (8, 41, 46, 55, 63, 130; recursive/numeric functions) exceeded the 3600 s facts-worker budget in the first
v4 facts run (the whole stage aborted at 127/133). Rule: a task whose facts worker exceeds the budget gets no facts
(empty top-3 and placebo, `timeout: true`), exactly like a task without reachable facts; its concept prompts equal
plain. The six records were written with the same provenance markers instead of re-running the same budget; no
other setting changed. Reported separately in the v4 results.

### v4 amendment 2 (2026-10-11, arms run, before any v4 arm output was evaluated)
The first v4 arms run aborted at 19:29 when one classification sandbox (final-assertion inputs) exceeded its 900 s
budget. Fix: a failed classification sandbox now returns an empty, recorded result (`classification_error`) instead
of aborting the run, the same rule already used for gen_inputs.classify in the v3m2 run. Because the run manifest
hashes the sources, the arms were rerun into `out/gen2_qwen7b_v4b/` with the LLM response cache copied (identical
requests are not re-sent). The aborted directory was moved unchanged to the session scratch folder.
The v4 offline worker also exceeded its 3600 s budget on exactly these six tasks (they have no v4 facts); their
HumanEval+ labels (n_plus, n_fail) were copied from offline_v3m2 (same PUT, same inputs) with empty fact lists.

### v4 amendment 3 (2026-10-11 ~20:30, after the v4 offline report, before any v4 arm output was evaluated)
The v4 offline report showed 90/133 LLM domain strategies falling back to `st.from_type`; 75 of them are
one-parameter functions where Qwen's strategy draws the argument itself (e.g. `st.text(...)`) instead of a 1-tuple,
which the draw worker rejected as wrong arity. Fix in the draw worker (applies to domain verification, fact fuzz and
hybrid round-2 strategies alike): for a one-parameter function a non-tuple draw is wrapped as `(x,)`, and a list of the
right length is converted to a tuple. Prompts, model, seeds, gates and ranking are unchanged. The v4 run with the
broken strategies (facts_v4, offline_v4b) is kept and reported as the registered v4; its arms run (gen2_qwen7b_v4b)
was stopped unevaluated. The fixed pipeline writes strategy_qwen7b_v4c, facts_v4c, tasks_v4c_all.json, offline_v4c,
gen2_qwen7b_v4c, reusing cached LLM responses.

### v4 amendment 4 (2026-10-11 ~21:30, v4c facts stage, before any v4c offline/arm output)
The v4c facts run again exceeded the 3600 s facts-worker budget on exactly the same six tasks (8, 41, 46, 55, 63, 130;
none of them is a strategy fallback). Same rule as v4 amendment 1: they get timeout records (no facts, concept prompts
equal plain) with the v4c validator/strategy hashes and the same provenance markers; the facts stage is then re-run to
assemble `tasks_v4c_all.json` from the cache. Their v4c offline records are written before the offline run (the v4 offline worker exceeded 3600 s on them while
computing HumanEval+ labels; PUT, inputs and B5 validator are identical in v4c): labels copied from offline_v3m2 as in
v4 amendment 2, empty fact lists.

### v4 amendment 5 (2026-10-11 ~23:10, v4c evaluation, before any v4c score was read)
The first v4c evaluation aborted at task 41 (car_race_collision, an n^2 PUT): its 1800 s per-task sandbox was spent
re-tracing the same large inputs (n up to 12345) for every assertion of every arm and sample (177 assertions, 37
distinct inputs). Fix in `v4_evaluation.worker`, diagnostics only: each distinct input's coverage/fact hits and PUT
output are computed once per task and reused; an input whose assertion already timed out on the PUT (5 s) is not traced
again (put_status Timeout, hits false, `trace_skipped`). Assertion statuses (canon/put pass/fail), hence detection and
false alarms, are computed exactly as before. Check: task 40 re-evaluated byte-identical; task 41 now takes 28 s. The
aborted job directory was moved unchanged to the session scratch folder and the evaluation re-run from scratch.
Addendum (~23:30): the re-run hung again at task 41, this time idle (0% CPU, one thread waiting on a futex): a SIGALRM
arriving just after its timer was cancelled raised inside coverage.py's locked bookkeeping and the lock was never
released (three hung classify workers from the stopped v4b run show the same state; they were killed). Further fixes,
evaluation only: inside the evaluation worker the alarm handler ignores signals that arrive after the timer is
cancelled; an input whose step-budgeted PUT call times out is not traced (hits false); a failed per-task sandbox is
retried up to twice with a 600 s budget. Task 40 is still byte-identical and task 41's assertion statuses are unchanged
(21 s). The second partial job directory was also moved to scratch and the evaluation restarted from scratch.

## v5 plan (registered 2026-10-11 ~23:30, approved by the user: steps 1 then 2 sequentially, step 3 in parallel)

Motivation. The user's intent for Hypothesis was "only when stuck": keep the v3 fuzz (perturbing base-test inputs) and use
an LLM-written Hypothesis strategy only for gaps the fuzz cannot reach. v4/v4c instead replaced the fuzz everywhere and
lost offline strength (v3m2 44/112 strong@3, v4c 29/112). Diagnostics on v3m2 (dev): 1,750 facts, 297 never reached
by the fuzz (73 tasks; BOUND 156, SHAPE 54, OUTCOME 32, NUM 30), 36 dev tasks show no fact. All three steps start
from the v3m2 setting (out/precond_qwen7b_v2 validators, v3 fuzz, tracer, frozen gates/ranking/K=3, placebo rules).
Defaults of existing code paths stay byte-identical; every new output goes to a fresh directory.

### Step 1: mutant-source ablation (offline only, no LLM)
v3m2 facts with exactly one change: mutants come from mutmut 3.8.0 (the v4 operator mapping in v4_tools, the frozen
80-point sampling strata of v4_facts) instead of facts.make_mutant. Outputs out/facts_v3mm, out/tasks_v3mm_all.json,
out/offline_v3mm (DEV only). Reported next to v3m2 with the same offline metrics (selected/ceiling/random/placebo@3,
per-kind). Decision rule for step 2: v5 uses mutmut mutants iff v3mm selected@3 strong >= v3m2's 44/112; otherwise
the hand-written mutants.

### Step 2: v5 facts (v3 fuzz + per-gap Hypothesis fallback)
Base: the facts of step 1's chosen mutant source. For every fact the fuzz did not reach (all 133 tasks; at most 10 per
task, in frozen fact order), one Qwen request writes `def strategy()` for inputs that reach that fact. Prompt: the v4
TARGET instruction with the specification, PUT, existing tests and the fact text; the base-test inputs are given as
examples in place of the v4 domain strategy. One corrective retry on verification failure (v4 RETRY prompt). Draws use
the v4c draw worker (arity fix) with the v3m2 mined validator as the hard filter, at most 200 attempts per gap. The first
valid draw that reaches the fact (same reach rule as the fuzz) becomes its witness; the fact counts as reached and all
facts then pass the unchanged gates and ranking. Seeds follow the v4 scheme with a new stage tag. Outputs:
out/strategy_qwen7b_v5, out/facts_v5, out/tasks_v5_all.json, out/offline_v5 (DEV). Primary offline comparison:
v5 vs v3m2 selected@3 strong (sign test over tasks as in v3). Arms on v5: the six v3m2 arms plus step 3's arm,
K=3, out/gen2_qwen7b_v5, run regardless of the offline result; scored by o0 and re-oracled with ref/full.

### Step 3: combined arm `concept-toolinput` (on the v3m2 bundle, parallel to steps 1-2)
One prompt per sample: the concept prompt (same header, the same top-3 fact sentences) where each fact that has a
witness is followed by that input ("An input that reaches this: `f(x)`") and the toolinput instruction "Write an
assertion for each of these inputs; you may add others." Facts without a witness stay as sentences; tasks without
facts get the plain prompt (as concept does). Arm appended after the existing arms (existing seeds unchanged), K=3,
133 tasks, out/gen2_qwen7b_v3m2_ct with the v3m2 response cache copied. Scored by evaluate.py (o0) and re-oracled
with ref and full (oracle_b01, parameterised run/out directories; the ref programs per task are reused).
Primary: concept-toolinput vs toolinput, per-task sign test on DEV under ref. Secondary: vs concept, vs plain, and
against the post-hoc two-call unions (concept+toolinput 68.0, plain+toolinput 68.7, toolinput x2 65.0 detections per
sample under ref).
Clarification (step 2, before implementation): the single corrective retry is used when the first strategy fails
verification (syntax/draw errors) OR when its valid draws never reach the fact; the RETRY prompt then carries the error
text or "N valid draws, none reached the fact". Each of the (at most two) strategies gets its own 200 draw attempts.
Addendum 2 (~23:45): run 3 stopped at task 68 because the evaluation sandbox result exceeded the 8 MB output cap: rows
carried the gen-plain raw generator candidates (24 MB for task 68) into the job and back. The evaluation now passes
generator attempts without their raw candidate lists (their count is kept; gen.jsonl keeps them). Scoring inputs are
unchanged. Run 3's job directory was moved to scratch and the evaluation restarted.

### v5 step 1 result (2026-10-12 00:03) and step-2 choice
v3mm (v3m2 with mutmut mutants) offline DEV: selected@3 strong 43/112 (v3m2 44/112), ceiling 49 (53), random 42.2
(45.0), placebo 10 (13); MUTANT facts reached 181 (220), MUTANT strong tasks 33 (33). By the registered rule
(mutmut iff >= 44) v5 uses the hand-written mutants. Step 2 started with `--mutant-source handwritten`.

## Input-validity filters (registered 2026-10-12 ~00:40, user-approved; three separate sub-versions, never combined)
Motivation: under the ref oracle 478/575 remaining false alarms (83%) on the v3m2 dev inputs are EvalPlus-contract-
invalid inputs; plain/concept assertions are not filtered at all today. Each filter drops an assertion whose input it
judges invalid, BEFORE scoring; it is applied post hoc to the same inputs (v3m2 six-arm run; later also the
concept-toolinput and v5 runs) and reported per oracle (o0, ref, full) next to the unfiltered numbers. The EvalPlus
contract stays labels-only and is used only to measure each filter (invalid caught / valid wrongly dropped / detecting
assertions lost).
- F1 mined-validator filter: the task's v3m2 mined precondition (out/precond_qwen7b_v2/<task>/valid.py, the same
  validator lane A uses) must return True on the input; errors count as invalid. No LLM.
- F2 reference-crash filter: among the task's surviving ref programs (B2, >= 3), if at least half raise or time out on
  the input, it is judged invalid. No LLM. (Under the ref oracle such inputs already abstain; F2 matters for o0/b1.)
- F3 LLM validity judge: Qwen sees only the specification and up to 10 calls per request ("does each call satisfy every
  input requirement the specification states or clearly implies? VALID/INVALID"), 3 samples at temperature 0.7,
  invalid if the majority says INVALID; missing answers count as VALID. One-time requests per unique call, cached.
Primary readout per filter: dev FA% and detections/sample under ref and full for each arm, and concept vs plain
(per-task sign test). Script: validity_filters.py (outputs out/validity_filters/).

## Property concepts, step A (exploratory, registered 2026-10-12 ~00:55, no LLM)
Context: the user proposed concept-guided property discovery (property-concept taxonomy: structural, relational,
boundary, algebraic, metamorphic) after arXiv 2510.25297 (PBT vs EBT; their PBT_EdgeCases pilot used input-side
concepts only). The course-vocabulary requirement for concepts is lifted (user, 2026-10-12). Step A measures whether
spec-derived properties have bug-finding power in this setting before any new prompt is built: the B3 postconditions
already produced for the v3m2 inputs (5 per task, Qwen, spec-only; kept iff they hold on every base-test pair) are used
as the oracle. For every dev task and every contract-valid input in the pooled v3m2 inputs (all six arms), a kept
property "detects" when it is violated by PUT(x) and holds on canonical(x); it is a false alarm when violated by
canonical(x). Reported: tasks detected by properties alone, false-alarm tasks/pairs, PUT-crash detections separately,
and the ref oracle's detections on the same input pool for comparison. Script: property_oracle.py.

### v5 step 2 re-run note (2026-10-12 ~01:00)
The v5 facts stage stopped with "strategy manifest mismatch": the mining manifest pins PREREG.md's hash, and unrelated
sections (input-validity filters, property step A) were appended between mining and facts. The mining directory is
moved unchanged to scratch; mining is re-run into a fresh out/strategy_qwen7b_v5 with the LLM response cache copied
(identical requests, no new responses), then facts and offline, with no PREREG edit until the offline report exists.

### v5 step 2 result (2026-10-12 01:40) and arms deviation
Hypothesis strategies reached 10 of 276 unreached gaps (3.6%). The v5 bundle differs from v3m2 in 4 tasks only (dev 20,
23; pilot 70, 151); dev tasks with facts 78 (v3m2 77). Offline DEV: selected@3 44/112, ceiling 53, random 45.0, placebo 13
(identical to v3m2). Deviation from "arms on v5 regardless": for the other 129 tasks the v5 arm prompts are byte-identical
to the v3m2 run, so their v3m2 rows (and the concept-toolinput rows of out/gen2_qwen7b_v3m2_ct) stand for v5; only the 4
changed tasks are run (seven arms, K=3) into out/gen2_qwen7b_v5_changed and merged for v5 reporting. Reason: the GPU
budget left tonight (~3 h) is needed for F4 and the oracle runs; the full re-run would only re-sample identical prompts.

### Input-validity filters addendum: F1b and F4 (registered 2026-10-12 01:40, before any F4 output)
A coverage audit (scratch constraint_concepts/; EvalPlus contracts used only as yardstick) found the main loss in the
v3m2 mining is the evidence-substring filter (126 spec-supported atoms dropped), and that the B5 validator already in
out/precond_qwen7b_v4 (same prompts, filter off) flags 283/591 contract-invalid observed calls vs 71 for v3m2, with 48
valid calls flagged (0.40%). Two further sub-versions, reported separately like F1-F3:
- F1b: the B5 validator (out/precond_qwen7b_v4) as the filter. No new LLM calls.
- F4: concept-guided mining. Same pipeline and settings as B5 (Qwen, temperature 0, seeds, confirmation and code
  prompts, verifier on base tests, evidence filter off); only the observation prompt changes to walk a generic
  input-constraint taxonomy (S1-S4 structural, B1-B3 boundary, R1-R3 relational, F1-F3 format, D definedness,
  A arithmetic, with quantifier scope over elements / nesting / numbers inside strings). The taxonomy was derived from
  even-numbered dev tasks and pilot only; the prompt carries definitions without task examples
  (precond_concepts.py, out/precond_qwen7b_f4). Held-out reading: odd-numbered dev tasks.
Primary F4 readout: contract-invalid observed calls caught and valid calls wrongly flagged, F4 vs F1b (the clean
ablation: only the observation prompt differs), overall and on odd dev tasks; then FA%/detections under ref and full.

### F4 result and F4b (2026-10-12 02:00, before any F4b output)
F4 vs F1b on the observed v3m2 inputs (contract-invalid caught / valid wrongly flagged): all 211/113 vs 283/48;
held-out odd dev 65/30 vs 146/25; even dev 57/62 vs 54/16; pilot 89/21 vs 83/7. Under ref, FA% falls for both (concept
4.8% -> F1b 2.6%, F4 3.1%) with detections nearly unchanged. F4 is worse than F1b: the category walk makes Qwen turn
what the function tests or returns into input requirements (e.g. "sort the integers between 1 and 9" -> elements in
1..9; the right-triangle condition itself as a precondition) and guess element types from examples. F4b = F4 + three
rules written only from these even/pilot errors (conditions the function tests/filters/returns on are not
requirements; only caller guarantees and annotations; most categories do not apply, empty answer allowed). Same
pipeline/settings, out/precond_qwen7b_f4b; held-out reading on odd dev tasks.

### F5: mined input requirements written into the generation prompt (registered 2026-10-12 02:05, before any output)
Generation-side counterpart of the filters: the plain, concept and toolinput prompts get one extra section,
"Input requirements (mined from the specification)", listing the B5 surviving conditions (out/precond_qwen7b_v4;
121/133 tasks have at least one), placed before the instruction. Everything else, including arm names and therefore
seeds, equals the v3m2 run (paired design: same seed, only that section differs; prompts without requirements are
byte-identical to v3m2). Bundle out/tasks_v3m2_req.json, run out/gen2_qwen7b_v3m2_req (K=3, 133 tasks), scored by
evaluate.py and re-oracled (out/oracle_req). Readout: share of contract-invalid inputs, FA% and detections under ref
and full, per arm vs the same arm in v3m2 (per-task sign test), with and without the F1b filter.

### v3m2-hybrid: the seven v4 arms on the v3m2 facts (registered 2026-10-12 ~02:25, before any output)
On v4c, the hybrid round 2 (targeted Hypothesis strategies for shown facts no round-1 assertion reached) clearly helped
(ref: concept-hybrid vs concept 22/0, plain-hybrid vs plain 14/0) but v4c facts are weak. This run applies the unchanged
v4 arm code (run_v4.py arms, seven arms, K=3) to the v3m2 facts: bundle out/tasks_v3m2_hyb.json = tasks_v3m2_all.json +
B5 validator (out/precond_qwen7b_v4), the v4c domain strategies and full mutant sources (labelled facts_version v4 only
for the format check). Output out/gen2_qwen7b_v3m2hyb_v4, evaluate.py, then oracle_b01 (out/oracle_v3m2hyb).
Primary: concept-hybrid vs plain-hybrid and vs placebo-hybrid under ref (raw and assertion-budget-matched), and
concept-hybrid vs toolinput. A 2-task K=1 smoke runs first into a separate directory.

### v3m2-hybrid result (2026-10-12 ~12:00) and RBCTest step ablation (post hoc, analysis only)
v3m2-hybrid (bundle renamed out/tasks_v3m2hyb_v4.json because run_v4.safe_path requires "v4"; GPU stopped at 04:51,
resumed from cache 09:05). Dev 113 tasks, ref: concept-hybrid 62.0, toolinput 60.7, plain-hybrid 53.0, concept 47.3,
placebo-hybrid 47.0, plain 45.0, gen-plain 41.3. Per task (ref): concept-hybrid vs plain-hybrid 32/14 p=.011 (budget-
matched 29/15 p=.049); vs placebo-hybrid 33/11 p=.001 (matched 21/19); vs toolinput 19/17 (matched 16/33). Budget
matching keeps each sample's first N unique calls (N = the comparator's count), so it mostly removes round-2 tests.
RBCTest step ablation (not registered beforehand; reported as exploratory): rbc_ablation.py rebuilds B5 validators
without the verifier, without the confirmation step (one new code call per task, same prompt/seed), or without both;
scored as filters Rnv/Rnc/Rnn in validity_filters.py (out/validity_filters/gen2_qwen7b_v3m2_rbc/report.txt).

### v6: facts re-fuzzed under the B5 validator (registered 2026-10-12 ~13:30, before any v6 output)
Motivation (RESULTS §11.10): NUM/BOUND facts such as "n was never zero" lead the LLM to inputs the specification
forbids. v6 = v3m2 with one change: the fuzz validator is the B5 precondition set (out/precond_qwen7b_v4, the F1b
filter) instead of out/precond_qwen7b_v2, so facts reached only by inputs violating a mined requirement disappear.
run_v6.py facts -> out/facts_v6; bundle -> out/tasks_v6_all.json and out/tasks_v6hyb_v4.json (same recipe as the
v3m2-hybrid bundle). Offline: offline.py -> out/offline_v6 (dev). Then run_v4 arms (seven arms, K=3) ->
out/gen2_qwen7b_v6hyb_v4, evaluate, oracle_b01 -> out/oracle_v6hyb. Primary: share of contract-invalid inputs and
false alarms of concept/concept-hybrid vs v3m2-hybrid; concept-hybrid vs plain-hybrid under ref. Nothing else changes.

### v7: specification input-class facts for tasks without code facts (registered 2026-10-12 ~15:30, before any v7 arm output)
Motivation: on the 36 dev tasks without v3m2 facts, a blind Codex pass found bugs in 33 (out/codex_nofacts); the 14
tasks it found but concept-hybrid missed are mostly input-class edge cases. v7 = v6 + spec_facts.py: for tasks with no
v6 code fact, up to 3 facts of the form "no existing test passes <param> of class C; the input requirements allow it",
C in LARGE (>= 1000 items / value), DUP (repeated element), NONASCII (non-ASCII letters), SPACE (leading/trailing/
repeated spaces), checked on base-test inputs; witness = fixed transformation of a base input accepted by the B5
validator (no witness call when its literal exceeds 1000 chars). Classes derived from even-numbered Codex-only tasks
(8, 16, 26, 46, 66, 86, 130); odd tasks are held out. Hits of these facts are input-class membership (patched
additively into v4_worker/gen_inputs/evaluate/gen_evaluation; existing facts unchanged). Offline (HumanEval+ labels):
out/offline_v7/report.txt. Arms: run_v4 seven arms on out/tasks_v7hyb_v4.json -> out/gen2_qwen7b_v7hyb_v4 with the LLM
cache copied from the v6 run (unchanged prompts replay), evaluate, oracle_b01 -> out/oracle_v7hyb. Primary: on the 36
spec-fact dev tasks, concept-hybrid vs plain-hybrid and concept vs plain under ref, even/odd reported separately.
- v7 amendment (2026-10-12 ~18:30, after the v7 arms, before any v7 scoring output): gen_evaluation.input_metrics stores
  input_repr truncated to 2000 characters (the task-23 job exceeded the 8 MB sandbox output limit with inputs such as
  'a' * 10**6); scoring is unchanged (assertion sources are re-executed). GPU stopped at 18:08 with 4 plain-hybrid
  samples missing (46/1, 46/2, 63/2, 160/1); a provisional score on the 2789 finished samples uses ref/post only
  (cached), no b1/judge (out/gen2_qwen7b_v7hyb_v4_partial, out/oracle_v7hyb_partial). Registration times written above
  for v6/v7 ("~13:30", "~15:30") are wrong: v6 was registered ~13:15, v7 ~14:20, both before their outputs.
- v7 amendment 2: v4_evaluation.observe also scores spec-fact hits by input-class membership (the first v7 evaluation
  recorded 0 hits for all spec facts because this path was not patched). Detection and oracle scoring are unaffected.

### v7 completion run (2026-10-12 ~19:30)
The v7 arm directory's manifest pins the PREREG/source hashes at its creation, and both changed afterwards (v7
amendments), so the 4 missing plain-hybrid samples are produced by re-running the unchanged v7 bundle into a fresh
directory out/gen2_qwen7b_v7hyb_v4_r2 with the LLM cache copied from out/gen2_qwen7b_v7hyb_v4 (identical requests
replay; only the 4 missing samples call the model), then evaluate and the full oracle (b1, judge) -> out/oracle_v7hyb.

### EvalAndMitigate baselines (registered 2026-10-12 ~19:30, before any output; user-approved port)
Two arms from Zhao, Zhou & Cohen, ISSTA'26 (EvalAndMitigate/Prompt_example), ported to Python/Qwen by Codex in
trickcatcher_linefacts/evalmitigate/: "onlydoc" (tests from signature + original docstring, no code) and "advdoc"
(stage 1 Advanced prompt on the PUT: critique, corrected implementation, final docstring; stage 2 the onlydoc prompt
with the generated docstring, no code). K=3 on out/tasks_v3m2_all.json; scored with evaluate.py and oracle_b01
(ref/full). Primary: concept-hybrid (v3m2-hybrid run) vs advdoc and vs onlydoc per task under ref; secondary: false
alarms and the copied-the-bug class. The paper's own fix-then-diff is NOT part of this (user decision).

### advdoc-hybrid (registered 2026-10-12 ~21:40, before any output; user request)
Our round 2 on top of the paper's Advanced Doc tests. Round 1 = the advdoc assertions of the same (task, sample) from
out/gen2_qwen7b_evalmitigate. Round 2 exactly as run_v4's hybrid arms on the v3m2 facts (out/tasks_v3m2hyb_v4.json):
"advdoc-hybrid" asks a targeted Hypothesis strategy for each shown concept fact no valid round-1 input reached (one
retry), "advdoc-plainhybrid" uses the CONTROL prompt with the same number of requests (no retry). Expected values for
the injected inputs are written from the signature + the advdoc-generated docstring only (no code), in the paper's
spirit. Implemented as a clone of run_v4 (run_v4.py itself unchanged) in evalmitigate/. Scored with evaluate and
oracle_b01 (ref/full). Primary: advdoc-hybrid vs advdoc-plainhybrid and vs advdoc under ref.

## Held-out confirmation on MBPP+ (registered 2026-10-12 ~22:05, before any PUT or output exists)
Every result above was selected on the 113 dev tasks (RESULTS §11.19). Confirmation set: MBPP+ v0.2.0 (EvalPlus,
378 tasks, downloaded to out/heldout_mbpp/raw). PUTs: Codex writes one solution per task blind (it sees only the MBPP+
prompt text and the entry-point name; no canonical solution, no base/plus inputs, no contract). A PUT is kept iff it
passes all base inputs (expected from the canonical solution) and fails at least one plus input; base tests for the
harness are HumanEval-style check() functions over the base inputs. Labels (canonical, plus inputs, contract) are used
only for this selection and for scoring, as in TrickCatcher's construction. Frozen configuration, run once, no tuning:
facts v6 recipe (fuzz validated by B5-style mined preconditions, mined afresh for MBPP+ with the unchanged prompts),
run_v4 arms (plain, concept, toolinput, gen-plain, concept-hybrid, placebo-hybrid, plain-hybrid), K=3, oracle_b01
ref/full. Primary: concept-hybrid vs plain-hybrid under ref (per task sign test); secondary: concept vs plain,
concept-hybrid vs toolinput, concept-hybrid vs placebo-hybrid.
- Held-out amendment (2026-10-12 ~22:30, before any arm output on MBPP+): pass 1 (Codex default model) gave 42 PUTs
  (out/heldout_mbpp/filter/summary3.json; numeric comparison tolerant as EvalPlus, plus failures counted only on
  contract-valid inputs). A second blind pass with a weaker Codex model (gpt-5.6-luna, effort low) writes into
  out/heldout_mbpp/blind_luna/ under the same rules; a task contributes one PUT, pass 1 first, else pass 2.
- Pass-2 attempt 1 (gpt-5.6-luna, effort low; session log confirms the model) is discarded: it generated all 378 files
  from one template script (`*args` signature, boilerplate), and all 378 fail to parse
  (kept as out/heldout_mbpp/blind_luna_try1_template). Attempt 2 uses the same model and rules with an explicit
  instruction to write each function individually.
- Held-out amendment 2 (2026-10-12 ~23:00, before any arm output): a third blind pass by Claude Haiku (user request)
  on the 322 MBPP+ tasks pass 1 solved correctly, into out/heldout_mbpp/blind_haiku/ under the same rules; a task
  contributes at most one PUT (pass 1, then pass 2, then pass 3). Manual real-bug/ambiguous labels are assigned before
  any arm output.
- Pass 3 result (2026-10-12, before any arm output): Haiku wrote 322/322 files, all parse, no duplicate files.
  Filter (out/heldout_mbpp/filter_haiku/summary.json, same worker and rules): 10 PUTs, 5 on tasks without a pass-1/2
  PUT (93, 223, 264, 453, 792; puts.json "pass3_only"). Manual labels: real bug 93 (negative exponent returns 1),
  264 (int() truncates 10.5), 453 (square-root factor counted twice); ambiguous 223 (all 58 failures use n != len(arr),
  against "its length (n)"), 792 (canonical counts only top-level list elements). Held-out total 58 PUTs, 12 real bugs.
- Held-out amendment 3 (2026-10-12 ~23:05, before any MBPP+ bundle, fact or arm output): the facts recipe is the final
  dev method v7 (= v6 code facts; spec input-class facts only for tasks with no code facts), since v7 finished as the
  selected configuration on dev (RESULTS §11.21). Mining reuses run_v4 `mine` (B5 preconditions + domain strategies,
  v4c draw worker), unchanged prompts/seeds. Oracle ref/full only (TrickCatcher's released dpp/tc variants do not exist
  for MBPP+). Analysis: primary on all 58 PUTs (puts.json pass1 + pass2_only + pass3_only); secondary on the 12
  manually labelled real-bug PUTs (labels_manual.json), reported separately, no other subsets.
- advdoc-hybrid amendment (2026-10-12 ~23:10): the Qwen endpoint went offline (ngrok 404) at 23:05 while the last
  sample (160/1 advdoc-plainhybrid, round-2 request 2) was running; 797/798 samples are finished. Provisional scoring,
  labelled as such: out/gen2_qwen7b_advhyb_v4_partial (gen.jsonl from the finished result.json files) -> eval.jsonl
  -> out/oracle_advhyb_partial (ref/post from the v3m2-hybrid cache, score without LLM: no b1/judge); paired
  comparisons drop task 160. The final run resumes the same generate command from cache when the endpoint is back.
- Held-out amendment 4 (2026-10-12 ~23:45, user decision, before any MBPP+ fact, mining or arm output): the MBPP+ run
  uses only the 12 manually labelled real-bug PUTs (93 99 126 161 239 244 264 267 453 594 620 765), root
  out/heldout_mbpp_real12 (`heldout.dataset build --out .../he --ids ...`, `heldout.run --root ...`); the 46
  ambiguous-spec PUTs are not run. Same frozen v7 configuration and comparisons; with 12 tasks the per-task sign test
  is significant at .05 only from 10/2 (or 9/0), so this is a small confirmation, reported as such.

## v8-strict: round 2 without self-added tests (registered 2026-10-13 ~00:20, before any v8 output)
Finding (RESULTS §11.26): the round-2 call reuses the toolinput prompt ("write an assertion for each of these inputs;
you may add others", up to 10), and with no selected input it is a fresh plain call. concept-hybrid keeps fewer
round-2 inputs (hint-hitting only), so it gets more such free calls than plain-hybrid; part of concept-hybrid >
plain-hybrid is therefore not from the hints. Fix (user request, "cho công bằng"): round 2 contributes exactly the
selected Hypothesis inputs, nothing else, and no call is made when none is selected.
- CPU construction now (exact for ref/full, which ignore the written expected value): from the v7 run
  (out/gen2_qwen7b_v7hyb_v4_r2) rebuild concept-hybrid, plain-hybrid and placebo-hybrid as round-1 assertions + one
  assertion per selected input (Qwen's own assertion for that call if it wrote one, else a placeholder `== None`);
  every other arm copied unchanged. -> out/gen2_qwen7b_v8strict_est (v8_strict_est.py) -> evaluate (o0 numbers of
  the three rebuilt arms are not meaningful) -> out/oracle_v8strict_est (ref/post from the v7 cache, no LLM: no
  b1/judge; all arms scored in this same dir). Primary: concept-hybrid vs plain-hybrid under ref, per-task sign test;
  secondary: vs toolinput, vs placebo-hybrid, under full.
- A GPU version (strict prompt that only asks expected outputs for the selected inputs) is needed only for o0/b1.
- v8-strict result (2026-10-13 ~00:40): see RESULTS §11.27. Primary concept-hybrid vs plain-hybrid (ref) 29/20, p = .25
  (not significant); secondary matched-count 34/17 (p = .024), vs placebo-hybrid 33/13, vs toolinput 22/23.

## Run plan and serving environment (registered 2026-10-13 ~01:30, before any of these runs)
Serving: Kaggle's image moved to Python 3.13, where `pip install vllm==0.7.3` fails (numba==0.60.0 has no 3.13 wheel).
The serve notebook (kaggle/serve/qwen2-5-coder-7b-vllm-serve.ipynb) now creates a Python 3.12 venv with uv and installs
the same pins (vllm 0.7.3, transformers 4.48.2); model, dtype, tensor parallel, max-model-len and served name are
unchanged, so cached responses stay valid and new calls use the same server version. The notebook prints the server
env versions; a run is valid only if they read 3.12.x / 0.7.3 / 4.48.2.

GPU queue (in order, one session; each step resumes from cache):
1. advdoc-hybrid: finish sample 160/1 advdoc-plainhybrid, then evaluate + oracle collect/llm/score
   (out/runlogs_heldout/chain_real12.sh part 1). Replaces the provisional §11.23 numbers.
2. MBPP+ held-out, 12 real-bug PUTs (amendment 4): heldout.run --root out/heldout_mbpp_real12 mine -> facts -> specfacts
   -> bundle -> arms (7 arms, K = 3, 252 samples) -> evaluate -> oracle (chain part 2). Frozen v7; v8-strict
   construction applied afterwards on CPU as a secondary analysis.
3. v9 (plan rank 1, CONCEPT_WEAKNESS.md): round 2 with concrete calls + trace feedback, strict, with matched
   plain-hybrid control; registered separately before its run, built in pipelines/v9_* copied from pipelines/v7.
CPU queue (no endpoint): pipelines/v7 packaging + equivalence (Codex, running); CrossHair on the 276 v5 hard gaps
(Codex, running); plan rank 2 (fault-oriented hint selection, even/odd) and rank 3 (trigger inference); v7lib
(coverage.py + mutmut swap, offline equivalence first).
- Correction (2026-10-13): the serve-notebook change above was not requested and is reverted; the notebook is back to
  its previous version. Ignore the "Serving" paragraph of this entry; the GPU and CPU queues stand.
- Run-plan addition (2026-10-13 ~02:00, user request, before computing): (a) re-report existing dev runs (v7, v8-strict,
  advdoc/onlydoc, advdoc-hybrid partial) with VibePass's metrics (arXiv 2603.15921, RQ1): V_I = contract-valid input
  rate, V_IO = valid input with correct expected value (per oracle), D_I = input on which PUT != canonical (bug-
  revealing), D_IO = bug-revealing input with correct expected value; per assertion and per sample, CPU only
  (analysis/vibepass_metrics.py). (b) Feasibility check of the VibePass dataset (Salesforce/vibepass, 173 instances,
  CC-BY-4.0) as a second held-out set: do buggy solutions pass the LiveCodeBench public tests (TrickCatcher setting)
  and fail hidden tests/silver on test_checker-valid inputs; format conversion (LeetCode class methods, AtCoder stdin).
  No method run on it until a separate registration.
- GPU queue amendment (2026-10-13 ~01:10): the advdoc-hybrid generate refused to resume because its manifest pins the
  PREREG hash (edited since). As with v7 (_r2), it finishes in fresh dirs out/gen2_qwen7b_advhyb_v4_r2 /
  out/oracle_advhyb_r2 with the LLM response cache copied (cached prompts replay; only 160/1 needs new calls).
  Order swapped: MBPP+ real-12 held-out runs first, advdoc-hybrid second. PREREG is not edited while the queue runs.
- GPU queue result (2026-10-13 ~07:45): MBPP+ real-12 done (RESULTS §11.32: no concept advantage, concept arms more
  contract-invalid inputs); advdoc-hybrid final (RESULTS §11.34) equals the provisional numbers.

## v9_callfb: round 2 = concrete calls + trace feedback (registered 2026-10-13 ~07:50, before any v9 arm output)
Folder pipelines/v9_callfb (copied from pipelines/v7; README lists the diff). Only round 2 of the hybrid arms changes:
for each shown hint missed by round 1 (concept-hybrid; placebo-hybrid with placebo hints), Qwen writes 5 concrete
calls; the tool runs them sandboxed and returns per-call feedback at three levels (reached the site / local behaviour
differed / output differed from the mutant for MUTANT facts) plus validity under the mined validator; up to 2 feedback
rounds; keep up to 2 valid hitting calls per hint. Strict: round 2 adds exactly the kept calls; the expected-value call
covers only them and is skipped when none is kept. plain-hybrid control: same number of proposal requests as
concept-hybrid per task/sample, same format and feedback loop without a hint, keep rule = valid input. Round 1, hints
(v7), seeds of round 1, oracle and K = 3 unchanged; new requests use a disjoint seed range. Input-level trigger
conditions (RESULTS §11.30) are not yet in the feedback (computed for v3m2 facts only) — a later version.
Primary (dev, ref): concept-hybrid vs plain-hybrid, per-task sign test. Secondary: same with matched test count;
concept-hybrid vs toolinput (raw and matched); vs placebo-hybrid; hint-hitting kept inputs per sample (v7/v8: 0.9);
D_I (RESULTS §11.28). Compared against v8-strict (concept-hybrid 61.0, plain-hybrid 55.7). Pilot reported separately.
- v9 amendment 1 (2026-10-13 ~09:30, before any v9 evaluation or oracle output): the first arms run stopped at
  2363/2373 samples because the endpoint rejected over-long round-2 conversations (HTTP 400; tasks 94 and 113, long
  literal calls in the feedback). Fix in pipelines/v9_callfb: a proposal request rejected with HTTP 400 is recorded as
  made, nothing is kept from it, and that hint's loop stops; an HTTP 400 on the expected-value call leaves None
  placeholders (ref scores inputs). Prompts are unchanged, so all earlier responses replay from the copied cache. The
  pinned source hash changed, so the run restarts in a fresh generation dir (first try kept as generation_try1).

<!-- moved verbatim from PREREG_PENDING.md (commits e53df87, 8a26891, 9cc702b, dc35ddd) after the v9 run released PREREG.md -->
## v10_spechint: spec-behaviour concepts (plan rank 5) — registered 2026-10-13 ~09:40, before any output
Folder pipelines/v10_spechint, copied from pipelines/v7; only the hint pool changes (round 1/2, oracle unchanged).
New concept kind BEHAV: Qwen reads the specification only (signature + docstring; no PUT, no tests) and lists
behavioural requirements relating output to input (e.g. "output is sorted", "case-insensitive", "ties keep the first",
"duplicates are kept"), each with a verbatim spec quote, an input predicate D(args) for inputs where the requirement
matters (an implementation ignoring it could differ), and optionally an output check R(args, out). RBCTest-style gates
as F1b: list -> confirm quote -> code -> verify (D runs on all base inputs; R, if present, holds on every base pair).
A BEHAV hint is emitted only when no base input satisfies D and a B5-valid fuzz input does (witness). Hint text states
the requirement and that no existing test exercises it, without the witness (toolinput gets the witness).
Offline first (dev, HumanEval+ labels for measurement only): PF/good@3 of BEHAV hints, alone and in the pool, even/odd
split; then an LLM run (registered with its own comparisons) only if BEHAV adds good hints on odd tasks.

## v7_mutref: hint selection by fault hypothesis (plan rank 2) — registered 2026-10-13 ~09:40, before any output
Folder pipelines/v7_mutref, copied from pipelines/v7; only the choice of the 3 shown hints changes: all kinds compete,
ranked by the logistic rule LR[noref + mutref] fitted on even dev tasks (analysis/hint_rank.py; coefficients frozen in
the folder's config). mutref uses the spec-only ref programs (B2, DPP prompt) that pass the base tests; this is close to
TrickCatcher's idea and is reported as such; refdis is not used. toolinput and placebo use the same shown hints /
witnesses. Offline check: good@3 must reproduce RESULTS §11.29 (odd 35). LLM run after v9, combined with the better
round 2 (v8-strict or v9), primary concept-hybrid vs plain-hybrid (ref) and vs toolinput, on ODD dev tasks (even tasks
were used to fit the rule), matched test counts as secondary.

### v10_spechint amendment 1 (2026-10-13 ~10:30, before any offline-behav or LLM-run output was read)
The first mining run kept 40 requirements over 133 tasks and produced 1 BEHAV fact. Two gate bugs:
(1) the quote check was an exact substring test and rejected 260/276 quotes that match the docstring up to whitespace
(docstrings wrap and indent); it now compares after collapsing whitespace (words must still match verbatim);
(2) 291 predicates were rejected only because Qwen renamed the parameters (e.g. `D(xs)` for `make_palindrome(string)`);
same-arity predicates are now renamed positionally (references included) before the unchanged purity/arity gate.
Prompts unchanged (LLM cache copied; new code requests only for newly kept items). First outputs kept as *_try1; the
offline-behav of try 1 was stopped unread.
- v10 amendment 1b (2026-10-13 ~11:50): try 2 (after amendment 1) kept 67 requirements but 342 items failed with
  `predicate_load_failed` (StopIteration): my renaming code reused the variable `name` and renamed the predicate
  itself (e.g. `def string_m` instead of `def D_m`). Try 2's offline-behav WAS read before the bug was found: 4 BEHAV
  facts, good@3 unchanged vs v7 (54/112), 0 BEHAV good — invalid because of the bug, reported here for transparency.
  Fixed (loop variable renamed, test added); try 3 reruns from mining with the copied cache; outputs of try 2 kept
  as *_try2.
- v10 result (2026-10-13 ~11:50): try 3 offline-behav — 157 requirements, 146 already satisfied by a base input, 7 BEHAV
  facts on 5 tasks; good@3 even 29 -> 30, odd 25 -> 25. Decision rule (LLM run only if BEHAV adds good hints on odd
  tasks) not met: no LLM run for v10. RESULTS §11.35.
- v9_callfb result (2026-10-13 ~12:00): RESULTS §11.36. Primary concept-hybrid vs plain-hybrid (ref) 26/19, p = .37;
  v9 concept-hybrid vs v8-strict 3/19 (worse). Round 2 with concrete calls kept 0.19 hint-hitting inputs/sample vs
  0.9 for Hypothesis. v9 is dropped; Hypothesis round 2 (v8-strict) stays.

- v7_mutref amendments (recorded 2026-10-14; made during the run, before any oracle output was read):
  (1) GPU outages: the run was relaunched from the last finished stage with the same cache (chain_from_eval /
  chain_from_oraclellm / chain_from_score); (2) evaluate ran through analysis/mutref_eval_longtimeout.py, which
  raises the per-task scoring sandbox timeout 600 -> 3600 s (task 83 timed out); (3) v4_evaluation.py scores an
  assertion whose input raises MemoryError as a crash on both programs (task 87; commit 1b67d00); (4) oracle-score
  needs --online for the B4 judge (first attempt failed offline on a cache miss).
- v7_mutref result (2026-10-14): RESULTS §11.39. Primary (odd dev, strict, ref) concept-hybrid vs plain-hybrid 17/9,
  p = .17; vs toolinput 11/8, p = .65. vs the old rule (v8-strict) 13/10. The mutref rule is not adopted; v7 rule stays.

## Final comparison protocol (registered 2026-10-13 ~21:05, user-approved, before any baseline/held-out output)
Addresses six fairness problems (user-reviewed critique, verified in data):
1. Dev (113 HumanEval tasks; even/odd; pilot) has been used repeatedly for design choices and is development data only.
   Confirmatory claims come only from held-out sets run once with a frozen configuration: VibePass LeetCode (66 PUTs,
   24 questions, statistics clustered by question) and MBPP+ real-bug (12 PUTs). Dev results are reported as such.
2. The final configuration is generated for real in strict mode (round 2 contributes only tool-verified inputs; the
   expected-value call covers exactly those inputs and is skipped when none is kept). No CPU-reconstructed arm is used
   for confirmatory claims; LLM calls/tokens are those of the real run.
3. Placebo control matched in budget: placebo-hybrid receives the same number of round-2 strategy requests as
   concept-hybrid for the same task/sample (as plain-hybrid already does), targeting placebo hints.
4. Budgets fixed at generation time and identical for every arm and baseline: at most 8 LLM calls and at most 20
   assertions per sample (assertions beyond 20 are dropped in generation order and recorded). Matched-count analysis is
   secondary and uses random equal-size subsets (fixed seed, 100 draws, mean), not prefix truncation.
5. TrickCatcher-full adapter: inputs serialised with repr/ast.literal_eval instead of a JSON round-trip (task 127 lost
   400/400 inputs); crash/timeout accounting and budgets aligned with the other arms; the 7 empty-pool tasks rerun.
   Until then no claim of beating TrickCatcher is made.
6. One scorer everywhere: output equality = EvalPlus-style comparison with the task's atol (floats rel 1e-6 / atol,
   recursive over lists/tuples, exceptions/timeouts as distinct outcomes), used by the oracle, evaluation and analyses.
   Three separate metrics per arm: D_I (a contract-valid input on which PUT != reference), D_IO (D_I with the correct
   expected value under the oracle), and precision of bug reports (assertions failing on the PUT that are correct /
   all assertions failing on the PUT); false alarms over the same denominator for every arm.
Arms on held-out: concept-hybrid (final hint selection: v7 rule unless v7_mutref's registered odd-task comparison favours
the mutref rule), plain-hybrid, placebo-hybrid (matched), concept (round 1 only), toolinput, plain, and baselines
CoverUp, MuTAP, SymPrompt, ACH (filter: inputs where PUT and mutant differ; paper filter secondary), TrickCatcher-full
(fixed adapter), EvalAndMitigate onlydoc/advdoc. Same model, endpoint, K = 3, ref/full oracle (10 spec-only programs).
Primary: concept-hybrid vs plain-hybrid and vs each baseline, D_IO under ref, per-question sign test (VibePass) /
per-task (MBPP+). Secondary: D_I, precision, matched-count subsets, placebo.

## Dev sanity run of the final comparison protocol (registered 2026-10-14 ~00:40, before any output)
Development data only (protocol fix 1): checks that the frozen configuration and every baseline run end to end under
the protocol, and gives dev numbers reported as such; no confirmatory claim. Runs:
- `pipelines/v11_fair` (v7 hint rule; all four flags on: real strict round 2, matched placebo, <= 8 calls / <= 20
  assertions per sample, shared tolerant scorer), seven arms, all 133 tasks, K = 3; round 1 reuses the v7 LLM cache
  (identical prompts and seeds).
- Baselines on the 113 dev tasks, K = 3, budget 8 LLM calls / 20 assertions per sample: SymPrompt, ACH (filter run),
  CoverUp, MuTAP (N = 7 surviving mutants); TrickCatcher-full = tc_full_v2 (existing generations, CPU).
- Scoring: every run through v11_fair evaluate + oracle (same ref programs: oracle cache copied from the v11_fair run),
  ref and full. Witness-only computed as in RESULTS §11.37.
Primary (dev, descriptive): concept-hybrid vs plain-hybrid, vs toolinput, vs witness-only and vs each baseline,
D_IO under ref, per-task sign test. Secondary: D_I, precision, random-subset matched counts, placebo.
Held-out runs only after this run completes and nothing is changed except bug fixes (recorded as amendments).
- Dev sanity run amendment 1 (2026-10-14 ~00:45, before any arms/oracle output; user: "tạm thời chưa cần chạy cả full …
  mình đang cải tiến input"): oracle = **ref only**. No b1, no postconditions, no B4 judge (saves GPU; b1 was the most
  expensive stage and is used by no conclusion). Primary/secondary comparisons are on ref; full is not computed in
  this run (can be added later from the same calls if needed).

## B3 v12_rel: concept ablation ladder (registered 2026-10-14 ~01:10, design only; before any code or output)
Question: does the *structure* of concepts help the LLM, beyond the facts and witnesses themselves? Folder
pipelines/v12_rel, copied from pipelines/v11_fair (all four fairness flags on). Same tasks, spec, PUT, base tests,
tool, K = 3, call cap 8 and assertion cap 20, same round-2 strict Hypothesis mechanism, and the same 3 selected hints
(v7 rule) for every concept arm. Prompt input budget equalised: every arm's hint block is padded or truncated to the
same token budget (the rel arm's length), recorded per sample. New arms (round 1 + round 2 as in concept-hybrid):
- `review-hybrid`: generic code-review guidance of equal length (a fixed checklist: boundaries, off-by-one, empty and
  singleton inputs, ordering/ties, types, large values), no task-specific facts. Round 2 targets the same hints
  internally (like plain-hybrid) without showing them.
- `flat-hybrid` = concept-hybrid (the 3 hint sentences, unrelated to each other).
- `rel-hybrid`: the same 3 hints, each expanded into a typed chain computed by the tool on CPU from the AST and the
  tracer: data dependence (value defined at line A used at line C), control dependence (line C guarded by the condition
  at line B, with the branch outcome base tests never/always take), and a spec link (the docstring sentence whose words
  best match the site's identifiers/operators, lexical, no LLM), shown as "spec clause R → condition B → line C ←
  value from line A". Witness inputs are NOT shown (as in flat).
- `rel-nospec-hybrid`: rel-hybrid without the spec-link edges.
References always reported: plain-hybrid, toolinput, witness-only, placebo-hybrid (matched).
Oracle: ref only (dev sanity amendment 1 applies). Run on dev only after the v11_fair dev sanity run finishes;
held-out only if rel-hybrid beats flat-hybrid on dev.
Primary (dev): rel-hybrid vs flat-hybrid, D_IO under ref, per-task sign test; secondary: flat vs review, rel vs
rel-nospec, every concept arm vs toolinput and witness-only, random-subset matched counts, D_I, precision.
- Final protocol amendment 1 (2026-10-14 ~01:20, before any held-out output): TrickCatcher-full (tc_full_v2) keeps
  the paper's design, 10 program variants + 4 input generators = 14 LLM calls per task shared by its K = 3 resamples
  (4.7 calls per sample on average). The call budget for this baseline is applied per task (14 <= 3 x 8 = 24, the
  budget of every other arm per task); the 20-assertion cap per sample applies unchanged. Reason: faithfulness to the
  original method; its samples are resamples of one shared generation, reported as such.

## B4 v13_hyp: spec-violation hypotheses (registered 2026-10-14 ~02:00, design only; before any code or output)
Question: does linking facts into explicit fault hypotheses (incl. ones without a fuzz witness, and at sites base tests
already execute) help the LLM find bugs beyond flat/rel concepts and beyond the witnesses themselves?
Folder pipelines/v13_hyp, copied from pipelines/v12_rel (fairness flags on, same caps and budgets).
- Hypothesis = (spec clause R, code chain "value from line A → condition B → line C" from v12_rel relations, trigger
  condition T as a Python predicate over the entry's arguments, expected violation "output breaks R when T holds").
- Generation: one Qwen call per task (cached, same for all samples) proposes up to 6 hypotheses from spec + code +
  the tool's relation chains for ALL candidate sites (covered sites included, not only gaps). Tool checks each: T must
  parse, be pure, and be satisfied by no base-test input (otherwise "already tested" → dropped); a Hypothesis search
  (the v4c domain strategy filtered by T, 200 draws) looks for a witness; hypotheses without a witness are KEPT and
  marked "unwitnessed". Ranking: witnessed and PUT output differs from >= 1 surviving mutant first, then witnessed,
  then unwitnessed; ties by task-level frozen order.
- Arm `hyp-hybrid`: round 1 shows the top-3 hypotheses (R, chain, T; no witness values); round 2 targets hypotheses
  whose T no round-1 input satisfies, with the strict Hypothesis mechanism using T as the filter (no LLM strategy if T
  is a usable filter). References in the same run: flat-hybrid, rel-hybrid, plain-hybrid, toolinput, witness-only
  (+ hyp-witness-only: witnesses of the shown hypotheses, ref oracle, no LLM).
Oracle ref only. Dev only after B3; held-out only if hyp-hybrid beats rel-hybrid/flat-hybrid on dev.
Primary (dev): hyp-hybrid vs flat-hybrid and vs toolinput, D_IO under ref, per-task sign test. Secondary: vs rel-hybrid,
hyp-witness-only vs witness-only, share of detections from unwitnessed hypotheses and from covered sites,
random-subset matched counts, D_I, precision.
- Dev sanity run amendment 2 (2026-10-14 ~03:50, after arms, before any evaluation/oracle output was read): evaluate
  failed with the per-task scoring sandbox timeout (600 s), as in v7_mutref. Same two fixes as the v7_mutref
  amendments: evaluate runs through analysis/v11_eval_longtimeout.py (3600 s), and pipelines/v11_fair/v4_evaluation.py
  gets the MemoryError guard (oversized input scored as a crash on both programs). Resumed from evaluate.
- B3 v12_rel run note (2026-10-14 ~04:50, before any output): launched on dev, all 133 tasks (dev and pilot reported
  separately), arms review/flat/rel/rel-nospec-hybrid + plain-hybrid, toolinput, placebo-hybrid in the same run; LLM
  cache reused from v7 and v11_fair (identical prompts/seeds give identical responses). Evaluation with the same
  MemoryError guard and 3600 s sandbox as v11_fair amendment 2. Runs concurrently with the baseline generation of the
  dev sanity run on the same endpoint (affects wall time only).
- B4 amendment 1 (2026-10-14 ~05:20, before any B4 output): under the v12 budget rule (target = rel block) the
  three-hypothesis block (~230 whitespace tokens) would be truncated on most tasks (rel median 119; 5 tasks 0). In
  v13_hyp the per-unit budget is the LONGER of the rel and hypothesis renderings of that unit; every arm in the v13 run
  is padded to it, the hypothesis block is never truncated. Without hypotheses the rule equals v12_rel. Other
  implementation choices (recorded in pipelines/v13_hyp/CHANGELOG.md): T usable as filter = the T-filtered draw yields
  >= 1 valid input; "missed" = no valid round-1 input satisfies T; R accepted as an exact or near quote (difflib >= 0.9);
  the per-task proposal call is reported separately from the per-sample cap of 8.
- Dev sanity run amendment 3 (2026-10-14 ~06:30, before any baseline output was scored): CoverUp aborted on one Qwen
  request (baselines/common.py had a 120 s timeout and no retries; the endpoint was shared with the B3 run) and MuTAP
  was stopped. The baseline client now uses the pipelines' transport policy (600 s; up to 8 retries with backoff on
  timeouts, connection errors and 5xx; identical payload and seed; 4xx not retried). Because manifests pin source
  hashes, CoverUp and MuTAP restart in fresh dirs coverup_r2 / mutap_r2 with their LLM caches copied (same keys, so
  completed requests replay identically). SymPrompt and ACH (finished, own clients) are unchanged.
- Dev sanity run amendment 4 (2026-10-14 ~08:00, before any MuTAP output was scored): MuTAP_r2 aborted on an HTTP 400
  (one augmentation prompt was 24.6k tokens > the 16,384-token context). As in v9 amendment 1, an over-context request
  now counts as a request made with an empty answer (baselines/common.py ContextTooLong), so the method continues or
  stops by its own logic. MuTAP restarts in mutap_r3 with the caches of mutap and mutap_r2 copied.

## Exploratory v14_obgraph / v15_mrconcept (2026-10-14, before implementation outputs)

User requested trying grounded obligation graphs and conditional metamorphic concepts FIRST, each in a new folder.
These are LineFacts adaptations inspired by literature, not reproductions of PromeFuzz/MR-Coupler/MemoRIA.
Copies of v13_hyp inherit v7/v11 mining, tracing, Hypothesis, sandbox and common ref scorer; protected copies stay intact.

Initial cohort: 20 dev task IDs sampled without inspecting new outputs, random.Random(20261014).sample on sorted
v11_fair dev IDs; IDs are frozen in each config. K=1 exploratory mechanism/effect smoke, no held-out and no confirmatory
claim or promotion from its p-values. Expand to full dev only with a separately recorded scope before new outputs.

v14_obgraph: one cached proposal/task, <=6 (clause ID, semantic family, tool concept IDs, connected typed edge IDs,
trigger T, pure obligation O(args,result), explicit alternative hypothesis). Tool validates graph adjacency and concept
anchors, exact clause IDs, predicate purity, finite base consistency. Base-trigger hits do not alone discard obligations.
Discovery uses 200 common domain draws; unwitnessed cards stay. Ranking: witnessed PUT violates O while a surviving
mutant satisfies it, then PUT violates O, then witnessed, then unwitnessed; ties proposal order. These are candidate
spec violations, not ground truth. Display top 3 without witness values. Actual generated inputs must satisfy T and the
observed selected path; trace-incomplete/path errors abstain. Path observation is co-execution evidence, not causal proof.
Primary exploratory contrast graph-strategy vs card-strategy, same selected evidence/targets/filter. Secondary removes
concept labels; plain/placebo controls and both original/new-pool toolinput/witness-only are mandatory.

v15_mrconcept: one proposal/task, <=6 conditional relation cards (exact clause IDs, fixed family, D, pure tau(args),
pure rho(args,followup_args,result,followup_result)). Families permutation, monotonicity, multiplicity, idempotence,
round-trip; every applicability claim remains candidate. Both source/follow-up inputs must pass B5 and size/arity checks.
Only relations contradicted by a pair of *already base-tested* inputs are rejected for base inconsistency. Never reject
a relation for failing on untested buggy PUT inputs. Rank witnessed relation violations before witnessed/unwitnessed.
Primary exploratory mr-strategy vs mr-blind; tool applies identical D/tau filters and paired input selection in both,
so this isolates relation guidance. mr-flatfacts omits concept labels; placebo and original/new-pool witness references.

Both: fixed three strategy slots/sample/arm, one LLM request/slot (no retry or expected-value request); max 1024 completion
tokens/request, proposal max 4096. Empty slots use generic strategy guidance with explicit status. Model outputs only
Hypothesis strategies; sandboxed draws <=100 valid unique candidates from <=500 examples/slot; select <=2 sources/slot,
up to 12 distinct PUT inputs/sample (a pair costs two), <=20 placeholder assertions. Original witness-only and new-pool
witness-only use zero generation requests; proposal cost is shared once/task and reported separately. Prompts are not
declared tokenizer-equal: record server actual input/output tokens and matched call counts; no punctuation padding.
Use original v11 mining/task bundle, no canonical/hidden inputs/ref outputs in proposal, selection or generation.

Main endpoint D_IO under shared spec-only ref oracle, same saved v11 ref responses for all arms; D_I/precision, paired
task effect and fixed-seed random-subset matching secondary. Missing references abstain (never silently fill with gold).
Evaluate obligation/MR oracle validity separately against canonical+contract ONLY after generation is frozen; report
candidate violations, confirmed finite-input violations and false alarms, not universal relation correctness.
Record proposal rejection reasons, chain hits, trigger hits, input overlap, witnesses, draws, executions and actual tokens.
CPU fixture checks and real cached-task graph preparation precede online run. No paid API and no held-out run.
- Implementation clarification (2026-10-14, before any proposal/model output): paths must end at an observable
  RETURN node; exact duplicate proposal cards are rejected. Pair validation is repeated in property scoring and
  no atomic pair may be partially kept under the input-call cap. Empty accepted-card slots use generic singleton
  generation with explicit status. New toolinput is a fixed-slot strategy adapter, not the historical one-call arm.
- Run status (2026-10-14): user reports exhausted quota and no Qwen endpoint. CPU checks/preparation only;
  no online proposal/generation, paid API fallback or held-out run has started.
- CPU implementation check (before model outputs): normalize base keyword/default arguments to complete positional
  tuples before T/O/rho consistency checks, so known base evidence is retained regardless of calling style.
- Online run note (2026-10-14 ~12:52 local, before any model proposal/generation output): user supplied the Qwen
  endpoint and explicitly requested GPU execution. Run v14_obgraph then v15_mrconcept, frozen 20 dev tasks/K=1,
  source commit 4ff245d, existing caps/seeds/controls and saved v11 spec-only references. Detached sequential chain
  under out/runlogs_v14_v15, four workers per variant, keepalive owned by each runner. No paid API or held-out run.
- Resume queue note (2026-10-14 ~13:06 local, before new B3 scoring/B4 outputs): after the two new smoke runs,
  resume the interrupted B3 with its original seven-arm/K=3 manifest and response cache using the current endpoint;
  its previous arms stage stopped with HTTP 404. Then run registered B4 with the handoff's frozen configuration and
  reuse v7/v11/v12 caches. No restart of completed baselines and no held-out run. Model inputs/config remain frozen.
- B3 resume clarification (2026-10-14 ~13:30 local, before evaluation/scoring): the protected runner retraces all
  base/witness relations even on resume. Reuse relation_meta from its already immutable generation/tasks.json via
  analysis/resume_b3_frozen_relations.py instead. Require exact task equality and original source-hash equality;
  preserve the original generation manifest, prompts, seeds, saved samples and cache. This avoids both repeated
  CPU extraction and changing time-limited trace evidence. Adapter/snapshot hashes are logged; no method tuning.
- User order correction (2026-10-14): resume B3 → B4 before returning to v14/v15. The original two smoke runs
  had already completed when this arrived. No additional v14/v15 model calls may start until B3/B4 complete.

## Python/JSON format repair: v14_obgraph_py / v15_mrconcept_py (2026-10-14, before their model outputs)

Original smoke produced zero accepted cards in both methods, so it did not exercise the semantic treatments.
Create separate copies. Only proposal guidance changes: explicit Python-only system instruction, one JSON-escaped
toy FORMAT example (not a target-program proposal), instructions before evidence and a final format reminder.
Suggest up to three cards within the original cap of six. Exact validators, graph grounding, D/T/O/tau/rho rules,
ranking, search, generation budgets/controls, 20 dev IDs/K=1, seeds and shared refs remain unchanged.
No target outcomes/canonical code enter format guidance. Original results remain archived; repair is exploratory.

Mechanism gate: run all 20 cached/shared task proposal stages first; if zero cards survive checks, stop before
generation and record mechanism_gate.json. If >=1 card survives, run the original full 20-task arm grid and scorer,
report accepted-card task coverage and guidance-slot counts alongside D_IO; sparse treatment limits interpretation.
Reuse original model-response caches only for byte-identical prompts/params/seeds, not old proposals/samples/results.
Worst-case request caps remain 440/380; a zero-card gate costs only 20 proposal requests/method. No repair retries,
paid API or held-out run. User priority: start model stages ONLY after B3 and B4 finish; CPU preparation can proceed.

- Operational checkpoint (2026-10-14 ~15:30 local): B3 generation/evaluation/collect/ref completed; score
  aborted with incomplete ref executions, missing task 44 only (132/133 result files). Retry only its original
  saved job using unchanged worker source, per-call timers and 3,000 s outer timeout, capturing stderr.
  Preserve successful results and resume B3 score → B4 → repaired v14/v15 only after complete score gates.
  First failure cause is undetermined; no task exclusion, scoring-policy change or efficacy claim.

- Scheduling amendment (2026-10-14 19:05 +0700, before repaired-method model outputs):
  user requested using the GPU during B4 CPU work. B4 has 13 exported generation samples remaining, mostly
  CPU classification; its original generation/evaluation/ref/scoring chain continues unchanged and may still
  issue model calls. Start v14_obgraph_py then v15_mrconcept_py concurrently with B4, two workers per new
  method. Replace only the dormant score-gated waiter; keep methods sequential and their original 20 dev
  tasks/K=1, prompts/seeds/validators/budgets/ref cache/mechanism gate frozen. No B4 outcomes feed these runs.
  CPU contention may affect wall time/timeouts; record overlap when interpreting exploratory results.

- Operational GPU restart (2026-10-14 19:28 +0700): user restarted GPU and requested resume.
  B4 stopped on HTTP 404 with 2,783/2,793 exported samples; repaired v14 stopped with 15/20 proposal summaries.
  Resume B4 and the overlapping repaired v14→v15 chain from original caches. B4 uses
  analysis/resume_b4_frozen_relations.py: verify all 133 incoming tasks and protected source hashes against
  immutable manifest; replay exact relation_meta; require all original hypothesis cache keys and slim metadata
  to match frozen tasks. Native hypothesis cache handling, prompts/config/seeds/sample limits/scorer remain
  unchanged. Skip completed bundle/B3 stages. Repaired methods retain two workers and original mechanism gate.

- Operational B4 scoring retry (2026-10-14 23:49 +0700): generation/evaluation/collect/ref
  completed, but score exited with incomplete executions (132/133); only task 44 result is missing.
  Re-run that exact saved job with unchanged oracle worker, original per-call timers and 3,000 s outer
  timeout, capturing exit code/stderr. Keep all 132 existing results and complete native scoring only
  after all executions exist. No new model calls, task exclusions, source/config/prompt/scoring changes.


## 2026-10-15 — v16_behavior, abstract behavior and semantic concept MVP

User requested starting now, overriding the wait for benchmark research. New source copy from
v11_fair; author/vendor code and all earlier versions remain unchanged. This implements our
LineFacts design, not a reproduction of any cited paper. Foundation source hashes saved locally.

Before new outputs: fixed design dev cohort [27,31,51,56,57,59,63,76,78,85,91,94,98,110,118,126,
136,144,149,152], K=1, seed 20261015. No held-out access. Representation artifacts include
source-mapped structured control flow, explicit collection state observations, operation requirements,
first-order bounded mutations, and a finite observed predicate-state machine. The observed machine
is an under-approximation; no abstract-interpretation soundness/completeness or symbolic proof claim.
Float division, eval, recursion, unrecognized external operations and unresolved aliases are opaque.
Every task remains in the denominator. Gate B: >=16/20 with a supported input-output summary,
base passes, >=1 completed replay, and no known replay mismatch. Stop after gate failure.

CPU discovery: <=8 unique recorded base inputs/task, <=40 frozen mined strategy draws/task,
first 12 compatible mutants in source/operator order, <=12 unique shared inputs/mutant,
2s per execution, 20000 recorded events maximum. Mutations are implementation-origin hypotheses,
not actual bugs or validated spec models. Base-distinguished mutants reported separately.
No canonical/reference code, plus inputs or detection outcomes used for preparation or ranking.

Gate C: <=2 Qwen proposals/task (spec-only extraction then binding), 2048 completion tokens each,
<=6 candidate cards, <=3 shown. Quoted docstring spans and typed DSL/bindings checked; semantic
entailment remains a candidate. Reject base contradictions. Require >=10/20 grounded nontrivial
concept tasks with explicit alternative/gap and computable discriminator. No repair model calls.
If B/C fail, stop and report; changing treatment requires a new copy/amendment before new outputs.

Conditional generation after gates: six LLM arms plain/flat-facts/behavior/behavior+concept/placebo/
toolinput, plus witness-only. All share spec/PUT/base, domain filter, draw pool, request and selection
policy: 3 strategies/task/arm, 1024 tokens each, <=2 random-valid selected inputs per slot and
<=12 distinct calls/sample. Semantic activation is measured after common selection, never used
as a private acceptance filter for the concept arm. Max logical model calls: 40 proposals + 360
strategies =400. Common saved spec-only ref oracle, primary behavior+concept vs behavior; secondary
behavior vs flat-facts, matched plain/placebo/toolinput/witness-only. D_IO primary; false alarms,
random-subset equal-count contrasts, coverage and actual input/token/discovery costs reported.
No content repair, paid fallback or MCTS run. Transport errors stop for resume. GPU requires live
user Qwen; CPU artifacts are not an efficacy result. Full dev expansion is not automatic promotion.


### 2026-10-15 — v16_behavior_compact storage repair, before repaired-run outputs

Original CPU prepare aborted on task 94: 30 MiB worker JSON exceeded inherited 8 MiB IPC cap;
19/20 task artifacts existed, no complete representation gate, model calls or detection scores.
Keep failed v16_behavior sources/results intact. New copy v16_behavior_compact retains only
first 64/last 64 events per replay after computing the full observed predicate machine, with
omission counts. Native comparison/final state, execution/event/time caps, domain, mutant order,
shared inputs, cohort, seeds, gates and all model/generation budgets unchanged. Re-run CPU audit
in fresh output. This repairs storage, not a treatment/gate change; no efficacy claim.


### 2026-10-15 — v16_behavior_ready format rejection hardening, before new outputs

After compact CPU gate passed (17/20), code review found schema-invalid but syntactically valid
JSON such as a top-level list could raise AttributeError instead of counted rejection. No model
requests or concept/detection outcomes exist. New copy v16_behavior_ready explicitly rejects wrong
JSON container types, non-string IDs/operators/quotes and malformed reasoning. No model repair
calls, relaxed validators, new operators, budgets, task filtering or treatment changes. Re-run CPU
gate fresh and freeze new source hashes; previous copies/results retained.


### 2026-10-15 10:00 +0700 — user-authorized GPU availability waiter

User requests continuing and expects GPU online in ~10 minutes. Outside frozen pipeline, use
analysis/run_behavior_when_ready.py to verify protocol, wait until 10:10:40 +0700, then check the
inherited user Qwen model endpoint once/minute for at most 40 minutes. Endpoint/key are environment
only, never saved. When the pinned model is listed, execute the unchanged v16_behavior_ready `all`
runner with two workers and the dedicated v4 interpreter. Maintain the existing 20-minute metadata
keepalive only during the run. Gates, tasks, requests, seeds and scoring unchanged; no extra completion
probe, paid fallback or model repair call. A failed concept gate stops before generation; transport/
worker failure preserves caches for reviewed resume. Queue the completion/stop report back into this
existing session. Operational state and logs live under out/runlogs_v16_ready (ignored).

Preflight: protocol unchanged; all 20 first-stage prompts contain docstring/parameter/DSL instructions
without PUT implementation or canonical material. 15/20 tasks have both usable behavior and at least
one compatible implementation mutant under the frozen grammar; all 20 remain in the concept-gate
denominator. This is engineering capacity, not accepted-concept coverage or detection evidence.


### 2026-10-15 10:14 +0700 — v16 frozen resume, main-thread tracer initialization

GPU ready at 10:13:41. First run stopped at binding prompt construction: lazy import of behavior
loaded tracer in a ThreadPoolExecutor worker; its existing SIGALRM registration requires main thread.
Three spec responses cached (1,310 input / 949 output tokens), zero binding responses, summaries,
concept gate, generation or scoring. Frozen sources/config/tasks still match the protocol.
Resume through analysis/resume_v16_frozen.py, importing behavior/tracer on main thread before the
unchanged CLI. Reuse exact cached requests; no new seeds, prompts, validators, budgets or task
exclusions. This changes initialization order only; no source edits or model-response repair.


## 2026-10-15 — v17_templates, compiler-owned semantic concepts

User requested continuing after v16's 0-card failure. Before new outputs, new copy from
v16_behavior_ready. Replace whole expression-tree generation with a fixed registry of reusable
MAP, FILTER, REDUCE, ORDER_CHECK, BALANCE, SEGMENT_COUNT, CAPACITY, NEIGHBOR_SELECT and CONTAINMENT
models. No registry dispatch on task number/function name or canonical solutions. Parameters are
LLM proposals from public spec-only units with tool-owned raw source spans; type/schema compilation
is not proof of entailment. No implementation or reproduction of a cited paper.

First Qwen call chooses <=6 template instances plus spec-unit IDs. Tool compiles them and <=6
first-order spec-model alternatives each (boundary, reducer, filter membership, multiplicity,
index parity, ordering, guard omission, containment). Second call selects proposal/fault/source
block IDs and a short explicit missing-condition rationale. Discriminator is computed by the tool
from original/alternative model outputs, not LLM-generated Python/DSL. Empty-output and component
properties are valid; no requirement that the output relation mention input structurally when
domain/template already binds it. No missing-R0 propagation: accepted proposal IDs assigned anew.

Same fixed 20 design dev tasks as v16, K=1, seed 20261015. Same CPU representation rules/gate
>=16/20, 8 bounded base replays, 40 mined discovery draws, existing first-order implementation
mutants retained as common discovery artifacts. Before card acceptance, verify candidate property
against ALL captured public base calls, cap 200 unique inputs/task; if cap exceeded abstain rather
than silently truncate verification. No canonical/reference/plus inputs before frozen generation.
A shown concept requires valid spec-unit/typed-template/fault/block references, complete rationale,
no base contradiction/unknown and >=1 actual valid model-discriminating discovery input. Original
input admissibility is unchanged; type/requirement assumptions are candidate metadata.
Concept gate remains >=10/20 tasks, all 20 retained. Stop before generation if it fails; no repair calls.

Two proposal requests/task, each <=2048 completion tokens, no content retries. At most 6 cards checked,
show 3, deterministic rank: non-base candidate PUT violation, then non-base discriminator, then
base-covered discriminator, original model order for ties. This uses candidate semantics, not gold.
All base/fuzz/old tool/semantic-discriminator discovery costs shared; common pool available to
toolinput/witness-only. Guided arms do not see concrete discovery inputs. Main comparison remains
behavior+concept vs same behavior. Six LLM generation arms plus witness-only, each 3 strategy slots,
1024 tokens/slot, 100 validity-filtered draws, random <=2 picks/slot, <=12 unique inputs/sample.
Common domain-only acceptance filter; concept activation recorded after selection. Max completion
requests 40 proposals +360 strategies=400, excluding transport retries; actual ledger reported.
Same saved spec-only ref oracle and canonical/contract evaluation only after generation freezes.
Report D_IO, false alarms, random-subset equal-input contrasts, mechanism coverage and token/time
costs; candidate-property validity must be audited separately from D_IO. No held-out or MCTS run.
Preregister new revisions before outputs; do not relax v16 or reinterpret its failure.


- v17 operational detail, before outputs: each checked card replays at most 3 ranked discriminator
  inputs with source-state tracing, requiring a completed trace touching a bound source line.
  This is witnessed grounding, not causal/semantic proof. The common old+new witness union is
  capped at 12 inputs by uniform fixed-seed sampling (20261015+task ID), shared by toolinput and
  witness-only, to keep prompt size bounded. Guided prompts contain no concrete witnesses.


- v17 preflight checkpoint before Qwen: 44 CPU tests, representation 17/20, all 20 public base
  capture sets below cap. Manual compiler-only positive control on task 152 (MAP abs_sub) checked
  four public base inputs; this is not an LLM proposal and never feeds proposal selection/gate.
  Proposal/generation starts with a fresh cache. Native canonical-property audit is scoring-only;
  report activated candidate violations, confirmed violations, false alarms and abstentions separately.


### 2026-10-15 — conditional synthetic template-interface capability probe

Registered while v17 proposals are running; exploratory design informed by v16 and partial v17
rejections. ONLY IF v17 concept gate fails, run a separate six-case synthetic capability probe,
not a new detection cohort or rescue of v17. Cases: character filtering, bidirectional non-strict
ordering, index/value-qualified sum, paired absolute difference, filtered multiplicity, empty-safe
minimum. Each has predeclared English requirement, candidate configuration and hand-written
finite expected examples verified by CPU before calls. No benchmark task IDs/code/gold references.
Compare (a) current parameter-synthesis interface, (b) selection among 2–4 tool-built candidate
models, with randomized correct ID positions. Same Qwen, temperature 0, two calls/case, 512 output
tokens each, max 12 logical completions separate from v17's 400 cap. No content repair or retries.
Report syntax/schema compilation separately from semantic agreement on declared examples and ID
selection correctness; actual tokens. Different prompts/interfaces intentionally differ; no clean
causal claim about output format alone, no D_IO or general ability claims from six examples.
Probe outputs never alter frozen v17 proposals/cards/gate. Source/data in own analysis folder.


## 2026-10-15 — v18_modelselect, candidate coverage and ID selection pilot

User explicitly authorizes tool-built candidate models + LLM choice and says MCTS is unnecessary.
New source copy v17_templates -> v18_modelselect; no paper reimplementation, paid fallback or held-out.
This is a SELECTION-ONLY pilot on the same fixed 20 design dev tasks, not a test-generation D_IO run.
Before outputs: seed 20261018, unchanged 17/20-capable observed behavior substrate, template semantics
from v17. Enumerate <=2048 typed template configurations/task; no task-ID/function-name dispatch.
Arguments/element/output types and optional output components come from public base observations.
Membership alphabets use a disclosed primitive vocabulary (English vowels, prime-valued hexadecimal
digits computed arithmetically) and quoted literals from public spec. Segmentation tokens from quoted
public words. No PUT constants or gold/reference code supply normative parameter values.

Filter against ALL captured public base calls (cap 200). Rank survivors by a disclosed hand-engineered
lexical compatibility/complexity prior, retain <=64. Choose <=4 displayed models, prioritizing distinct
predictions on frozen discovery inputs; keep the full retained pool for evaluation. Shuffle display IDs
with a fixed task seed. Report raw/retained/displayed coverage separately. Rule-first and uniform over
EXACT same displayed models are mandatory selection controls. Lexical ranking is feature engineering,
not learned semantic proof. No selection correctness claim from base agreement alone.

Discovery/audit input pool <=80/task: captured base, frozen old tool witnesses, fixed mined strategy
pool and <=80 structured typed proposals (empty/zero/sign/ties/duplicates/Unicode/delimiters/paired
values). Original mined domain filter applies uniformly. Pool fixed without canonical or plus inputs.
Record exact pool/models/model IDs/source hashes before LLM. Unsupported/opaque tasks stay in the
20 denominator with no menu. CPU gate >=10/20 candidate tasks before any model calls; otherwise stop.

One Qwen completion per task, <=256 output tokens, temperature0, return {"choice":"actual ID"} or
NONE. No parameters, source IDs, witness inputs, free-form rationale or content repairs. Model sees
public spec and displayed model definitions only, no PUT or concrete discovery inputs. All 20 queried
(including NONE menus) if CPU gate passes. Max20 logical completions, two workers, exact-cache resume.
No MCTS/search-agent loop. Invalid choice is reported as invalid; no silent fallback into LLM selection.

Freeze ALL menus, choices and discovery pools before opening canonical/contract material. Then run
scoring-only audit on this frozen pool (<=80 inputs/task): real contract validity; each model's
sampled canonical-property consistency, unknowns, and output-component scope. Coverage = at least one
retained/displayed model consistent on all valid audited inputs, with no unknown; not universal
semantic correctness. Compare LLM selection vs lexical-rule-first and uniform expected consistency,
including conditional-on-availability and true competing-model ambiguity by output scope. Report
partial-component requirements separately; no implication of complete program specification.

Tool-produced records for up to3 selected-model discrepancies contain requirement, observed source
blocks/state/guard sites, input relation class, actual effect and alternative-model matches. These are
bounded execution evidence, not causal proofs or LLM internal reasoning. Canonical audit confirms or
rejects candidate discrepancies AFTER freeze. Report false requirements/false alarms separately.
This pilot ends after selection audit: no strategy generation or D_IO assertion/oracle comparison,
and no generation decisions feed back from this pilot's gold into the same run. A later benchmark
comparison needs a separately frozen protocol (LLM-selected vs rule/random candidates, plain,
toolinput and witness-only with matched budgets). Keep all earlier failures intact.


- v18 pre-Qwen checkpoint: 52 CPU tests passed; representation17/20, candidate menus13/20,
  seven menus ambiguous on sampled predictions within a scope. Task78 has mixed str/empty-list
  public input representations, conservatively unsupported by current type inference; retain
  zero coverage in the denominator, do not alter this frozen run. Input pools are literal-call
  semantics; hidden aliases are normalized away before native execution. No canonical material
  or plus-inputs have been read for this pilot at this checkpoint.


## v19_rulegen — 2026-10-15, before generation

User authorized implement and run rule-first generation comparison after v18. Full registration: `pipelines/v19_rulegen/PREREG.md`. Same20 dev, K=1, primary behavior+concept vs behavior; plain/placebo/toolinput/witness-only controls; max300 generation requests, same saved references; no canonical-driven model replacement, no held-out run.

## v20_groundedflow CPU increment — 2026-10-15, before tests/outputs

User requires plan then independent subagent audit before implementation. Two reviews complete; all blockers resolved in PLAN_GROUNDED_FLOW_V20.md/P0 resolutions and analysis/v20_plan_review.md. New folder only; initial scope narrowed to multiplicity. Full prereg: pipelines/v20_groundedflow/PREREG.md.21 known authored fixtures + static regressions, then all20 known-dev representation inventory without gold/canonical/reference; no minimum coverage, no GPU/D_IO stage. Freeze before first run, preserve failures. No change to older treatments/results.

### v20 cpu_v2 pre-output correction — 2026-10-15

Independent code audit rejected frozen cpu_v1 despite21/21 fixtures. No inventory/GPU was run. Preserve parent. New copy `v20_groundedflow_checked`,28 prewritten fixtures plus12 static/helper tests; lexical scope, entry shadowing, concrete input provenance, same eligible-value count loss and transparent output transport required. Conditional/Boolean provenance outside current evidence subset. See its PREREG.md and plan amendment; independent post-code review precedes inventory. No gold/reference/model API/D_IO.

### v20 cpu_v3 bounded-analysis correction — 2026-10-15, pre-output

Preserve cpu_v2/28-fixture outputs. Independent audit found coordinator recursion on sources already invalid for reassignment/unbound definitions; inventory not run. New folder v20_groundedflow_bounded, early unsupported return before slicing plus visited-name guard,32 prewritten fixtures/13 static checks. No semantic scope expansion. Independent recheck precedes all20 inventory. No model/oracle/GPU/D_IO.

### v20 cpu_v4 size/depth correction — 2026-10-15, pre-output

Preserve cpu_v3/32-fixture outputs; inventory never run. New v20_groundedflow_strict returns unsupported on oversized/deep AST before recursive helpers, catches parse failures, new oversize fixture/size-depth regression.33 prewritten fixtures/14 helper tests; same semantics and no GPU/D_IO. Post-review before all20 inventory.

### v20 cpu_v5 validator adapter — 2026-10-15, pre-output

cpu_v4 inventory retained:1/20 source supported;12 unresolved TypeError attempts. New v20_groundedflow_domainfix only corrects predicate invocation valid(*args), adds accept/reject integration fixtures and explicit worker reasons.35 prewritten native fixtures/14 static checks; same tasks/subset/validity/spec statuses, no relaxation. Independent review before fresh inventory; no GPU/D_IO.


## v21_qwenchain P1 offline — 2026-10-16, before adapter checks

Scheduled user authorization starts offline interface phase only. New v7 source copy; scope/limits in pipelines/v21_qwenchain/PREREG.md, audited Qwen-chain plan. Mechanical source/schema/lineage/literal/evidence/budget checks with explicitly hand-authored response fixtures. No model/API/GPU/canonical/ref/D_IO or semantic pilot. Check runs preserve hashes/failures; final P1 freeze after review.

## v21_qwenchain_pilot P2 controlled16 — 2026-10-16, pre-completion

User explicitly authorized real Qwen endpoint calls. New copy from frozen v21 P1. Exactly16 authored fixtures,5-stage chain,80 scheduled slots/240attempt maximum; same stage caps, no content repair, no paid fallback. Exact alias normalization/reference maps, JSON field-shape examples, real server raw tokenization with pinned official template and per-completion usage equality. All source/labels/metadata freeze before first completion. Human semantic gate pending: no automatic real20, canonical/ref or D_IO. Full prereg: pipelines/v21_qwenchain_pilot/PREREG.md.

## v21_qwenchain_singlejson prompt-only controlled16 adaptation — 2026-10-16, pre-output

First live pilot final:32 completions,0 validS1/S2, downstream blocked; retained/reported separately. User's broad Qwen-call authorization used for one distinct interface adaptation: single JSON root example, full-spec quote bounds and S2 masked-view clarity. Same validators/16fixtures/gates/caps/transport/role split; no static matcher or output repair. New frozen copy max80slots/240attempts, human gatepending, no real20/D_IO. See its PREREG.md. Do not pool runs or relax validators mid-run.


# v22 contract/alignment audit — registered 2026-10-16 before outputs

User requests fixing both empty-guard contract and missed S3 mismatch. Separate exploratory adaptation after observing v21 singlejson; same16 diagnostic fixtures (not unseen validation). Preserve prior frozen runs. Qwen owns semantics, tools only references/coverage/consistency/execution, no static semantic matcher or fault catalog.

S2 permits empty guard to mean unconditional and empty effect to mean no separately described observable effect (statement remains required). Optional S3 alternative may be empty; selected hypothesis condition/effect remain required. S5 withdraw/unknown may omit condition; keep/revise require it. Prompts state conventions explicitly. S1 retains exact full-spec quote/span provenance, adds instruction not to substitute clause-sized spans while keeping full quote.

S3 adds comparisons: exactly one Qwen-authored audit per S1 obligation, with obligation_ids (one), behavior_ids/source_ids, required_relation, actual_relation, divergence_condition, verdict consistent/mismatch/unknown and justification. Tools check exact coverage/references and explicit verdict-to-hypothesis/terminal consistency, never decide whether semantics are true. Each mismatch must link to a hypothesis; each selected hypothesis must cite a mismatch obligation. Unknown audit cannot be reported as all-consistent abstention. Required/actual relations and divergence (or explicit no divergence established) are model text. Prompt asks whether implementation adds/removes a condition and to consider admissible cases satisfying one relation but not the other; public examples alone cannot establish equivalence. No fixture-specific witness/answer in prompt.

S3 output budget rises1024→2048 to fit audit+existing hypotheses; other caps768/1024/768/1024 unchanged. Max80 scheduled slots,240physical attempts,90112 one-attempt/270336 retry-inclusive output tokens. Context16384,2workers,temperature0,seed/order/16fixtures/domain filters/3cumulative attempts/120s/2+8s retry unchanged. No content repair/retry, no quota reuse, no paid fallback. Same12 unique inputs and ordinary/traced limits; execution evidence is not spec oracle. S4 concrete duplicate example replaced by nonconcrete format description so no discriminator seed provided.

Offline regression checks must include empty-guard/effect, required statement, unknown vs consistent abstention, duplicate/missing audit coverage, wrong-type/foreign references, mismatch-to-hypothesis consistency, alias roundtrip, cached feedback and frozen fixture labels. They establish contracts only, not model accuracy. Source+fixtures freeze before model calls. Same mechanical62mandatory gate>=90%, probe>=6/7, independent human semantic12/16 gate pending; no automatic real20/canonical/ref/D_IO. Report stage failures, coverage, costs, model reasoning examples and limitations separately from prior pilots. If gate fails stop.

Pre-freeze review clarification: absence of S1 obligations requires S3 unknown, not vacuous consistency; absence of S2 behaviors requires unknown comparisons with empty behavior references. Mechanical references permit empty list only when no upstream behavior claims exist.


# S3 isolation diagnostic — 2026-10-16 before outputs

User requests fixing guard and S3 missed mismatch. Full v22 audit diagnostic failed gate largely on upstream ID format; f12 never reached S3. Isolate S3 on exactly f11/f12/f13, the three original singlejson fixtures with accepted real Qwen S1/S2 parents. This set is fixed by prior accepted-parent availability, not new S3 outputs. No new extraction or end-to-end success claim.

Copy frozen v22 treatment/schema/prompts/caps unchanged except VERSION/phase. Import ONLY exact accepted S1/S2 records from frozen v21 singlejson, verify old generation/source snapshot, exact task/source and artifact validation/IDs, preserve Qwen raw/origin and record file hash provenance; do not rewrite content or synthesize claims. Current namespaces validate original registered artifacts. Do not copy original S3 or downstream records.

Exactly3 scheduled S3 slots (2048output tokens each), max9 physical attempts/18432 retry-inclusive output tokens; same context/tokenizer/transport/temperature/seed formula and cumulative attempts. No S4/S5/input/native/ref/canonical/D_IO, no auto20. Freeze replay parent hashes and all source before completions. Every raw result including rejection is retained. Report comparisons/verdicts, status/ID/schema errors, costs, imported-vs-new usage separately. Correct f11, known mismatch f12 and ambiguous f13 are prior seen hand-authored cases; no unseen accuracy/human-gate claim. Interpretation remains provisional.


## 2026-10-17 — v23_concepthyp code-first mechanism diagnostic and separate Luna probe

User authorizes direct best-v7 copy, code/CPU first, clean-context subagent audit, libraries where adequate; optionally gpt-6-luna low to test concept use. New folder v23_concepthyp has parent/port hashes, isolated spec/code views, concept-guided vs direct hypotheses and three matched downstream presentation arms. Full16 seen authored fixtures, no Qwen completions this increment; no benchmark/held-out or automatic progression. Future exact Qwen protocol/caps and truth boundaries in its PREREG.md/README.md; freeze source/generation before post-hoc fixture scoring. CPU scripted responses are not model evidence.

Separate exploratory clean-context Luna/low probe, registered BEFORE agent outputs: exactly f02/f06/f12/f13/f14. One independent agent per concept/plain arm, same original spec/code/base/syntax/native-base evidence. Concept arm additionally receives an authored normative relation/domain/uncertainty, with no hypothesis, fault label, trigger or distinguishing input. Each agent outputs one hypothesis and at most3 literal tests per case, no feedback revision, labels/oracles excluded. One batched context per arm is disclosed; not API-stage-isolated, no exact token/request cost parity. Raw answers frozen together before replay/reference evaluation. Report schema correctness, verdict/trigger review, input discrepancies, correctly specified failing assertions, false alarms, ambiguity and masked-code handling. Equal outcomes mean no observed concept gain. Supplied-concept use only: cannot establish Qwen extraction reliability or benchmark gain. Probe packet hashes in analysis/v23_luna_probe/protocol.json.


### v23 diagnostic16 online authorization and preflight audit resolutions — before first Qwen output

User supplied live endpoint and explicitly requested launch after code completion. This supersedes the code-first/no-Qwen increment status only for diagnostic16. Same registered16 cases and three-arm matrix, no benchmark expansion. Clean-context audit found terminal-failure/resume, inherited CLI, stage reporting, HTTP parser cap and stale CPU gate problems; fixes are made before source freeze with regression tests. Tokenizer/protocol mismatches quarantine and stop globally; ordinary terminal transport/context failures remain failed artifacts. Full-denominator incomplete reporting, no repairs/retry beyond registered transport attempts. Code and exact fixtures CPU-preflight before detached launch; endpoint env-only. Separate Luna probe completed equal3/3 buggy cases for both arms and is not used to tune Qwen prompts, cases or selection.


### v23 completion disposition — 2026-10-17, post-output decision

Diagnostic16 completed exit0; source/generation and160 raw Qwen artifacts verified. Schema reliability does not establish the mechanism: correct assertion cases2/7 in all three arms; semantic alignment, sufficient triggers, expected-output reasoning and argument/prediction transport remain weak. No promotion, automatic real20/benchmark/held-out, output repair or additional Qwen adaptation. Full denominator/costs and independent model-assisted semantic review in analysis/v23_qwen_diagnostic_results.md. Prior frozen protocol is unchanged; this is a completion decision, not a preregistered new test. Callback handled, no duplicate/resume work.


## 2026-10-17 — v24_obligations executable-contract mechanism diagnostic9

User explicitly approves executable obligation repair. Copy best v7, preserve v23. Plan independently audited before code; clean-context code audit/CPU gate required before model outputs.9 seen authored cases: f01/f02/f14/f15/f03/f04/f05/f06/f13 (3buggy,5correct,1ambiguous). Full protocol in pipelines/v24_obligations/PREREG.md and README.md. One model-authored full returned-value relation per function, source quote/domain/uncertainty; restricted isolated predicate and trigger execution; named JSON arguments. Diagnostic-only authored finite semantic qualification explicitly disclosed, never represented as reference-free spec verification. No bank rows or failed-predicate repairs fed to model.

Freeze24 type-only Hypothesis inputs/task plus bases before Qwen. Code-only behavior, model hypothesis, one fixed-pool feedback revision; obligation immutable. Witness support needs qualified predicate, true trigger, reached target and observed violation; counterevidence/unknowns preserved. Same6 selected concrete inputs/native traces for verified_hyp/text_hyp/toolinput; no private witness.2 generation calls×3 candidates/arm, raw AND mechanically selected yields scored using SAME independent post-freeze fixture oracle. witness_only entire24+base pool; novel task/input detections subtract whole pool. f13 unqualified/no gold oracle, raw overconfidence preserved. Input-generation-only, not model expected-output or changed-oracle efficacy. Max90 logical/270 completion attempts; tokenizer/liveness separate; no content repair, paid fallback or automatic real20/held-out/benchmark. CPU scripted controls are not model evidence.


### v24 code-audit resolutions — before any Qwen completion

Clean-context audit found semantic-bank loose-type gaps (float/int and bool/int inside lists), interrupted worker result recovery/rerun ambiguity, missing reach counterevidence for hypothesis revision and incomplete novelty/coverage/worker-cost reporting. Fixed before freeze: typed negative probes and CPU controls; durable one-attempt isolated execution with private .part output and atomic canonical cache; no retry of interrupted unknowns; explicit S4 reach/native/omission/counterexample data; full raw/selected/novel/duplicate/fallback reporting and recorded launches/reported calls with interrupted upper bounds. Worker binary/version pinned in dependency/cache identities. No previous model output used to tune these changes. Shared pool may saturate3 bugs; no score-based pool change or new-task gain claim under saturation.


### v24 completion disposition —2026-10-17, post-output decision

Frozen diagnostic9 completed90/90 calls. Contract0/9 accepted (Python/prose fields swapped), generation0/54 accepted (Markdown fences), initial/final hypothesis8/9 and1/9. Calibration never reached for Qwen obligations; all support unverified, no generated inputs/flags to evaluate. Text control loses rejected artifact content via value(), so intended executable/raw-text contrast not realized. Witness-only3/3 bugs saturates cohort. Report interface infeasibility with full9 denominator and separate CPU/trigger counts; do not treat zero flags as precision or these zeros as a causal concept-effectiveness test. No field swap, fence extraction, missing-field filling, recovered candidate execution, repairs, new adaptation or benchmark launch. Source/raw artifacts unchanged. Completion callback handled.


## 2026-10-17 — v25_interface_gate, prospective split-output feasibility5

User explicitly authorizes continuation, clean-context audits and old endpoint automatic use when GPU returns~10min. New best-v7 copy, explicit v24 audited runtime ports; v24 unchanged. Five seen authored cases f02/f04/f06/f14/f13. Code-only predicate separate from spec-only metadata; code-only trigger separate from small hypothesis metadata; structured JSON inputs. Parser prospectively accepts bare payload or exactly one matching whole fence with no extra prose, never swaps/fills/repairs content or recovers v24. Raw text control preserves original response bytes/status/origin/hash regardless of validation.

Small staged feasibility only: A four defined predicates calibrated +f13 proper unknown; B three bugs supported +correct unused-set f14 consistent/no pool violation +f13 unknown; C valid discriminators, f14 normal contrast/obligation=True, f13 inputs=[] with reason. Gate failure stops dependent phases, full5 denominator and NA slots preserved. Frozen24+base type-only pools/typed negative bank; finite diagnostic-gold calibration disclosed. Common6 selected by contract violation then input order BEFORE hypotheses; same rows across exported controls. No model arm comparison or benchmark launch. Novel inputs/tasks subtract whole pool, same independent post-freeze oracle; witness ceiling may saturate3 bugs.

Source/CPU freeze before optional capability selection: root OpenAPI advertised guided_json plus at most1 adversarial echo (prompt NOT_JSON, exact bare JSON {schema_gate:true},64 output tokens, seed20261017, cumulative3 transport attempts) determines guided vs plain before tasks. No task-output-based mode change; protocol/tokenizer mismatch stops globally. Max30 task slots/30720 logical output tokens plus1 echo64; physical attempt ceiling93. Metadata/wait/liveness separately counted; endpoint env-only, no paid fallback/content retry/new adaptation. Plan audited before code; code/CPU audit before any real completion.


### Pre-output audit clarification —2026-10-17

Before any echo/task completion: f14 Gate B requires every full-pool obligation check
evaluated=True and native checked with a usable observation (unknown is not a pass).
Bug Gate C requires observed_supported over the generated candidates, including no
known trigger counterexample/unresolved evidence, plus at least one witness. This
makes explicit the registered conjunction. Other candidates retain individual
binding/domain/runtime outcomes in the denominator; they are never silently repaired.
Failure-stage exported controls include identical selected native pool rows even when
no contract qualifies. Resume reconstructs missing context exports from durable cases
without repeating model calls. Decoded whole-envelope payload/framing are retained
even when subsequent syntax/schema checks reject it. Capability raw evidence is hash
bound and included in final snapshot. Worker calls and unresolved upper bounds are
reported separately from model/tokenizer metadata traffic and CPU preflight.


### v25 completion disposition —2026-10-17, post-output decision

Owned feasibility5 stopped after gate A with no task completion body: f02/f04 each3ReadTimeout; f06 completion503→404; f14/f13 tokenizer3HTTP errors each. A=false/B-C blocked, no task semantics or serialization performance observed. Tiny capability echo passed42/10tokens and fixed guided_json;8task completion attempts have unknown usage, not zero consumption. Preserve all attempts/raw records/frozen source; no recovery, reset, alternate backend, prompt adaptation or relaunch. Raw nulls reflect missing transport responses. All5 denominators retained; generation/false-flag/novelty zeros are unmeasured defaults, not concept efficacy. Read-only native baseline3/3bugs/36inputs saturates cohort. Transport cause beyond persisted timeout/503/404/tokenizer errors remains unknown. Callback handled; no automatic comparison/benchmark/real20/held-out/paid calls. Independent terminal review and analysis-time ledger hashes recorded separately from original freeze.


## 2026-10-17 — delayed v25 transport probe, before new completions

User says "10 nữa thử lại" after proposal of a2-call transport diagnostic; schedule one owned new probe at2026-10-17T14:08:06UTC (~21:08Vietnam), old endpoint env-only. No edits/resets to original frozen v25 attempts/source. Utility outside pipeline; imports frozen interfaces read-only, not a new semantic treatment. Exact f02 metadata messages/seed/model/temp/top_p/max_tokens768 from v25; plain first then identical request plus guided_json schema. Fixed order is operational diagnosis, not a causal backend comparison. Max2 completion requests/1536 output-token ceiling,1 physical attempt each, max2 metadata requests (models/tokenize) once; no retries, wait polls or fresh echo. Readiness/protocol failure blocks remaining calls. A received usage-valid but schema-invalid plain output still permits guided transport probe. No diagnostic5 chaining/full comparison/benchmark/real20/held-out/paid calls even on success.

Freeze utility hash, original v25 source/run snapshot identity, both payloads and scheduled timestamp before network. Before/after verification uses unchanged old source/data hashes. HTTP status, latency, bounded redacted body/hash, exact received response/usage or unknown-usage reservation persist in separate out/transport_probes/v25_20261017_140806. Response errors cannot establish server-internal root cause without server logs. Missing/uncertain responses never become zero-cost or semantic failures. Scheduled controller detached with exclusive lock; any existing attempt reservation is consumed and never resent. Terminal same-thread callback will audit/report; no endpoint URL/key in files/logs. Authored httpx controls plus clean-context audit precede launch.


### Delayed transport probe disposition —2026-10-17, post-output

Scheduled probe ran14:08:06UTC; only models GET attempted, HTTP404/ERR_NGROK_3200 endpoint offline after0.217735796s. Metadata preflight failed before tokenizer/plain/guided;0completion attempts/0unknown completion usage. No backend/schema/semantic comparison. Source/probe hash/original v25 artifacts unchanged. Preserve frozen utility and attempts; no retry/reset/diagnostic5/benchmark/paid calls. Error body bare-hostname privacy gap documented without copying hostname into analysis; no repair of frozen source. Terminal callback handled.


## 2026-10-18 — explicitly authorized fresh transport retry

User says "tử lại đi" after prior endpoint-offline report. Fresh run v25_20261018_040624, immediate old-endpoint retry, original diagnostic5 and prior probe untouched. Reuse exact frozen f02 plain/guided payloads, fixed plain-first order, max2single-attempt completions/1536output-token ceiling and max2metadata GET-models/POST-tokenize once. Preflight or plain transport/protocol failure blocks remaining calls. No reset/retry/polling/diagnostic5/full comparison/benchmark/real20/held-out/paid expansion. Frozen utility is reused read-only through new wrapper; only persistence privacy adapter masks bare/encoded hostname. Protocol records original source/snapshot identity, frozen utility hash, fresh wrapper hash and exact payload pair before network. New output directory must not exist (exclusive creation), including interrupted/terminal run. HTTP latency/status/sanitized body and known vs unknown completion usage retained. Local CPU controls and independent audit before launch; terminal callback audits actual results. Sequential-order/server-log limits unchanged. No endpoint/hostname/key in tracked reports or logs; no Kaggle changes.

Audit clarification before launch: authorization/cap applies only to v25_20261018_040624. Never create another run-id automatically after any failure.7local HTTP/privacy controls pass; clean-context wrapper audit reports no blocker. No actual model output used to tune this retry.


# Luna chain diagnostic — 2026-10-18 before subagent outputs

User explicitly requests Luna subagent comparison to test model bottleneck. Six fixed packet probes: S2 f10/f02/f12 (representative v22 local-ID/item-cap failures), S3 f11/f12/f13 (all prior accepted-parent replay cases, including consistency/mismatch/ambiguity). This is failure-targeted, seen-case diagnostic, not representative accuracy/causal model benchmark.

Read exact saved Qwen request messages, give each packet to a fresh gpt-6-luna subagent with no parent history. No evaluator labels, Qwen answers, reports, hints or schema repair supplied. Subagent may read its packet and write one response only; no code inspection outside packet, tests, extra agents or endpoint calls. System/user message content is unchanged; subagent wrapper/tools/default reasoning budget differ from Qwen endpoint. Cannot match raw token cap/temperature/decoding or measure comparable token costs through this harness. Record this limitation, model name, packet hashes and one-attempt/no-content-retry contract.

Score with existing frozen v22 alias expansion/schema validation, exact task/registry/selected IDs. Raw text unchanged; any invalid output stays invalid. S3 semantic review assesses whether required-vs-actual divergence is noticed, condition sufficiency, correct-control false alarms and unknown eligibility kept unknown; provisional manual interpretation, not semantic accuracy certification. No generation/native inputs/D_IO, paid API fallback or automatic pipeline promotion. No first-pilot source modifications.


## 2026-10-18 — native v23/v24/v25 diagnostics with requested Luna/low subagents

User explicitly requests model gpt-5.6-luna low retest of thread versions, tools optionally disabled. Prereg in analysis/luna_versions_20261018/PREREG.md written before model outputs; native16/9/5 cohorts and exact run(client,root) engines preserved, fresh output roots only. Adapter and source freezes, independent plan/code audits,16CPU checks and single actual canary precede scientific task launch16:36:02UTC. Max160+90+30 single-attempt task CLI invocations plus1canary turn; no endpoint/paidAPI/fallback/held-out/benchmark. v25 plain backend and originalA/B/C early-stop.

Operational canary outcome/amendment explicitly preserved:2config-only CLI rejections before any model turn, then1canary (13565in/199out) FAILED schema-exposure gate, host denied its tool attempt. Before scientific tasks, epoch4 permits exactly2pre-turn configuration warnings, discloses schemas exposed/host disabled, rejects any task tool/router attempt before score/cache. No additional canary or task-based prompt repair. Role flattening/base instructions and unenforced numeric Qwen sampling/output budgets differ; no matched causal model inference. Requested CLI identity/catalog only unless server event supplies ID; separate origins/usage, oldQwen/otherLuna results unchanged. See protocol_v4/readiness_v4 and AUDIT.md. This is native small diagnostics only; no automatic wider comparison even if v25 passes.


## 2026-10-19 — explicit continuation of Luna v23/v24 after usage limit

User says "thử tiếp đi m". Original epoch1v23/v24 stopped with usage-limit turn.failed/error, after73/65accepted stage responses, one unknown-usage quota attempt each; no task tool execution. v25 remains completedAfailed. Register before calls in analysis/luna_versions_continue_20261019/PREREG.md. Newroot imports complete old native artifacts/caches byte-identically, original whole-file inventories+source hashes verified. Originalsource/Client/prompt/schema unchanged, accepted stages reused, not new independent samples. Only missing stages can call exactgpt-5.6-luna/low through new continuation_transport namespace, max87/25 new single attempts; quota slots cumulativeatmost2 undernewauthorization. No auto retries/further run-id. Startv23first; v24 onlyafterfreshreceivedresponse confirms access. No new canary/model/provider/Qwen/paid/benchmark/held-out. Native costs omit newnamespace, so external aggregates old+new exactlyonce; retain original2unknown usages and pause-across-days/harness limits. No v25validator repair or rerun inthiscontinuation. Independent read-only audit and CPUcopy/provenance checks before call.


### Luna native diagnostic retest disposition —2026-10-19, post-output

Complete original16/9/5denominators afterexplicitquota continuation; noacceptedresponsesrepeated, old2quotaunknown preserved.251receivedtargetresponses/253CLIinvocations, no tasktool/router use. v23C/D/H correctbugassertioncases5/7/5of7,FA1/0/0,2C/HcasesblockedmalformedhypothesisJSON; rawreasoningfaithful, f13C/Hunknownvsdirectunsupportedrule. v24verifiedselected1/3bugs vtext/tool/witness3/3; normativerelationsfaithfulbutexplicitpolicyviolation/validatorfalsepositives andfrozen-supportgaterejectusefulf06newwitness. v25AfalseB/Cblocked;3correct-in-domainpredicatesrejectedbyglobalcomprehensionnameset. No repairs/renaming/execution/rescoringrejectedpredicates, newmodel/comparison/benchmark/heldout/paidcalls orpromotion. Reportrawvsgatedinputyield,unknownoracle,finiteauthoredgoldlimits andrequestedCLIrole/sampling/serveridentity limits. Originalcanaryexposurefailed,schemasexposedhostdisabled; donotrelabelfullytoolsfree. Cumulativeknown2,010,148/54,531targettokens,canaryseparate13,565/199,2quotausagesunknown. Callback/workcomplete, noactivejoborautomaticretry. Independentterminalreviews+read-onlyintegrity/costverificationrecorded; futurefixrequiresnewfrozenvariant/protocol.


## 2026-10-19 — v32_scope_support, prospective lexical scope + cumulative support

User accepts fixes after Luna version retest. New best-v7 copy + explicit v25 ports;
no frozen historical source/output repair or rescore. Detailed preregistration in
pipelines/v32_scope_support/PREREG.md. CPU regression tests and clean-context audits
before freeze. Same seen5 authored packets/full24+base pool, fresh Luna/low requested
through unchanged CLI adapter, max30 single attempts; no Qwen endpoint/paid fallback.
A finite contract calibration, B supported or fully-known all-trigger-False provisional
admission, C cumulative evidence and novel witness/consistent contrast/abstention.
Provisional candidate never labeled verified. Unknown/invalid slots and old evidence
retained. No full arm comparison or task-gain claim, benchmark/real20/held-out/retry.
Raw origin, usage, worker calls, full-pool novelty, all5 failures and semantic review
reported. Old inventories verified; package immutable after model launch.


### v32 disposition — post-output 2026-10-19

Fresh seen5 Atrue/Bfalse/Cblocked,22receivedCLIcalls. Lexical reuse accepted in f04/f14; support promotion only CPU-tested. f06 trigger wrong signature rejected unchanged, plus evidence-grounding error. No prompt/source/output repair, retry, comparison or benchmark chaining. All5/usage/workers/unknown coverage and independent reviews in analysis/v32_scope_support_20261019/REPORT.md and RESULTS §11.73.


## 2026-10-21 — Astra D1 supplied-concept selective revision, before task outputs

Explicit user authorization: exactqwen2.5-coder-32b-instruct on suppliedendpoint, no paidfallback; Codexquota stop<=15%. Newbest-v7copy v40_concept_agent +explicitv30tools/v23fixtures, originalrunsunchanged. Priorart includesv28active replay33nativechecked withnoincrementalgain; D1novelmeasurement is prediction→evidence→selectiverevision, notfirsttooluse. Protocol in pipelines/v40_concept_agent/PREREG.md and d1_protocol.json.8seen authored episodes,3arms(conceptadaptive/genericadaptive/conceptcommitted),3turns/arm,72single-attempttaskcalls; no retries/reset. Same spec/code/base/fallibleH/raw observations; C adds strict relation/binding/recomputedgap package. Private evaluator/examples excluded, no oracleverdict fromtools. Two native sharedrows/case; E3/E6already exposing, discoverydenominatorE1/E2/E4/E5. Max6actions4replays2finalinputs/arm,160native requests/320processes overall; input6144/output1536/context8192 withtokenizerbinding andexactmodelmetadata required. All24rows/72slots retained, unknowns explicit. No hard claim gate for finalinput; artifact predictiondurablebeforequeries. MeaningfulCPU12/12 andclean-context codeaudit passed; exactsource/prepared/dependency/guard frozen beforeanytaskcall. Capability is notconceptutility; genericparity orcommittedparity/insufficientopportunities meansnoincremental/combinedclaim andno n/Kexpansion,training,benchmarkorheldout. TodayprelaunchmodelsGET404; no task/model/tokenizer calls haveoccurred. No readjustment based onmodeloutputs.


### 2026-10-21 v40 external delayed-launch authorization (before Qwen outputs)

User says wait10min thenrun unchangeddiagnostic. Notbefore05:23:50UTC/12:23:50Vietnam, detached externalcontroller; no treatment/schema/source/seed changes. Quota>15% +frozenverification +exactmodel/context/tokenizer remainrequired. Waitquotaresetonly; terminaltransport/protocolfailure stops, no retry/fallback orunknownslotreset. CallbackusesCodexqueueexistingthread toavoidpreviousactivewriterconflict. All72slotsstillnotattemptedatscheduling. See analysis/v40_concept_agent_20261021/SCHEDULE.md andruntime delayed_launch.json.


### v40 terminal disposition2026-10-21 — incomplete, no semantic treatment result

Scheduledauthorizedlaunch occurred05:23:51UTC; exactmodel/context/tokenizer matched, firstE3conceptadaptivecompletion failedtransport after180.101s. Oneunknown-usageattemptconsumed,0modelresponses,71slotsnotattempted. No schema/evidence/tool-use/semanticresult, no retry/reset orfrozenprompt/source/outputrepair. Terminal162-fileinventoryandindependentreadonlyaudit verified. Report RESULTS§11.79 and analysis/v40_concept_agent_20261021/TERMINAL.md. No automaticnewrun/benchmark/paid/training; underlyingtransportsubcauseunobserved.


## 2026-10-21 — explicit v40 transport retry, before new outputs

User says “thuwr lai di”. One fresh d1_retry_20261021 namespace with unchanged
frozen v40 treatment/180s client. See analysis/v40_retry_20261021/PREREG.md.
Historical d1 remains byte-identical with1unknown completion consumed. Newcap72
single attempts, cumulativecap73; shared CPU preparation/approval copied identically,
not rerun or independent evidence. New root passed explicitly to unchanged d1.run.
No new probe/canary, prompt adaptation, timeout change, unknown-attempt reset,
automatic retry, paid fallback, training, benchmark or held-out. Quota<=15 stops.
Transport/protocol failure stops. Clean-context external-launcher audit before calls;
post-terminal full-slot saved-data review plus new/cumulative cost reporting.


### Explicit v40 retry terminal disposition —2026-10-21, post-preflight

New root d1_retry_20261021 stopped12:22:34UTC on requested_model_or_context_unavailable
after one received/models request. Exactalias/context8192 combined check failed;
metadata body absent, so individual failed condition/served model unobserved.
No tokenizer/completion/new workers; all72slots not_attempted. Original1unknown
attempt and frozen source/old inventory untouched, no further retry or repair.
Saved-data scoring only; no concept/capability/semantic conclusion.


## 2026-10-21 — second explicit v40 retry, metadata gate only

User says “thế thử đi”; protocol registered before request in
analysis/v40_retry2_20261021/PREREG.md. One GET/models saved secret-safe body/hash
to diagnose alias and context separately, conditional unchanged32BD1 only if
frozenmetadata matches. HTTP200 advertises only qwen2.5-coder-7b-instruct/16384;
required32B alias absent, so conditional diagnostic never launched.0tokenizer/
completions/workers;72notattempted. No silent substitution/repair/automaticretry.
This metadata does not recover previousretry's missing response body.


## 2026-10-21 — third explicit v40 retry after served32B correction, before task calls

User supplies32Bservedlabel and says retry. Prospective GET/models (protocol
analysis/v40_retry3_20261021/PREREG.md) at13:18UTC returns exact32B alias/context8192,
rootQwen/Qwen2.5-Coder-32B-Instruct-AWQ. Metadata advertised, not loadedweightproof.
Fresh d1_retry3_20261021 registered, copied byte-identical historical preparation/
shared/approval, all3prior inventories unchanged. Up to72fresh single-attempt
completions+cumulativeoriginal1unknown=73ceiling; priorretry1/2 completions0.
Frozen treatment/180s unchanged, explicitroot launcher requires clean-contextaudit
beforecalls. Stopquota<=15 ortransport/protocol; no automaticretry/reset/repair,
substitution, paidfallback, benchmark/heldout/training. Preliminary1metadataGET
separate from frozenclientmetadata; preserve actual new/cumulative costs/unknowns.


### v40 retry3 terminal disposition —2026-10-21, post-output

Complete72/72received,65controlleraccepted,all24finalvalid. Threearms6/6revealing
buggytasks and4/4no-supplied cases,0CA-only/0oppositetaskwins. CAfailedcorrect-H
retentionE2/E4, E6multiplicityretention andcoherentE3normativebindingrejection;
E7finalcalibrated/E8unknown. Proactive E1/E5/E6 notcountedfeedbackrevision, onlyE7
clearunresolvedinitialHchallenge<2registeredminimum. CC7/8emptylaterbatches and
6invalidT2 limit causaladaptivity inference. Registeredcapability+incremental
conceptrequirements fail; combinedpackage no-go. No treatment/outputrepair,
retry/reset, modelassertionclaim, automatic n/Kexpansion/training/benchmark/paid.
Savedpost-freeze fixture scoring and2independent semanticreviews+integrity/cost
auditcompleted, oldunknown preserved. SeeRESULTS§11.82 andanalysis/v40_retry3_20261021.


## 2026-10-22 Vietnam — v43 tool-assisted binding selection, before model calls

Explicit user implement+run. Freshbest-v7copy v43_concept_identify+hashedv40ports.
Globalfinite relationvocabulary, Qwenproposes8candidate sets then16pairedraw/tool
finals, max24single-attemptcompletions. No per-taskAstrabinding/goldfill. Same
78reused nativeobservations inbotharms, no newPUTcalls/newinputdiscovery claim.
Prospectivefullprotocol/amendments in pipelinePREREG; pairednormativebinding/
observedbehavioradjudication, >=2tool-onlyepisodewins/0oppositelosses/controlchecks.
CPU19/19pass, independentexact-sourcepreparation+frozen-readinessauditsPASS.
60source/eightpools/deps+all4parentinventories frozen beforemetadata/taskcalls.
Stableenv replaces vanishedtemporaryenv, originalparents unchanged. Up to25
metadata-onlycontext-envelope readiness requests registered; taskrunapproval
awaitsreadinessresult. No content/transportretry/fallback/training/benchmark.
Userquota<=15 stop, safequota-onlycachedcontinuation; oldunknowns neverreset.


### v43 pre-inference engineering amendment — synthetic readiness1 over-cap

Originalreadiness1 stoppedE1synthetictool8359>6144, only4metadatarequests/0model
completions. Failedstatus/rawmetadata preserved. No actualcandidatebinding outcome
observed. Explicit user implement+run permits prospective engineeringcorrection:
analysis/v43_concept_identify_20261021/READINESS_AMENDMENT.md supersedes ONLY the
original synthetic-readiness stop/noautomaticrepair orchestration rule. One fresh
readiness2<=25metadatarequests with validpublicquote/realargumentmeasurements and
partialASTreadshapes, no diagnosticrelation/goldcomputation; no payloadtruncation.
60frozen source/eightpools/prompt/schema/model/arms/caps/scientificGOgates unchanged.
Independent review before newmetadata, anyreadiness2failure stops. No additional
taskattempts beyond24, no oldnamespace/unknownreset, no thirdreadinessadaptation.


V43 metric operationalization before anycompletion: evaluator-only rubric at
analysis/v43_concept_identify_20261021/EVALUATOR_RUBRIC.md. Testedfacet coverage,
selectedbindingtruth/roles, truthfulimplementationjudgment andcontrols assessed
separately; no repairedcandidatefill. Exactquoteformat separate from semantic
entailment. Original>=2tool-onlysemanticwins/0loss gate unchanged; pureformat wins
are notsemanticwins. All8cases retained, including missingcandidate/blockedfinals.


### v43 terminal disposition — post-output2026-10-22Vietnam

18received/4schemainvalid+6blocked =>all24slots,0retry/unknownv43completion.
All8initial/10actualfinals/6blocked independentlyreviewed. Completebinding+judgment
raw1/8,tool2/8,1tool-onlysemanticwinE5/0loss (<2required),toolvalid5/8not8; E7not
correctlyresolved/E8normativeambiguityfailure. RegisteredscientificNO-GO, no new
calls/n/K/schemaadaptation/goldcandidatefill/training/benchmark. E3rawcorrect
bindingblockedbyunknownconceptenumretainedwithoutrepair. Readiness1FAILED8359
andpre-inferenceengineeringamendment/readiness2READY4748 preserved/reported, no
thirdadaptation. Source/pools/parents/outputsunchanged; saved-datareviewonly.


## 2026-10-23 — round-novelty saved-data analysis (v11_fair dev), before scoring

CPU-only analysis of saved v11_fair dev outputs (ref oracle), motivated by Anthropic's code-review blog (59% of
repeatedly flagged code existed at the first review pass). Splits each hybrid sample into round 1 / round 2 and
asks whether round 2 finds bugs round 1 missed, and whether real hints beat matched placebo on that novelty.
Full registration, gate (replay must equal final_protocol_v11_dev.json), definitions and decision rule:
[analysis/round_novelty_20261023/PREREG.md](analysis/round_novelty_20261023/PREREG.md). No LLM call, no new run.


## 2026-10-23 — v51 latent concept oracle (frozen Qwen2.5-Coder-1.5B probes), before any VibePass score

User-approved new direction ("đồng ý"). Concept-bottleneck probes on frozen hidden states as a per-input oracle,
trained on MBPP+ mutants (tool-labelled discrepancy concepts), tested on the saved v41 VibePass pool; controls are the
direct probe, a placebo bottleneck, and verbal/likelihood/surface baselines. CPU only, $0. Full registration and
decision rule: [analysis/v51_latent_concept/PREREG.md](analysis/v51_latent_concept/PREREG.md).
