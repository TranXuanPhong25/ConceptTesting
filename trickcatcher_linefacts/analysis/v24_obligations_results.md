# v24 diagnostic9 complete — output interface failed before concept verification

2026-10-17. Normal controller exit0,90/90 logical requests/physical completions, all
finish_reason=stop. Source, dependency/interpreter, prepared-packet, CPU-gate,
preparation/generation hashes and unchanged parent v7 verified. Actual responses match
Qwen transport records and tokenizer-bound usage. No additional Qwen/oracle request, new PUT execution,
predicate execution, output repair or relaunch was made during this completion analysis.

**The run did not produce a usable executable-obligation pipeline.** All9 model
contracts failed before semantic calibration, and all54 generation responses were
rejected by the registered strict JSON interface. No meaningful concept-effectiveness
or between-arm superiority conclusion can be drawn from these zeros.

## Where the interface broke

| Stage | Accepted | Failure |
| --- | ---: | --- |
|Spec-only contract|0/9|All put Python in `relation`, prose in `predicate_source`; configured code field raises `predicate_syntax`|
|Code-only behavior|9/9|Mechanically valid; semantic quality varies|
|Initial hypothesis|8/9|f06 missing required `reason`|
|Feedback hypothesis revision|1/9|Other8 missing required `reason`|
|First generation,3 arms×9 cases|0/27|Outer Markdown JSON fences rejected as `invalid_JSON`|
|Generation revision,3 arms×9 cases|0/27|Same outer-fence failure|

All contract root JSON/schema field types and exact quotes pass up to the code parse;
this is a semantic-role/serialization failure, not9 calibrated predicates rejected as
semantically false. All9 have decision=proposed and uncertainty empty;7 also put
`domain="Python"` instead of the actual input domain. The ambiguous case never yields
a valid abstention. Strict format/source policy was registered before outputs and is
preserved: no swapping fields, stripping fences, filling missing fields, executing a
recovered predicate/input or counterfactual rescoring.

The interface design did not reliably elicit Qwen's intended fields despite passing
CPU checks. Authored positive controls proved runtime mechanics, not model compliance.
Raw sketches in the wrong field also have substantive defects; moving fields alone
cannot be assumed to fix the method.

## Full9-case outcome and raw semantic review

Independent clean-context reviewer v24_output_review read original fixtures,36 shared
raw artifacts and generation responses before aggregate metrics. Review is qualitative
model-assisted adjudication, not human gold. Rejected raw content remains rejected.

|Case / intended status|Raw semantic issues|Shared witness-only bug inputs|
| --- | --- | ---: |
|f01 correct sorted multiplicity|Wrong-field sorting sketch uses loose `isinstance(int)`, lambda/attribute outside policy and no exception handling; core behavior correct|0|
|f02 returned-dedup bug|Behavior recognizes `set` removes duplicates but initial hypothesis still claims multiplicity preserved; rejected revision proposes non-list input outside domain|14|
|f14 correct unused set|Model confuses unused local set/duplicate preservation with preserving original order, demands `[2,1]` rather than sorted `[1,2]`|0|
|f15 correct unreachable dedup|Dead branch recognized, empty-input defect fabricated; initial trigger alwaysFalse, revised empty trigger has no violation|0|
|f03 correct inclusive count|Wrong-field predicate only requires a nonnegative integer, not the required count; accepts bool; main behavior correct|0|
|f04 strict-versus-inclusive bug|Strict comparison recognized but supplied trigger is passing base `[1,3],2`; model count/arithmetic explanation is wrong|14|
|f05 correct inclusion|Wrong-field predicate computes membership from arguments and ignores observation entirely; initial consistent is reasonable|0|
|f06 equality-versus-inclusion bug|Behavior incorrectly describes equality as subset; only valid final hypothesis uses equal-set trigger where semantics agree and outside-domain noniterability explanation|8|
|f13 ambiguous suitable|Model invents normal/non-None requirement, leaves uncertainty empty and overclaims empty/non-list fault; no normative oracle for arbitrary suitable values|N/A|

Every case has0 calibrated obligations,0 initial/final supported hypotheses,0 accepted
generated inputs and6 rejected generation artifacts (2 calls×3 arms). Initial and
final support are unverified for all9. Contract checks on all224 pool rows are unknown
because no qualified contract exists, not because native workers failed. There is no
tested contract precision or successful ambiguity handling to report.

The124 online predicate evaluations were **triggers only**: four initial mismatch
triggers over99 pool rows, and one final f06 trigger over25 rows. No online obligation
predicate reached execution or the authored semantic bank. CPU-authored calibration
success from preflight must not be substituted for model predicate success.

## Arm comparison was not realized

|Arm|Usable generation artifacts|Raw executed inputs|Gated selected inputs|Novel inputs/tasks beyond full pool|
| --- | ---: | ---: | ---: | ---: |
|verified_hyp|0/18|0|0|0/0|
|text_hyp|0/18|0|0|0/0|
|toolinput|0/18|0|0|0/0|
|witness_only|No generation|224 pool records, including ambiguous case|Same common pool|3/3 declared bugs,36 bug-revealing inputs|

There is an additional implementation/control limitation: `value()` forwards only
accepted parsed artifacts. Actual text_hyp contexts therefore contain a null concept
on9/9 cases and a null final hypothesis on8/9 (only f06 final hypothesis survives).
The intended raw textual guidance control is absent for the rejected contracts.
verified_hyp likewise receives null contract/hypothesis on all9; although its prompt
requires abstention without a calibrated contract, all18 raw responses contain
nonempty fenced proposals. No registered valid abstention is observed.

All3 arms do receive exactly identical6 concrete input/native-trace rows for every
case in both rounds. Selection is indices0..5 everywhere because there is no supported
contract witness. No extra private pool execution is supplied to one generation arm.
The preparation views are correctly isolated: signature/spec for contracts and masked
code/syntax for behavior. No hidden semantic-bank row, authored fault label, gold
output or evaluator witness is sent in these model request contexts.

The entire frozen24+base pool contains224 distinct records across9 cases (25 for8
cases,24 for f13). Independent recomputation confirms14/14/8 bug-revealing inputs for
f02/f04/f06, total36 across3 bugs;5 correct cases have none and f13 is unscored. This
already saturates the tiny bug cohort, so incremental new-task headroom is zero.
These are3 bugs, not36 bugs. LLM receives no detection credit for this shared pool.

False verified flags and false flags on correct code are zero **because no calibrated
contract or accepted input exists**. They are not evidence of high precision/safety.
Generation duplicate/invalid-candidate counters are also zero because whole artifacts
failed before candidate extraction; this does not mean raw proposals were valid or
nonduplicated. Raw prose still shows wrong semantics (dedup-as-correctness, invented
first-nonzero suitability, duplicates treated as missing membership), without credit
or rescoring of the rejected objects.

## Actual costs

|Group|Completion calls|Input tokens|Output tokens|
| --- | ---: | ---: | ---: |
|Shared contract/behavior/initial/revised hypothesis|36|45,899|5,313|
|verified_hyp generation|18|36,723|3,451|
|text_hyp generation|18|33,657|3,582|
|toolinput generation|18|33,069|3,536|
|**Total**|**90**|**149,348**|**15,882**|

86 tokenizer metadata calls; no retry or unknown completion usage. Model-metadata/keepalive
requests are not persisted by this controller and cannot be exactly reconstructed;
they are excluded from the90 completion count. Wall time31m04s.
Recorded shared-pool workers:448 launches/PUT calls, representing ordinary+traced
execution of224 pool records,0 worker failures/unknowns. Online trigger workers:
5 launches/124 evaluations,0 obligation evaluations. No generated-candidate executions.
All reservations have recorded launches; interrupted uncertainty upper bounds are0.

Additional CPU-authored preflight controls are separate from online efficacy:
25 predicate-worker launches/2,779 evaluations and6 evaluator-only PUT-worker calls
for the3 known bug witnesses. Public-base warmup reuses the native cache and is
already included in the448 shared-pool launches. Totals across these recorded run-root
worker directories:484 launches,454 PUT calls,2,903 predicate evaluations. None of the
CPU-authored predicates is claimed as a Qwen-produced or calibrated obligation.

## Disposition

Completed transport run with output-interface failure; no tested concept gain, no
valid executable-vs-text comparison, no promotion, benchmark, held-out or new adaptation.
A later proposal would first need a prospectively frozen interface that can emit the
correct predicate field/required fields/bare JSON, and a textual control that preserves
the intended raw semantic content independently of executable validation. Such a fix
has not been applied to this run or tested here. No promising fenced input or wrong-field
predicate has been retroactively accepted. The separate Luna probe remains unpooled.

[Machine-readable verification and all90 raw Qwen artifacts](v24_obligations_results.json)
and [read-only recomputation script](v24_obligations_results.py) preserve origin and
failure reasons. Original pipeline/status/artifacts remain unchanged. Callback handled;
no work to resume or duplicate.
