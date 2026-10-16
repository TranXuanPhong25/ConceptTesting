# Qwen prompt chaining — direction correction, 2026-10-15

User explicitly corrects the proposed static `align(property,effect)` design: Qwen should extract concepts and identify obligation/behavior mismatches; the research direction is to break reasoning into inspectable prompt stages. This supersedes static semantic matching as the proposed main method. v20 remains a limited verification prototype, not the desired extractor/reasoner. No new implementation/GPU experiment in this correction.

## Active responsibility boundary

Qwen performs semantic interpretation, abstraction, alignment, hypothesis selection and discriminator design. Static tools provide source IDs/AST relations, input/trace observations, schema/syntax checks and executable checks where supported. No hardcoded property-name/effect-name matching, no lexical rule choosing the intended concept, no registry-prefix fault selection. Structured fields constrain the interface, not a nine-family semantic vocabulary. Unknown verifier support is recorded; it does not turn a Qwen hypothesis into a false semantic claim or erase it from coverage reporting.

## Proposed chain

1. **Spec obligations:** Qwen sees original spec and signature, extracts candidate obligations, original domain, per-element eligibility, scope/ambiguity and exact supporting spans. No PUT-derived behavior accepted as requirement truth. Quote/base agreement alone is not semantic entailment.
2. **Actual implementation behavior:** separate Qwen call sees source body/source IDs and available structural facts; produces an abstract data/control account, output-affecting operations and conditional effect claims. Spec docstring is separated from implementation evidence so intended behavior is not silently substituted for actual behavior.
3. **Alignment/discrepancy:** Qwen receives original spec/code plus both prior artifacts; identifies compatibility or a candidate violation, cites obligation/source IDs, states the condition under which behavior diverges and a plausible alternative interpretation. No tool-defined semantic matcher. Empty/no-mismatch/unknown answers allowed.
4. **Discriminator:** Qwen turns the chosen hypothesis into an executable input condition and bounded input proposals/strategy. It states the predicted local effect and observable relation, distinct from an oracle-certified full expected output. Original domain remains fixed; ineligible elements need not be domain-invalid.
5. **Execution feedback:** tools validate supported aspects and run inputs in isolation, recording actual activation, before/after effects and outcomes. A separately budgeted Qwen call may revise/reject the hypothesis from those observations. A failed concrete prediction is not hidden by content repair or unlimited retries. No MCTS.

Artifacts link by immutable IDs/hashes; stage output cites the preceding evidence it uses. These are inspectable external claims/actions, not access to internal neural reasoning or a correctness certificate. Examples and schemas must preserve Qwen's role in the semantic decisions.

## Illustration

Spec stage: candidate requirement preserves eligible duplicate occurrences.
Code stage: source `set(...)` converts a sequence to unique elements before a returned collection.
Alignment stage: Qwen identifies possible count loss contradicting preservation if eligible duplicates exist.
Discriminator stage: Qwen proposes a duplicate eligible value and predicts count2→1.
Execution stage: tools verify exact operation/argument/value/output evidence where supported; an unreviewed normative interpretation remains an unreviewed candidate.

The tool does NOT contain `if property == preserve_multiplicity and effect == collapsed_to_one` to choose this hypothesis. The same stage interface should permit Qwen to articulate other relationships, guards and temporal concepts without first writing a matching rule for each family.

## Verification/evaluation before GPU

- Audit chain prompts and role boundary with independent subagents before implementation, as user requested earlier. A fresh new pipeline/preregistration is required.
- Offline transport tests: stage IDs/spans, exact original context, structured output extraction, missing/ambiguous answers and bounded failures. Existing v19 format failures require interface checks, not post-hoc repaired scoring.
- Independently labeled cases evaluate obligation interpretation, code-behavior accuracy, alignment and discriminator success separately. Qwen self-confidence/self-grading is not correctness evidence. Include wrong specs/models, correct implementations, masked effects, unreachable operations, alternative explanations and unknown tool semantics.
- Tool check outcomes are supported/contradicted/unknown with evidence/scope; no invented semantic verification. Preserve raw Qwen proposals alongside normalized supported checks.
- Before any online outputs, freeze per-stage calls/tokens, candidate/revision limits, source/context, common discovery and full20 denominator. Report every proposal/execution cost and verifier coverage.
- Later generation comparison must distinguish chaining gain from concept gain and extra calls: matched-budget direct baseline, same-chain behavior-only ablation, plus plain/placebo/toolinput/witness-only. Shared discovery/final admissibility/selection policy; concept-only filtering would change the tested system. Original source/spec available as registered to prevent amplification of an early wrong intermediate artifact.
- Generation freezes before saved-reference/canonical scoring. Separate candidate property false alarms from D_IO. No paid fallback, held-out run or paper reproduction.

Status: user direction recorded; detailed chain prompts/contract still require independent plan audit before implementation. Existing v20 results are preserved and do not establish success of this Qwen-chain direction.

# Implementation plan v3 — 2026-10-16, independent review resolutions incorporated

This section makes the direction concrete. Current user request is planning; no implementation or model run is started by this plan. New implementation would live in `pipelines/v21_qwenchain/`, with its own preregistration and frozen source/config. Preserve earlier versions. Budget numbers below are proposed ceilings for that future registration, not consumption in this planning turn.

## 1. Questions and stage contract

First determine whether Qwen can produce usable intermediate semantic claims, and locate the earliest independently identified error. Only after that assess test-generation gain. Successful JSON transport, plausible explanations and confirmed output predictions are different outcomes.

Use five logical Qwen calls per task. Calls S1/S2 have independent contexts and may run concurrently; later calls use persisted predecessor artifacts. Every call gets explicit task/source hashes and the original context appropriate to its role; no model-generated summary silently replaces the source of truth.

| Stage | Inputs visible to Qwen | Required output | Tool checks |
|---|---|---|---|
| S1 Requirement concepts | Original spec, signature, public base examples clearly labeled as examples; no PUT body | Up to4 obligations: short semantic statement, exact spec quote/span, domain D, element eligibility E if relevant, output/state relation, ambiguity and applicability | JSON/schema; quote span; parameter IDs. Meaning stays candidate until independent review. |
| S2 Actual behavior | PUT body with stable statement/expression IDs and signature; docstring and non-executable comments excluded; optional syntactic facts labeled by scope; no S1/spec | Up to6 behavior claims: abstract operations/state changes, guards/early returns, output effects, source IDs, conditions and unknowns | Source IDs/spans exist; relationships visibly supported by source/observations where available. No automatic inferred-semantic correctness. |
| S3 Alignment | Original spec + full source, S1, S2 | Up to3 candidate mismatches; each links obligation IDs and behavior/source IDs, states divergence condition, predicted observable effect, alternative interpretation; Qwen selects up to2 IDs for probing, or abstains | References exist; no static property/effect matcher, no tool ranking by concept names. Stage records may reject an earlier artifact with a cited contradiction; original artifact remains unchanged. |
| S4 Discriminating inputs | Original spec/source/base examples, S1/S2/S3 selected hypotheses | Up to6 complete positional input tuples total, each with hypothesis ID, domain justification, predicted observation; predictions may be exact result/status or a partial relation; allow unknown | Parse bounded Python literals, arity/size, frozen input filter; execute eligible candidates in sandbox; record actual result/exception and trace evidence with verification scope. |
| S5 Feedback/revision | Original spec/source, relevant prior artifacts, actual tool feedback for all S4 attempts including failures/unknowns | Per-hypothesis keep/revise/withdraw/unknown with cited evidence; up to6 final input tuples and predictions, including reused inputs if justified | Same literal/domain/size/execution interface; report unsupported local claims as unknown; no further revision loop. |

S2's original source positions map to the complete stored PUT even when docstrings/comments are masked in the view. Function/variable names may still leak intent; report this limitation. S3 can re-read the original spec/body and reject a contradictory S1/S2 claim. It cannot reconstruct missing prerequisite artifacts in this first pilot. No MCTS, beam search or automatic concept catalog selection.

## 2. Artifact schema and failures

All responses use one JSON object, with a fixed envelope and stage-specific payload. Semantic statements/concept names are open vocabulary. No whitelist of nine concept families, no named-property switch in alignment.

```json
{
  "status": "ok | abstain | unknown",
  "items": [
    {
      "id": "H1",
      "statement": "Candidate relation or behavior claim",
      "evidence_ids": ["O1", "B2", "N18:23"],
      "condition": "When the proposed effect would occur",
      "uncertainty": "What remains unresolved"
    }
  ]
}
```

Actual schemas specialize required keys: S1 quote/span/domain/eligibility/relation; S2 source_ids/guard/effect; S3 obligation_ids/behavior_ids/source_ids/alternative/selected_ids; S4/S5 input_repr/hypothesis_ids/prediction. These interfaces hold short checkable claims and explicit references, not requests for lengthy hidden/internal chain-of-thought.

Input example: `"input_repr": "(['aa', 'aa'],)"`. No generated Hypothesis/Python functions in the first pilot: direct input tuples reduce the v19 code-format confound. The model still chooses semantic hypotheses and inputs. A later strategy extension is a separate version, not an in-run fallback.

Prediction type is `exact_value` (literal representation), `exception_type`, `relation_text` or `unknown`. Tools can compare supported exact values/status; arbitrary relation text requires an independently supplied check or remains unknown. Never infer a universal semantic claim from one successful prediction. S5's keep/revise text is a model decision, not a correctness label.

Parser policy fixed before online calls: accept one strict JSON object or one uniquely identifiable fenced JSON object with surrounding prose; validate against the stage schema. Preserve raw text and extraction offsets. Multiple objects, malformed JSON, unknown IDs or truncation are failures; no model content repair/retry. Pilot recovery policy: no upstream reconstruction. If S1 or S2 fails transport/schema, S3–S5 slots become typed blocked records without model requests. If S3 has no selected valid hypotheses (including legitimate abstention), S4–S5 are not requested; if S4 fails, S5 is blocked. A valid S4 with rejected inputs/unknown observations still permits S5. All slots remain in the full report; required failures and legitimate downstream N/A are distinguished by the predeclared fixture applicability rubric. A future recovery-enabled chain needs a new version. S5 can revise a valid existing hypothesis/trigger, but cannot invent replacement S1/S2 artifacts.

Artifacts: task/context hashes, prompt hash, raw response, parsed output or error, source/claim IDs, parent hashes, request/usage/cache metadata and tool observations. Source normalization, output extraction and all limits are frozen before outputs. Resume exact missing artifacts only.

## 3. Tool boundary and execution contract

Tool services are mechanically defined: `source_index`, `validate_artifact`, `parse_inputs`, `execute_inputs`, `compare_supported_prediction`. They do not decide which behavior violates a requirement. v20's `SETIFY → multiplicity` matching cannot select or silently rank a Qwen hypothesis. Its operation observer may be reused solely as a disclosed verification capability.

All20 tasks are eligible for the Qwen chain even if the v20 semantic verifier supports only1/20. General native output observations are distinct from narrow operation-level verification. Reports must distinguish statement line observed, exact operation observed, observed value change, unsupported claim and unresolved/timeout. A line hit does not verify an expression ran; static may-dependency does not establish a concrete causal path.

Before literal serialization, reject unsupported alias/cycle topology. Frozen mined_valid is an uncertain admissibility filter, not an independent proof of spec domain. D applies to the input; E selects elements and never requires every element to be eligible. Trace/PUT execution runs isolated with clean env, bounded objects/output/events/time; instrumentation comparison uses fresh copies and value/type/status/post-input/alias signatures within supported scope. Exceptions/timeouts/unsupported observations remain explicit.

S4 at most6 and S5 at most6 proposed tuples/task. Deduplicate globally; at most12 unique input evaluations, each at most one ordinary and one traced execution (24 PUT executions upper bound), plus separately counted validity checks. Oversize/filtered/malformed proposals still count against proposal slots; no replacement fishing. Base/source preparation cost reported separately. Use cached result for duplicate input/source/config; never rerun a timeout to manufacture a success.

Each supported prediction is tagged `observed_match`, `observed_contradiction` or `unverified`, with the exact input/evidence scope. These tags concern that prediction, not correctness of the normative spec interpretation or actual bug confirmation. Final reference/canonical evidence never flows back into S1–S5 of that frozen run.

## 4. Pilot phases and budgets

**P0 — plan audit:** two independent reviewers check semantic role division and evaluation/fairness. Resolve blockers in writing before implementation; user request this turn stops at the reviewed plan.

**P1 — offline adapter:** implementation in new folder, no model calls. Tests cover stage-context boundaries, source mapping after doc/comment masking, reference IDs, strict/fenced/ambiguous JSON, literal/arity/types, failed predecessors, instrumented/native observation scope, validator invocation, caches, truncation and budget enforcement. No test that merely restates a prompt is counted as semantic verification.

**P2 — controlled Qwen diagnostic:** independently specify16 fixture tasks BEFORE model outputs. Six contrasting pairs (correct/buggy) cover multiplicity, inclusive/exclusive boundary, containment/equality, empty-group behavior, quantifier/eligibility and guarded early return. Four stress fixtures cover ambiguous requirement, masked local effect, unreachable operation and multiple plausible faults. Temporal rules may be a subsequent explicitly labeled extension; no claim that these fixtures cover arbitrary business logic. These are authored mechanism cases, not benchmark detection performance.

Five calls per fixture, max80 logical calls. Per-call output ceilings S1=768, S2=1024, S3=1024, S4=768, S5=1024 (4608/task;73728 output-token ceiling). Temperature0/top_p1, pinned Qwen2.5-Coder-7B-Instruct and fixed stage/task seeds. Actual input/output tokens, cache hits, physical requests and transport attempts reported. No paid fallback. Context-window fit checked before calling; no silent context truncation. Context overflow counts as failure with all originals retained.

Gate from P2 to P3: no known adapter/source/provenance/budget defect; at least90% schema-valid slots among predeclared required slots plus any optional slots actually requested; at least6/7 predeclared probe-applicable tasks with both S4/S5 parseable and at least6/7 with one input accepted by the shared filter. Legitimate terminal cases have downstream N/A, not failures; full80-slot totals remain published. The exact denominator is fixed below. The blinded semantic audit must establish the task-pass contract below on at least12/16 tasks; provisional labels cannot satisfy this gate. Publish per-stage numerator/denominator and ambiguity/unknowns. Abstention on an intentionally ambiguous fixture may be correct. These are proposed engineering gates, not proof. Do not lower thresholds after outputs; a failed gate stops progression and motivates a new copy/preregistration.

**P3 — same20 dev diagnostic:** if P2 passes, freeze and run full known20 cohort/K=1 unchanged,100 additional logical calls;92160 output-token ceiling. Do not choose canonical-consistent models/tasks or require a supported v20 concept. Label prior task familiarity (especially149/110/152). First report stage quality and input yield; no automatic larger experiment.

Combined P2+P3 ceiling180 scheduled logical slots and165888 completion tokens for one attempt per slot. At most3 physical attempts/slot (540 total); retry-inclusive completion ceiling497664 if every attempt generates its cap. Timed-out server consumption may be unknown and must be labeled; do not report successful-response usage as total physical usage. No repair calls, no unbudgeted Qwen judges. CPU input cap12/task, traced/ordinary cap24/task; Denominators are16 fixtures and20 dev tasks, reported separately (36 tasks total).

## 5. Semantic audit and error attribution

Freeze a labeling rubric before P2: requirement faithful/contradicted/ambiguous; behavior faithful/contradicted/insufficient; alignment supported/plausible/contradicted/unknown; discriminator reaches claimed condition or not; prediction observationally matched/contradicted/unverified. Semantic labels require evidence, not word matching, fluency or Qwen confidence. Ground-truth fixture specs/implementations and accepted alternatives are independently authored before Qwen output. Model-assisted reviewers may suggest labels, but such labels remain provisional until evidence/human adjudication; no model-self-judged accuracy claim.

Report both unconditional per-task success and conditional stage accuracy. All failed/abstained tasks remain in denominator. Record earliest invalid intermediate artifact and downstream recovery, without calling that a causal proof of final failure. To claim causality later, separately register controlled replacement of one intermediate artifact while holding other inputs/budget fixed; do not replace artifacts in the main run using post-hoc gold.

On real20, source/spec-only human or evidence-based review is distinct from canonical outcome confirmation. Freeze S5 artifacts before any reference/canonical audit. Native PUT output alone cannot confirm that a suspected behavior is a bug. Optional post-freeze candidate discrepancy audit is labeled separately from D_IO and from property truth outside observed inputs.

Primary pilot deliverable is a per-task traceable failure table: source/spec evidence → Qwen artifacts → selected hypotheses → predicted/observed effects → final decision, including counterevidence and unknowns.

## 6. Later matched generation comparison (separate preregistration)

Do not infer concept gain merely from P2/P3 success. Proposed arms, all retaining original spec/PUT/base context:

- `chain-concept`: the five semantic stages above.
- `chain-flow`: same five-call/execution schedule, but intermediate outputs focus on implementation behavior/input classes; omit the explicit obligation-to-behavior alignment artifact. This measures the structured concept package, not a pure isolated word-label effect; implicit concept reasoning may remain.
- `plain`: same five-slot ceilings, first3 calls unconstrained testing analyses, fourth proposes initial6 inputs, fifth uses same execution-feedback interface and proposes final6.
- `placebo`: same schedule with frozen base-covered source facts, matched requests; facts are truthful, no adversarially wrong hints.
- `toolinput`: same schedule with common pre-generation witness pool.
- `witness-only`: execute shared frozen witness pool, no generation LLM; shared discovery cost is counted.

All five LLM arms: same slot-wise output caps, same ordinary/traced execution limits, same final filter and selector; budget ceilings matched, actual tokens/context sizes reported (no padding claim). Shared pre-generation discovery is frozen independently of arm outputs. Arm-specific probes/feedback are part of the tested adaptive system and costs, not free common evidence.

Union initial/final candidates capped12; common selector samples at most6 unique valid inputs with fixed seeds, without looking at predicted failure or concept activation. Reports also expose stage4 and stage5 separately. Witness-only uses same input cap/selection from common pool. Compare raw task D_IO and100-seed random equal-input subsets; matching input count does not erase discovery/adaptivity cost differences.

Same20/K=1 would cost at most500 logical generation-stage requests across five LLM arms (plus any newly registered common discovery). Compare chain-concept vs chain-flow (explicit concept architecture), and vs plain (decomposition package); placebo/toolinput/witness-only are required controls. Do not claim pure concept semantics or generic prompting superiority from a bundled contrast. Freeze generation before the same saved spec-only ref oracle; canonical used only for evaluation. No held-out, larger sweep or automatic GPU run under this planning task.

## 7. Proposed code organization and order

```text
v21_qwenchain/
  schemas.py          # artifact shapes, reference integrity, no semantic matching
  source_view.py      # stable IDs, separate spec/body, documented AST limits
  prompts.py          # five stage prompts + format-only examples
  chain.py            # dependency DAG, failure propagation, fixed budgets/cache
  execution_worker.py # isolated inputs, results, observation scope
  evidence.py         # supported prediction checks, unknowns, provenance
  audit_export.py     # blind per-stage review packets and label accounting
  compare.py          # later preregistered controls/shared selection/scoring
```

Implementation order: interface contracts/source views → offline tests → five prompts/runner → isolated feedback → fixture audit/export → controlled pilot → full20 diagnostic → review whether a comparison is warranted. Tests and checkpoints target semantic-role boundaries and traceable claims; they do not certify the model's private reasoning. No implementation has started in this planning revision.


## 8. Binding contracts added after independent review

These resolutions supersede any less specific wording above. Reviewers: `audit_flow_plan` and `audit_experiment_plan`, read-only plan audits, no implementation/model calls.

### IDs and prerequisite failures

Global identity is `(task_hash, stage, artifact_version, local_id)`. The tool verifies IDs/references and namespaces them; it does not select their semantic content. Missing/failed/blocked/abstained are distinct states. A schema-valid abstention counts toward schema validity, but not non-abstaining semantic coverage. Blocked mandatory slots/no response/context overflow remain failures in the required-slot denominator; predeclared legitimate terminal optional slots are N/A. All80 possible slots and actual requests/received replies are also reported separately.

The first pilot has no upstream reconstruction. S1 and S2 remain independently attempted even when the other fails. Mandatory missing predecessors block descendants as specified above. S5 revisions create new `S5.H*` records with `supersedes=S3.H*` and preserved O/B/source references; prior hypotheses are immutable. Rejected/withdrawn hypotheses remain visible in reporting. A wrong-but-schema-valid predecessor can be contradicted by S3/S5 using original evidence, followed by abstention; this does not silently repair S1/S2 or count them correct.

### Exact S2 context isolation

Parse/index the original frozen module source once. S2 sees executable module context present in that bundle, including helper functions/global bindings/import statements, with all docstrings and non-executable comments masked. Missing external/helper context is explicit unknown; do not fetch hidden benchmark/reference implementations. Masking is a view only, not executable rewritten code.

Source IDs identify original source hash, AST node type and original line/UTF-8 byte-column spans. Preserve newlines and original byte positions in the masked view; test Unicode/multiline strings/comments. Spec quote spans use Unicode character offsets in the frozen decoded spec string, a separately hashed document; never confuse those with AST byte columns.

Structural facts allowlist: syntactic node IDs/spans, syntax edges and observations with provenance. No v18/v19 candidate models, concept_facts, inferred requirements, canonical outcomes or reviewer labels in S2. Function/variable names and executable string constants remain visible and may reveal intent; disclose that residual dependence. Missing source context cannot be replaced by an inferred behavior without an uncertainty tag.

### Prediction and feedback projection

Exact-value comparison is recursively type-aware for supported literal values: True differs from1, list differs from tuple, and container ordering/type semantics are explicit. Capture up to4096 UTF-8 bytes of a literal output; unsupported/oversize output gives unverified, not equality based on truncated repr. Exception comparison uses actual native class/status; timeout is unresolved, not a predicted functional exception. `relation_text` is NEVER translated into a checker by prose matching; unsupported relation remains unverified. No use of v20 `complete_evidence` or its candidate-model matching as a Qwen-hypothesis rank/label.

S4 may request up to2 source IDs/hypothesis with observation kind `statement_reach`, `operation_value` or `function_output`. The set of kinds is an execution interface, not a semantic taxonomy. Tool reports supported observations only for exactly requested IDs. It does not scan prose to pick interesting nodes. A statement hit cannot satisfy operation_value. Requests outside observer support return unknown and remain in denominator.

Feedback includes every S4 proposal slot and its parse/filter/execution/check status, including counterevidence. Always include bounded function output/status summary. For requested traces use fixed chronological first+last observation per requested ID; event/field retention limits are fixed before outputs, full retained trace is separately archived and omission counts are explicit. No result-dependent trimming. The prompt must fit its registered context window with mandatory statuses; overflow is a typed failure, not silent removal of counterevidence. Interface/fixture tests exercise these bounds before GPU.

### Transport and resource ceiling

Per exact logical request: maximum3 cumulative attempts,120-second request timeout, retry backoff2 then8 seconds. Retry only transport/service failures; identical prompts, params, seed and cache key. Schema/content/truncation errors never retry. Resume reads the attempt ledger and cannot reset attempts. Metadata availability polls are separate from generation attempts and logged without endpoints/secrets. No paid fallback.

Across16+20 tasks:180 scheduled slots, at most540 physical attempts,432 input-proposal slots, at most432 unique ordinary and432 traced PUT executions (864 total upper bound), plus separately counted validity/preparation executions. Malformed/filtered/duplicate proposals consume slots. Report actual physical usage and unknown timed-out usage; logical cache accounting is distinct. Source/context overflow emits no HTTP request but remains a failed scheduled slot.

### Semantic gate authority and task-pass rubric

Before P2, independently authored fixture label packets specify: critical obligations/domain/eligibility distinctions, critical actual behavior/effects, accepted alternative interpretations, and the ambiguous/unsupported statuses that are appropriate. General statements such as “process the list” cannot satisfy a critical effect criterion. No task passes if any material S1/S2 claim contradicts those references, even if other claims are correct.

A task passes the interpretation criterion only if BOTH S1 and S2 cover all predesignated critical items without material contradiction. Intentional ambiguity allows abstention only for the predesignated ambiguous item and still requires the clear items; “unknown” on a clear buggy fixture is not semantic success. S3 alignment, S4 reachability/discrimination and S5 correction are scored separately, including false suspicions on correct implementations; accepted input alone does not count as a discriminator.

Mechanical checks and independently authored executable expectations support evidence labels. Free-text semantic adjudication requires an independent human reviewer (user/research reviewer), blinded to arm/outcome where applicable. Separate model reviewers may prepare provisional annotated packets, but agreement/self-grading cannot satisfy12/16 semantic gate. If human adjudication is unavailable or unresolved, stop after P2 and publish diagnostics with semantic labels provisional; do not automatically launch P3 or claim accuracy. No extra judge API calls are hidden in the180-slot budget.

### Later comparison failure policy

Matched ceilings do not guarantee equal actual work when a chain blocks. Future comparison registration must expose scheduled/attempted/successful stage counts and distinguish raw system performance from conditional successful-chain analyses. Do not spend skipped slots on ad hoc repair or claim realized-call equality. Five LLM-arm architectures differ in decomposition/adaptivity; any measured gain is that registered architecture/package, not an isolated semantic-label effect. The exact failed-stage policy per arm is frozen before comparison outputs.

## Reviewed-plan disposition

All independent plan-audit must-fix items have explicit resolutions above: no reconstruction, global ID/version lineage, exact S2 source/context isolation, mechanical prediction/observation limits, cumulative transport caps, and a task-level semantic rubric with adjudication stop condition. This is a plan deliverable only. No implementation, Qwen call, benchmark run or GPU launch occurred in this turn. Proposed numerical gates/budgets become binding only through a future pre-output registration; changing them after outcomes requires a new version.


### P2 gate correction: correct code must be allowed to terminate

Independent review found that requiring72/80 schema replies and14/16 probe-complete tasks would punish legitimate no-mismatch decisions on the six correct programs. Those thresholds are replaced above BEFORE any implementation/output.

Predeclare fixture applicability in the independently authored label packet: all16 require S1–S3 (48 slots). Six buggy paired fixtures plus the multiple-fault stress case require S4–S5 (14 more slots). Thus62 mandatory slots. The six correct fixtures and ambiguous/masked/unreachable stress cases have18 optional downstream slots: legitimate no-mismatch/appropriate abstention is terminal N/A; choosing to probe makes the requested optional slots count in stage validity/costs.

Required/requested stage-validity gate = schema-valid required-or-requested slots / (62 mandatory slots + number of optional slots actually requested), threshold90%. Missing/blocked mandatory stages are failures, even if Qwen declares no hypothesis on a buggy fixture. Optional N/A cannot be assigned by Qwen to change the predeclared probe-applicable set. Keep raw80-slot outcomes (including N/A), actual requests and conditional received-reply rates alongside this gate.

Probe gate = at least6/7 predeclared probe-applicable fixtures with valid S4/S5 artifacts and at least6/7 with an admissible input. Successful discrimination and correct-code false suspicions remain separately adjudicated metrics; no-mismatch on correct code is allowed and scored as such. S1/S2 task-interpretation gate remains12/16 under the independent rubric. Labels indicating fixture correct/buggy/applicability are evaluator-only and must not leak through prompt IDs, filenames or example labels.

Real20 has no gold-informed applicability gating during generation: record upstream failures, genuine model abstention, selected hypotheses and attempted probes separately on the full20 denominator. Do not reuse post-freeze bug labels to choose which tasks should have been probed. This numerical gate exists only for the pre-labeled controlled fixture suite.


Final review status (2026-10-16): both independent reviewers accepted v3 after rechecking the62+optional denominator and legitimate-terminal policy. No unresolved must-fix plan blocker within this scope. Review history: analysis/qwen_chain_plan_review.md. User-facing deliverable remains the plan; no code, tests, requests or GPU run were started.
