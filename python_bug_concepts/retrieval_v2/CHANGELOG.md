# Retrieval v2

2026-10-26: user requests HumanEval retrieval coverage of at least half the tasks.
Frozen lexical baseline and the original 132-card corpus; isolated public inputs
for the existing 113 DEV PUTs. Conditional applicability evaluation is registered
in PREREG.md. Structural retrieval implementation and scored results pending.

No original upstream source, existing linefacts pipeline, model endpoint, or
paid service is changed by this variant.

2026-10-26 completed: user clarified that the top-3 concept must describe the
actual bug on 113 PUTs. Added 30 pinned semantic cards separately, authored strict
mechanism labels and replayed native witnesses, then froze ranking for the 40-task
audit. Primary family + first faulty site hit@3 = 74/113; audit = 25/40. Family-only
hit@3 = 88/113. Full metrics, per-task misses and single-author/development-informed
limitations are in RESULTS.md. Public code-search routing now defaults to this
evaluated engine; legacy base.py and the original corpus stay unchanged.
