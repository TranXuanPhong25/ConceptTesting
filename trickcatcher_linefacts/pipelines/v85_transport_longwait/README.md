# V85 longer completion wait

The old240-second completion timeout was close to an observed237-second response
for4096tokens. This child changes only completion waiting to900seconds, preserving
model/prompt/token settings and the hybrid algorithm. See [protocol](PREREG.md).

Resume from54complete pairs and694successful receipts.3historical failed physical
attempts retain unknown usage and count toward the same3503cumulative cap.

Live output: `../v85_retrievalhybrid/out/humaneval/comparison_contextfit_4/`.
Check STATUS.json and controller.pid before action. No automatic retries.

16:25:07UTC launch: PID76780.54pairs restored,694received receipts imported and
the first missing completion submitted.9focused checks pass;694request identities
and5833parent output files verified/frozen. Longer waiting is an execution repair,
not proof that the earlier timeout was caused solely by generation latency.
