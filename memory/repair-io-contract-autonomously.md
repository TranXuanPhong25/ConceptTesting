---
name: repair-io-contract-autonomously
description: User requires agents to fix input/output contract failures autonomously and rerun, not report them as the result
metadata:
  type: feedback
---

User2026-11-08: "lần sau mà còn bị lỗi in/output contract thì tự fix,
cấm báo cáo lại cho t".

**Why:** reporting zero yield caused by serialization/schema/prompt-adapter
failures wastes the user's time and does not evaluate the research method.

**How to apply:** fix routine input/output contracts autonomously, verify native
admission and rerun authorized work before reporting the actual result. Preserve
old artifacts; record technical failures/amendments internally, without presenting
contract failures as a terminal research finding or repeatedly asking permission.
Do not silently weaken semantic checks, fabricate results, erase histories,
retry usage-unknown requests indefinitely or spend on unauthorized backends.
Report meaningful results/remaining substantive blockers honestly.
