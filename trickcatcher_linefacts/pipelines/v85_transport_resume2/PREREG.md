# V85 second connection recovery — 2026-10-28

Standing user request: run the full113 paired comparison. On the user's status
check, comparison_contextfit_2 had stopped15:27:07UTC on RemoteDisconnected.
GET/models15:50:04UTC confirms the same qwen3.5-27b-awq/context8192 is reachable.
Register this checkpoint continuation before new completions; no target scoring
or method change. No retry loop inside the terminal run.

Preserve43complete pairs,44v11/43retrieval final rows,113prepared tasks and653
successful responses. Task81 retrieval's round2 expected-output request failed
after1.97seconds; remote usage is unknown. Preserve that attempt together with
the earlier task78 timeout, even though task78's subsequent request succeeded.
One new attempt at the currently unresolved task81 request is part of recovery
under the standing full-run instruction. No automatic transport retry loop.

New root: v85_retrievalhybrid/out/humaneval/comparison_contextfit_3. Active ledger
imports653successful attempts, with2historical failed physical attempts retained
separately. Cap active ledger at3501, so cumulative cap remains3503;2848new
attempts remain. Final known usage sums received responses; unknown usage stays2.

Same frozen card-to-v11-fact binding,2rounds,10shared ref programs/task, seeds,
caps and context allocation. This remains the disclosed v85 method, not a clean
removal of fact generation. Target canonical/contracts remain final-grading-only.
Freeze source and parent output inventory, verify imported receipts before launch.
All113tasks remain the denominator; no efficacy conclusion from partial results.
