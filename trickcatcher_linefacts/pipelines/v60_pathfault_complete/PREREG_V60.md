# v60 registration — P0A/P1/P2-P3 engineering

Date: 2026-10-24, before any v60 model generation, hidden-reference scoring, or new private outcome.

This version implements the finite first repair package in
`PLAN_PATHFAULT_COMPLETION_20261024.md`: public source capability inventory,
raw-final scorer primitives, typed recipe IR, native candidate construction and
repeatability handling. It is not a model effectiveness experiment.

Frozen P1 scope:

- cases: `61,66,124,58,131,85` from the already frozen public request list;
- backend: native-first for every P1 case; symbolic summaries only if separately
  registered, at most three total;
- recipes/case ≤3; candidates/case ≤64; native executions/case ≤256; wall
  budget/case ≤120s; worker call ≤2s;
- repeat seeds: `20261024`, `20261025`; repeats/program/seed:2;
- unstable observations are `unknown`, never certificates.

P0A may test score parsing with authored fixtures. P0B evaluator attachment and
historical reference labels remain a separately reviewed stage after P1 is frozen.
No source, response, cache, request or result from the frozen v57 generation is
changed by this version.

## Amendment — independent review, before reference-free diagnostic

Fixed exact event binding, alternative/type/closed recipe validation, shared per-case candidate/execution/deadline accounting, per-variant seeded execution, sanitized worker honoring hash seed, explicit unknown sensitivity and scope-safe helper exclusion. Freeze all compiled recipes/config/request/source hashes before the one diagnostic; report all6cases including no_recipe. Keep site-only evidence distinct from local-fault realization. No new private/model run under this amendment. Reviewer approved this limited diagnostic; P0B/P2/P4 remain incomplete.

This amendment documents code changes already completed before native diagnostic execution; no second diagnostic or changed cap follows the observed yield.
