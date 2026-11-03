# V11 clean family on the frozen new cohort — 2026-11-01

## Runtime-only continuation after observed collector deadlock

Original run stopped for repair after155case results;145complete and10base rejects.
Both unfinished workers151/156 had zeroCPU progression, single-thread futex wait,
and identical py-spy collector._clear_data stacks. Preserve original run/source.
Runtime correction in RUNTIME_FIX.md was registered before any resumed cohort work:
same pinnedcoverage version but supportedpytracecore; normalfixture arcs/lines
equal, generator-timeout regression passes, timing-boundary variability disclosed.
120sprocess-tree CPU-idle watchdog allows one freshscratch native retry within one
overall deadline. Recurring idle or deadline-after-idle is WorkerStalled infrastructure
error, never an empty method suite. All4439completed result/response hashes imported
unchanged; per-worker CPU/idle telemetry added.14engineering checks pass and final
independent review cleared. Manifest pins imported provenance/runtime policy.
No original kernels/prompts/seeds/cohort/oracle/modelbudget changed; no extra model
calls in migration. Only unfinished151/156 and later native work use this runtime.

User explicitly requests one new arm/stage using V11's actual pipeline, clean code,
run on the existing roughly1.6kPUT cohort, autonomous progress monitoring and fixes.
User says the supplied qwen3.5-27b-awq endpoint becomes available25minutes later;
Earliest metadata/inference launch is defined by schedule.json:
2026-11-01T07:05:32UTC /14:05:32Vietnam. No completion before that deadline.

## Method identity and explicit adaptations

Original v11_fair source stays untouched. Use original B5 prompts and predicate
syntax/verifier, domain/Hypothesis prompts and checker, pinned constant pool,
coverage.py/mutmut facts/ranking/gates/G-prime, spec fallback, hybrid prompts/seeds,
100draws/cap500, two picks per missed hint, retry rules, strict unseen selected calls,
8logical-call/20assertion cap and matched plain/placebo request counts. Low-level
kernels execute unmodified in a pinned dedicated sandbox environment. The new
classes replace orchestration, not the fact taxonomy or ranking algorithm.

Differences from historical V11 are specified rather than hidden:

- User-selected Qwen3.5-27B-AWQ replaces old Qwen2.5-Coder7B; actual model identity
  is recorded, never spoofed to bypass old mining's hard-coded model guard.
- One sampleK1 per PUT for this run, not historical K3. Per-PUT alias=`task_id*10+
  program_id` gives unique caches/seeds; original seed formula otherwise unchanged.
- The existing source cohort has1634programs.169base rejects are logged without
  generation;1465base-pass PUTs are eligible, including shortfall-task programs.
  No programs are regenerated and no new source bugs are injected.
- Generated sources can omit the spec/import scaffolding/type annotations V11 expects.
  Build a method view restoring original docstring, missing annotations and prompt
  helpers/imports, retaining function bodies and actual parameter names. Store raw
  source hash plus view. Gold evaluation runs the ORIGINAL saved program with the
  original HumanEval scaffold, never the view. Validate this bridge before launch.
- LLM assertion/expected-value calls remain in generation to preserve V11 prompt/
  selection behavior. Primary detection uses canonical reference gold, NOT those
  LLM expected values, as requested for the final benchmark. Trusted EvalPlus
  contracts filter inputs; use existing tolerance/root-aware final oracle.
- v11 family contains concept-hybrid plus its matched plain-hybrid/placebo-hybrid,
  original toolinput and witness-only controls. Omit unrelated gen-plain/direct-only
  result rows; concept/plain round1 requests remain as hybrid dependencies.
- Score each PUT's OWN generated suite, not a pooled10-PUT super-suite. Record raw
  yield, own-program detections and calls; compare valid-input budgets separately.
  Task-level matched-valid-input comparisons use the previously tested random
  subset/permutation algorithm; encode input IDs per-owner PUT so a suite cannot
  claim a different PUT's failure. Include failed preparation as zero detection
  in its original base-pass denominator. These are separate from V11's matched
  logical strategy-request control and are labeled explicitly.
  Matching here is task-TOTAL input counts across owner programs, not equal counts
  within every owner PUT; report this allocation limitation. Owner IDs prevent
  cross-program credit. No post-outcome switch to a different matching unit.
  Historical one-call-per-task arms have different request budgets; raw counts
  versus those prior arms are descriptive, not causal concept gain.

## Execution/failures

- Dedicated worker environment pins Hypothesis6.169.0/mutmut3.8.0/coverage7.16.2/
  libcst1.9.0. Original run datasets/reference comparisons keep their prior env.
- No canonical/plus outcomes enter mining/facts/generation. Per-case arm inputs are
  saved before its reference evaluation. No feedback from scoring to later cases.
- Durable checkpoints per case/stage. Content-addressed calls include actual model,
  full messages/temperature/top_p/output cap/seed; streaming transport preserves
  partial/unknown attempts and its persistent total3attempt cap.
- Exact original syntax/selection fallback rules are retained. Unrecoverable
  preparation/runtime errors remain visible zero-evidence cases in full denominator,
  not silently dropped. Source/config changes require a versioned continuation.
- Supervisor waits deadline+independent review/test/source-hash readiness. Monitors
  process/checkpoints each30seconds; retries endpoint/read-only transient failures
  from cache, never resets exhausted completion caps or rewrites scientific choices.
  Active runner uses the reviewed separately-accounted20minute1token keepalive
  during potentially long CPU fact stages; none is started before deadline.
- First validation uses synthetic engineering fixtures and request/selection parity
  against original V11. Independent review before model/native cohort outcomes.
  Then launch full run; no auto run enlargement or model fallback.

## Prelaunch validation / independent review

Ten engineering checks pass. Five generation profiles reproduce original V11
assertions, missed hints, strategy-request/retry counts, strict missing-expected
behavior and caps. Native synthetic facts/draw use actual pinned original kernels.
Additional regressions verify restored view/body/future imports, raw-owner gold
instead of LLM expected value, explicit bridge failure and exact top_p forwarding.
Static compilation/body preservation passes1634/1634views. Original51V11file hashes
match. Independent read-only Codex review cleared launch; no API or native cohort
outcomes were generated during review.

Review fixes move bridge failures into explicit zero-evidence cases, separately
account for received responses missing usage footers, and use reviewed20minute
keepalive during CPU facts. Monitoring progress includes active case/stage; systemd
may restart a lost supervisor, while terminal/user-stop/cap states stay terminal.
