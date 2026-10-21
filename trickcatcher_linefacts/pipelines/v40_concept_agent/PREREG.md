# Astra D1 implementation protocol — 2026-10-21, before task outputs

User explicitly requested Astra catalog/design then exact qwen2.5-coder-32b-instruct
on supplied endpoint. Stop Codex work at remaining<=15%; no fallback, paid calls,
training, benchmark, held-out or automatic next experiment. v7 unchanged best parent;
explicit v30 tools and v23 authored fixture/oracle ports. No old output import/repair.

Prior art: v7 grounded facts, v13/v23 hypothesis prompting, v17–19 typed relations,
v21 tools, v28 active replay33native-checked actions with no added detection benefit,
v30 contract CPU repair, v32 support/scope, v33 hard-gate loss, v35 fixed-pool ceiling.
D1's limited new measurement is explicit predicted observations and selective claim
revision under known false/correct/ambiguous supplied claims + committed query control.
No promise of better concepts. Broader Astra design at analysis/astra_concept_design_20261020/DESIGN.md.

Frozen source includes7relation catalog,8episode manifest, private truth and reply schema.
All8 seen authored cases remain denominator. Arms concept_adaptive/generic_adaptive/
concept_committed see identical spec, original code/base, fallible H and initial native
row. Concept arms additionally receive strict catalog projection, binding and recomputed
finite gap. No catalog examples, private labels or expected oracle enter messages.
After round1 all receive same additional native row plus own query results. E3/E6
shared rows already expose bugs; no discovery claim from reusing them. Only E1/E2/E4/E5
eligible for no-supplied-witness within-diagnostic discovery. Novel input subtracts union
of ALL shared base/injection rows, not arm-local examples. Historical novelty and real
new-task/benchmark gain unmeasured; no improvement in model-authored assertions claimed.

Three calls per episode/arm,72 single attempts total. No content/transport retries.
Each call prompt<=6144 tokens including template/history; max_tokens1536, context8192,
temperature0/top_p1/seed20261021. Server exact model/context required; tokenizer raw
rendered chat count must equal completion usage.prompt_tokens. Reject/quarantine and
stop on mismatch, model/protocol/transport failure or context excess; record known
vs unknown usage. No silent context truncation or post-output adaptation. Optional
canary ceiling1 not used in this implementation; metadata checks precede task calls.

Every arm max3 actions/round, max2replays/round,6actions+4replays+2final inputs total.
Recognized invalid/duplicate query still charges slot, original action retained.
Valid sibling action survives an invalid action. Whole reply invalid JSON/schema is
retained as turn failure, receives error next turn; no recovery/extraction/field fill.
Prospectively accept bare JSON or exactly one whole json fence. Claim state does not
gate final input. No later_queries outside committed turn1; no replacement commitment,
premature final inputs or queries in final turn. Rejected replacement does not cancel
already committed batch. Every prediction artifact durable BEFORE native execution.

committed turn1 freezes both batches; round2 executes that batch after updated claim
reply; final inputs may adapt in all arms. Thus this isolates intermediate query
adaptation, not all adaptation. Generic adaptive uses same action/call ceilings and
raw observations; additional catalog semantics+gap summary are a combined treatment,
not isolated concept wording. Equal maxima do not imply equal actual calls/tokens.

Native execution:16shared requests +96in-round +48final <=160requests/320processes.
Preparation/cpu regression controls separate. Ordinary+traced agreement required; every
worker attempt reserved durably, unknown attempts cached unresolved/no retry. Input
limits disclosed: full positional Python literals,<=1000chars,<=256ASTnodes,depth16,
container<=64items, integer<=4096bits; only exact list[int]/integer fixture domains.
No model-authored Python execution. Resource/domain/trace failures remain unknown.
Public tools inspect_flow/inspect_data/replay_input only; no shell/reference/score tool.
Feedback contains native observation, scope/limits and validity provenance, never
expected value, relation verdict or bug flag. Structural reach is not semantic proof.

Source/prepared/guard/dependency hashes before launch; raw generation freeze before
fixture-oracle scoring. CPU validation + independent clean-context code review required,
approval bound to exact source snapshot. Controller lock and immutable slots prevent
duplicate calls; resume replays exact durable requests/actions/cache, never resets an
unknown completion attempt. Quota checked at safe boundaries, no credit resets.

Report all24episode-arm rows/72slots, raw actions/native checked/rejected/unknown,
repeated queries, predictions, proactive corrections vs evidence-linked revisions,
actual adaptation opportunities, final inputs, shared witness floor and independent
fixture discrepancies. Free-text semantic grading by independent review after freeze;
the literal words revise/withdraw are insufficient. No semantic gold for new tasks.

Use go/no-go in d1_protocol.json: capability needs8valid concept finals, correct handling
of E1/E5/E6/E7, retain E2/E4, reject E3 false binding, unknown E8, no false bug claims
on E7/E8, useful replay/final on>=3/4 no-supplied-witness episodes. Incremental concept
signal requires>=2concept-only vs generic discoveries,0opposite losses/no extra false
claims. Adaptive signal separately>=2 useful evidence-linked changes missed by committed
on unresolved opportunities; <2opportunities => inconclusive/ceiling, not resampling.
Combined mechanism needs both signals. If generic/committed equal or stronger, no
incremental claim; no larger n/K, changed score, training or automatic expansion.
