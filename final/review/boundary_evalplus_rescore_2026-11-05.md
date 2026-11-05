# Boundary/all44: corrected HumanEval+ reference rescore

User authorized oracle correction without regeneration. Modern oracle now uses
the pinned reference-only HumanEval+v0.1.10 export;signature/spec/contract/tolerance
compatibility verified for all164tasks. Task115only relocates math import.
No hidden test inputs were retained or used.

Source run:`final/out/boundary_all_plain_bva_20261105`.
Corrected output:`final/out/boundary_all_plain_bva_evalplus_v0110_20261105`.

| Arm | Valid novel inputs | Old reference detections | Corrected reference detections |
|---|---:|---:|---:|
|plain|595|3|0|
|boundary|121|3|0|

All44tasksrescored;all previous detection disagreements disappear under the
corrected reference. This is not a new generator comparison:inputs/PUTs/seeds/
budgets are unchanged and no output formatting repairs were applied.

- Generation freeze exactly equals source freeze for44tasks.
- All1,336original artifact files match the pre-rescore hashes.
- New model calls/requests/tokens:0.No model/tokenizer was instantiated.
- Cache:3,178records,1,412hits/1,766new native executions,separate repeat slots;
  0timeouts/uncached/corrupt/missing receipts.
- 118source/datahashes verified;full44taskread-only replay reproduces entire
  corrected summary with model/native execution forbidden.
- Full modular engineering suite122checks pass,including10new reference/rescore
  checks and all prior112checks.

The raw old3vs3counts remain in their original artifacts for traceability. Do not
interpret them as confirmed PUTbugs. BVA's generation-only weaknesses remain
visible:17no_boundary,5no_inputs,1invalid_selection;only121of473raw BVArecords
survive construction validation. See the [improvement plan](boundary_improvement_plan_2026-11-05.md).

Implementation: `references.py`,reference-only data export,
`generators/frozen.py`,`rescore.py`,default oracle provider in modern pipeline.
Legacy/synthetic experiments explicitly retain original-task references when
reproducing old protocols;completed source outputs are not migrated in place.
