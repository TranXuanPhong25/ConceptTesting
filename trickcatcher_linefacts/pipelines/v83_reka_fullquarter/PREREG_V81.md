# v81 HumanEval quarter — prospective registration, 2026-10-26

User requests one quarter HumanEval on DeepInfra after selecting exactly combined
versus original concept-hybrid, K1. Floor(113dev/4)=28 public dev tasks: sample
sorted v11dev IDs with random.Random(20261026).sample(...,28), then ascending order.
Exact IDs/source digest in COHORT.json before any generation/output scoring.
No heldout/pilot/design tasks, score-based selection, replacement or enlargement.

Isolated copy of v77, no parent/vendor changes. Only two executed/exported arms:
concept-hybrid original v11 and concept-hybrid-ft combined v7/v31. No hidden plain,
placebo, toolinput or discarded-arm calls. Baseline round1 uses original concept
seed; baseline round2 uses original concept-hybrid seeds. Combined seeds retain
reserved offset. Both independently write round1, classify missed hints, generate
Hypothesis strategies for missed hints, retain only unseen verified hits, then
write expected output from spec. Keep8logicalcalls/20assertions per arm/task.
Same hint count<=3 and frozen v77 alternating v7(nonMUTANT)/v31fault merge. No
witness arguments or PUT/alternative outputs in concept text. No private oracle
in public generation. CPU mining/fault phases only, original v31 module unchanged.
Baseline and combined have same call cap, natural missed-hint counts may differ;
this is a package comparison, not an equal-realized-compute concept-effect claim.

Model deepseek/deepseek-v4-flash-0731, provider only deepinfra/fp8, no fallback,
require_parameters true, enabled reasoning, max_tokens131072 total, temp.6/top_p.95,
text response format, no API seed. Streaming transport saves durable attempt,
wire/SSE/usage/provider/finish receipts. Serial task-major baseline then combined,
K1. Runtime context gate using conservative2UTF8bytes+4096 bound; no truncation.
Per-call timeout1800s avoids v80's360s interruption; no provider swap.

Budget$4.20 max generation, planning$2.752512 (448maxlogicalcalls,4096input+32768
output average), all-at-outputcap projection$10.67974656. Hard cap can cause partial
run; no promise of completion. Price ceilings .06/.18 USD/M input/output. Durable
reservation uses full advertised context plus outputcap, includes reasoning.
Prior v79/v80 unknown charges remain separate and are not cleared/reused.

One physical dispatch unless an explicit HTTP429 rejection is confirmed as
upstream_provider_shared_pool, without generation_id/usage. Then <=3attempts
per same logical request, backoff30/60s; each rejected attempt retains its FULL
maximum reservation in globalcap (bill unknown, never called free). No resend
after any generated/incomplete/length/empty answer, timeout or unknown generation.
401/402/403/login/usage and other transport failures stop immediately. Persistent
third429 stops run; no adaptive retry schedule or output-cap changes. Max1344
physicalattempts still under hardcap, no budget increase/borrow/unknown clearing.

Score only after generation freezes: unchanged v11ref oracle programs/public
postconditions reused; no fresh paid judge. Full-sensitivity result, if emitted,
must be labeled CPU-only/nojudge. Primary paired task comparison combined versus
concept-hybrid: wins/losses/ties on correctly detected buggy PUTs, false-positive
assertion counts, unknown/abstentions. Package rule: wins>losses AND FPcombined<=
FPbaseline, descriptive K1dev subset only, not a statistical efficacy claim.
Do not infer gain from tests/coverage alone. Report both total calls/tokens/costs
and differing realized budgets. Incomplete run reports ONLY complete paired
leading tasks; no GO/NO-GO or causal conclusion for partial data. No larger run.

CPU preparation and independent read-only engineering review before paid calls:
two-arm-only dispatch and original baseline prompt/seed equivalence, new scorer
denominators, deterministic subset, streaming429budget/unknown/route handling,
real networkless worker smoke. Freeze source/config/runtime/prepared public inputs,
endpoint metadata and this protocol before launch. Keep detached PID/status,
final artifact audit and independent semantic/integrity review after terminal.

Prior art: v11 matched-round2 removes most early concept gain; v31weak18vs15,
v34FA rule not met. v77 merge prepared but unrun. v80 task85 DeepSeek diagnoses
correct, structuredReka feasible, DeepInfra raw correct but schemaextra; task124
unmeasured. This experiment tests the requested package change, not a new concept.

Pre-dispatch review amendment A: enforce exact expected arm/sample triples in
paired scorer, not counts alone. Explicitly label ref primary as replacement
oracle: its expected values/FP counts come from frozen reference programs,
not DeepSeek's own expected output. Add secondary o0 scoring of the model's
original assertions from the same frozen executions, no extra paid/native calls.
No outcome has been computed; all task-selection/treatment/budget rules unchanged.
