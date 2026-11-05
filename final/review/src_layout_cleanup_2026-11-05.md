# Source/data layout cleanup — 2026-11-05

User approved deleting retired concept code, then selected final/src and final/data.

- Current source: final/src/modular, final/src/runtime, final/src/audits and
  final/src/development_groups.py. Original plain baseline also lives under src.
- Datasets/domain/reference metadata, group inventory/labels/plans and fixtures:
  final/data. Prior inventory/subsets preserved in development_groups/archive.
- Removed 41 executable source/launch files from concept_reference_v1, recovery and
  old V11 packages. Documentation remains archived; original source is in Git.
- Reports remain in final/review; all existing run/checkpoint outputs remain in
  final/out. New commands use python -m final.src.modular.run/rescore.

Validation:

- 214 tests pass (18.00s), including baseline, current modular/runtime and development
  grouping. Current modules import with old experiment packages blocked.
- Offline inventory rebuild changes only builder_sha256. All task records and all
  group task/PUT selections exactly equal pre-layout snapshots; subset inventory
  hash updates accordingly. No model, reference or PUT calls in this rebuild.
- 153,397 recorded output/checkpoint file hashes match before/after (0 changes).
  The ledger excludes mutable logs, PIDs, keepalive and shared execution-cache files.
- Runtime execution.py/worker.py/contracts.py exactly match original Git source bytes.
- Independent read-only review checked imports, dataset/cache/manifest paths and
  retirement completeness. Its two output-location findings were fixed: baseline
  default remains final/out/humaneval164; PUT audit summary stays in final/review.
- No Python/launch files remain outside src/tests except final/__init__.py marker.
- git diff --check passes. No model/benchmark run or commit performed.

New source/module identities require a fresh output directory; historical manifests
are never rewritten to force source compatibility. Exact frozen-input rescoring
can still consume saved inputs into a separate output directory.
