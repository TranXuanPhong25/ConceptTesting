# Final native v23/v24/v25 retest — requested gpt-5.6-luna/low

Completed native diagnostic16/9/5 using original engines and unchanged prompts/parser/
fixtures, fresh model contexts per stage. Original Qwen outputs unmodified/unpooled.
User authorized continuation after quota;73old v23 +65old v24accepted responses reused,
79/25missing stages called once in a new namespace. Both original quota attempts stay
consumed. No model/provider fallback, repaired response, v25 rerun, paid API/Qwen
endpoint/held-out/benchmark expansion or rejected-code execution.

The result is useful mechanism diagnosis but **no demonstrated concept task-detection
advantage** on these small seen fixtures. Failures include actual serialization/oracle
mistakes and concrete validator/gating losses; attributing every failure to model
semantics or concept content would be wrong.

## Outcomes and within-version controls

|Version|Native outcome|Control comparison|Interpretation|
|---|---|---|---|
|v23,16cases/7bugs|Concept5/7correct-assertion bug tasks, direct7/7,hyp-only5/7. FA cases1/0/0.|Concept/hyp-only blocked f04/f16 on malformed hypothesis JSON; direct proceeds. C adds f12 wrong expected output.|No concept bug gain. Raw fault reasoning for rejected hypotheses is correct; concept preserves ambiguity better than direct on f13.|
|v24,9cases/3bugs|5contracts calibrated,3policy rejected,1unknown. Final supported hypothesis onlyf04.|Selected verified1/3bug tasks vs text3/3,toolinput3/3,witness-only3/3.|Strong raw semantics, but validator false rejections and frozen support gate discard useful output. No new task beyond whole pool.|
|v25,5cases|9responses;5metadata valid;1/4defined predicates calibrated;f13unknown. Afalse,B/Cblocked.|No downstream generation/arm comparison occurred.|3normatively correct predicates rejected for legal separate-comprehension variable reuse. No end-to-end feasibility or gain claim.|

The cohorts/protocols/output types differ. These are within-version diagnostic results,
not a cross-version ranking. v23 scores model-authored expected values/assertions;
v24/v25 generate inputs only and use common post-freeze fixture scoring. v23 "new"
subtracts public bases, v24/v25 subtract ENTIRE frozen24+base pool; do not merge metrics.

## v23: full16 and practical oracle findings

All16 concepts and behavior summaries semantically faithful by independent static
review.30/32hypothesis artifacts accepted; f04/f16concept hypotheses have correct raw
mismatch reasoning but malformed JSON (f16also duplicate trigger). They remain rejected,
blocking C/H for those2bug cases.44input+44revision calls all parse and all236candidate
slots are native-observed. No output repair or hypothetical rescued score.

Expected values: C73/74,H74/74,D84/84scorable plus4unscored f13. C false alarm is
([1,2,3],5) expectedTrue despite sum6>5. H has one wrong predicted-actual value on f06,
while its expectedTrue is correct and exposes bug. Direct f13 invents first-element
semantics under undefined suitability; FA0 does not cover those4unscorable claims.
C/H retain unknown and abstain. Correct masked f14/dead f15 understood by all arms.
Full16case review: [V23_REVIEW.md](V23_REVIEW.md).

## v24: input yield vs accepted yield

All90responses have valid JSON shape. Native executable validity contract6/9
(5calibrated+unknown), behavior9/9,initial8/9,final9/9,generation54/54. f02contract
uses explicitly forbidden .get despite correct relation. f03/f14contracts and f04initial
trigger hit validator's global Store-name check on repeated x in separate scopes.
Initial support allunverified; finalonlyf04observed-supported.99/224pool contract rows
remain unknown (3unqualified cases +ambiguous24rows). No native pool execution failure.

|Arm|Observed inputs|Raw bug inputs/tasks|Selected inputs/bug inputs/tasks|Novel bug inputs outside entire pool|
|---|---:|---:|---:|---:|
|verified_hyp|30|10/2|4/4/1|raw10;selected4|
|text_hyp|48|12/3|48/12/3|11|
|toolinput|48|14/3|48/14/3|14|
|witness-only|224pool rows|36/3|baseline|NA|

Novel generated inputs30/46/46.0new detected tasks beyond witness-only;3bugs saturated
by14/14/8baseline inputs.0false contract flags on calibrated cases and0false verified
flags on4selected inputs; not universal precision or evidence about rejected contracts.
f13 unknown oracle, toolinput first round emits3inputs contrary to abstention instruction.
Some trigger/contrast purpose labels are inaccurate, distinct from verified flags.

f06 exact trigger[1,2]/[1] is feasible but absent whole pool, so hypothesis stays
unverified even though pool has8otherviolations. Verified generation supplies exact
trigger; cached check has obligationFalse+triggerTrue+reachTrue, but acceptedFalse due
frozen preparation support. All6novel bug inputs discarded. Narrow trigger coverage
and rigid gate, not inability to synthesize a counterexample. All3controls share6native
rows/case; text contract null at3rejected cases, verified hypothesis present onlyf04.
Full9review: [V24_REVIEW.md](V24_REVIEW.md).

## v25: semantic capability vs validator scope bug

f02/f04/f14model predicates correctly encode sorted multiset or inclusive count in-domain
by independent static review, but repeat x across separate generator comprehensions.
Python3 scopes are separate; global known-Store set incorrectly calls this mutation.
Never renamed/executed/repaired/rescored those candidates; A remains failed.
f06calibrated2028finite bank rows +25poolchecks (2053evaluations);f13properunknown.
Onlyf06worker sources executed. No behavior/hypothesis/trigger/input stage, so generation
zeros/false flags/novelty are unmeasured blocked defaults. Correct source f14 unused-local
understanding is untested in v25, unlike v23/v24. Review copied from independent audit:
[epoch1 V25_REVIEW.md](../luna_versions_20261018/V25_REVIEW.md).

## Costs and provenance

|Version|Cumulative CLI invocations / received|Known input tokens|Known output tokens|Unknown usage attempts|
|---|---:|---:|---:|---:|
|v23|153/152|1,176,568|31,383|1quota|
|v24|91/90|770,067|20,965|1quota|
|v25|9/9|63,513|2,183|0|
|Target total|253/251|2,010,148|54,531|2quota|

Cache-reported input tokens1,291,136; reasoning-reported output21,660, subsets of totals,
not added again. Separate actual canary1turn:13,565input/199output (cached12,288,
reasoning156), failed exposure gate with at least1denied tool attempt.2additional CLI
config invocations exited before model start; not model turns. Known totals including
canary2,023,713input/54,730output, with2target usage amounts still unknown. Dollar cost
and internal CLI HTTP retry count unavailable; CLI invocations are not HTTP requests.
Native resumed reports' cost objects cover imported namespace only; external totals
read original+continuation ledgers once. No accepted response regenerated;251successful
target thread IDs distinct. Quota interruption across days is disclosed, not independent
replication or silently reset trial.

Recorded CPU work, unique caches once: v24main682PUT calls,47predicateworkers/
3281evaluations; separate CPU25predicateworkers/2779evaluations and6evaluator PUT calls
(base checks share main cache). v25main248PUTcalls,17predicateworkers/2053evaluations;
separate CPU10PUTcalls +22predicateworkers/2776evaluations. No worker failures/unresolved
launches. v23legacy378worker result files (366ok/12exception) but no durable launch or
put_calls counter; exact physical invocation count is unavailable, not0.

Requested model is exact localcatalog/CLI gpt-5.6-luna/low; no server model ID reported.
Stage messages preserve content but CLI flattens original roles and adds Codex base
instructions; numeric Qwen max_tokens/seed/temp/top_p parity unenforced. Schemas remain
exposed; execution host disabled. Scientific responses have0recorded tool/router
attempts and0external tool results. Canary's original no-exposure gate FAILED; readiness
is fail-closed host evidence, not a claim that schemas disappeared. No causal equal-
budget model comparison, human-gold/generalization or real benchmark/D_IO claim.

## Verification and disposition

Native generation/frozen manifests, original version/source hashes and full old run
inventories verified unchanged. Imported responses/cache bytes preserved; raw CLI
last-message/usage/event streams match native artifacts. Full16/9/5denominators, all
failures/abstentions/unknowns preserved. Root plus independent clean-context reviewers
read allactual16/9/5outputs, static only for rejected predicates. No post-hoc repairs,
accepted score recovery, model calls or new worker launches during terminal audit.

Useful next increment would address lexical scope in validator, support promotion on
new valid witnesses and structured serialization robustness, with a separately frozen
version/protocol. This report does not authorize or launch that work. Current retest
complete; no promotion or automatic benchmark/held-out/paid/new comparison expansion.
[Read-only cumulative verifier](finalize.py), [raw outputs and provenance](results.json).
