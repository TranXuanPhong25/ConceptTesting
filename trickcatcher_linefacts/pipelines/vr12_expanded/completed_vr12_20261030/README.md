# Completed VR12 raw artifacts

11/11tasks,39physicalcompletions,39,878newtokens,0unknown. Source/review and
generation freezes verify; pipeline sources and frozen results unchanged.

`artifacts.tar.gz` contains the complete saved diagnostic run, relative to
`vr12_expanded/out/humaneval/diagnostic/`, including generation/scored receipts,
completion ledger, original failed-preflight history and final COMPLETE/RESULTS.
No model files, credentials, endpoint values or inherited virtualenv are included.

SHA256: `fbef6bf276427299fc2515330a9178214e8612eb2bef9b6f9557ff639d0c27be`.
Verify the archive before use. Inspect/read entries without executing source.
Use the pinned Python3.11.14 when recomputing expression-based call identities.

Final report: `analysis/vr12_schedule_20261030/FINAL_REPORT.md` under LineFacts.
The original scheduled audit had unpinned-runtime Unicode call-key misses;
RUNTIME_AUDIT_ADDENDUM.md explains why pinned recomputation matches RESULTS.
This archive preserves original RESULTS, not the unpinned audit interpretation.
