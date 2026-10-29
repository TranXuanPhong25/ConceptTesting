# V85 paired comparison complete — 2026-10-29

All113paired generation tasks,1130shared reference programs and113scored tasks
are complete. HANDOFF_COMPLETE.json exists; MacPID46002 exited, no pending model
request and no new transport failure in this continuation.

| Oracle | v11 confirmed tasks | Retrieval confirmed tasks | v11 false-alarm tasks | Retrieval false-alarm tasks | Retrieval-only / v11-only | Paired sign-test p |
|---|---:|---:|---:|---:|---:|---:|
| ref (primary) | 77/113 | 78/113 | 13 | 10 | 10 / 9 | 1.0 |
| o0 (secondary) | 61/113 | 73/113 | 57 | 51 | 17 / 5 | 0.01690 |

The primary outcome is nearly tied: one additional detected task and fewer
false-alarm tasks for retrieval, without evidence of a reliable detection gain.
The secondary direct-expected-output oracle favors retrieval, but it does not
replace the preregistered primary result. Both have substantial secondary false
alarms. A task can have both a confirmed bug and a false alarm; these columns
are not disjoint classes.

Primary assertion-level precision is234/263=88.97% for v11 and265/292=90.75%
for retrieval; these are assertion counts, distinct from the task-level table.
Round1 ref finds72vs73tasks; the final two-round hybrid finds77vs78.
Input-only D_I_samples is84vs85, also a near tie at task level.

## Integrity and accounting

`AUDIT.json` verifies original source hashes, imported checkpoint hashes,
generation freeze, all1130saved oracle request identities, receipt ledger,
paired win/loss sets and cumulative token arithmetic. `artifacts.tar.gz` saves
all final JSON/JSONL/Python artifacts relative to the run root; its manifest and
SHA256 are in AUDIT.json. The frozen source is in the parent checkpoint archive.
No new model call, target execution or full rescoring was performed for this audit.

2030active received completions+18historical physical attempts=2048attempts.
The18historical records include4unknown-usage failures,1known404failure and13
successful duplicate Mac calls. Known cumulative usage is1,118,505tokens
(772,829prompt+345,676completion), including duplicate tokens; unknown usage4
is additional. RESULTS.json is authoritative for cumulative usage: the original
STATUS/COMPLETE marker usage excludes duplicate tokens, although its attempt and
unknown counts were updated. Original runtime files are preserved, not rewritten.

## Interpretation limits

This is one development113/K1 run with Qwen3.5-27B-AWQ. Execution moved
Mac→Linux→Mac; retries and duplicate physical calls are documented in PREREG.md.
The retrieval treatment still uses v11 fuzz/trace facts for executable binding.
This does not test the requested future clean removal of that dependency, or
establish held-out generalization. No automatic new experiment or retry follows.

The saved secondary `confirmed_tasks` count73 and `D_IO_samples` count72 have
different definitions: the former uses a valid, correct expected assertion that
fails PUT, while the latter additionally requires the saved direct PUT/canonical
input-difference predicate (`d_i`). Do not mix these metrics. The one-task
secondary discrepancy has not been independently replayed; primary ref counts
agree under both summaries.

## Subsequent cost and concept-mechanism audit

[2026-10-29 audit](../../../../python_bug_concepts/research/v85_concept_quality_20261029/REPORT.md)
attributes generation268vs154calls and273274vs187568tokens. Shared overhead
reduces the normalized total-token difference to9.24%. Most retrieval gates are
line reachability,which does not measure the card's semantic trigger. No new
inference or change to this completed experiment.
