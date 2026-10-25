# v68_symbolicgen

2026-10-25 — copy of v66_symbolicpath (PARENT_V68.json). v57 four-arm ngrok protocol with v66 CrossHair evidence.

- `deep_run.prepare` uses `crosshair_construct.construct` (per-hypothesis budget, full catalogue, harness errors kept).
- `ngrok_run`: `cpu_stage` (writer slot reused from v57 generation_v2, identity-checked) + `prepare-cpu` offline command;
  shared spec-validity call filters shown witnesses (fail closed); compact evidence shows put/alternative outputs; config `symbolicpath`;
  protocol pins scorer hashes (`analysis/v68_symbolicgen/score_v68.py`).
- `value_graph.show` for prompt display. PREREG_V68 frozen before generation.

# v66_symbolicpath

2026-10-25 — copy of v57_pathfault (hashes in PARENT_V65.json); folder first created by Codex as v64_symbolicpath, renamed because v64 = Haiku plain-oracle.

- Replaces v57's own Z3 interpreter with unchanged pinned CrossHair 0.0.112 / Z3 5.3.1.0 (`crosshair_construct.py`), same reach + local-difference + output-difference objective.
- `path_instrument.py` (exact-site paired instrumentation, pre-state snapshot with shared memo, Store-subscript index sites), `path_domain.py` (public-type search domain), `value_graph.py` (alias-preserving codec), `native_replay.py` (isolated CPython replay, instrumented + plain, twice).
- `hypotheses.catalog` skips annotation subscripts; `patch_tree` keeps Store ctx. Other v57 files unchanged.
- 12 regression tests (`test_symbolicpath.py`). PREREG_V66 frozen before real-case outcomes; `diagnostic_v65.py` runs it.

# v57_pathfault

2026-10-24 — CPU engineering complete and independently reviewed; not promoted.

- Isolated copy of best v7, source hashes in PARENT_V57.json.
- Ported v31 ft_concepts unchanged as legacy_templates.py for fixed-transform controls.
- Implemented `hypotheses.py`, `symbolic.py`, `construction.py`, `replay_worker.py`, `deep_run.py`, `public_adapter.py`: source-bound hypotheses, expanded executable facets, bounded Z3 reach/infection/propagation construction, isolated concrete replay, public-data adapter and equal-evidence prompt export.
- Earlier v31/v34 results and source, all vendor code and other sessions' work preserved.
- 34 authored regression tests pass; independently reproduced by reviewer. Review defects and prospective fixes in REVIEW.md / PREREG_V57 amendments1–2. No model calls or benchmark efficacy result.
- Runnable authored joint-multiplicity example in `examples/`: from seed `([1,2],5)`, solver constructs `([0,0,0],1)`, jointly satisfying guard/length/duplicate conditions, and concrete replay verifies outputs1 vs3. This is an authored engineering example, not a benchmark success rate.
- Repeating preparation with the same manifest reuses the immutable artifact; no second execution. Z3/Python/config/source/proposals pinned. Dependencies in requirements-pathfault.txt.
- Local tree is VERSION_TREE.md; shared private diagram publication is outside this environment's tool access.
- Follow-up user request: ngrok only, no OpenRouter. Added bounded serial transport/runner, exact context-token preflight, persisted attempts/atomic caches, public-only six-case preparation, and normalized simple-method wrapper integration.49tests pass independently; see REVIEW.md and PREREG Amendment3. No live model calls: user restarting notebook after saved endpoint404.
