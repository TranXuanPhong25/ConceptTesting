---
name: subagents-sonnet-only
description: "User rule 2026-10-24 — every spawned subagent must use model sonnet (reviewers, helpers, writers); never Opus/default-inherit"
metadata:
  node_type: memory
  type: feedback
  originSessionId: bff6dd90-c044-4e71-bda0-a5213ecbb610
  modified: 2026-10-24T07:32:05.833Z
---

Always pass `model: "sonnet"` when spawning any subagent (Agent tool), including critique/review agents and
mechanical helpers (artifact updates, searches). Do not leave the model unset (it inherits Opus) and do not pick Opus
for "independent review". Codex reviews go through the codex agent as before.

**Why:** user, 2026-10-24: "subagent thì dùng sonnet thôi, lạy bố" — Opus subagents burn the Claude quota; the user had
already asked for Sonnet writers and was annoyed that a review and an artifact helper ran on Opus.
**How to apply:** check every Agent call has `model: sonnet`; earlier "nhờ một subagent opus" instructions are
superseded by this rule. Related: [[codex-quota-fallback]], [[working-rules]].
