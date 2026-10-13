---
name: codex-quota-fallback
description: "When Codex's 5-hour quota is exhausted, switch implementation to my own subagents; if the reset is near, schedule the Codex task instead"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 2dddac78-7845-4887-9c28-b6313bcf7c52
  modified: 2026-10-11T16:46:50.947Z
---

Implementation normally goes to Codex (codex:codex-rescue). If Codex's **5-hour** limit is used up while the weekly
limit still has room, do not stall: temporarily hand the implementation to my own subagent (Agent tool, general-purpose
or fork) with the same spec, then continue. If the 5-hour window resets soon (rule of thumb: within ~30 min), schedule
the Codex task for the reset time (CronCreate one-shot) instead of switching. If the weekly limit is exhausted too,
use my subagents.

How to check quota: the latest `~/.codex/sessions/YYYY/MM/DD/*.jsonl` contains `"rate_limits":{... "primary":
{"used_percent", "window_minutes":300, "resets_at":<epoch>}, "secondary": {... "window_minutes":10080 ...}}`;
convert with `date -d @<epoch>`.

**Why:** user instruction 2026-10-11 ("nếu codex hết giới hạn 5h (còn tuần) thì tạm thời switch sang subagent của m
để làm tiếp, nếu sắp hồi quota codex thì schedule để chạy"); Codex hit 87% of the 5-hour window that night.

**How to apply:** check the quota before delegating a sizeable build to Codex; pick Codex / my subagent / scheduled
Codex by the rule above, and tell the user which one was used.
