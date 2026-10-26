# v61 completion engineering — 2026-10-24

User explicitly instructed completing the reviewed plan and objected to stopping at partial v60. This successor preserves frozen v60 diagnostic artifacts. Source-only design uses the same six dev cases; no new model or private outcomes have been opened for this version.

Engineering scope: compositional predicate data AST (typed literals/input/local references, length/arithmetic/Boolean/duplicate relations), source-bound semantic writer using stable tool AST IDs, individual proposal validation, bounded joint scalar/string/nested-sequence construction, original native replay/repeatability, equal-evidence prompt controls, final-input realization audit, immutable/resumable lifecycle and independent scoring.

Input search domain: int[-16,16], lowercase string codepoints97..122, outer lengths0..6, nested width2. These are search bounds, not normative validity claims. Unknown element type, unsupported predicate, Z3 unknown, deadline and no witness are reported; no whole-program UNSAT claim. Per case≤3hypotheses/64candidate inputs/256native program executions/120s construction time. Final audit has separately reported≤96native program executions per arm/case and≤8s per final-input/hypothesis verification; it rechecks predicate/site/local-event/repeats and alternative sensitivity, retaining unknown on error/instability. No construction recipe is selected based on private wins.

Review refinements before any model output: hypotheses IDs include full proposed predicates including local-event/source identity; only input+event+site+repeatability-realized witnesses enter any arm. All five arms receive the same known-bug premise. Positive sensitivity is a behavioral certificate, never a private bug/validity label. Probe feedback and construction checkpoints are persisted immutably and hash-verified for resume.

Proposed future five-arm comparison: plain, format-adapted explicit-pattern baseline, concept, equal-evidence raw, inputs-only. Four logical slots/arm; deep/raw/input allocate one common writer+3generation stages; plain/pattern get four useful calls. Physical18slots/case (108for6cases),2transport attempts/slot. Shared writer/tool costs must be reported separately. This differs from old v57's78slots; no actual model run is authorized by a ready code path alone. Independent code/protocol review and source/request freeze must precede launch. Ngrok-only, serial, no external provider fallback.

Tests use authored deterministic transport fixtures to verify orchestration, not simulated paper/model outcomes. Old v57 private scores remain provisional until the external scorer passes review; no changed code or new witness is retroactively assigned to v57.

## Packaging amendment — 2026-10-25, before effectiveness evaluation

Initial pilot folder `pilot6_20261025/generation/` is archived as an instrumentation trial. A late source-only prompt check found duplicate source/spec in the author-baseline context (case66>24kcharacters) and oversized full native trace feedback. Stopped the exact runner; preserved5response records/2chat attempts, including prompt-cap records and an interrupted unknown completion. No labels/effectiveness result is taken from this trial.

Fix: author prompt carries source/spec exactly once while public examples/known-bug premise remain; probe feedback carries only status/output/reason, not full branches/events. All arm limits, cases, sampling and predicates unchanged. A fresh output folder with newly reviewed readiness identity is required. Count archived transport/model usage separately; do not silently reuse trial completions or call them fair comparison results.
