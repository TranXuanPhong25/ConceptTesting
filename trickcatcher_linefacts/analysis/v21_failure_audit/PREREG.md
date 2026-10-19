# Post-hoc v21 mechanism audit — 2026-10-19

Scope: existing frozen v21_flowtools diag16/pilot20 artifacts only. This is a retrospective diagnostic, not a preregistered efficacy experiment. The published arm outcomes, a preliminary tool-count scan and several raw hypotheses have already been read. No model/native/reference execution, output repair or new arm selection.

Before implementing the diagnostic aggregation, pin these analyses:

1. Verify every generation_frozen.json file hash; separately hash score/protocol/reference files read by this audit. Preserve all source/output files.
2. Count all agent actions by tool, explicit hypothesis linkage, repeated identical queries and round-to-round repetition; summarize non-agent tool usage separately.
3. Count all shared mismatch hypotheses, missing/unmapped source lines, and their static source mapping. Report the actual contract: single concept, line IDs, uncompiled prose triggers, frozen hypotheses; do not call schema validity semantic truth.
4. From saved score rows report discrepancies versus confirmed assertions and false alarms. Audit cached reference results only if needed; never execute a new reference or PUT. Do not infer lack of path activation from lack of bug detection.
5. Inspect the actual prompt/call/code contracts for feedback omission, observation requests and structured hypothesis revision. Report mechanical implementation limits separately from model errors.
6. Source/spec review of illustrative tasks 0,82,90,108,116,131,143,151, selected after raw inspection, is explicitly post-hoc and nonrepresentative. Materialized source evidence must match frozen worker source records; semantic judgments remain evidence-backed case observations, not an aggregate accuracy score.

Deliver reproducible script + JSON counts + report. No new pipeline/model run or benchmark promotion. Any follow-up treatment needs a fresh copy of the best pipeline and pre-output protocol.
