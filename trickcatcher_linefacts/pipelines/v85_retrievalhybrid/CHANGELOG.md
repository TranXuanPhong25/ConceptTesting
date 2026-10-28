# V85 retrieval-hybrid — 2026-10-28

Status: comparison_live_1 terminal (context overflow),27CPU tests pass. Parent:v11_fair,
57files copied and hash-recorded in PARENT.json. No changes to parent/vendor.
Earlier v77 combines v11 with v31 fault types; this variant instead uses v2 cards.

- Add retrieval_adapter.py: v2 top3/card text, source-span binding to existing
  v11 executable targets, explicit weaker line-reachability fallback and receipts.
- prompts.py labels retrieved mechanisms as unverified hypotheses; baseline
  heading and prompt unchanged. run_v4.py accepts a restricted arm list while
  retaining original arm seed indices, strict selection and caps.
- Fresh common Qwen27B B5 validity/domain preparation and original v11 fact
  computation;10shared spec-only oracle programs per task. No old response reuse.
- comparison.py, comparison_score.py, transport.py and prepare_comparison.py
  provide the paired113/K1 run,3503-attempt cap, frozen inputs/generation,
  checkpoints, final native grading, paired task counts and usage. No paid API.
- Port copied worker dispatch to Mac sandbox-exec; inherited nested validators
  remain inside that sandbox. Sampled process-group RSS replaces unsupported
  Darwin RLIMIT_AS. Original tools are pinned in a separate venv.
- Tests cover binding, unchanged baseline, omitted/weak targets, public projection,
  native shared preprocessing, strict two-arm dispatch and seed identity, oracle
  information boundary, consensus threshold, budget/duplicate control, real
  drawing/classification and denied network access. Parent fairness tests retained.

Limits: two-arm package comparison, not plain/placebo-controlled; K1 rather than
historical K3. Same caps do not guarantee the same realized calls. Reachability
of a bound target is not semantic proof of the retrieved card. No result yet.

Initial live controller97647 exited after GET /models HTTP404 at08:36UTC.
All113pairs unattempted, no unknown completion usage.225frozen source/input files
and57parent files verify unchanged. Preserve the original claim/terminal receipt;
the next user-authorized live attempt needs a fresh output root, same frozen code.

Version-number correction before any completion: remote main already contains
`v84_reka_completion`, discovered during push. This retrieval package is renamed
to v85; algorithm, cohort, seeds and budgets are unchanged. Initial v84-named
source snapshot is preserved in commit7bf6d3c and PREFLIGHT_FREEZE_V84.json;
its zero-completion HTTP404 receipt is retained. The existing dedicated venv
keeps its original temporary path; no environment/tool versions changed.

2026-10-28 09:46UTC: user-authorized live_1 launch PID51658,exact Qwen27B/context8192.
226source/input and57parent hashes verified. First checkpoint6/113prepared tasks,
31received preprocessing responses,0transport errors. No treatment/code changes,
no result claim; automatic paired generation/shared oracle/final grading follows.

2026-10-28 10:38UTC: context preflight stopped task125 retrieval correction,
4964input+4096output>8192.509responses,0unknown usage,113prepared/6paired tasks;
no oracle/grading. Original source/output preserved. Amended continuation lives
in sibling v85_contextfit; its status is comparison_contextfit_1/STATUS.json.
