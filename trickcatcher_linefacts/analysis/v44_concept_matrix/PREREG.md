# v44 (registered as "v42", renumbered) concept taxonomy × tool method matrix: coverage and accuracy per concept kind (CPU, before any LLM)

Written 2026-10-21 before any code output. User diagnosis after v41: what is missing is (1) coverage of the tool's
methods and (2) the accuracy and taxonomy of the concepts given to the LLM. This measures, per concept kind, how often
an accurate concept of that kind would put a bug-revealing input in front of the LLM, and how precise its flagged
inputs are. LLM concept selection is a later, separately registered step.

## Prior art (version tree)
v7 had a taxonomy of code line facts (OUTCOME/STMT/MUTANT/BOUND/REL/SHAPE/NUM), not of spec relations; v15/v26 only
metamorphic/property relations written by the LLM; v31–v35 mutants only; v41 one kind (blind metamorphic minorities,
C2 11/33, lift 0.38). No version measured several kinds side by side for coverage and accuracy.

## Material
vibepass_half (33 PUTs). Shared pool = the v41 pool (Hypothesis samples x and their transforms T(x), cached, same job
content). Tool side uses only the PUT, public examples and the spec text; references/contract only where stated.

## Concept kinds (instances) and tool methods
1. **Input class** (equivalence partition). Instances: generic classes applied to the first 40 pool samples per
   argument — list: singleton, all-equal, sorted ascending, sorted descending, strictly increasing (dedup+sort), many
   duplicates (x[:2] repeated), contains the public/spec lower bound, contains the spec upper bound, longest (2×max
   public length, ≤ 30); str: single repeated char, sorted chars, palindrome, single char; int: lower bound, lower+1.
2. **Boundary from spec constraints**. The tool parses `a <= name(.length|[i]|[i][j]) <= b` (and `<`) lines in the spec
   (`10^k`, `k * 10^m` forms). Instances: length = min / min+1 (truncate samples), all elements = min / max, one element
   = min / max, int argument = min / min+1 / max / max−1. Lengths capped at 30.
3. **Metamorphic relation** (v41 transforms). Instance = (transform, predicate ∈ {equal, non-decreasing,
   non-increasing}); the *accurate* concept is a predicate the reference satisfies on 100% of ≥ 10 valid pairs (the
   reference stands in for a correct LLM). Flagged = pairs (both inputs valid) where the PUT violates it.
4. **Output property**. Templates on (input, output): out ≥ 0; out ≤ len(arg); out ≤ sum(arg); out ∈ arg; out ≤ max(arg);
   out ≥ min(arg); len(out) = len(arg); out sorted; set(out) ⊆ set(arg). Accurate = reference satisfies it on 100% of
   ≥ 20 valid pool inputs. Flagged = valid inputs where the PUT violates it.
5. **Code coverage** (coverage.py branch arcs, library). Instance = an arc of the PUT not covered by the public inputs.
   Flagged = pool samples x that cover it.
6. **Mutation** (v31 surviving mutants, first 50). Instance = a survivor. Flagged = pool samples x where it differs
   from the PUT (timeouts excluded).
Each kind shows at most K = 32 flagged inputs of one instance (first in a fixed order).

## Measures (references only here; exposing = contract-valid and PUT ≠ reference; batch AND official re-check as v41)
Per kind: **ideal coverage** = tasks where the best instance (chosen with the reference = an accurate concept) has an
exposing input among its ≤ 32 shown; **precision** = exposing share among the shown inputs of the best instance (mean
over tasks with that kind applicable); **any-instance precision** = exposing share among all flagged inputs of the kind
(no reference choice); applicability = tasks with ≥ 1 instance. **Union ideal coverage** over the 6 kinds.
Baseline: expected coverage of k random pool inputs with k = the union's total shown inputs per task (hypergeometric).

## Go / no-go for an LLM concept-selection step
GO iff union ideal coverage ≥ 22/33 (the raw pool reach, v41 C1) AND union ideal coverage ≥ expected random coverage
+ 3. Per-kind rows decide which kinds enter the taxonomy given to the LLM (kinds with ideal coverage ≥ 5 and precision
≥ 0.5). If no-go, the taxonomy/tool coverage is insufficient and must be extended before any LLM run.

## Amendment 1 (2026-10-21, after an independent read-only review, before any reference/exposure was computed)
Renumbered v44 (v42 and v43 were taken by parallel work). Prior art added: **v42_mutoracle** (surviving mutants on the
v41 pool as oracle questions: D2 15/33 vs random 13.3, lift 0.62, no-go) and v43_mutjudge/v43_concept_identify. Kind 6
reuses the v42_mutoracle mutant outcomes on the v41 pool read-only (all survivors, chunked, `max_timeouts` 2) instead of
re-running 50 mutants.
- Frozen material: the v41 pool and reference batch are read-only (input hash must equal v41 `inputs_sha256`; nothing
  is re-run in the v41 cache). Kinds 3–6 use the whole pool as universe; kinds 1–2 their own generated inputs.
- Baseline matched to oracle selection: because the best instance is chosen with the reference, a kind is covered iff
  its reach set R (union over instances of their first ≤ 32 flagged inputs) holds an exposing input. Per kind and for
  the union, baseline = hypergeometric chance with k = |R| from the kind's universe (union: pool ∪ generated inputs).
  Also reported: random-instance coverage (mean over instances, no reference choice). Instances with identical flagged
  sets are merged. Applicable = ≥ 1 instance with ≥ 1 flagged input (one definition for all kinds).
- Kinds 3/4 are reported as a separate **oracle-concept** block: their flagged inputs are exposures by construction
  (precision is not informative). Instead their **accuracy** is measured tool-only: candidate relations = predicates /
  templates the PUT itself satisfies on ≥ 75% of valid pairs/inputs (what a tool would mine); accuracy = share of
  candidates the reference satisfies on 100%; false alarms = non-exposing inputs flagged by inaccurate candidates.
- Precision is reported only on C1 tasks (pool or generated inputs expose), as lift over the kind's universe base rate.
  Best instance is selected and credited on the same exposure definition (batch AND official).
- **Gate (unchanged in form): GO iff union ideal coverage ≥ 22/33 AND ≥ matched random + 3.** Taxonomy rule
  (input-side kinds 1, 2, 5, 6): ideal coverage ≥ 5 AND median lift on C1 tasks ≥ 2; kinds 3/4 enter as oracle concepts
  with their measured accuracy.
- Errors are recorded per kind (a failing kind does not void the case). Coverage runs on the whole pool; cov_worker
  checks that the source file is measured and that public inputs produce arcs, else the kind errors. Fixes: palindrome
  of the first ≤ 15 chars, `out in arg` requires matching types, constraint parser also reads `a <= n == x.length <= b`
  and comma lists of `x[i], y[i]`.
- Re-review (before any output): the gate's union is over the **input kinds 1, 2, 5, 6 only** (reach set and matched
  random likewise); the union including oracle kinds 3/4 is reported, not gated. `random_instance` and `lift` use batch
  exposures, `covered` batch AND official (conservative). New official re-checks are added to the v41 content-keyed
  official cache (never overwritten). c1 includes generated inputs.
