---
name: workflow-burr-trial
description: User rejected Burr and explicitly requested deleting the entire isolated trial; retain current pipeline
metadata:
  type: project
---

2026-11-05 user explicitly says to drop Burr and delete it. Removed the entire
untracked final/workflow_burr folder, including trial code, local .deps package,
tests, SQLite checkpoints and synthetic outputs. No production code was changed.

The completed engineering trial had21passing tests but no meaningful code-size
reduction (272physical lines versus270for the current orchestrator). User chose
the existing pipeline. Do not restore or migrate to Burr without a new request.

**Why:** user rejects the trial after seeing no meaningful simplification.
**How to apply:** keep current pipeline; the Burr folder no longer exists.
