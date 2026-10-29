# VR9 repair: CPU ready; fresh expected outputs blocked by endpoint404

Implementation/source/inputs are frozen.48CPU checks pass (47-test suite plus
one added native exact-pool replay test). Twelve control arms replayed without
live calls: original assertions, response receipts and selected inputs are exactly
equal to vr8 semantic/generic controls. Source and parent hash checks pass.

The repair separates observed false from a refuted local fault hypothesis. Static
refutation currently supports an equal literal character class with a conservative
local binding check. Reassignments, dynamic scope access and unsupported forms
remain unknown. This says nothing about whole-function correctness. A second
repair selects novel valid inputs with room for both hits and non-hits, including
unknown observations, within the existing four-input round2 budget.

CPU selection preview, using native reclassification of the exact saved pools:

| Selection count | Strict vr8 semantic | Retain | Applicable + retain | Generic |
|---|---:|---:|---:|---:|
| Task51 newly selected valid inputs | 0 | 4 | 4 | 4 |
| All six tasks newly selected valid inputs | 19 | 24 | 24 | 23 |

Strict/generic numbers are actual cached native generation results. Retain/
applicable numbers are CPU selection previews; their new expected-output
requests are pending. No canonical labels were used for this preview. More
selected inputs is not evidence of better bug detection or oracle accuracy.

Onlytask51has a refuted selected target: its literal vowel table equals the
registered hypothesis class. Retain keeps that target but no longer rejects all
non-hits. Applicable skips the refuted target and uses the existing generic
strategy pool. On the other five tasks the selected predicate was already hit
in round1, so routing remains generic. This scope cannot establish a broad
concept-guidance improvement; task detection also has the known R1ceiling.

The same-pool strict→retain comparison isolates filtering/selection. Applicable
changes routing, so its task51pool differs and must be reported separately.
Selection remains seeded sampling of at most four inputs, not an exhaustive
retention guarantee. No card taxonomy/model training/vendor source changed.

Live preflight returned HTTP404; controller64941exited.0newcompletion attempts,
0newtokens, no unresolved completion or new final score. Cached controls remain
ready for resume. Restore the authorized model endpoint and run `diagnostic check`
then `diagnostic run` as documented in ../README.md. At most12fresh expected-output
completions; strategy requests and strict/generic expected requests must replay
exactly or fail closed. Do not launch a duplicate controller.

AUDIT.json contains exact control equality and per-task preview decisions.
The evidence archive preserves native jobs, cached controls and preflight status;
archive/member hashes in EVIDENCE_MANIFEST.json passed round-trip verification.
No automatic fresh-writer/full113/vr10 expansion.
