# Independent v24 terminal semantic/practical review

Fresh clean-context luna_v24_output_review read all9 actual preparation/generation
packets and cached native/contract results after complete status15:46:30UTC. No new
model/endpoint/PUT/predicate calls, source/raw edits or rejected-code repair/execution.
Qualitative model-assisted review, not independent human semantic gold.

All9 normative/behavior/fault diagnoses are semantically faithful:3 true mismatches,
5correct implementations (including masked/dead operations) and1undefined suitable
criterion. All90 responses have valid JSON shape; executable-policy failures are
separate from that. Native stage validity contract6/9, behavior9/9, initial hypothesis
8/9, final9/9, generation54/54. Calibration5defined contracts;3rejected/1unknown.

|Case|Actual output and formal outcome|Bug inputs: verified raw→selected / text / tool|
|---|---|---:|
|f01|Correct sort, consistent initial/final, contract238/238bank.|0→0 /0 /0|
|f02|Duplicate-loss behavior/mismatch correct. Complete normative relation uses observation.get, violates explicit no-attributes policy, so contract rejected.|0→0 /4 /6|
|f03|Correct inclusive count/consistent; contract reuses x in separate comprehensions, false binding rejection.|0→0 /0 /0|
|f04|Strict > behavior vs >=spec recognized. Initial sufficient trigger false-rejected on comprehension x reuse. Final boundary trigger valid, observed-supported14pool witnesses; contract510/510bank.|4→4 /4 /3|
|f05|Correct membership/subset/duplicates/extras, consistent; contract2028/2028bank.|0→0 /0 /0|
|f06|Equality-vs-subset mismatch correct; contract2028/2028bank. Exact [1,2]/[1] trigger feasible but absent fullpool, support unverified.|6→0 /4 /5|
|f13|Unknown suitability and first-element-or-None behavior correct. Verified/text abstain; tool emits3unscored inputs first then abstains.|Oracle unknown|
|f14|Correct sorted multiplicities; unused set local recognized. Contract false-rejected on separate-comprehension x reuse.|0→0 /0 /0|
|f15|Dead ifFalse and active sorted return recognized, consistent; contract238/238bank.|0→0 /0 /0|

f02 rejection differs from scope false positives: .get is explicitly prohibited,
although semantic relation is faithful. f03/f14 contracts and f04 initial trigger use
independent Python3 comprehension-local bindings; frozen validator's global Store
set rejects the second x. Native failures remain unchanged; no repaired scoring.

f06 shows coverage/gating loss. Shared pool already has8violations, but exact trigger
[1,2]/[1] is absent, so preparation support remains unverified. Verified generation
round1 supplies that exact trigger. Cached checks explicitly show obligation=False,
trigger=True,reach_and_violation=True,accepted=False because frozen preparation support
was not observed-supported. All6 generated f06inputs genuinely reveal bugs and are
novel outside entire pool, yet none is accepted. This is a sufficient but narrow
trigger plus rigid support-gate limitation, not semantic inability to generate witnesses.
One rationale also misses a shown nonempty required-subset counterexample in common row6.

|Arm|Observed unique|Raw bug inputs/tasks|Selected inputs/bug inputs/tasks|Novel bug inputs outside fullpool|
|---|---:|---:|---:|---:|
|verified_hyp|30|10/2|4/4/1|raw10; selected4|
|text_hyp|48|12/3|48/12/3|11|
|toolinput|48|14/3|48/14/3|14|
|witness_only|224pool records|36/3|baseline|NA|

Novel generated inputs: verified30,text46,tool46.0new detected tasks beyond witness-only;
all3bugs already covered by14/14/8pool inputs.0invalid/unknown native slots,0failed
generation stages,0within-arm duplicate observed inputs. No expected-output/assertion
synthesis in this input-only track.

0false contract flags on calibrated contracts;0false verified flags on4accepted
inputs only. This does not establish rejected contracts' accuracy, f13 oracle, universal
soundness or real-task precision. f13 toolinput acknowledges ambiguity yet violates
abstention instruction on first round. Purpose labels sometimes overclaim: f02/f04
contrasts still expose bugs; an f06text equal-set input is labeled trigger but passes.
These labels are not verified flags.

All9cases have identical6native rows across3arms,2generation calls/arm, arm-specific
revision feedback. Text contract is null atf02/f03/f14 due native parse/policy rejection;
verified contract present5cases, supported hypothesis onlyf04. Names of arms do not
imply every case received full guidance. Toolinput retains spec/code/base and can solve
faults directly. Native report.costs onlyimported old namespace; external finalizer
sums old+new once, retaining quota attempts and all harness/provenance limitations.

Conclusion: model reasoning much stronger than original Qwen interface failures on
this authored cohort, but no causal equal-budget model inference or concept task gain.
Mechanical policy and support coverage suppress semantically useful output. No version
promotion, benchmark/new calls or silent validator/gate repair.
