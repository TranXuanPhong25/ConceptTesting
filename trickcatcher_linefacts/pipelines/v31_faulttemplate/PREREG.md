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

## Amendment v21_flowtools-1 (2026-10-18, before any flowtools model output)

Registered before the first completion of `flow_run.py`. User authorized finishing the plan
(`PLAN_FLOW_HYPOTHESIS_TOOLS.md` steps 3–5) with the Qwen endpoint on 2026-10-18.

- Model: qwen2.5-coder-7b-instruct (vLLM, context 16384), temperature 0, top_p 1, seeds from
  `config.json:flowrun.seed` + case/arm hash. Transport/token accounting = v23 client port; max 3
  attempts per call; failed or schema-invalid calls stay in the denominator (no repair calls).
- Cohorts, run in this order, each frozen (`protocol.json`, `generation_frozen.json`) before scoring:
  1. `diag16`: the 16 controlled v23 fixtures (7 buggy with known witness, f13 ambiguous and unscored).
     Common inputs = public base calls. Scoring oracle = `fixture_oracles.py`.
  2. `pilot20`: the 20 v7 pilot tasks (frozen design cohort, not held-out). Common witnesses = v7 frozen
     fuzz `tool_inputs`, stored order, first 6. Domain filter = v7 mined validator. Scoring oracle =
     HumanEval+ v0.1.10 canonical solution, used only by `score` after the generation freeze.
- Shared per case (frozen once, used by every arm): concept (spec only), behavior (code + CFG structure),
  up to 2 hypotheses (v23-style JSON Schema). Only `verdict=mismatch` hypotheses enter packages, in model order.
- Arms (all 10 from the plan): concept+hyp, input+hyp, concept+input+hyp, agent-tools, fixed-tools,
  flow+input, toolinput, plain, placebo+input (truthful base-covered statements), witness-only.
  Each LLM arm: 2 rounds + 1 final call = 3 calls. Probe arms propose ≤6 inputs per round and get replay
  feedback for them; fixed-tools uses `fixed_schedule`; agent-tools chooses ≤6 tool actions per round.
  Final call: ≤6 tests {arguments, expected}, executed with no further revision.
- Metrics per arm: tasks with a confirmed detection (admissible input, PUT ≠ reference, model expected ==
  reference), same beyond the witness-only pool, false alarms (expected ≠ PUT while PUT == reference),
  input-discrepancy tasks, schema errors, calls/tokens, tool actions/errors. Paired task wins/losses vs
  toolinput, plain, placebo+input, flow+input, input+hyp, fixed-tools.
- Interpretation: descriptive diagnostic only (n=16/20, K=1). No human semantic adjudication has been
  done, so no claim about hypothesis correctness and no promotion over v7. A concept arm counts as
  promising only if it beats toolinput AND plain AND placebo+input on paired task detection with no more
  false alarms; otherwise report as negative/inconclusive.

## Amendment v21_flowtools-2 (2026-10-18, after 8 shared hypothesis responses, before any arm or score)

Format-only fix. The first diag16 launch rejected all 8 received hypothesis responses as `invalid_JSON`
because Qwen wrapped the object in one ```json fence (concept/behavior 32/32 were raw JSON). No arm call,
execution of model inputs or scoring had happened. Change: `flow_run.validate` uses the ported
`schemas.extract` (whole-text JSON or exactly one fenced object, no other JSON outside), then the same JSON
Schema. The first attempt is archived unchanged as `flowrun/diag16_attempt1_fenced_parse/`; its transport
cache is copied so already received completions are re-validated, not re-sampled. Everything else in
amendment 1 is unchanged.

## Amendment v21_flowtools-3 (2026-10-18, after the diag16 attempt-2 score, before any pilot20 arm)

Two pipeline defects found in the diag16 attempt-2 records (scored, archived unchanged as
`flowrun/diag16_attempt2_inputfmt/`; reported as a superseded diagnostic, not the registered result):
1. Bug: `fixed_schedule` replays with `ids=[]` (cases without hypotheses) were rejected as
   `ids_shape_or_count` (96 actions), so fixed-tools lost replay feedback on 8 cases. Fix: an empty optional
   id list is accepted.
2. Format confound: 30–45% of inputs in arms without example inputs (plain, concept+hyp) were rejected
   because the model wrote a bare value (`[1, 1]`) or an unparenthesized argument list. Fix: one
   arm-neutral `parse_call` normalization used by replay, final execution and scoring: full tuple; else for
   a one-parameter function wrap the literal as (value,); else wrap the text in parentheses; else reject.
pilot20 attempt 1 was stopped after 4 shared stages and no arm (archived as `flowrun/pilot20_attempt1/`).
Both cohorts rerun from scratch with transport caches copied (identical prompts reuse received
completions; changed feedback produces new calls). Metrics, arms and decision rule of amendment 1 unchanged;
the registered diag16 result is the attempt-3 score.
- 2026-10-18 operational note (amendment 3): the first attempt-3 launch failed on cache-slot collisions
  (copied attempt-2 slots with different prompts, `immutable_record_changed:request.json`), before freeze or
  score. Slot names now include the prompt digest; reruns start from empty transport caches. Partial attempt
  archived as `flowrun/*_attempt3_slotclash/`.
- 2026-10-18 operational note 2: the next launch hit a temp-file race (fixtures with identical specs share a
  token-count file; fixed `.tmp` name) → `FileNotFoundError` in shared stages, before any arm. Temp names are
  now unique per process/thread. Partial run archived as `flowrun/diag16_attempt4_tmprace/`.

## v26_proporacle preregistration (2026-10-18, before any v26 model output)

Plan: `trickcatcher_linefacts/PLAN_PROPERTY_ORACLE.md`. User approved on 2026-10-18 after the v21_flowtools result.
Folder copied from `v21_flowtools` (infra parent; PARENT.json). Amendments above belong to v21 and are inherited text.

- Model/transport as v21 amendment 1 (Qwen2.5-Coder-7B, temperature 0, v23 client port, ≤3 attempts/call,
  prompt-digest slots, schema-invalid = arm error kept in the denominator, no repair calls).
- Cohorts in order: pilot20 (primary), diag16 (secondary; known ceiling).
- Fixed pool per task (no model, no outcome selection): frozen witnesses + public base calls, then the v21
  frozen final-test inputs of all arms sorted by sha256(literal); first 12; `parse_call` normalization.
  Only admissible (mined validator / fixture domain) and natively checked inputs reach oracles.
- Arms (one call per task each): exact_spec, exact_code, property (≤3 `check(args, output, error)`),
  metamorphic (≤2 `follow` + `relation`). Model code runs in the isolated sandbox (2 s, 512 MiB, no network);
  errors are unknown. Verdict per input: bug / ok / unknown (exact: expected ≠ / == PUT; property: any False;
  metamorphic: any relation False on an admissible follow-up).
- Scoring only after `generation_frozen.json`, reference = HumanEval+ v0.1.10 canonical (pilot20) or
  `fixture_oracles` (diag16, f13 unscored). Input-level TP (bug & PUT ≠ reference; metamorphic also counts a
  discrepancy on the follow-up), false alarm, missed, unknown; precision; task-level confirmed and false-alarm
  tasks. Evaluator-only property soundness: property evaluated on the reference output.
- Secondary: consensus (exact_code ∧ property) and union.
- Decision rule: property or metamorphic is "promising" only if on pilot20 its precision exceeds both exact
  arms AND its confirmed-task count ≥ exact_code. Descriptive only (n=20, K=1); no promotion over v7.

### v26 amendment 1 (2026-10-18, after 7 pilot20 cases, before freeze/score)

Format-only. Qwen often returned a bare JSON array instead of the requested object, mostly in the exact
arms (e.g. 9 of the first 14 exact calls), which would bias the comparison against the baseline arms.
Rule now applied identically to all arms: a bare array (raw or in one fence) is wrapped as
`{<array field>: [...], "reason": "wrapped_bare_array"}`, then the same JSON Schema. Attempt archived as
`oracle/pilot20_attempt1_barearray/`; its transport cache is copied (prompt-digest slots, identical prompts),
so received completions are re-validated, not re-sampled. Nothing else changes.

## v27_codexoracle preregistration (2026-10-18, before any v27 registered output)

User question: is the v26 oracle failure caused by the model (Qwen 7B) or by an insufficiently precise prompt?
Design: 2×2 model {qwen2.5-coder-7b, Codex CLI gpt-5.6-luna reasoning=low} × prompt {original v26, strict}.
Pools, arms, sandbox, freeze and scoring are identical to the v26 preregistration (same code, copied).
The qwen×original cell is the frozen v26 result (`out/pipelines/v26_proporacle/.../oracle/{pilot20,diag16}`).
New cells: codex×original, codex×strict, qwen×strict, each on pilot20 (primary) and diag16.

- Strict = original instruction + appended rules targeting the v26 failure modes (special-case guards, relate args
  to output, no unstated requirements, only defined names, exact Python type of expected literals, spec-only
  derivation). Fixed before seeing any strict output (`oracle_run.STRICT`).
- Codex runs `codex exec` in an empty read-only directory with --ignore-rules/--ephemeral: it sees only the prompt.
  One live single-case smoke (diag16 f02, codex×original) ran in scratch before this registration to check the
  interface; it is not part of any reported cell. Up to 3 attempts per call; failures stay in the denominator.
- Reading: model effect = codex vs qwen at fixed prompt; prompt effect = strict vs original at fixed model;
  per cell report precision, TP/FA, confirmed/FA tasks, property soundness on reference outputs.
  "Model-limited" if codex×original clearly beats qwen×original (precision and soundness); "prompt-limited" if
  strict clearly improves qwen; both may hold. Descriptive only (n=20/16, K=1).

## v28_codexflow preregistration (2026-10-18, before any v28 registered output)

User request: run the full pipeline on part of the dataset with Codex to see whether the direction improves with a
stronger model than Qwen. Finding before this run: in v27 Codex could execute shell commands inside its read-only
sandbox (verified with a SHA-256 probe), so v27 Codex cells measured model + code execution. v28 disables Codex tools
(`--disable shell_tool code_mode_host browser_use computer_use apps`); probe confirms no execution; every response
records `tool_executions` (must be 0).

1. Full pipeline = v21_flowtools `flow_run.py` unchanged in logic (shared concept/behavior/hypothesis, common
   discovery, 9 LLM arms × 3 calls + witness-only, freeze, scoring) with model = Codex gpt-5.6-luna reasoning=low,
   no tools. Cohort: pilot20 (same 20 tasks, witnesses, validator, canonical reference as v21). Comparison:
   v21 Qwen pilot20 frozen result. Same metrics and amendment-1 decision rule (concept arm must beat toolinput
   AND plain AND placebo+input on paired task detection with no more false alarms).
2. Oracle check: v27 codex×{original,strict} cells rerun without tools on pilot20 and diag16 (same pools/prompts),
   to separate model ability from code execution.
One live smoke (pilot20 task 90: shared + 2 arms) ran in scratch before registration; not reported.
Descriptive only (n=20, K=1); HumanEval memorization caveat applies.

## v29_vibepass preregistration (2026-10-18, before any v29 output)

User request: move the Codex full-pipeline test to VibePass (harder LeetCode PUTs, less likely memorized than HumanEval).
Held-out status: VibePass is also the registered held-out of the v11_fair_vp final protocol (Qwen, HELDOUT_RUNBOOK).
That protocol's config is already frozen and is not changed by this run. This v29 run is itself a one-shot held-out run
of the frozen v28 configuration: no prompt, arm, budget or scorer change after seeing any v29 output.

- Pipeline = v28 `flow_run.py` (shared concept/behavior/hypothesis, discovery, 9 LLM arms × 3 calls + witness-only)
  with Codex gpt-5.6-luna reasoning=low, all tools disabled. Only adapter changes: (1) CFG/trace analyse the
  `Solution` method that the public wrapper delegates to (fail-closed on nested defs/nonlocal: CPU check 39/66
  supported); (2) cohort = 66 VibePass PUTs, common witnesses = public `base_input` (190 inputs, none exposes a bug
  by construction); no mined validator in the pipeline.
- Scoring after freeze: reference = VibePass silver (`prompt + canonical_solution`); input validity = the VibePass
  checker contract, evaluator-only; a claimed bug on a contract-invalid input counts as a false alarm; float
  tolerance as in v21 scoring.
- Metrics and decision rule as v21 amendment 1 (concept arm must beat toolinput AND plain AND placebo+input on paired
  task detection with no more false alarms). Descriptive: n=66 PUTs / 24 questions, K=1.

### v29 amendment 1 (2026-10-18, before any v29 freeze or score)
Transport-only fix. The first launch passed the prompt to `codex exec` as one argv string; 50/66 shared stages failed with
`OSError E2BIG (Argument list too long)` for long VibePass prompts; 16 cases completed all arms; nothing was scored.
`codex_client` now sends the prompt on stdin (`codex exec ... -`), verified with a 200 KB probe. Attempt archived as
`flowrun/codex/vibepass_attempt1_argmax/`; its transport cache is copied (identical requests reuse received completions).
Nothing else changes.

## v31_faulttemplate preregistration (2026-10-19, before any v31 model output)

Plan: `trickcatcher_linefacts/PLAN_FAULT_TEMPLATES.md`. User request: explicit fault-site/fault-type ranking (a) and
per-fault-type input templates (b) instead of implicit LLM reasoning; compare with plain only (cost); model
`qwen/qwen3.5-35b-a3b` via OpenRouter, sampling temperature 0.6 / top_p 0.95 (Qwen thinking-mode recommendation),
`response_format=json_object`, max_tokens 8192, seed per slot, same for both arms.

- Cohorts: VibePass 66 (primary; already used once in v29 with Codex — this is a new method on a seen benchmark, the
  template registry is task-agnostic and its only reference-based dev check was pilot20); pilot20 (secondary).
- Tool stage (`ft_concepts.py`, `ft_worker.py`, `ft_run.tool_stage`) as in the plan; no LLM, no reference, no spec.
  VibePass tool statistics were inspected before this registration (no reference): 65/66 tasks with site concepts.
- Arms: plain, fault-template (3 calls each, identical loop; fault-template adds `guidance`), template-only and
  witness-only (no LLM). Exhausted transport = arm error, arm continues. Generation freeze, then scoring with the v29
  scorer (HumanEval+ canonical / VibePass silver; VibePass contract evaluator-only; contract-invalid claimed bug =
  false alarm).
- Decision rule: fault-template promising on VibePass iff paired task detection wins > losses vs plain AND false
  alarms ≤ plain. Descriptive: discovery tasks, template-only vs witness-only, pilot20. K=1, n=66: no significance
  claim. No toolinput/placebo control (user choice) → a positive result does not isolate the concept labels.

### v31 amendment 1 (2026-10-19, before any v31 model output; no protocol.json in the registered output tree yet)
User request: MVP run on half the data, keeping the dataset distribution, to save cost. Primary cohort becomes
`vibepass_half`: 33/66 PUTs from `half_split.py` (seed 20261019, seeded hash order, outcome-blind): every question
keeps floor(n/2) PUTs, the remaining PUTs come from odd-sized questions with no PUT yet first. Result: 24/24 questions,
hard 22 / medium 11 (population 45 / 21). Frozen list `vibepass_half.json`. pilot20 is not run in the MVP. Decision
rule unchanged, applied to vibepass_half. Expected cost ≈ 33 × 2 arms × 3 calls = 198 calls (≈ $0.8).

### v31 amendment 2 (2026-10-19, leak fix; no valid output yet, nothing scored)
The first launch showed 500k–700k-token prompts. Cause: the VibePass cohort (inherited from the v29 adapter) used
`humaneval_mbpp_plus.jsonl` `test` as prompt-visible base tests; that field embeds the canonical solution, the contract
and all hidden inputs (evaluator-only). Fix in `flow_run.cohort`: base tests from `humaneval_mbpp.jsonl` `test`
(public example asserts only, ≤ 1 KB), with a guard that refuses evaluator material. Reference/contract unchanged
(evaluator-only). Attempt archived as `faulttemplate/openrouter/vibepass_half_attempt1_leak/` (≈ $0.07 spent, never
scored, cache not reused). The v29_vibepass results are invalid for the same reason (recorded in its report).
Nothing else changes.

### v31 amendment 3 (2026-10-19, after an independent read-only review; before any valid output)
Review findings applied (no output was seen; the leak attempt was never scored):
- Client: openai SDK (`max_retries` 4 with Retry-After for 429/5xx); 400 fails fast; empty content or
  finish_reason ≠ stop is retried up to 3 attempts and cached only on the last (then a model failure, counted per arm
  as `incomplete_calls`); max_tokens 16384; provider pinned (`deepinfra/fp8`, then `parasail/fp8`, no fallbacks,
  `require_parameters`). An arm with an exhausted transport is not recorded and generation is not frozen (resume).
- Tool stage: survivor cap 200 (was 80; truncated late lines); "distinguished" counts only inputs on which the PUT
  returns normally; a public-information domain filter drops template inputs outside the public examples' profile
  (integer lower bound ≥1/≥0, minimum sequence length, string character classes; never the evaluator contract);
  seeds interleaved within each type cap; concept code lines from the comment-masked source; seeds parsed from the
  prompt-visible public asserts; per-source retry if a batch worker dies.
- New free baseline `template-random` (no LLM): 6 seeded-random inputs from the same filtered template pool on which
  the PUT returns normally (tests whether the ranking adds anything over the templates).
- witness-only reuses the common views (no concurrent re-discovery). Leak guard: base calls must equal the public
  inputs and contain no `exec(` / `is_valid_test`; a CPU test checks no canonical/contract line or hidden input is visible.
- protocol.json adds environment (`pip freeze`) and evaluator-file digests; `score` refuses if sources changed.
- Wording: seeds are per arm (`hash(case_id + arm)`), not shared. False-alarm unit for the decision rule = number of
  false-alarm tests (inputs); tasks with a false alarm are reported too. Unique-PUT view reported (duplicate sources,
  e.g. 39/58, counted once); concept/template type match share reported.
- CPU after changes: 39 tests pass; pilot20 dev discrepancy with template-only drops 8 → 4/20 tasks (the domain
  filter removes out-of-profile inputs; accepted to avoid contract-invalid false alarms); vibepass_half tool stage
  (no reference): site concepts 31/33, 195 selected inputs, type match 62/143.
Decision rule otherwise unchanged; cohort vibepass_half, K=1.
