# VR8 semantic-gate diagnostic — complete, no improvement shown

All six registered tasks and three arms completed with Qwen3.5-27B-AWQ,
context8192. Source/selection remained frozen. Canonical implementations and
contracts were decoded only after generation freeze. This is a six-task
measurement diagnostic with a fixed strategy budget, not a full113 comparison.

| Final metric | Old gate | Semantic gate | Generic |
|---|---:|---:|---:|
| Primary shared-ref confirmed tasks | 6/6 | 6/6 | 6/6 |
| Primary false-alarm tasks | 0 | 0 | 0 |
| Secondary o0 confirmed tasks | 5/6 | 5/6 | 5/6 |
| Secondary false-alarm tasks | 3 | 2 | 3 |
| New valid inputs retained after round1 | 23 | 19 | 23 |
| New valid inputs satisfying selected semantic predicate | 7 | 7 | 7 |
| Tasks with final semantic predicate observed | 5/6 | 5/6 | 5/6 |
| Final valid inputs with unknown semantic value | 2 | 2 | 2 |
| New logical strategy calls | 12 | 12 | 12 |
| New logical expected-output calls | 6 | 5 | 6 |
| New logical tokens, counting shared receipts per arm | 16,254 | 16,086 | 16,254 |

Confirmed and false-alarm task counts can overlap. `ref` uses the same ten saved
spec-only reference programs per task; `o0` uses assertion expected values.
Novel inputs are compared to that task's saved round1. Semantic counts measure
the bound OBS property, not a specification violation. Unknown is not covered.
See RESULTS.json for task-level values and AUDIT.json for request accounting.

## What this result does and does not establish

Saved round1 already confirmed all six tasks under `ref`. Neither task detection
nor the paired sign-test p=1 establishes equivalence or improvement: detection
was at ceiling before this diagnostic. Old gate considered every selected target
covered; semantic gate considered five covered. Consequently old and generic
made identical requests on every task, and semantic differed only on task51.
The cache reused those exact request bodies/seeds; these are not independent
replications. There are only six tasks and one changed target decision.

No additional semantic realization was obtained over either control. The lower
o0 false-alarm count comes from retaining fewer tests on task51, not from repairing
its expected-output model. Do not promote this gate or expand the benchmark on
these results.

## Mechanism failure: an inapplicable hypothesis becomes a hard input filter

Task51 `remove_vowels` has the correct table `aeiouAEIOU`. Its actual bug is
`text.replace(' ', '')`, which deletes spaces that should survive vowel removal.
The selected semantic target asks for membership disagreement with exactly the
same `aeiouAEIOU` class. At the bound comprehension lookup the value is a single
character and the table is unchanged, so that target cannot hold in this PUT.

Both semantic strategy requests executed successfully and each produced100valid
candidate inputs. The hard target filter rejected all200candidate occurrences;
no input reached expected-output generation. This is not a transport, syntax,
or invalid-input failure. Nor does a false OBS value establish that the whole
function is correct.

One discarded generated input was `remove_vowels('w u')`. A separate post-hoc
native oracle replay, after all generation and final scoring, confirms it is valid,
differs from canonical output, and is exposed by the same ten-reference oracle.
The public behavior requires `'w '`, while the PUT returns `'w'`. The membership
measurement is correctly false: the vowel table is not the cause of this bug.
That replay is diagnostic evidence only and is not added to any method score.
The job/result are in the evidence archive under `posthoc/task51_discarded_witness/`.

The next design question is applicability and input retention: distinguish an
observed false predicate from an unobserved site, an unsupported binding, and a
statically refuted fault hypothesis. A card needs a description of the behavior
and tests for relevant input classes; its failure hypothesis need not be true.
Keep novel valid inputs available for other targets/generic exploration when a
hypothesis is refuted. These are proposals for a separately registered vr9,
not changes made to this frozen run.

This also clarifies ConceptCoder alignment: an attribute/relation can be a
concept, but requiring every suspected defect predicate to become true is not
its concept definition. VR8 is an own-method observable measurement diagnostic,
not a reproduction of ConceptCoder's learned bottleneck or training.

## Cost and integrity

53 logical new calls used20physical completions, all received, no retries,
failures, or unknown usage. New usage:15,133prompt+2,975completion=18,108tokens.
The reused six round1 responses and60reference programs account for30,099known
historical tokens, incurred earlier. Shared preparation costs are excluded;
18,108is actual new usage, while48,207includes this particular inherited subtotal.
The roughly1%lower logical tokens in semantic versus old result from skipping
one expected-output call after rejecting inputs, not better concept coverage.

41 CPU tests passed before launch. Terminal audit verifies frozen source and
parent hashes,692generation/transport file hashes, shared round1 receipts,
fixed two strategy slots per arm, request identity, ledger, and per-arm costs.
The controller exited; no active job or automatic vr9/full113 expansion.

`evidence.tar.gz` preserves native jobs/results, generation, transport receipts,
final scoring, readiness, and the separate post-hoc replay. Its SHA256 and every
member hash are in EVIDENCE_MANIFEST.json; archive round-trip verification passed.
The archive contains no endpoint URL. Extract into a scratch directory to inspect;
source files and frozen inputs remain in the parent vr8 folder.
