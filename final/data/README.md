# Pipeline data

- `humaneval.jsonl`, `LICENSE`: original 164 HumanEval specifications, base tests
  and canonical solutions. Original dataset bytes are unchanged.
- `humanevalplus_v0.1.10_references.json`: pinned corrected reference-only export,
  with no hidden input arrays. Provenance: [reference notes](references_README.md).
- `contracts.json`, `evalplus_LICENSE`: unchanged domain/tolerance metadata.
  Pre-layout snapshots are recoverable from Git history. Offline rebuild changed
  only the builder source hash and its dependent inventory hash; task records and
  selected task/PUT identities remain unchanged.
  Input annotations come from the original task signatures. Domain validation
  uses the contracts in this metadata.
- `fixtures/`: synthetic/saved inputs used by engineering tests.
- `humaneval_bugs.json`: reference-bug notes, when present.

Code loads this directory via `final.src.modular.dataset` and `references`.
Generated executions/cache/checkpoints remain under `final/out`, not here.

18/11/2026: HumanEval-X C++/Java loader, adapter selection và CLI đã gỡ theo yêu cầu.
Pinned datasets và historical outputs chỉ giữ làm nguồn lịch sử.
DatasetLoader chỉ còn HumanEval Python và MBPP+.
