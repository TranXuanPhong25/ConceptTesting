# Pipeline data

- `humaneval.jsonl`, `LICENSE`: original 164 HumanEval specifications, base tests
  and canonical solutions. Original dataset bytes are unchanged.
- `humanevalplus_v0.1.10_references.json`: pinned corrected reference-only export,
  with no hidden input arrays. Provenance: [reference notes](references_README.md).
- `contracts.json`, `evalplus_LICENSE`: unchanged domain/tolerance metadata.
- `development_groups/`: manual task labels, structural inventory and subset plans.
  `archive/` preserves the exact pre-layout inventory/subset snapshots. Offline
  rebuild changes only the builder source hash and its dependent inventory hash;
  task records and selected task/PUT identities remain unchanged.
- `fixtures/`: synthetic/saved inputs used by engineering tests.
- `humaneval_bugs.json`: reference-bug notes, when present.

Code loads this directory via `final.src.modular.dataset` and `references`.
Generated executions/cache/checkpoints remain under `final/out`, not here.
