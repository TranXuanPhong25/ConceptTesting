# V7 independent recall and evidence overlay

2026-10-29: actual copy of V6; new source/provenance in COPY_FROM_V6.json.
Added hybrid_engine.py (structural/open-BM25/dense), dense.py (pinned local ONNX),
concept_evidence.py +8record overlay, standalone CLI,23engineering tests, owner
snapshot audit, prospective PREREG_V7/review and4source actual embedding smoke.
No root default change, no author code changes, no new target/Qwen execution.
Copied V6 results/completion explicitly renamed PARENT_V6_*. Source and original
corpus hashes verified; outcomes are not evidence of semantic/utility gain.

## Parent V6 changelog

2026-10-27: actual copy of v5; COPY_MANIFEST preserves all copied hashes. User
explicitly requests iterative repair from errors, replacing the prior stop on
v5's no-gain outcome. Runtime edits only here; old frozen variants stay unchanged.
No new model/paid inference. Status: auditing/implementing, new scores pending.

Completion: six append-only development iterations retained. Final code is
semantic-v6.6, iter06. Balanced family91/site90/113 with126cards (label matches
74.6%); v2/v5 family88/site74 with275cards (34.9%).16site wins,0losses. Precise
family/site63 with82cards,80.5%label matches; canonical over-retrieval5/113 vs
v2 100/113. These are not independent precision/efficacy estimates.
242tests PASS;126exact bindings/160dependency links verified;21official-valid
native mechanism cases replay-confirmed with unchanged outcomes reused and one
input-shape correction preserved. Source/corpus/parent hashes PASS.0new modelcalls.
API/CLI v6 defaults balanced; engine default precise; public auto remainsv2.
