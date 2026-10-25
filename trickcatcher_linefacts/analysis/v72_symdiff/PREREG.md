# v72 PREREG — CrossHair differential search: PUT vs spec-only plain-implementation programs (CPU gate)

Frozen 2026-10-25 before any search or score outcome. CPU only, $0, no new model call.

## Question
v64 (Haiku plain-implementation oracle, 33 dev tasks) left 10 tasks with **no exposing input in its pool**
(universe pool reach = False: 6, 39, 48, 58, 69, 70, 73, 74, 168, 171). v68 showed the oracle must not see PUT output, and
v66 showed CrossHair can construct inputs in these programs. Can a solver search for inputs where ≥2 of the 3 Haiku
plain-implementation programs (written from the spec only, v64) agree on a value different from the PUT output, restricted to
inputs accepted by the v55h/v64 Haiku open validity checkers, newly confirm bugs on those tasks?

## Mechanism (frozen)
- Public-side export (`export.py`): PUT source/entry, public base inputs, v64 tolerant plainimpl programs, kept open checkers.
  No reference/contract/label.
- `search.py` (pinned CrossHair 0.0.112 / Z3 5.3.1.0, v66 `path_domain` profile from base inputs, ints [-1000, 1000],
  sequences ≤6, nested ≤4): a path is a witness iff every kept checker returns True, PUT returns normally, and ≥2 programs
  return equal values (same type) different from the PUT output. Program exceptions count as no vote.
  Budget per task: 300 s, 2 s/path, ≤5000 iterations, ≤5 distinct witnesses. One run, all 33 tasks, no retries.
- `score.py`: the v64 scoring code path for the `plainimpl` arm unchanged (open-checker acceptance re-run natively, tolerant
  programs re-executed natively, primary quorum vote, `S.truth_for` with official reference), with an extra pool
  `crosshair` and `union_x` = v64 union + crosshair. All new executions under `out/analysis/v72_symdiff`.

## Decision
Primary: plainimpl confirmed tasks from the `crosshair` pool on the 10 unreachable tasks.
- **GO** (write a separate PREREG to integrate as the concept/evidence stage): ≥2 of 10 newly confirmed and crosshair-pool
  precision ≥ .90.
- **STOP** otherwise. No budget or cohort increase after outcomes.
Reported: per-task witnesses, path outcome counts, precision/FA of crosshair tests, union_x vs v64 union on all 33 tasks.

## Caveats
Haiku programs are wrong on 69/70 (heuristic minDifference, v64 FA); case 58 had 0 witnesses in v66/v68. The "concept"
(divergence path condition/site) is not evaluated here; this gate only tests whether solver-directed disagreement adds reach.
