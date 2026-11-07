# Soft BVA tools: construction helps; optional direction interface failed

Completed the user-authorized Phase A and conditional Phase B, followed by a
separate envelope-only loss audit. The main soft BVA default remains unchanged.
There were10new model responses in total, all received, no unknowns or truncation;
Phase A and the envelope audit used0new model calls. Phase B used16206known tokens.
All input batches froze before corrected reference/domain scoring and two native
repeats. Each evaluation matched immutable read-only replay. Source and original
response hashes were verified at each run's completion.

## Phase A: construction from existing seeds

Artifacts:`final/out/boundary_precision_phase_a_20261107_152738`.
Policy:first10soft seeds + up to10float-neighbor expansions, remaining seed fill.
No new anchors from known bugs, task-specific rules, LLM direction or score-based
selection. Supported top-level finite floats and numeric strings with direct
float(parameter)conversion evidence. Shared task input cap20.

| Policy | Valid novel inputs | Detected PUTs/tasks |
|---|---:|---:|
| Saved direct | 199 | 6 |
| Saved soft | 192 | 7 |
| Fixed20generic precision | 193 | 8 |
| Full pool ceiling, outside primary budget | 318 | 8 |

Gate PASS:added stable value-mismatch99and kept all7soft detections. Tool maps
the existing seed'0.5'to'0.49999999999999994'; reference0, PUT1in both repeats.
This isolates a construction deficiency:soft already supplies the location but
the literals it chose were not sufficiently close. No new model concept was
needed for this gain.126expansions across2/72/99/157; fixed policy selects34.
All other tasks retain their original seed batch because the tool has no
supported scalar-float anchor there.

## Phase B: seed writer plus optional concept directions

Artifacts:`final/out/boundary_precision_direction_20261107_153836`.
Same10task/PUT/spec/contract/base packets,model,sampling and2048completion cap.
The writer outputs20seeds plus at most2requests:seed_index,parameter,quantity,
anchor,neighbors. Concept and generic policies share the same new writer output
and actual expansion countK<=4, and retain the same number/order of seeds.
Generic K is conditioned on admitted concept requests, so this is not an
autonomous generic-tool baseline. Original soft is replayed unchanged separately.

| Primary policy | Valid novel inputs | Detected PUTs/tasks |
|---|---:|---:|
| Original soft | 192 | 7 |
| New writer seeds | 95 | 4 |
| Concept-directed | 95 | 4 |
| Matched generic | 95 | 4 |

Gate FAIL:no concept wins and original soft losses2/76/124/140. However,4is
primarily an admission result, not a semantic capability score:

-2/76/99/124/140return complete JSON inside a Markdown code fence. The frozen
  strict bare-JSON parser rejects the entire envelope despite finish_reason stop.
-Raw responses contain8directives. After envelope normalization,7fail the tool
  interface:6use boolean/list neighbors instead of the fixed'adjacent'string;
  one72request points to seed18with anchor3.9while that seed actually hasw5.
-Only one directive is admitted:72seed14,w1.0. Its2neighbors add no detection.
-Many envelope-rejected responses have useful seeds:140contains' '/'  ',76
  contains(1,0)/(1,-1)/(0,2),124contains five-digit year fields. Seed construction
  did not fail merely because the formal response wrapper was not accepted.

Thus the added interface introduces failure modes. It is not valid to conclude
from4vs4that all semantic directions are unhelpful. The trial gives little
coverage of successfully executed concept directions. It does show the requested
structured interface was not reliable under this prompt/model/sample. No automatic
repair/retry was used to change the primary result.

## Envelope-only audit: separate and explicitly post-hoc

Artifacts:`final/out/boundary_precision_interface_20261107_154844`.
Strip only a complete single outer```json...```fence and apply the same remaining
validators. No values,quotes,escapes,neighbors,quantities,anchors or indices are
repaired. Reuse original responses; freeze all derived batches before scoring.
Original Phase B metrics/gate remain unchanged.

| Audit policy | Valid novel inputs | Detected PUTs/tasks |
|---|---:|---:|
| Recovered new seeds | 193 | 7 |
| Concept-directed, strict directives | 193 | 7 |
| Generic, matched actualK | 193 | 7 |
| Autonomous fixed20precision | 195 | 8 |

Recovered seeds detect16/23/72/76/124/140/157. Original soft detects
2/23/72/76/124/140/157. Equal total7masks a concrete swap: new Unicode seeds
catch16while the new decimal values miss2. Concept and matched generic remain
equal; admitted direction count remains1. These audit results cannot rescue the
failed primary gate or demonstrate concept-selection superiority.

Autonomous precision adds2and99but loses72, giving8rather than9. On72,the new
writer has6eligible w-neighbors. The fixed policy keeps10seeds +6expansions +
the next4seeds, dropping seed15`([-1,-1],-2)`. That seed is a stable witness:
final sum=-2=wbut the first prefix=-1>wcauses premature False. The matchedK2
policies keep it because they retain8remaining seeds. This is a demonstrated
allocation/context-loss mechanism, independent of parser failures.

Task99also separates arithmetic precision from target relevance. The writer
requests neighborhoods around seeds that parse to1.5, while existing seed0.5
is left unrequested. Autonomous expansion executes'1.4999999999999998'and both
reference/PUT return1; it also executes'0.49999999999999994'and gets0vs1. The
raw requests themselves fail the neighbors field check. The observed candidate
outcomes show that not every half-integer neighborhood is equally useful here.

Representation also matters beyond numeric spacing. The new16writer includes
literal backslash-u text such as`\\u0100`alongside actual'中文'and'😀'. The former
is ASCII text after JSON decoding, so it does not exercise code point256. The
actual Unicode strings catch the PUT. A boundary idea expressed as escape text
is not automatically a concrete character at that boundary; the encoder
correctly preserves the submitted string instead of guessing an unescape.

## Why historical naive can beat explicit boundary pipelines

Distinguish three comparisons. Historical naive saw multiple PUTs/task; current
soft/direct see one selected PUT. Within the matched original diagnostic,soft7
preserves direct's6. The new seed+request writer has a different schema/prompt;
its losses must not be attributed to the production soft default.

| Case | Historical naive / direct success | Where explicit BVA lost it |
|---|---|---|
| 2 | Near-integer-below literals expose Fraction.limit_denominator rounding | Legacy v5abstains before construction. Current soft already succeeds; the new writer's coarser seeds miss it, generic neighbors restore it. |
| 11 | Naive emits('', '')and gets ValueError vs expected'' | Legacy v5denies a scalar boundary because it sees equal lengths. Current soft/new seeds still omit empty pairs:coverage remains missing after removing the gate. |
| 157 | Naive emits a coupled float tuple near squared-Pythagorean equality | Legacy v5selects unrelated scalar a≈0and breaks the joint relation. Current soft/direct succeed without that target compiler restriction. |
| 76 | Naive includes negative/zero-base cases with wrong returned values, plusx0timeout | Current soft originally only hitsx0timeout. The new raw writer has useful branch cases but primary envelope rejection hides them. |

There is no evidence historical naive solved every current miss:it also misses16
and has no admitted source inputs on99. Worksheet's precise99inputs and Unicode16
inputs are separate evidence. Extra boundary instructions are not verified
knowledge; actual quantity/context selection, representation, formal binding and
budget allocation determine which calls reach execution.

## Resulting diagnosis

1. Precision is mechanically repairable when a useful anchor already exists.
2. Missing quantity/context coverage remains:empty11and the original Unicode16
   miss cannot be fixed by neighboring existing numeric values alone.
3. The optional direction schema adds avoidable interface/binding risk. The
   scalar anchor/mode are redundant for a single adjacent-float tool, yet are
   model-produced fields that can be inconsistent. This design should not replace
   direct seeds or become an admission gate.
4. A correct constructor can displace the only useful joint context under a
   fixed budget. Allocation needs its own evidence; selecting more neighbors is
   not automatically better.

Keep the soft default. Generic precision has a construction signal, but its
budget policy is not reliably loss-free on the new seed batch. The tested concept
request interface has no demonstrated benefit and fails its prospective gate;
do not promote it or retune this run. Prompt length, hidden reasoning and
general superiority were not isolated. These10known-bug, outcome-selected cases
are mechanism diagnostics, not a held-out detection-rate estimate.
