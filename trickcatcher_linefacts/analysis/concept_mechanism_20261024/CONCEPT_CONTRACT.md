# Concept contract — operational definition, 2026-10-24

Scope: specification-grounded, execution-informed concepts for test generation. This document defines admissibility and measurements; it does not introduce or claim a successful generator. Existing v7/v11 gap facts, v14–v26 obligations/properties and v40/v43/v50 bindings remain the internal prior art.

**Meaning and source**

A concept is a reusable human-defined abstraction. A task instance binds that abstraction to typed roles under explicit applicability conditions. A useful testing instance must identify an actionable obligation and provide information such as a measured gap, rather than merely repeat a code tag the generator can read directly.

Keep these roles distinct:

| Role | Meaning | Evidence needed |
|---|---|---|
| Input validity | A caller obligation defining allowed inputs | Specification clause and faithful interpretation; public inputs are sanity checks |
| Behavioral requirement | A required input/output or cross-execution relation | Specification justification under explicit preconditions |
| Observation | A relation held or failed on particular PUT executions | Exact execution IDs and bounded scope |
| Test gap | The declared suite has not exercised an obligation under the stated coverage definition | Suite digest, executable coverage predicate, observed count |
| Fault hypothesis | A possible explanation for a mismatch or risky behavior | Fallible hypothesis and a discriminating experiment; not normative truth |

`observed`, `justified`, `hypothesized`, `unknown`, and `rejected` are different statuses. Finite agreement with the PUT cannot promote an observation into a justified requirement. PUT disagreement cannot demote a spec-justified requirement: record a potential implementation violation separately. An exact spec substring cannot establish entailment by itself. A human-authored vocabulary is permitted; a separate executable answer written for every task does not establish transfer.

**Minimum task-instance record**

```json
{
  "concept_family": "a reusable semantic family, not a task ID",
  "role": "behavioral_requirement",
  "definition": "typed relation with quantifiers and declared scope",
  "bindings": {"role_name": "task argument or justified expression"},
  "applicability": ["input-domain and specification conditions"],
  "spec_evidence": [{"clause_id": "...", "interpretation": "..."}],
  "normative_status": "justified | hypothesized | unknown | rejected",
  "observations": [{"execution_id": "...", "result": "..."}],
  "gap": {
    "suite_digest": "...",
    "coverage_definition": "what exercising this obligation means",
    "covered_count": null,
    "measurement_status": "measured | unknown"
  },
  "obligation": {
    "change": "the semantic dimension to exercise",
    "preserve": ["validity and other required relations"],
    "check": "input predicate, cross-execution relation, or independent oracle"
  },
  "provenance": {"extractor": "...", "runtime_evidence": [], "gold_assisted": false}
}
```

This is a documentation contract, not an enforced output schema. A machine format must not discard an otherwise correct semantic item because an unrelated item is malformed. Any later implementation needs raw-response retention and separate interface/semantic metrics, as the v25/v32/v43/v50 history requires.

Use a numeric covered_count only after measurement; unknown coverage remains null. Any executable binding expression needs a declared grammar/type/scope before implementation, rather than an unrestricted expression field.

**Worked example and its limits**

Suppose the spec defines a sum of contributions from pairs `(value[i], weight[i])`, with each pair independent of its position. The general concept is preservation of paired associations under a shared permutation. Bind the two arguments and the same permutation; justify order independence from the spec. The relation is:

`F(permute(values, p), permute(weights, p)) == F(values, weights)`.

The applicability conditions include equal array lengths, valid elements and a spec that is insensitive to pair order. The generator must preserve pairing and apply a nontrivial permutation on distinguishing data. The checker separately measures input validity, transformation realization, and output relation. A reported gap applies only to the archived suite and declared pair-coverage criterion.

Counterexamples: permuting only one array does not preserve pairing; identical elements may make a permutation nondiscriminating; a prefix-dependent or order-sensitive spec does not justify this relation. Passing this relation does not prove full correctness and may leave bugs unchanged on both executions. This worked example is illustrative, not an evaluation fixture or demonstrated new capability.

**Admission and effect checks**

1. Check applicability and binding before generation. Ambiguous or unsupported requirements remain unknown; no invented eligibility rule or expected value.
2. Check candidates for validity and actual obligation realization. A call that merely finishes is not coverage of the semantic obligation.
3. Distinguish generated inputs from replayed witnesses and supplied alternatives. Runtime tool agreement never grants hidden-reference access to generation.
4. Measure confirmed bugs with an evaluator separate from the PUT. Relation violations need validity and sound relation premises; incomplete relations cannot certify correctness when satisfied.
5. Report all assigned problems/PUTs, including unsupported, malformed and blocked items. Conditioned metrics are diagnostic and cannot replace total treatment results.
6. Use ablation/intervention to investigate actual use: hold raw evidence and resources fixed, remove a semantic relation or gap, and test the predicted change in obligation realization. A rationale or semantic-looking output alone is insufficient.

**Representation and useful information**

Raw evidence, prose carrying semantic propositions, and a typed concept contract are separate comparisons. Prose can express a genuine concept. If prose and typed concepts perform alike, that limits the structure/taxonomy claim, not necessarily the semantic-content claim. If the same raw evidence or witness-only tool performs as well, there is no shown incremental benefit of the added semantic packet.

Generalization requires declaring the supported domain and freezing the vocabulary, binding rules and construction operators before evaluation on unseen problems. Renaming variables is a robustness check, not evidence of semantic transfer. An input-validity improvement or better oracle is useful engineering; neither by itself proves concept-guided generation.
