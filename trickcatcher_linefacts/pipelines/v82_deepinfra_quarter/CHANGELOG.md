# v82 full DeepInfra HumanEval quarter

Fresh isolated copy of v81 on same fixed 28-task cohort, two arms/K1. New run includes all28 tasks; does not splice partial v81 outputs or retry canceled v81 task19 slot. Protocol amendment reduces total output cap to32768 for both arms so planning fits remaining cumulative cap. Per-call reservation uses conservative prompt envelope plus output cap. Other prompt/merge/scorer rules unchanged. Previous v81 receipts/reserves retained separately.

Worst-case reserve over the full logical-call envelope is $3.39625920 against $3.47684946 available. Retry reserves for more than ~12 extra provider429 attempts can force a paired-prefix stop. Returned length/empty answers fail the arm/sample but don't halt later tasks; missing stream/usage or unknown generation stops.

Status: preparing independent review; no model requests launched yet.

CPU public bundles and current DeepInfra endpoint gate pending. Independent review required before any call.
