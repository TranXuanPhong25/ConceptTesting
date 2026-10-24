# v53 Stage 2: small-scope input concept with a correct oracle (dev run, vibepass_half, 33 tasks / 24 problems)

Written 2026-10-24 (Claude) after Stage 1 RESULTS and before any Stage 2 model call or execution. Codex 5h quota is out;
the user asked Claude to review it ("codex hết quota rồi, m tự review đi"); the self-review is appended below, before any
call. Dev run, no claim; the held-out stays untouched; a claim needs a fresh LiveCodeBench cohort.

## Question
With a correct oracle (v52: Sonnet `defn` is right on every valid input; Stage 1: a Sonnet validity filter removes all
invalid-input FA), what is left is the input side: reach, and abstention when brute force cannot finish on large
exposing inputs (v52 141; DIAGNOSTICS D2: a ≤ 10-size exposing input exists on 21/23 reachable tasks). Does a
**small-scope concept** for input generation — name every input dimension (each parameter's size, element values,
characters, and each relation between parameters), give each a small bound that includes the boundary values the
Constraints allow and values that create ties/duplicates, then enumerate *all* combinations in that scope — confirm
more tasks end-to-end than a plain LLM generator, a type-driven exhaustive tool and random small inputs?

## Prior art (version tree)
v41 (Hypothesis sampling, reach 22/33, no brute force), v44/v47 (concept/tool input menus, ≈ random), v48 `llm_code`
(Qwen TC-style generator; inputs are in the universe), v13/v21 fuzz witness (no brute-force oracle), PLAN_NEXT_v50 R2/R7
(small-scope exhaustion planned, never run). External: AutoCode (ICLR'26) small-data exhaustion with brute force;
small-scope hypothesis (Jackson; Andoni et al. 2003). New here: the concept chooses the scope dimensions from the
statement (including relations), and the oracle can judge what it generates.

## Fixed pipeline (all arms)
input source → validity filter = Stage 1 `open` answers (registered: "Stage 2 uses the better of open/tool"; same
public-input drop rule) → **Sonnet `defn` oracle**, k = 3, primary quorum (≥ 2 and > V/2 agree, ≠ PUT), programs valid
on public inputs (`O.rejection`), 1 s per call → cap 20 in v48 hash order → judged by the hidden reference contract,
reference output and official per-input exposure (v49 `labels_for`).
- Oracle programs: v52 answers for its 6 problems (shared by sibling tasks of the same problem); new answers for the 18
  other problems, prompt = `gen.messages(task_view, 'defn')` (identical across sibling tasks; asserted).

## Arms (input sources; per distinct problem, used for every task of that problem)
- `scope` (concept, Sonnet, k = 1): statement + public tests + signature; "First write a comment block `# DIMENSION:
  <name> | <scope> | <why>` for every input dimension: the size of each parameter, the values of its elements or
  characters, and every relation between parameters stated in the Constraints. Choose small scopes that keep the
  boundary values the Constraints allow and values that create ties, duplicates and equal elements. Then define
  `inputs()` that enumerates **all** valid combinations within these scopes (itertools allowed), between 100 and 300
  distinct inputs; shrink the scopes rather than truncate."
- `plain` (prompt control, Sonnet, k = 1): same context; "Define `inputs()` returning between 100 and 300 distinct small
  valid inputs most likely to reveal a bug in a plausible but incorrect solution."
  Shared: each input is a tuple of the arguments in signature order; only builtins + itertools; deterministic; no I/O.
- `typed` (tool, $0): per parameter from the signature: `int` → integers in the numeric bounds (`constraints_report`)
  intersected with [lo, lo + 5]; `List[int]` → lengths within bounds up to 4, elements from the int domain of that
  parameter (≤ 4 values: lo, lo+1, lo+2, hi-clipped to lo+5); `str` → lengths up to 4 over the characters of the public
  inputs (≤ 3); `List[List[int]]` → up to 3 rows with the row length of the public inputs, elements as `List[int]`.
  Cartesian product, then a seeded sample to the `scope` arm's accepted count per task.
- `random_small` (count control, $0): seeded sample, same count as `scope` accepted per task, from the v41 pool inputs
  of size ≤ 10 (DIAGNOSTICS size) accepted by the filter.
- `universe` (reference input source, report): v49 decisive universe accepted by the filter.
Generator answers run once in the sandbox (20 s); outputs that are not argument tuples of the right arity or do not
round-trip through `repr`/`ast.literal_eval` are dropped (counted); duplicates removed; at most 300 kept in answer order.

## Protocol
Sonnet subagents only (user rule). Batching to save quota: one subagent per (arm or oracle sample index, group of 6
problems); it Reads each listed prompt file and Writes each answer file, nothing else (verified from transcripts; a
violating subagent's answers are regenerated once, else the problem is dropped from every arm). v52 used one call per
answer: stated difference. Problems are independent within a subagent; the three oracle samples of one problem always
come from different subagents; one subagent never writes two arms.
**No verdict while any included answer is missing or unparseable** (an `inputs()` that raises, times out or yields 0
accepted inputs is a valid answer with 0 inputs, not a block).

## Measurement (per arm; 33 tasks)
Primary: **confirmed tasks** (≥ 1 confirmed test, cap 20). Secondary: FA tests, precision, accepted inputs, reach
(∃ accepted input that is contract-valid and officially exposing; official check only on proxy-exposing inputs, in hash
order, until one passes), finishing reach (∃ such input where ≥ 2 oracle programs finish), oracle abstention (reached
but not finishing), per task outcome; union `universe ∪ scope` and `universe ∪ plain` (report). Comment-format audit
of `scope` answers (DIMENSION lines present).

## Decision (dev; promising ⇒ fresh-cohort replication, not a claim)
`scope` is promising iff, against each of `plain`, `typed`, `random_small` separately: confirmed tasks ≥ comparator + 2,
with the `scope`-only tasks spanning ≥ 2 problems, FA tests ≤ comparator + 5, and precision ≥ 0.8; and every
`scope`-only task passes a manual audit (emitted input contract-valid, officially exposing, oracle value = reference).
Otherwise not promising. Report-only: `scope` vs `universe`, the unions, and the 10 tasks with no exposing universe
input (8 R7 + 73, 74). No enlargement of k or of the cohort to rescue a result.

## Self-review and Amendment 1 (2026-10-24, Claude, read-only pass over this file and the v49/v52/v53 code; before any call)
Codex unavailable (quota); the user asked Claude to review. Findings and fixes:
1. **Count matching favoured `scope`** (a task where `scope` yields 0 inputs would give the tools 0 too, copying its
   failures). Fix: `typed` and `random_small` always take **min(300, available accepted)** inputs, independent of
   `scope` (conservative against the concept). Report-only: the same seeded lists cut to `scope`'s count per task.
2. **`typed` cannot be enumerated in full** (87: two lists + int ≈ 7·10^5 combinations). Fix: seeded sample of up to
   20 000 product indices (mixed-radix decoding, no materialization), filter, keep the first 300 accepted in seeded order.
   Domains: int = [lo, min(hi, lo + 5)] from the numeric bounds, default [-2, 3]; elements = [lo, min(hi, lo + 3)];
   lengths / row counts = [lo, min(hi, lo + 3)] (lo ≥ 0), rows of `List[List[int]]` use the most common public row
   length; strings use up to 3 characters seen in the public inputs (default `ab`).
3. **Strict public-input validity can discard a correct brute-force oracle** that only times out on large public
   examples, which is exactly the regime small-scope inputs avoid. Fix (symmetric across arms): **primary** oracle
   validity = resource-tolerant (v49 `resource_only` rejections allowed if ≥ 1 public input finishes and every finished
   one matches); v49 strict validity reported.
4. **The worker truncates outputs at 4000 chars**, so `inputs()` cannot be returned whole. Fix: the generator runs as a
   module with a cached `list(islice(inputs(), 2000))`; entry `__gen__(i)` returns item i (and `__gen__(-1)` the
   length), one sandbox job, 20 s per call.
5. `scope` vs `plain` mixes two factors (dimension listing, exhaustiveness); `scope` vs `typed` isolates the LLM's choice
   of dimensions, `scope` vs `plain` the small-scope framing; both are required for the verdict (already so).
6. Single-parameter answers yielding a bare value instead of a 1-tuple are dropped by the arity rule in both LLM arms;
   drop counts are reported per answer.
7. Residual risks (stated, not fixed): k = 1 generator per problem; sibling tasks share answers (span counts problems);
   contamination (LeetCode); batched subagents differ from v52's one-call protocol.
