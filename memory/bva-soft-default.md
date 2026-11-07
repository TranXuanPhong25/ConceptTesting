---
name: bva-soft-default
description: User chose soft BVA as the boundary default; typed selection/compiler/grounding moved under legacy
metadata:
  type: project
---

2026-11-07 user explicitly asks to make soft BVA the main BVA pipeline and put
deprecated/legacy implementations in a subfolder within the BVA module.

`--arms boundary` now means soft direct generation, one completion per allocated
PUT; exact diagnostic prompt/decoder behavior retained for20inputs. Main API
BoundarySettings/BoundaryValueAnalysis is soft. Typed selection, compiler/literal,
worksheet/context and checked grounding live under
final/src/modular/boundary_value_analysis/legacy/. Explicit legacy imports remain
for historical diagnostics/accounting. No default fallback or promotion of checked
grounding. Plain remains available as the existing control.

342modular/development tests pass; exact10saved-response request/decode parity
verified offline. No new model or benchmark cohort run. Historical results and
manifests preserved; frozen-input rescore distinguishes original protocols.
Multi-PUT budget splitting is implemented but diagnostic evidence only covers
one PUT/task. This user decision does not establish general superiority from
soft7/direct6 on the outcome-selected10task diagnostic.

Details: BVA module README, modular CHANGELOG/PREREG dated2026-11-07, and
final/review/boundary_soft_promotion_offline_2026-11-07.json. User authorizes a
BVA-only commit/push on2026-11-07. Current field names generated/target_programs
stay compatible; count clarity uses local variable names only.

User subsequently asks for a plan for concept-directed tool input construction.
Proposal only:final/review/boundary_soft_tool_plan_2026-11-07.md. PhaseA uses
saved seeds and bounded float-neighbor expansion, reporting pool ceiling and
fixed20input policy separately; requires stable new value-mismatch detection
without losing existing soft detections. PhaseB is conditional:direct seeds plus
optional bounded expansion requests, compared with generic expansion using the
same writer output. Recall v5selector/compiler failures and v47menu no-go.
No implementation, new model/native run, default change or commit in planning.

Subsequent "tiếp đi" authorizes execution. Both phases and the interface audit
are now complete; see [[bva-precision-tools]]. Phase A passes a construction gate,
Phase B fails its interface/direction gate; main soft remains unchanged. Do not
interpret earlier proposal-only status as current or launch duplicate trials.
