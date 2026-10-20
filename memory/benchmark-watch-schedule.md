---
name: benchmark-watch-schedule
description: Hourly local checks from 05:00 2026-10-15; resume abstract concepts after benchmark thread completes
metadata:
  type: project
---

User authorized on 2026-10-15: check “Chọn benchmark phân tích nguyên nhân” every hour from 05:00 Asia/Ho_Chi_Minh; once it finishes, continue the new abstract concept direction.

**How to apply:** the local user timer `concepttester-benchmark-watch.timer` queues checks into the existing LineFacts Codex thread. It uses a daily 05:00 calendar anchor plus `OnUnitActiveSec=1h`. Watcher/config live in `/home/phong/.local/share/concepttester/benchmark-watch/`; units in `/home/phong/.config/systemd/user/`. Machine and Codex app server must be running. Confirm latest turn is `completed`, read final results, then disable the timer and write the `started` marker before beginning implementation. An interrupted/error/input-waiting turn is not successful completion.

New work follows `trickcatcher_linefacts/DIRECTION_ABSTRACT_CONCEPTS.md` and `PLAN_ABSTRACT_CONCEPTS.md`: behavioral abstraction/FSM, semantic concepts and typed spec/model mutations, new folder, preregistration and CPU gates before experiments. This request authorizes continuing our proposed direction; it does not authorize paid API fallback or reproducing third-party paper code.

2026-10-15 05:00 check: watched turn is completed/idle, but final answer explicitly reports only 4/500 full-text audits and quota checkpoint with continuation pending. Root report confirms 4/500. Keep hourly checks; do not treat ending a turn as finishing the benchmark task. Next check 06:00. No new pipeline started.

2026-10-15 user override: “thôi, m làm luôn đi”. Disabled benchmark-watch timer and wrote started marker immediately; abstract concept implementation starts without waiting for the 500-paper audit. Do not resume hourly waiting. Other thread/timer preserved.
