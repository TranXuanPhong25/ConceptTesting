# v55: spec interpretation before a definitional oracle

Registered 2026-10-24, before new writer calls, executions or outcomes. Dev only;
VibePass held-out is excluded. Prior art: v49 defn improves program yield but not
paired correctness; v53 validity taxonomy is null, input small-scope loses 18–24.

## Design and fixed budget

33 vibepass_half PUTs, 24 statement clusters; no task exclusion for poor results.
Codex gpt-6.1-sol, medium reasoning, fresh isolated `codex exec` calls. Three
oracle arms, k=3: original v49 defn; interpretation (list ambiguities, choose an
interpretation consistent with all public examples, explicit INTERPRETATION
comment, then defn); placebo (equally requested 80–120 word comment on code
formatting, then defn). No deliberate incorrect interpretation diversity.
Each oracle requests <=1024 output tokens; CLI has no verified hard token cap,
so this is equal requested budget and equal calls, not guaranteed equal usage.
Record actual usage. All arms receive identical spec/signature/public tests.
Batch at most eight different problems per call; samples of a problem always
come from separate calls. No tools or repository visibility in writer calls.
Log prompt hashes, transcript, exit status, answer and tool-event audit.
Never reuse a Sonnet answer in compared arms. Generate one new Codex Stage2
plain input generator (100–300 inputs) and one new Codex Stage1 open validity
checker per cluster, shared across oracle arms. Union these inputs with the
existing v49 universe; report plain-only and universe-only secondarily.

## Execution and outcomes

Reuse v53 smallscope machinery in a new output root, v49 primary quorum, k=3,
public-test program filtering, resource-tolerant primary and strict sensitivity,
cap20 deterministic assertion order. No change to old source/caches. Checkers
failing any public input are dropped as in v53; report drops and parse failures.
Missing/malformed answers make the run incomplete; no outcome-directed repair.
All three arms run exactly the same input union/filter. Confirmed tasks,
confirmed tests, precision, FA invalid vs valid wrong-value, and paired task
wins/losses are primary descriptive outcomes. Common-mode: valid exposing inputs
with >=2 finishing surviving programs all agreeing on the same incorrect value;
report separately unanimity with PUT (miss) and away from PUT (FA), plus task
and distinct-problem counts. Report abstentions and reach.

Promising only if interpretation beats BOTH controls by >=2 confirmed tasks,
on >=2 distinct problems, has no more FA, precision >=.95, and fewer distinct
problems with common-mode wrong values than BOTH controls. Otherwise no-go.
No larger run or extra sample to rescue a borderline/negative result. Any
semantic audit is descriptive; no post-outcome treatment changes.

## Gates and continuation

Independent Codex read-only review before computing outcomes; apply must-fixes
as append-only amendments before seeing outputs. Quota from latest timestamped
rate_limits.primary in ~/.codex/sessions before each batch: remaining <15%
means checkpoint, commit and stop, report reset time. Transport failure stops
the batch; no silent fallback or unknown-call retry. Reviewer and writers must
be Codex, not Sonnet. Task B receives its own folder/PREREG after A; choose
interpretation only if the above rule passes. Fresh cohort size/mining and
freeze rules must precede its outcomes. Task C summarizes terminal results
and distinguishes incomplete/blocked work from negative scientific findings.

## Amendment 1 — independent Codex review, 2026-10-24

Written before any experiment writer answer or outcome. Reviewer
`/root/v55_review` independently inspected PREREG and source read-only.
Applied must-fixes: reserve immutable unresolved attempt before subprocess;
stop without retry on timeout/interruption/launch failure; reject tool items
at started/updated/completed events; extract only sanitized quota timestamp,
remaining percent and reset time from isolated sessions before deleting them,
and use the newest host/isolated observation. Missing writer quota requires a
newer host observation before the next batch, including after restart.
Review gate now pins PREREG and runner hashes. Report explicit nonfinishing
and exposing-input abstention counts. Production isolation adds a separate
PID namespace to block host `/proc/<pid>/root` access. Synthetic lifecycle
checks do not execute PUTs, model programs or hidden tests. No scientific arm,
budget, input pool, threshold or cohort changed. Transport-only preflight
failed with workspace routing discovery failed, zero model answers. This
is a transport blocker and cannot be reported as a negative concept result.

## Amendment 2 — final syntax/execution gate, 2026-10-24

Written before any experiment writer output or outcome. Independent re-review
identified ambiguity in malformed-answer handling. Every answer must contain
syntax-valid Python with its requested module-level entrypoint (or parseable
open checks); otherwise the run is incomplete, no repair or scoring. A plain
generator runtime failure/timeout also makes the run incomplete. A normally
returning generator yielding few/zero accepted literals remains a zero-yield
failure, with drop counts as in v53. Syntax-valid oracle programs that fail
public tests retain the registered rejection/abstention treatment. No call is
repeated and no arm budget changes. Manifest additionally records required
entrypoints and is copied into this experiment folder for durable provenance.
