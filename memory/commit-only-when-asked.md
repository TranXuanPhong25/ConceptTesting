---
name: commit-only-when-asked
description: "trickcatcher_linefacts: commit+push my own files after each new finding (standing permission since 2026-10-13); elsewhere only when asked"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 7ff5ccb6-c822-4e0c-85b2-728de325d857
  modified: 2026-10-12T17:31:20.324Z
---

For the trickcatcher_linefacts work, the user gave standing permission on 2026-10-13: "mỗi khi phát hiện mới thì commit lên"
(commit whenever there is a new finding). After each new result/finding (RESULTS/PREREG entry, new version, analysis),
commit and push to main the files I created or changed for it. Never stage files I did not touch (e.g. other sessions'
research/mutgen, research/savior). Follow AGENTS.md rule 1: no AI attribution lines, push straight to main.

**Why:** earlier (2026-10-10) I committed on my own and the user objected ("ai cho m commit?"); on 2026-10-13 they
explicitly asked for commits after every finding.

**How to apply:** in trickcatcher_linefacts, commit+push per finding without asking. In other folders/projects, still
only when asked. out/ is gitignored, so anything that must be kept (analysis scripts, small label files) goes to a
tracked folder. Related: [[pipeline-folder-workflow]].
