# v25: split output contracts and small feasibility gate

2026-10-17 user-authorized continuation. Direct copy of best v7 (PARENT.json), with
explicit audited v24 runtime/worker/transport ports (PORTS.json). No previous outputs,
caches or paper reproduction. v7/v23/v24 source stays unchanged. Uses jsonschema,
inspect, ast, Hypothesis, Counter, httpx/Jinja2 and existing isolated execution policy.

This is a5-case **feasibility-only** adaptation on seen authored f02/f04/f06/f14/f13:
three bugs (multiplicity, inclusive count, inclusion), one correct unused-operation
case, one ambiguous suitable criterion. It is not an efficacy arm comparison, a
reference-free semantic verifier, generalization test or benchmark promotion.

## Separate payload roles

1. Spec-only concept metadata JSON: decision, spec_quote, input_domain as an exact
   original quote, required_relation as prose, uncertainty. Unknown intent requires
   nonempty uncertainty and no subsequent predicate call.
2. Separate spec-only CODE response: exactly obligation(arguments, observation), no
   competing code/prose fields. Pure code and full input/output relation checked by
   the inherited sandbox and finite authored positive/negative calibration bank.
3. Behavior has code-only input context; output is structured behavior JSON.
4. Hypothesis metadata JSON: verdict, target_line, trigger_condition, explanation.
   A separate CODE-only call converts each mismatch condition to trigger(arguments).
5. Input generation returns named JSON arguments, purpose and reason, no code/tuples,
   expected outputs or predicted outputs. Binding/original-domain checks remain fixed.

Serialization is registered prospectively: bare payload OR exactly ONE complete
matching json/python fenced block, optional outer whitespace only. Language tags are
case-insensitive. No extra prose, multiple blocks, field swapping, filling omissions,
syntax/semantic fixes or arbitrary extraction. Raw response and decoded payload/envelope
are distinct artifacts. This decoder never recovers or rescores historical v24.

## Real model gates and stopping

| Gate | Requirements | Task slots up to this phase |
| --- | --- | ---: |
|A|Four defined predicates calibrated; f13 model unknown with uncertainty/no code|10|
|B|All3 bugs observed-supported; f14 consistent with no pool violation; f13 unknown; all behavior/hypothesis interfaces valid|25|
|C|Each bug has a valid contract+trigger+target-reach discriminator; f14 a normal contrast with obligation=True; f13 inputs=[] plus reason|30|

Failure stops before all dependent phases; all5 case rows retain failed/blocked/NA
status. No prompt/content retry or alternate predicate repair. A legitimate unknown
does not fail merely because its code slot is not applicable. Passing every gate
permits only a narrow feasibility conclusion. No automatic full comparison even on pass.

The common24+base discovery pool and authored semantic probe bank freeze BEFORE calls,
with dependencies, seed and worker interpreter/binary. Calibration has the same explicit
diagnostic-gold authority/limits as v24. No bank rows/hidden oracle outputs enter model
prompts. Qwen retains normative semantics; no static property/effect matching.

Phase B replays the entire frozen pool. Common6 rows selected by calibrated obligation
violation then original pool index, before any hypothesis. The hypothesis is checked
against full pool: true trigger, checked native/traced execution, primary source line
observed, false obligation, no observed trigger counterexamples or unresolved checks.
This is finite observed support, not universal trigger sufficiency or causal proof.

Phase C scores after complete frozen outputs using the same independent fixture oracle.
Novel inputs/task detections subtract the ENTIRE24+base pool, not just6 shown inputs.
Witness-only can already saturate the3 bugs. Input copies remain visible; no credit
for repeated tool discoveries. f13 has no authoritative normative output oracle.

## Raw control preservation

control_contexts exports verified_hyp/text_hyp/toolinput packets with identical concrete
input/native-trace rows. text_hyp ALWAYS gets unchanged raw metadata/predicate/hypothesis/
trigger responses with origin, state, request/response hashes, regardless of parser,
syntax or calibration failures. Only a genuinely missing response is null/missing.
verified receives qualified/observed-supported content only. Poisoned-artifact tests
check that rejected raw responses survive. Packets are exported even on gate A failure;
they are reviewable control interfaces, NOT a GPU arm comparison in this increment.

## Optional backend enforcement

Source/prepared data freeze before an OpenAPI check and optional1 adversarial echo.
Only advertised guided_json is considered. Echo prompt requests NOT_JSON while the
schema requires exactly {schema_gate:true}. It must return valid RAW BARE JSON, not
a decoded fence, with normal usage binding. Only that success selects guided_json
for task JSON stages; otherwise fixed plain mode. No task-output-based mode switching.
This is observed capability evidence, not a universal API enforcement proof.
HTTP metadata/wait/keepalive calls are separately logged without URLs/credentials.
Protocol/tokenizer accounting failures stop globally; no unsafe fallback after quarantine.

## Budget and operations

At most30 task slots/30,720 logical output tokens, plus1 echo slot/64 tokens. Max3
cumulative transport attempts/slot:90 task attempts +3 echo attempts, no content retry.
Code caps1536, metadata/behavior/hypothesis/inputs768. Model/context pinned, temperature0.
Raw-response ledgers, source/data/dependency hashes, protocol quarantine, one-attempt
workers, staging/canonical result separation and interrupted uncertainty reuse v24.

Controller waits for the previous authorized endpoint after12:20:22UTC, polling models
every60s for up to60min after code readiness. Source/CPU verification precedes model
requests. Endpoint/key remain environment-only. During code work a metadata-only
prelaunch keepalive may run; it stops when the owned controller starts. Detached
controller and same-session watcher use exclusive locks; no duplicate task launch.

```bash
CoverUp_concept/.venv/bin/python -m pytest -q trickcatcher_linefacts/pipelines/v25_interface_gate/test_gate.py
CoverUp_concept/.venv/bin/python -B -m trickcatcher_linefacts.pipelines.v25_interface_gate.gate preflight
CoverUp_concept/.venv/bin/python -B -m trickcatcher_linefacts.pipelines.v25_interface_gate.gate freeze
# After audits/source freeze and environment-only endpoint setup:
CoverUp_concept/.venv/bin/python -B -m trickcatcher_linefacts.pipelines.v25_interface_gate.controller
```

Legacy online v7 entrypoints disabled. CPU authored response fixtures/calibration
controls are never represented as model success. Reviews/results live outside this
source folder, which is not edited after real calls start.
