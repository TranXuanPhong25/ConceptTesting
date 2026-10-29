# vr10 completed retrieval diagnostic — NO_GO for incremental dense recall

2026-10-29: all28sources ×5arms retrieved/sealed; all8historically labelled sites
hit by everyarm. Independent blinded review117/132unionbindings covers every
incremental dense top3query and its controls. B−A andD−C each recover0new supported
buggybindings; no downstream integration or parameter tuning follows.
[Report](REPORT.md), [machine results](run01/RESULTS.json),
[unblinded review decision](run01/REVIEW_SUMMARY.json), [final integrity](FINAL_VALIDATION.json).

Historical run instructions below document the completed single-use outputs;
do not rerun prepare or overwrite run01. Source/label/model freezes remain intact.

Run from repository root with the existing V7 Python environment. Preparation
hashes files and selects from saved predictions; it does not load an encoder.

```bash
.venv/bin/python python_bug_concepts/research/vr10_retrieval_diagnostic_20261029/diagnostic.py prepare
```

Use the actual dedicated V7 interpreter if it differs from `.venv/bin/python`.
Root obtains independent read-only review, applies must-fixes as a PREREG amendment,
and creates REVIEW_APPROVAL.json as specified in PREREG.md. Then:

```bash
<v7-python> python_bug_concepts/research/vr10_retrieval_diagnostic_20261029/diagnostic.py verify
<v7-python> python_bug_concepts/research/vr10_retrieval_diagnostic_20261029/diagnostic.py retrieve --out python_bug_concepts/research/vr10_retrieval_diagnostic_20261029/run01
<v7-python> python_bug_concepts/research/vr10_retrieval_diagnostic_20261029/diagnostic.py score --out python_bug_concepts/research/vr10_retrieval_diagnostic_20261029/run01
```

Worker entrypoint is internal: code strings via stdin only. It never executes
target code. Retrieval stores all arms and seals them before the separate scorer
reads frozen gold. Keep REVIEW_KEY.json hidden from the independent semantic
reviewer until their judgments are frozen. SEMANTIC_REVIEW.json retains all132
union bindings; the registered incremental contrast review covers117from23query
unions, with15unchanged bindings outside the reviewed sample. It includes real-task
canonical queries and the exploratory engineering fixtures. A machine score cannot substitute for causal applicability
review, and no downstream integration is justified until the P4 gate is assessed.

Read-only engineering checks: compile the harness or `--help`; do not run the worker
before review. Output directories are single-use and inherited V7 results stay intact.
