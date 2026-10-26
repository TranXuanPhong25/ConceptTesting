---
name: v79-deepseekdiagnosis
description: DeepSeek four-call v72 replay stopped on first Relace upstream429;0responses,1unknowncharge,no retry
metadata:
  type: project
---

2026-10-26 (Codex): user cancelled Qwen27B endpoint diagnostic before completion
and authorized DeepSeek instead. Isolated v79 from v73, exact four frozen v72
messages on85/124, raw_known/full_known; Relace/fp4 only, reasoning enabled,
131072total output cap, no unsupported seed, $0.15 overallcap. Independent
Codex review, two must-fixes before freeze,19 targeted tests pass.

Terminal first85/raw_known request HTTP429, Relace upstream_provider_shared_pool:
zero modelresponses/semanticresults, three unattempted, one unknown-cost attempt,
reservation retained, no automatic retry/provider fallback. Actual bill unknown,
not zero. Source/output/priorv72 freeze verified; no native/private/modeljudge.
See [report](../trickcatcher_linefacts/analysis/v79_deepseekdiagnosis/RESULTS.md)
and terminal_audit.json. No v77 or Qwen generation launched.

**Why:** short model-capability diagnostic requested, not another full pipeline.
**How to apply:** provider availability failure is not reasoning/concept failure;
preserve unknown reservation and original terminal artifacts for any later retry.

Same-day user says continue: fresh retry under amendment B subtracts original
reservation, cap$0.12550714. First retry request again upstream429. Cumulative
2attempts/0responses/2unknowncharges, reservation$0.04898572, no further calls.
Independent read-only review confirms both freezes/exact prompts/source snapshots
and cumulative accounting. Actual charge remains unknown, not the reservation.
