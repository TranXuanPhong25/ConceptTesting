# Independent reviews before first model inference

2026-10-29. Agent semantic_retrieval reviewed FastEmbed implementation and this
engine read-only. Verdict: no blocker for the preregistered four-source engineering
smoke; no semantic-applicability or downstream-efficacy conclusion authorized by
that check. Agent concept_quality separately reproduced owner-audit counts and
source/mutant examples, with no substantive blocker.

Must-fix findings applied prospectively in PREREG_V7:

- Site cap originally gave structural candidates priority; use shared source order,
  expose omitted count. AST type restriction remains documented.
- A/B received revised obligations; now they receive only original preconditions.
- FastEmbed constructor max_length ignored; override runtime tokenizer explicitly,
  retain untruncated clone for counts and pin512 cap.
- Dense branch membership is not dense-added contribution; expose dense-top12 and
  paired shortlist changes. No success claim from those counts alone.
- Enclosing guards lacked branch labels; record body/else/header and mark them
  as controls rather than proven feasible path constraints.
- Add explicit cache key/corruption tests and runtime settings to model identity.

23 engineering tests pass before model inference. Local ONNX weights/tokenizer
downloaded and hashed at fixed revision; original model source not modified.
No benchmark labels/target oracle enter runtime. Review limits: multi-function
global query recall may mix contracts, source sites64 and text/token caps lose
context, syntax-constrained lexical binder cannot establish arbitrary mechanisms.
Owner audit demonstrates gate-targeting behavior, not lost bugs or efficacy gain.

Final read-only artifact review after smoke: reviewer checked16packets,522new
embeddings/474cachehits/0truncations, smoke source hashes and164parent file hashes.
No blocker for P3 engineering handoff; reports correctly retain applicability and
utility as unmeasured. The distinct-cardinality fixture limitation is present in
raw results. P2 tool pool still missing; no algorithm/model retuning from outcomes.
