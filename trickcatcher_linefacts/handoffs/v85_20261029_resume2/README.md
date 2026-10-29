# V85 continuation from Linux checkpoint on Mac

**COMPLETE (2026-10-29):** all1130refs and113scored tasks. Controller exited.
See [final report](completed/REPORT.md) and [results](completed/RESULTS.json).
Do not start the initial174-ref archive again; final artifacts are archived in completed/.

This supersedes the original handoff for further execution. User confirmed:
**run on Mac; Linux stopped**. Linux saved174/1130refs before503/404 failures.
The briefly launched Mac copy was drained/stopped;13duplicate successful calls
are kept in historical accounting, while the Linux outputs remain authoritative.

Saved:113paired generations,174shared references,1074unique received receipts.
Remaining:956references,then original paired scoring. History adds18physical
attempts (4unknown usage,1known404failure,13known received duplicates). Global
cap3503 includes every physical attempt across both hosts. No final result yet.

## Run

Only one host/controller at a time. The same setup as the original handoff:

```bash
cd trickcatcher_linefacts/handoffs/v85_20261029_resume2
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s . -p test_resume.py
.venv/bin/python resume.py --check
read -rsp 'Endpoint ending in /v1: ' CT_RETRIEVAL_BASE_URL
export CT_RETRIEVAL_BASE_URL
nohup .venv/bin/python -u resume.py --run > runner.log 2>&1 < /dev/null &
```

Requires exact `qwen3.5-27b-awq` with context8192 and tokenizer route. Never log
or commit the endpoint. Do not launch if the current Mac controller is running.
`work/LOCAL_RESUME.json` records its launch; verify the process and live status.

Output directory:
`work/snapshot/trickcatcher_linefacts/pipelines/v85_retrievalhybrid/out/humaneval/handoff_resume2_20261029/`.
Read STATUS.json for progress and HANDOFF_COMPLETE.json for final completion.
RESULTS.json includes historical attempts, duplicate known tokens and4unknowns.
No automatic retry after a new failed/unresolved attempt; preserve work/ for any
future transfer. The committed archive records the initial174refs,not later work.

Original generation/scoring sources and protocol are unchanged: v11 two rounds,
ten shared spec-only refs, retrieval cards bound to existing fuzz/trace facts.
The Mac/Linux/Mac execution history must be reported; this is one continuation,
not independent replications. Canonical/contracts are used only after ref freeze.
See PREREG.md for the complete accounting and checkpoint-selection rule.
