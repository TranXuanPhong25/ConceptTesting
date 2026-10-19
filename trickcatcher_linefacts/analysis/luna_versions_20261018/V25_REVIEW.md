# Independent terminal v25 semantic review

Root and fresh clean-context luna_v25_semantic_review independently read actual raw
metadata/code, frozen evaluator interfaces and validator. No models/endpoints, worker
launches, rejected-code execution, renaming, repair or rescoring during review.

Native result unchanged: A=false, B/C blocked.9/9 task responses received with known
usage,5metadata valid and4predicate responses. Reported model identity is requested
CLI gpt-5.6-luna/low; event-level server identity unavailable. Host execution disabled,
schemas exposed,0 task router/tool attempts recorded. No Qwen-origin attribution.

|Case|Actual semantic content|Native result|
|---|---|---|
|f02|Sorted integer list + occurrence conservation. Predicate strict element/output types, sorted value and Counter(value)==Counter(xs), rejects exceptions.|Rejected predicate_binding_mutation; no calibration. Static relation appears correct in valid domain.|
|f04|Count all values >=limit, strict integer output, rejects exceptions.|Same rejection; no calibration. Equality boundary is correctly included.|
|f06|Every required element must occur; extras allowed, duplicates irrelevant. Strict bool output matches all membership.|Calibrated2028/2028 bank rows;25 pool checks.|
|f14|Sorted multiset output; predicate preserves occurrences and order.|Same rejection; no calibration. Spec-only stages cannot demonstrate recognition of unused implementation local.|
|f13|Unknown because suitable criterion undefined; no invented universal eligibility rule.|unknown_spec, no predicate call.|

All3 rejected sources reuse `x` in distinct generator comprehensions. In Python3,
these comprehensions have separate scopes. Frozen predicates.py globally accumulates
all Store names into one `known` set and rejects the second occurrence as binding
mutation. Prompt permits local assignments and single-generator comprehensions; it
does not require globally unique target names across comprehension scopes. This is a
validator/policy false rejection, not evidence of model mutation or wrong normative
relation. No code is changed or accepted retroactively; original scores stay failed.

f06 finite bank comprises169 valid argument pairs (each list length0–2 over{-1,0,1}),
2028 observation rows=169 true/1859 false. Main predicate root has17worker jobs, all
matching accepted f06 source; total2053evaluations (bank+25pool). None uses rejected
source. f02/f14 banks238rows each, f04 bank510, but none reached with those candidates.
Accepted f06 predicate does not check out-of-domain input types; declared domain is
already enforced for discovery. Observation scope is returned JSON values, not object
identity/input mutation. No universal/reference-free/generalization claim.

All5 phase-A exports have identical6native rows across3controls. Onlyf06 gets a
calibrated verified contract; other defined cases null, ambiguity unknown. f06 selected
rows include original equality-code counterexamples (extras/empty-required) already
found in whole frozen pool. They are shared tool evidence, not LLM-generated novelty.

All827 run_frozen hashes verified.248 main PUT calls; separate authored CPU preflight
excluded from task model performance. No behavior, hypothesis, trigger or input stage
was asked because A failed. Therefore masked-code understanding/false alarms,
discriminator generation, verified-vs-text/control effect and all novelty rates are
unavailable. Zero generation counts are blocked defaults. This run demonstrates a
bounded spec-to-obligation capability signal and exposes a validator defect; it does
not establish v25 end-to-end feasibility or concept gain.
