---
name: codex-account-gateway
description: User requested a source-informed Codex gateway for routing/fallback across ChatGPT accounts; isolated package and setup guide
metadata:
  type: project
---

User request (2026-10-26): implement a Codex gateway from Codex source to route/fallback between multiple ChatGPT accounts.

Implementation and setup: [standalone gateway README](/home/phong/dev/codex_gateway/README.md). User explicitly moved the project out of ConceptTester to `/home/phong/dev/codex_gateway` on 2026-10-26. Source provenance is pinned there; the upstream Codex checkout was inspected under `/tmp`, with no upstream source modifications. Gateway has isolated login/import, Responses SSE/JSON, session/model routing, bounded fallback, quota reset cooldown, atomic OAuth refresh and local token auth.

2026-10-26 follow-up: user requested a web GUI to track each account's remaining quota. The standalone gateway now serves its dashboard at `/`, with browser login using the existing gateway token, per-window remaining percentages/reset times, separate model buckets, manual refresh, background usage polling (60 seconds by default), and routing activity. UI status updates every 5 seconds. Implementation verification: 65 local tests passed, desktop/mobile Chrome browser checks passed, and the wheel includes static assets. Test snapshots use fake credentials and a local upstream; real ChatGPT quota fetches remain unverified. Start/restart the normal `serve` command to use the GUI. No hosted deployment was requested or performed.

2026-10-26 startup fix: user reported connection refused because no server was listening. Started the normal gateway detached on loopback port 8787; verified GUI, health and authenticated dashboard HTTP 200. Both configured accounts (`personal`, `work`) then returned real quota snapshots with no refresh error; this supersedes the earlier quota-fetch verification limit (live inference remains untested). Runtime PID/log markers are in the project's ignored `.artifacts/` directory; check current process state instead of assuming it remains running. A local gateway token is stored outside the project at `~/.local/share/codex-gateway/gateway.token` with mode 0600. Use it for browser login and export it as `CODEX_GATEWAY_TOKEN` when starting a client or restarting the gateway. Never put its value in tracked files or logs.

2026-10-28 inference fix: user hit HTTP 502 `invalid upstream response`. A minimal request reproduced it; direct upstream returned valid SSE with HTTP 200 and no Content-Type header. Gateway now follows the forced `stream=true` Responses protocol instead of deciding from MIME headers. Added regression tests for missing/misleading Content-Type, incremental delivery, early quota fallback and interrupted-stream non-replay: 69 tests + 4 subtests pass. Restarted the existing local gateway after checking no requests were active; health/status HTTP 200. Live `gpt-6-astra` checks passed on both configured accounts (personal SSE completed, work JSON completed); actual Codex CLI using an isolated home also completed a shell-tool round trip and returned the expected final answer. This supersedes the previous live-inference verification limit. See the standalone README's 502 troubleshooting section. No commit/push requested.

**Why:** user wants one gateway endpoint for several ChatGPT logins.

**How to apply:** use isolated `CODEX_HOME` per account via the gateway CLI, configure account auth paths and a local token from environment, and use the documented Codex custom provider. Preserve the original credential files when importing. Imported copies share a refresh grant with the original, so prefer separate login. Engineering tests use fake credentials/local HTTP servers; live quota and inference verification are recorded above. No account credentials were read/imported from the user's active Codex installation. No commit/push was requested for this standalone task.
