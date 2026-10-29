# v83 full Reka HumanEval quarter

Terminal status: partial; complete paired prefix 26/28.

Stop reason: AccountingUnknown:missing_done;reserved_charge_retained; known new-run bill $0.68198775; unresolved reserve $0.0642930.

Two arms: concept-hybrid and concept-hybrid-ft; K1; Reka; output cap24k.
Partial outputs are descriptive and receive no efficacy verdict. Prior v81/v82 exposure remains included under cumulative $4.20 cap.

## Offline scoring recovery

Post-freeze CPU scoring was rerun from the saved `eval.jsonl`, cached reference/post responses, and oracle executions. The scorer originally raised `missing_oracle_task:3` because tasks with no parseable generated call are absent from `oracle_b01.execute` output. Inspection confirmed task 3 has zero assertions in both arms; these no-call tasks were represented as empty oracle-call maps for scoring. No model/API call or generation artifact was changed.

For the 26 complete paired tasks, o0 gives 4 wins / 4 losses / 18 ties (FT false positives 9, control 6). Reference and full give 3 / 4 / 19 (FT false positives 2, control 0). These are partial descriptive counts; the preregistered efficacy rule remains unevaluated. Machine-readable scores are in `humaneval/paired_subset/score.json` (`score_o0.json`, `score_ref.json`).

The requested 28-task run did not complete: it stopped at 26/28 after one unknown-accounting attempt. The frozen protocol forbids resending an unknown/incomplete slot and marks this terminal partial as non-resumable. The unresolved reserve remains $0.0642930; known V83 cost is $0.68198775. No further paid calls were made.
