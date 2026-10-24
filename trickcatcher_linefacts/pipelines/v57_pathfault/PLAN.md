# v57: explicit fault hypotheses and path-aware construction

2026-10-24. User explicitly requested deeper implementation and expanded fault families.
This authorizes engineering this version; previous v35/G1 STOPs remain historical, not a reason to label a new run a continuation of v31.

Parent: isolated copy of best v7. The unchanged v31 template module is ported as `legacy_templates.py` for controls. No paper reimplementation, vendor edit, model request or benchmark outcome is part of this engineering phase.

## Contracts

1. **Hypothesis extraction.** AST expression sites produce explicit candidate alternatives and reusable facets. A candidate is not a correct repair. Keep the five old families; add context facets LOOP_CARDINALITY, INDEX_SELECTION, STATE_ACCUMULATION, ORDER_TIE, MULTIPLICITY. Multiple facets per site are allowed. Unsupported effects (aliasing/mutation, external calls, complex containers) must be surfaced, not mislabeled as supported families.
2. **Semantic input interface.** Export a spec/code/public-example-only request for an external writer. Import explicit hypotheses (exact source expression, replacement, rationale, spec quote). Validate source binding and quotes; quote presence is not proof of normative interpretation. Imported claims retain `unverified` status. No private oracle or hidden tests enter construction.
3. **Executable templates.** A template is an AST alternative plus a parameterized construction objective, not a list of concrete edits. Jointly solve execution paths of PUT and alternative for distinct outputs, with one shared symbolic input. Bounded integer/boolean/scalar-string and integer/boolean/string-element sequence support is explicit. Actual implementation coverage must be documented precisely; unsupported syntax returns unsupported, not UNSAT.
4. **Conditions.** Record source-site reach, path predicates, local changed expression and final output disagreement. This measures a behavioral ambiguity, not spec violation. Model-supplied spec constraints are unverified and must never silently hard-filter search. Verified public examples can identify base-distinguished hypotheses, but survivors are not fixes.
5. **Concrete verification.** Solver models are candidates only. Replay original and alternative in isolated, networkless, time/memory-bounded workers with tracing; both must return normally, original target site must execute, and typed outputs must differ. No timeout-as-disagreement. Record replay discrepancies and bounded-search exhaustion.
6. **Ranking and prompts.** Distinguish untested-by-public-examples versus already-distinguished; prefer hypotheses with verified revealing inputs. This is adequacy/uncertainty ranking, not bug probability. Export plain, deep-concept, equal-evidence raw, inputs-only/placebo and witness-only controls. Abstract concept arm and raw arm must expose identical site/alternative/input/output evidence. Do not claim concept gain without model comparison.

## Engineering validation before benchmark outcomes

Use authored fixtures to test joint multi-argument reach, assignment substitution, path alternatives, loop cardinality/state effects, index safety, tie and multiplicity constraints, masked local effects, unsupported syntax, infeasible bounded constraints, typed outputs and stale cache protection. Independent read-only code review is required before benchmark scoring. Fixes are appended prospectively below.

## Limits and later evaluation

Bounded solver support is an implementation domain, not full Python correctness. Input types inferred from examples are observations, not normative validity. No example-derived minimum length/sign filter. Unsat refers only to the exact bounded query. Normative oracle remains independent.

First engineering deliverable: runnable CPU preparation/verification and prompt export, with tests and a concrete example report. No paid API run or held-out outcome. A later experiment requires frozen cohort, model, source hashes and shared query/model budgets, original v31 plus raw-evidence controls, independent evaluator and a new preregistration before outcomes. Existing v31/v34 scores stay unchanged.
