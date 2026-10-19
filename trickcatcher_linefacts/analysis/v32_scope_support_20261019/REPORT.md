# v32_scope_support — scope fix works; fresh run stops on trigger signature

2026-10-19, user-authorized fresh seen5, requested gpt-5.6-luna/low. Implemented both
accepted fixes in a new best-v7 copy with explicit v25 ports, stdlib AST lexical
validation, provisional candidate admission and cumulative evidence support. No old
model source/output was repaired, re-executed or rescored. Frozen run complete at
Gate B: **A=true, B=false, C=not run**. This is a valid protocol stop, not transport
failure. Full comparison/benchmark/held-out/paid/endpoint calls were not launched.

| Case | Actual normative/behavior/hypothesis review | Calibration | B admission | C |
|---|---|---:|---|---|
| f02 | Sorted multiset required; actual `sorted(set(xs))` loses duplicates. Correct duplicate trigger, nested comprehensions, target3;14 full-pool witnesses. |238/238|pass, observed_supported|blocked|
| f04 | Required count uses >=; actual uses >. Correct equality-boundary trigger,target3;14 full-pool witnesses. |510/510|pass, observed_supported|blocked|
| f06 | Required membership subset with extras allowed; actual set equality. Correct strict-subset fault concept and behavior, but trigger source declares two arguments instead of `trigger(arguments)`. |2028/2028|FAIL, invalid trigger signature|blocked|
| f14 | Correct returned `sorted(xs)` preserves duplicates; reachable unused set does not affect return. Correct consistent verdict, no invented fault. |238/238|pass, consistent (mismatch support NA)|blocked|
| f13 | “Suitable” undefined; normative metadata and hypothesis both unknown. Actual first-element/None behavior described faithfully. No oracle invented. |NA,0 bankrows|pass, unknown (trigger NA)|blocked|

All5 metadata/behavior/hypothesis records valid; all4 obligation code outputs valid.
Triggers2/3 valid, f14/f13 NA. Inputs0/5 called, all5 blocked by global B gate.
f06 rejected raw code is preserved and never executed, wrapped or renamed. Signature
instruction was explicit in the request. Its conceptual expression appears sufficient
on the stated domain, but that does not make it executable under this protocol.
A further material grounding error: f06 explanation says supplied cases lack the
condition, although all6 common examples are discriminators (five empty-required
cases and one nonempty strict subset). No missing-witness claim is justified here.

The lexical fix is exercised by fresh actual f04 and f14 code reusing `x` across
separate comprehensions, and f02 nested comprehension capture. Each passes validation
unchanged. CPU tests also cover sibling/nested scopes, leakage, protected bindings,
RHS/branch availability and guarded worker execution. This verifies removal of the
scope false rejection for these cases, not a universal language implementation claim.

The cumulative support fix is **CPU-tested only in this run**: a fresh authored
exact-condition candidate absent from the full pool is unverified, requests a witness,
and becomes observed_supported; old counterexamples/unknown and invalid proposals
block acceptance. No model candidate promotion, generated discriminator, contrast or
final input abstention was observed because C never ran. f13 metadata/hypothesis
abstention was observed; input abstention remains untested. No package changes or
prompt adaptation after model launch, and no auto-retry or next variant.

Independent fixture scoring of the full original pool:100/100 normative contract
checks known (25 each f02/f04/f06/f14),36 genuine bug flags (14+14+8),0 false contract
flags among64 correct observations,0 missed bugs among36 erroneous observations.
f13 has24 native observations but24 undefined-oracle/unknown-contract rows, so its
false flags/task correctness are NA, not zero-error evidence. Trigger evaluation
covers50/75 bug-case pool rows: f02/f04 known, f06 trigger unavailable on25 rows.
Initial f02/f04 support is bounded observed support, not causal or universal proof;
f06 unverified due invalid artifact; f14/f13 mismatch support NA. Final support after
input generation is NA for all5. No calibrated-contract ambiguity in the finite bank;
undefined “suitable” remains explicit. Calibration3014 logical probes, never a
reference-free semantic proof or proof beyond the authored domain/sample.

Raw generated-input yield0 calls/0 slots; accepted inputs0; acceptance rate NA (0/0),
not evidence of failed or successful generation. Novel inputs/tasks outside ENTIRE
frozen24+base pool are0 observed because no generation ran. Witness-only already
covers all3 bug tasks, so task gain would be ceiling-limited even if C succeeded.
Verified/text/toolinput contexts retain identical6 common rows and raw provenance,
but **no actual comparison arms ran**. No claim of better model-authored assertions:
this protocol generates inputs only and any future expected values come from the
common post-freeze fixture oracle.

Actual task costs:22 CLI invocations,22 received responses,22 distinct fresh threads,
0 unknown usage,163666 input /4463 output tokens. Cached109440 and reasoning2605 are
subsets of those totals. Recorded tool/router attempts0. Per-call latency4.329–7.689s,
median5.658s, sum125.756s; wall145.731s. Requested CLI model only; no independent server
identity field. Original message roles flattened under Codex instructions, Qwen
sampling/output caps unenforced. Tool schemas exposed with execution host disabled,
not a schemas-removed tools-free claim. Internal HTTP retries/dollar cost unobserved.
No new canary turn; reused unchanged-adapter/CLI host-denial readiness evidence.

Recorded main workers:248 native launches/248 PUT calls;30 predicate launches/3164
evaluations,0 failed/unresolved. CPU preflight separate:10 native/10 PUT,22 predicate/
2776 evaluations,0 failed/unresolved. CPU authored regression runs separate: initial
45pass/3fail (one incorrect test expectation fixed, two source-drift guards triggered
while development docs changed), then stable-source **48/48 pass**. Each full suite
recorded1774 PUT calls and234 predicate workers/20968 evaluations; targeted test-only
check launched0 workers. Combined task+preflight+both regression ledgers3806 PUT calls,
520 predicate workers/47876 evaluations; these CPU controls are not model evidence.
Temporary test ledgers summarized in cpu_worker_accounting.json; task/preflight ledgers
remain in the owned run root. All known counters are recorded worker calls, not a
claim to observe lower-level execution internals.

Source/prepared/old inventories/run/raw manifests verified. Clean-context plan and
code audits passed; separate independent actual-output semantic and terminal-accounting
reviews are recorded alongside this report. Historical Qwen origin stays Qwen and
previous Luna outputs remain separate. This fresh run source is frozen and stopped;
no active model job or automatic continuation. The remaining blocker is correct
trigger interface emission and evidence-grounded explanation, not this repaired
comprehension scope or demonstrated failure of cumulative support.

Derived analysis correction: results_initial.json preserves first scoring export;
results.json corrects f13 observed-input count24, explicit unknown contract coverage,
and NA oracle task metrics. Raw/model/runtime artifacts and scores were not modified.
See results.json, PREREG.md in the package, CODE_AUDIT.md, SEMANTIC_REVIEW.md,
TERMINAL_AUDIT.md, audit_approval.json and the immutable owned run manifests.

Git whitespace check flags eight inherited trailing/EOF whitespace locations in seven byte-identical v25-port files. They remain unchanged to preserve the frozen source. New analysis/own changes pass whitespace checks; no post-freeze cleanup was performed.
