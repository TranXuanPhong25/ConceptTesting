---
name: pipeline-folder-workflow
description: Edit the existing code for new pipeline changes; do not fork version folders or commit before user review
metadata:
  node_type: memory
  type: feedback
  originSessionId: 08a7596f-fd39-47c8-b7c7-c0ed6ea6f8c3
  modified: 2026-10-12T17:31:25.315Z
---

**Latest clarification (user,2026-11-01, supersedes folder rules below):** implement
new versions/arms by changing the existing code. Do not copy the pipeline into a
new version folder. Leave changes uncommitted for the user to inspect. Keep each
arm/stage in its own module/class, and preserve existing artifact/checkpoint data;
different run configurations still need separate output directories to avoid
mixing results. Current request: V11 concept extraction with the modern inputs-only
test generator and reference oracle, rather than the full V11 hybrid generator.

**Earlier clarification (user,2026-11-01):** fixes needed to make an existing version
run should be applied directly to that broken version. Do not create another
version/folder just for a runtime, transport, environment, compatibility or execution
bug fix. This overrides the earlier blanket "every change gets a new folder" rule.
Create a new experiment/version for a method, arm or protocol change. Log technical
fixes in the existing CHANGELOG and preserve completed responses/results/checkpoints;
audit/resume source hashes explicitly when needed instead of forcing a folder fork.

User (2026-10-13): "gom mấy cái best pipeline hiện tại vào 1 folder, rồi mỗi khi thử cái gì mới thì copy và sửa trong folder mới".
The current best pipeline (v7: v6 code facts + spec facts, run_v4 7 arms, evaluate, oracle_b01 ref/full) is packaged as
trickcatcher_linefacts/pipelines/v7/. A new experiment = copy the best folder to pipelines/<new version>/ and edit only
inside it; never edit the best folder in place. When a variant becomes the new best, it becomes the base for the next copy.

**Why:** the code was spread over many shared modules with additive patches; the user wants each version isolated and
easy to diff. The earlier blanket "sửa cái gì thì tạo folder mới, bump version"
is now narrowed by the latest clarification above to actual new experiments.

Every new folder must contain CHANGELOG.md (what changed vs its source folder, files, commits, status: in progress /
adopted / dropped) — user 2026-10-13: "mỗi bản folder mới phải có changeLog". Small fixes I do at once; large
pipeline/baseline changes wait for Codex.

**How to apply:** before any new variant, `cp -r pipelines/<best> pipelines/<new>`, register it in PREREG, update the
diagram ([[version-tree-diagram]]), commit after the finding ([[commit-only-when-asked]]).
