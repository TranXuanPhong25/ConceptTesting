---
name: boundary-test-applicability
description: Boundary applicability research distinguishes ordered boundaries, joint feasibility, oracle, and slide-specific 4n+1 assumptions
metadata:
  type: reference
---

2026-11-04 research requested by user completed; detailed evidence and page
references in `final/review/boundary_applicability_2026-11-04.md`.

Read test_slides functional-testing pp.5–17, official ISTQB CTFL4.0.1 §4.2.2,
Python nextafter documentation, and existing formal-contract paper pp.3–5.
Separate boundary identification, feasible input construction, and oracle verdict.
Independence/single-fault are assumptions supporting one-at-a-time 4n+1, not
universal BVA prerequisites. Joint constraints require feasible witnesses; no
finite global max required; generation caps are not semantic boundaries.

Follow-up clarifies reusable families classify input characteristics, not raw
types: ordered scalar, length/cardinality, position, ordered enum, relational
aggregate. Report now distinguishes type-derived candidates, contract-grounded
obligations and feasible witnesses; schemas/formal types may supply the contract,
so natural-language inference is not always necessary. Taxonomy is synthesis.

Current development_groups boundary fit uses manual label plus base-pass only;
it does not establish verified boundary witnesses or base gaps. Research report
contains the evidence checklist and its sources.

User subsequently authorized implementation on2026-11-04. Standalone per-PUT
`final/modular/boundary_value_analysis/` now implements the requested flow:
saved input types/signatures→templates→LLM boundary/domain selection→LLM inputs.
No templates means0calls; no boundary means1call; successful generation uses2.
Explicit unsupported/invalid/no-input states, immutable checkpoints and read-only
replay; no default-arm integration.41engineering checks pass; offline6PUT smoke
extraction succeeds with0rejected observations. No live LLM/PUT/reference calls.

Initial templates: numeric value,length,numeric elements,sum; threshold may use
another input value/length/sum. Validate quote presence,signature/literals,exact
boundary target and duplicates. LLM prose constraints remain unverified and need
external domain/reference checks. See module README/CHANGELOG/PREREG before runs.
No paper reproduction,benchmark launch,commit or push in this implementation.

Next user request on2026-11-04 integrates module into `BenchmarkPipeline` through
opt-in `BoundaryArm`/`--arms boundary`. Task budget split equally over eligible
visible PUTs,no redistribution;merge/dedup,then existing freeze/reference/evaluation.
Report task/PUT skip statuses and both logical call phases;not call-matched to plain.
Boundary-only bypasses CFG/DFG/witness sampling;empty suites avoid native execution.
CLI now has --task-ids,--target-programs,--input-budget for saved smoke cohorts.
Fullmodular85checks pass (41module+11integration+33existing),with tiny synthetic
sandbox fixtures only;no live model/cohort benchmark. Default arms remain unchanged.

Latest user steering2026-11-04 supersedes default-flow statements above: remove
initial concept-generation steps from the main pipeline and inject input generation
using dependency inversion. Main `BenchmarkPipeline(input_generator=...)` depends
on `generators.InputGenerator`; `MethodInputGenerator` composes any method/stage
returning input batches, without ExperimentArm inheritance or concept packets.
Modern default is plain only; plain/boundary have no legacy concept/witness steps.
Old flow remains in explicit `LegacyArmInputGenerator`, CLI --legacy-generation.
Shared output contract feeds existing freeze/reference/evaluation. Source/config
identity includes the generator. New default outputs:final/out/modular_pipeline.

Validation extracted into named response/input/task-binding functions, with
VALIDATION START/END comments at calls and API/cache/reference checks; checks stay
enabled. Fullmodular93checks passed; custom stage/producer injection, no-model/
no-packet flow, checkpoint/replay and old fixtures covered. No live benchmark.
Read final/modular/generators/README.md for the current API and code examples.

2026-11-05 user requests actual plain+BVA run on the direction-specific dataset.
Prepared/froze existing boundary smoke6PUT (HumanEval0,5,18,81,99,120;PUT0each),
input20/arm/task,target1,expectedQwen27/context8192,max18logicalcalls.60targeted
checks pass;67sourcefiles and source cohort hashes frozen. Registration appended
before any inference. Run directory:final/out/boundary_smoke_plain_bva_20261105;
review report:final/review/boundary_smoke_run_2026-11-05.md.
Endpoint models404;asked user for current endpoint. No controller/completion/
task input/reference result yet. Prepared launch.sh uses private runtime env
outside repo. Do not claim running or substitute a paid backend.

**How to apply:** consult the report before claiming boundary-ready or boundary
coverage; distinguish input boundary coverage from assertions and bug detection.
