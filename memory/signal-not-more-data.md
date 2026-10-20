---
name: signal-not-more-data
description: User rule 2026-10-20 — when a result is borderline, look for a go/no-go signal in existing outputs; never propose bigger runs to salvage it
metadata:
  type: feedback
---

When an experiment is borderline (e.g. v34 8–2 but rule not met), do NOT propose running more data / more K to
"prove" it. The user wants evidence that the direction is worth continuing: mechanism checks on existing outputs
(does the concept actually point at the bug? do wins use it?), cheap CPU metrics, a clear go/no-go.

**Why:** user (2026-10-20): "không nên cố chấp chạy thêm dataset để vớt vát chứng minh, thứ cần là tín hiệu rằng hướng
này có thể tiếp tục, chứ không phải là chạy nhiều hơn".
**How to apply:** after each result, first run a zero-cost mechanism analysis and state the signal plainly; propose
a new paid run only to test a changed hypothesis, never to enlarge n. Related: [[v34-ftplacebo]], [[working-rules]].
