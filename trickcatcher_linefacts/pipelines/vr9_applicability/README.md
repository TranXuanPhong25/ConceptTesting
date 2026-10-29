# vr9: applicability and valid-input retention

Copy of vr8 with two repairs: bounded static refutation of an equal literal
character-class hypothesis, and selection that reserves a slot for novel valid
non-hits rather than dropping all inputs outside a suspected defect predicate.
False observations alone do not refute a hypothesis. Other binding forms remain
unknown. Refutation is local to the registered single-character mismatch, not
whole-function correctness or a verified public requirement.

This diagnostic replays vr8's same six development tasks and exact strategy
responses/candidate pools. It reclassifies inputs using native workers; canonical
and contracts are final-only labels. Four arms: strict, retain, applicable, generic.
See PREREG.md. This does not test a fresh strategy writer or full113 efficacy.

Use Python with v4_runtime.py's pinned dependencies (current interpreter:
`/tmp/pytoy-v84-venv/bin/python`). Source `scripts/research_env.sh` silently and a
private environment file with `CT_RETRIEVAL_BASE_URL`. Do not store endpoints here.

```sh
python -m trickcatcher_linefacts.pipelines.vr9_applicability.diagnostic check
python -m trickcatcher_linefacts.pipelines.vr9_applicability.diagnostic run
```

Run detached; status is `out/humaneval/diagnostic/STATUS.json`. Never duplicate a
controller or resume a failed/unresolved completion automatically. An empty-ledger
preflight stop can be retried when the endpoint returns. Strict/generic and every
strategy request must exactly match saved receipts; only missing repaired-arm
expected-output requests may call Qwen27B, up to12new completions. No fallback.

Source/inputs are frozen in FREEZE.json; PARENT.json preserves original vr8 files.
`assets/REPLAY.json` holds inherited physical receipts, not new calls. RESULTS.json
separates newly incurred tokens, reused R1/ref usage, and reused round2 receipts.
Logical round2 calls include replay and must not be mistaken for new API cost.
Shared preparation costs remain outside these inherited subtotals.

Mechanism endpoints include refuted-target routing, novel valid selected inputs,
selected bug-exposing calls (canonical labels after freeze), missing expected
values and final semantic observations. Unknown does not mean covered. Task
scores remain at risk of the known round1 ceiling. Selection can still miss useful
inputs because the unchanged budget retains at most four; this is not exhaustive
pool preservation. No automatic vr10/fresh-writer/full113 expansion.

## Current readiness

**Completed continuation,2026-10-29, supersedes readiness below:** all6tasks/4arms
complete. Ref6/6andFA0allarms (already R1ceiling); retain/applicable keep24valid
newinputs vs strict19, but selected exposingcalls1vs2and no task51exposure.
5newcompletions/3,742tokens,0failure/unknown. No active controller or automatic
expansion. [Result report](continuation_check_20261029/RESULT_REPORT.md),
[independent audit](continuation_check_20261029/FINAL_AUDIT.md).

Historical readiness:

48CPU checks pass;12control arms exactly replay vr8 assertions/calls/selected inputs.
CPU preview:task51strict0→retain4/applicable4selected valid inputs; totals19→24
(generic23). This is not final bug detection. Endpoint404stopped controller64941
before any new completion;0newtokens. [Evidence and limits](readiness/REPORT.md).
