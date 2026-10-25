# v72 results — CrossHair differential search vs Haiku plain-impl programs (CPU gate), 2026-10-25

Artifacts: `out/analysis/v72_symdiff/{search/*.json, score.json}`. One run, PREREG budget, no retries.

**Decision: STOP.** Primary (10 tasks with no exposing input in the v64 universe pool): **0 newly confirmed**.
Witnesses there only on 69/70, where all ≥2-agreeing Haiku programs share the known heuristic error → 10 FA tests.
6, 39, 48, 58, 73, 74, 168 no disagreement within 300 s / 5000 paths; 171 unsupported (search venv lacks `sortedcontainers`).
(168 and 171 were already confirmed by v64's plain-generator pool; the real v64 gap is 8 tasks.)

Secondary:
- crosshair pool alone: 12/33 tasks confirmed with ≤5 inputs per task (55/70 tests confirmed, precision .79; FA 15 =
  69, 70, 87 — tasks where the Haiku programs agree on a wrong value).
- union_x = v64 union = 25/33: the solver adds no task. It finds the same bugs with far fewer inputs (seconds on 3, 96,
  121, 132, 161), including 124 and 131 that the v68 Qwen arms missed — there the spec-program oracle, not the input, was
  the difference.

Reading: on this cohort the remaining misses are not a reach problem that solver search fixes within budget; they are
search-space size (string/geometry tasks 6, 39, 48, 58, 73, 74) or common-mode wrong spec programs (69, 70).
Efficiency (few targeted inputs) is the only positive, and it is not the registered question.
