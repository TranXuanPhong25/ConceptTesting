---
name: flow-diagrams-html
description: User wants flow explanations as HTML graphs instead of text diagrams; use the installed visualization skills
metadata:
  type: feedback
---

2026-11-07 (Codex): user explicitly asks to install Archify, Visual Explainer,
and Interactive Flow Diagram, then draw the current Boundary module. User adds:
"sau này t hỏi cái gì liên quan đến luồng thì dùng cái đấy mà vẽ, không output ra text nữa".

**Why:** the user prefers a visual graph for understanding execution and data flow.
**How to apply:** for later questions about flows, trace the actual source and
deliver a linked HTML graph using the relevant visualization skill. Keep the
scope the user requests (for example, only Boundary), and use a brief Vietnamese
handoff rather than a text/ASCII flow diagram. Preserve original code and run
artifacts; producing a diagram does not authorize new benchmark/model runs.

**Correction (user2026-11-07):** user rejected the first Archify and Graphify
outputs: stage/function names and dependency edges alone do not explain the
mechanism. Each stage must visibly explain its purpose, logic, actual input and
output, what the LLM decides/generates, and what parsing validates or rejects.
Use concrete examples (prefer saved real requests/responses) and explain data
transformations in the diagram/page itself. Source links and click-to-inspect
are supplementary, not a substitute for stage explanations. Do not describe
unobserved model reasoning as observed behavior.

**Target display (user2026-11-07):** user uses desktop and objected to spending
time on mobile layout. Prioritize desktop readability, useful stage descriptions
and mechanism coverage. Do not delay delivery for mobile polish unless requested.

All three skills are installed under `/home/phong/.codex/skills/`: `archify`,
`visual-explainer`, and `interactive-flow-diagram`. New skills are discoverable
from the next turn; their installed instructions can be read directly now.
The first source-backed Boundary graph is at
`.archify/workflow-boundary-module-20261107-192414/boundary-module.html`.
Its source candidate and Archify delivery/browser receipts live beside it.

User then explicitly requested an additional graph using Graphify. The existing
CLI is `/home/phong/.local/bin/graphify` (uv tool `graphifyy`); its skill is
`/home/phong/.claude/skills/graphify/SKILL.md`. The additional artifact is
`final/slides/boundary-graphify/graphify-out/graph.html`, with reproducible build,
render and browser-check scripts in its parent directory. It indexes only the
four active Boundary Python files, excludes legacy/precision, and uses code-only
AST extraction with zero model calls. It is a file/symbol relationship map,
not a complete conditional runtime flow. A MultiDiGraph preserves all54extracted
relationships across37nodes, including two same-endpoint parallel pairs.
Pinned vis-network is bundled into the HTML; offline browser search, inspection,
community filters and layout checks passed. Report, source hashes, raw diagnostic
and browser receipt are beside the graph. This is an additional option, not a
user instruction to replace Archify as the default.

After the rejection, the mechanism-focused replacement is
`final/slides/boundary-mechanism/bva-mechanism.html` (Visual Explainer). Prefer
this page when explaining current BVA. It includes visible actor responsibilities,
six input/operation/output steps, a real saved Qwen HumanEval/72 prompt/response,
the distinction between AST signature parsing and JSON response parsing, and
ten selectable decoder cases computed using the actual repo decoder. The real
request/decoder match the current module; source and saved-artifact hashes are in
`evidence.json`. No new model or PUT/reference execution was used. Renderer
visual checks pass at390pxand1280px. Original stage/name-only graphs remain
historical artifacts; do not present them again as sufficient mechanism explanations.
