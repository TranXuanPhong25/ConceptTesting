---
name: pipeline-folder-workflow
description: Best pipeline lives in one self-contained folder; every new experiment = copy that folder to a new versioned folder and edit there
metadata:
  node_type: memory
  type: feedback
  originSessionId: 08a7596f-fd39-47c8-b7c7-c0ed6ea6f8c3
  modified: 2026-10-12T17:31:25.315Z
---

User (2026-10-13): "gom mấy cái best pipeline hiện tại vào 1 folder, rồi mỗi khi thử cái gì mới thì copy và sửa trong folder mới".
The current best pipeline (v7: v6 code facts + spec facts, run_v4 7 arms, evaluate, oracle_b01 ref/full) is packaged as
trickcatcher_linefacts/pipelines/v7/. A new experiment = copy the best folder to pipelines/<new version>/ and edit only
inside it; never edit the best folder in place. When a variant becomes the new best, it becomes the base for the next copy.

**Why:** the code was spread over many shared modules with additive patches; the user wants each version isolated and
easy to diff. Extends the earlier rule "sửa cái gì thì tạo folder mới, bump version".

Every new folder must contain CHANGELOG.md (what changed vs its source folder, files, commits, status: in progress /
adopted / dropped) — user 2026-10-13: "mỗi bản folder mới phải có changeLog". Small fixes I do at once; large
pipeline/baseline changes wait for Codex.

**How to apply:** before any new variant, `cp -r pipelines/<best> pipelines/<new>`, register it in PREREG, update the
diagram ([[version-tree-diagram]]), commit after the finding ([[commit-only-when-asked]]).
