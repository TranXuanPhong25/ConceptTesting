# v81 continuation results after API key repair

The replacement key passed authentication and the original expired-key slot (task15 combined round1) returned successfully. The next logical call had one upstream429 and then completed. A later DeepInfra generation streamed for about15 minutes then ended without `DONE`; a read-only OpenRouter usage lookup confirmed it was canceled and billed $0.00668988. That billing receipt resolves the reservation for that call; it does not make the missing model answer usable. No retry was sent for the canceled/incomplete generation.

The complete paired prefix is tasks **3, 10, and 15**. Both arms detect all3 under `o0`; reference/full both detect task3 and15 while both abstain on task10. Each comparison remains 0 wins, 0 losses, 3 ties, FP0; this is a partial run and has no efficacy verdict. Task19's incomplete generation stopped the paired prefix.

Confirmed cumulative bill for original plus continuation: **$0.03107886**. Unresolved reservations still held: **$0.69206016** (six original429s, original401, and the resumed429). Known bill plus unresolved reserves is **$0.72313902**, below $4.20. Prior v79/v80 reserves remain separate.

Both source snapshots and generation freezes verify (original 69 entries, continuation 83). Both run roots remain immutable and separate. No further calls, retries, or scoring judges. [Reconciliation ledger](RESUME_RECONCILIATION.json); [scores](../../pipelines/v81_deepinfra_quarter/out/deepinfra_quarter_resume2_20261027/humaneval/paired_subset/score.json).
