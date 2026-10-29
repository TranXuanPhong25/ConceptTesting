# Resume2: preserve the newer Linux checkpoint, execute on Mac

Registered 2026-10-29 before new inference. User requests running again and
explicitly confirms Mac execution with Linux stopped. SSH confirms Linux PID22898
exited:174/1130refs saved,1074received,2failed attempts (503unknown,404known).
The original archive/source/receipt prefix hashes pass on Linux.

Mac PID44302 was briefly launched before fetching the Linux continuation notice.
It is stopped after blocking reservations/draining all responses:13new successful
completions,0unresolved. All13request bodies match already received Linux slots.
Keep Linux responses as authoritative without comparing outputs for selection.
Retain those13Mac physical attempts and their known token usage in HISTORY.json.
No generation/scoring change; no output-based treatment or checkpoint selection.

Import113paired generations and174shared ref slots. Generate only956missing refs
with the same original Qwen27B transport, prompts, seeds, two workers,900s timeout
and context fitting. Explicit current resume authorizes one new attempt for each
of the two failed Linux slots; preserve failed records in history. No automatic
retry loop, paid fallback or model switch. Canonical/contracts final-grading-only.

Accounting before launch:1074active received+18historical physical attempts=1092.
History consists of3original unknowns,1Linux503unknown,1Linux404known and13received
Mac duplicates. Unknown usage=4; duplicate known tokens must be added to totals.
Active cap3485+18historical=original3503. With956new successes total=2048attempts.
All earlier checkpoint roots stay unchanged. The new snapshot excludes failed
requests from the active cache only; their full request/response records remain
hash-frozen in HISTORY.json. A future unresolved failure stops; never reset it.

Only driver changes: root relocation and accounting for mixed historical failed
and duplicate successful attempts. Original source bytes stay hash-verified.
Three focused CPU tests and native oracle/network checks must pass before launch.
