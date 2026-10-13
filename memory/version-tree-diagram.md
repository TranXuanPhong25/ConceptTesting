---
name: version-tree-diagram
description: Keep the ConceptTester diagram artifact (version tree + results with glossary + concept kinds + papers) updated after every new variant
metadata:
  node_type: memory
  type: feedback
  originSessionId: 2dddac78-7845-4887-9c28-b6313bcf7c52
  modified: 2026-10-11T17:14:35.398Z
---

Every time a new variant is tried (fact version, arm, oracle, baseline), update the diagram artifact
(https://claude.ai/artifact/7a6yvf5bhiVmZVyt9UvTC8, source: `trickcatcher_linefacts/out/diagram/conceptester-v4.html`, gitignored; publish with `url` since the path changed on 2026-10-12) as a **tree**:
each node = one version, child of the version it was derived from, with: what changed from the parent, why, method,
result (numbers), trade-off, and a status chip (main / running / dropped / upper bound / baseline). Plain Vietnamese,
explain any term or library.

**Why:** user request 2026-10-12 ("m nên cập nhật mỗi khi thử cái gì mới, làm theo kiểu cây ấy ... đổi cái gì, lí do,
kết quả, phương pháp, đánh đổi"); they lose track of what v4/v4c/v5 mean.

**How to apply:** when a run finishes or a new variant is registered, edit the tree section and republish to the same
artifact URL; also keep RESULTS.md in sync. The same page also carries, and must be updated together: (1) the
results tables with a "Cách đọc" glossary (every metric's definition, how it is computed, which file it comes from),
(2) the concept kinds table (kind, course criterion, example sentence, shown or not), (3) the papers table (what was
taken, where used, level: verbatim / adapted / numbers only / read but not used). See [[codex-quota-fallback]] for who implements.
