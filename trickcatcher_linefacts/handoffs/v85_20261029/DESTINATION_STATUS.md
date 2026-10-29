# Linux destination continuation

Started 2026-10-28 about 17:43 UTC (2026-10-29 Vietnam), on the user's explicit
continuation request. Detached controller PID: 22898. No source changes.

- Python 3.11.14; all four pinned tool versions installed from requirements.txt.
- Three resume unit tests pass.
- Archive/source/checkpoint/receipt checks pass: 113 complete generation pairs,
  936 received completions, three historical unknown attempts, 36 saved references.
- Linux native shared-reference consensus and network-isolation checks pass.
- Endpoint preflight passes for the required model/context.
- First two new reference slots received by 17:44:43 UTC.

The unchanged driver generates only the 1,094 missing references, then freezes
and grades both arms. This is an ongoing continuation, with no final score yet.
The three historical unknown attempts remain in cumulative accounting.

Inspect `runner.log` and the work-directory paths in README.md for live progress.
Require `HANDOFF_COMPLETE.json` before declaring the run complete. Do not launch
a second controller or automatically retry unresolved attempts. The `work/`
directory is local and ignored by Git; preserve it when moving machines.

Linux execution replaces the original Mac native sandbox, with both Linux
preflight checks passing. Report that OS difference with the final evaluation.
