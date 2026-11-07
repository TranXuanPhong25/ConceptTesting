# Plan: precision tools beside soft BVA

Initial status: proposal requested by user; no execution in the planning turn.
Subsequent user instruction "tiếp đi" authorizes Phase A implementation and
evaluation. The active default is preserved. Phase B still requires its own
prospective writer/control amendment if the Phase A gate passes.
Active boundary pipeline remains soft BVA at commit12a24b10.

## Hypothesis and prior work

Soft already emits useful testing locations but sometimes misses a concrete
representable neighbor. Task99has anchor0.5yet no sufficiently close below
neighbor. Test whether deterministic float-neighbor construction repairs this
specific stage without reducing discovery elsewhere under the same input budget.
Empty11and character-code16are separate coverage/quantity failures; the initial
float tool is not expected to repair them.

This is related to the archived BVA v5 target compiler. V5's constructors could
produce targets, while selector abstention and incorrect target/context choice
lost bugs. v47 on a different setting/model selected concept-menu instances no
better than random (16vs18.25covered@3); it does not support reviving mandatory
menu selection. v66demonstrated construction readiness, while v68did not produce
a concept efficacy gain. Tool construction and target relevance must be measured
separately. Proposed difference: preserve direct seed generation; bounded optional
expansion does not become a prerequisite for producing inputs.

## Phase A — offline precision diagnostic using saved seeds

1. Freeze the existing soft/direct requests, responses, decoded batches and
   analysis files as read-only sources. Register the policy before executing any
   additional inputs. These known10tasks remain post-hoc development diagnostics.
2. Implement only a small float-neighbor primitive: finite binary64below/at/above
   via math.nextafter, also supporting a numeric string representation. Encode
   exact round-trippable values; do not round JSON strings or execute generated
   Python. Use existing literal encoders and isolated execution infrastructure.
3. Enumerate eligible anchors from saved seed values in a fixed order for every
   task. Do not hand-label99or inject0.5because its bug is known. A numeric-string
   path must be supported by available task/contract/code conversion evidence;
   any such recognition policy is explicit and fixed. Other arguments remain
   the seed's values. No arbitrary relational-context solver in this phase.
4. Report two distinct quantities: whether the unscored candidate pool contains
   exposing inputs after freeze (construction ceiling), and results of a fixed
   budget20policy. Pool coverage alone is not an improvement result.
5. For budget20, keep the first10distinct seeds; try to fill10slots by neighboring
   anchors in deterministic round-robin order, skipping duplicates. Fill an unused
   expansion slot from remaining distinct seeds. Never select/reorder using
   expected outputs, PUT failures, hidden tests or reference scores. A valid
   construction receipt checks finite values, float adjacency and preservation
   of other seed arguments; domain validity is checked separately after freeze.
6. Score soft's saved20input batch and the constructed20budget batch with the
   same corrected reference/domain and two native repeats. Disclose every input
   replacement, domain rejection, duplicate and newly lost or gained PUT.

Decision: advance only if the predeclared policy produces a new stable
value-mismatch detection and preserves all previously detected soft PUTs in this
mechanism diagnostic. Track timeout-only detections separately. If a gain exists
only in the unlimited pool or needs manual target insertion, stop and report it.
Do not change the split, add task-specific transforms or retune the policy after
seeing outcomes to claim that gate passed. A failure does not justify a larger run.
This gate diagnoses a mechanism on known data, not general efficacy.

## Phase B — optional LLM concept requests, conditional on Phase A

Keep one generation call: soft returns concrete seed inputs and at most2optional
expansion requests. Each request points to an existing seed and actual parameter,
names the supported quantity/representation, gives an anchor and a neighbor mode.
Initial scope is the float-neighbor tool verified in Phase A. No free-form
predicate language, mandatory selection verdict, fault oracle or unbounded tool
loop. Example for schema illustration only:

```json
{"seed_index":0,"parameter":"value","quantity":"parsed_float",
 "anchor":0.5,"neighbors":"adjacent"}
```

A malformed/unsupported request is recorded and does not invalidate otherwise
valid seed inputs. The tool returns concrete literals and construction receipts,
not a claim that the input reveals a bug. If requests cannot fill their share,
use remaining direct seeds up to the same20input cap. Full20seed generation
allows that fallback; prompt/output budgets and truncation costs are disclosed.

Compare three policies, all with a20input cap:

- Current soft direct generation as a separate one-call control.
- Concept-directed expansion from the seed+request writer.
- Generic expansion using the exact same saved seed+request writer output,
  ignoring the requests and allocating expansion slots by the fixed Phase A rule.

Concept and generic policies share writer responses and completion usage; do not
charge that shared call twice. The direct control has a different output schema,
so any total difference from it includes schema/instruction cost. The concept vs
generic comparison isolates the usefulness of the direction information under
the shared seed packet; outperforming direct alone does not establish concept
selection value. Freeze all proposed/selected inputs before reference feedback.

Record wrong quantity, unsupported request, construction failure, invalid domain,
duplicate, seed replacement and valid non-exposing input as distinct failures.
Proceed only with stable concept-directed gains beyond generic expansion without
loss of existing detections under the fixed cap. Document a prospective cohort
selection rule and go/no-go threshold before any new model generation; do not pick
additional tasks by observed outcomes or silently widen this diagnostic.

## Deferred work

Joint empty/singleton construction and transformed character-code quantities need
their own evidence and construction contracts. For task16a future quantity must
evaluate the transformed value after lowercasing; raw chr(code)does not guarantee
the post-lowercase code point. Task72requires keeping palindrome/total/prefix
relations, not just adding negatives. Do not turn those examples into handwritten
per-task fixes or bundle them into the initial precision diagnostic.
