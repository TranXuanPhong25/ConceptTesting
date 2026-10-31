---
name: git-artifact-hygiene
description: User wants unnecessary local artifacts excluded from Git; preserve source, reports and checkpoints on disk
metadata:
  type: feedback
---

User requested discarding or gitignoring files that do not need uploading to Git.

**Why:** workspace includes large downloaded paper material, scraped responses,
runtime logs, worker caches and local tool installations unrelated to source changes.
**How to apply:** prefer narrow .gitignore rules and preserve local artifacts when
their contents might be useful. Keep source, memory, reports, experiment configs,
licenses, curated results and reproducible dependency lockfiles eligible for Git.
Ignoring a tracked file requires separately removing it from the index; retain its
working copy. Never treat an untracked research folder as disposable by default.
