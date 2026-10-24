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
