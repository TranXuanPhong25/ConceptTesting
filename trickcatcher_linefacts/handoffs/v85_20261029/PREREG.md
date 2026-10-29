# Portable checkpoint handoff — 2026-10-29 Vietnam

User explicitly asks to stop local execution, commit results and let another
machine run the remainder. Local controller76780 stopped17:19:23UTC28Oct after
blocking new reservations and draining both in-flight responses.936successful
completion receipts,36shared refs,0in-flight/unresolved current requests.
3historical failed physical attempts retain unknown usage:939cumulative attempts.
All113paired generations are complete.1094shared refs remain, then scoring.

The portable snapshot includes the exact frozen generation/scoring/transport
sources, their frozen dependency inputs, original v11 source inventory, generated
artifacts, prepared tasks, receipt ledger and partial shared refs. No endpoint or
credentials are included. SHA256 manifests verify source and checkpoint bytes.

The handoff driver skips generation entirely and skips completed oracle slots.
Use the same spec-only oracle prompts/seeds, modelqwen3.5-27b-awq/context8192,
temperature0.8/top_p0.95/max1024,2workers,900second completion waiting, original
context allocation. Active ledger cap3500 + historical3 =3503cumulative cap.
No automatic retry of failed/unresolved attempts; no paid fallback or model swap.

Only runtime relocation: use the running venv interpreter for native workers
instead of the old absolute Mac interpreter path; preserve config/source bytes.
Mac uses the original sandbox-exec network denial; Linux the original unshare-rn
path. Exact tool versions and native sandbox smoke checks are required before
inference. No source patch to original or vendor code. Cross-platform execution
differences must be reported with the final evaluation.

Canonical/contracts remain grading-only after all1130refs and generation freeze.
Report both o0/ref, paired task results, false alarms, actual known costs and the
3historical unknowns. Reuse does not create an independent replicate. The local
host will not resume inference; run this checkpoint on only one destination host.

## Local resume authorization — 2026-10-29T03:23:48.087513+00:00

User now explicitly asks this agent to run again, superseding the local stop
instruction. Resume the existing portable work directory after offline integrity
and native checks; unchanged model, prompts, seeds, caps and scoring. No fresh
generation, reset or duplicate controller. Original stopped root stays untouched.
