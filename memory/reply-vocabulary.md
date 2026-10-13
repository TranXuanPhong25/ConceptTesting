---
name: reply-vocabulary
description: "Reply in Vietnamese sentences, but every technical term stays in English (task, input, hint, oracle, false alarm, run, sample...), B1–B2 level"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 08a7596f-fd39-47c8-b7c7-c0ed6ea6f8c3
  modified: 2026-10-12T16:36:13.918Z
---

Write the sentences in plain Vietnamese, but keep every technical term in English instead of translating it:
spec, task, input, output, expected output, hint/fact/concept, test, base test, plus test, run, sample, arm, oracle,
false alarm, bug, PUT, round 1/round 2, prompt, baseline, property-result, invalid input, sign test, per-task win/loss.
Do NOT use Vietnamese calques such as "đề", "bài", "gợi ý", "đầu vào", "kết quả đúng", "lần chạy", "báo nhầm",
"tính chất kết quả". Keep English at B1–B2 (no fancy words).

**Why:** user (2026-10-12) first complained about calques ("dùng mẹ property-result đi, thay vì là đề thì m nói là
spec"), then after a mostly-Vietnamese status reply said: "trả lời tiếng việt đi, thuật ngữ thì dùng tiếng anh".

**How to apply:** every reply to this user, including tables and headers; also new terms get a one-line Vietnamese
explanation the first time. Related: [[course-vocabulary]].
