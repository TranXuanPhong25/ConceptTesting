---
name: prefer-standard-libraries
description: User prefers standard libraries over own implementations when results stay the same (fewer reviewer objections)
metadata:
  node_type: memory
  type: feedback
  originSessionId: 08a7596f-fd39-47c8-b7c7-c0ed6ea6f8c3
  modified: 2026-10-12T17:48:26.024Z
---

When a library can replace a self-written component without changing results, prefer the library; when a library is
clearly worse (v4: Hypothesis replacing the base-input fuzz dropped good@3 44 -> 22), keep own code and justify it.
For new capabilities use a library first (e.g. CrossHair for symbolic witness search).

**Why:** user (2026-10-13): "nếu thay mà không đổi kết quả thì càng tốt, t đỡ bị vặn" — standard tools are easier to
defend to reviewers/examiners.

**How to apply:** swap in a copied pipeline folder ([[pipeline-folder-workflow]]), check equivalence offline first
(facts / good@3 per task), adopt if not different; report the comparison in RESULTS.
