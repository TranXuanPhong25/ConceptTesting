# v81 terminal run report

Run stopped at 2/28 completed paired tasks when OpenRouter returned **HTTP 401: API key expired**. No more requests were sent after the authentication error. Key must be replaced in the existing local `scripts/openrouter_env.sh` before another authorized run; never paste it into chat.

- Design: 28 fixed HumanEval dev tasks, `concept-hybrid` vs `concept-hybrid-ft`, K=1, DeepSeek V4 Flash through DeepInfra/fp8.
- Calls: 15 physical attempts; 8 responses, 6 upstream shared-pool 429 rejections, and 1 expired-key 401.
- Confirmed bill: **$0.02159790**. Unresolved reservations: **$0.60555264** (six 429 reservations $0.51904512 plus one 401 reservation $0.08650752); these are not confirmed charges. Known plus unresolved exposure is $0.62715054, below the $4.20 cap. Prior v79/v80 reservations are separate.
- Paired prefix: tasks 3 and 10. Both arms detect both tasks under `o0`; reference/full scoring ties on both, with both arms abstaining on task 10. Partial run: **no efficacy verdict**.
- Source identity, PREPARED, endpoint metadata, prepared-input hashes and 69-entry generation freeze verify. No active runner or watcher remains. `o0`: both arms detect both tasks; reference/full: both arms detect task 3 and abstain on task 10. Each comparison is 0 wins, 0 losses, 2 ties; the partial-run decision rule is null.

See [final audit](FINAL_AUDIT.json), [live run record](CURRENT_RUN.json), and [full score details](../../pipelines/v81_deepinfra_quarter/out/deepinfra_quarter/humaneval/paired_subset/score.json).

## Continuation after replacing the expired API key

The replacement key passed authentication. The continuation reused cached tasks3,10
and the already completed task15 baseline, then retried the exact task15 combined
round1 slot that had received the old401. That slot succeeded. The next logical
request had one shared-pool429 then succeeded. A later DeepInfra generation streamed
for about15minutes but ended cancelled without a final answer. Read-only usage lookup
confirmed bill $0.00668988; the maximum reservation for that request is reconciled
against this receipt. No answer retry was sent. The partial paired prefix extends
through task15; task19 is incomplete and blocks the leading-pair prefix.

Across both roots, confirmed bill is **$0.03107886**. Unresolved reservations are
**$0.69206016**; combined known plus reserved exposure is **$0.72313902**, below
$4.20. Both roots keep their own immutable protocol, attempts, outputs and freezes.
See [continuation reconciliation](RESUME_RECONCILIATION.json) and
[continuation scores](../../pipelines/v81_deepinfra_quarter/out/deepinfra_quarter_resume2_20261027/humaneval/paired_subset/score.json).
The three-task subset still ties 3/3 under o0/ref/full, with zero false positives;
this partial run has no efficacy verdict. No additional retry or larger run follows.
