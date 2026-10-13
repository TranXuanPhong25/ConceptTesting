---
name: api-budget
description: "As of 2026-10-09 the user has only ~$25 of API (Vertex) budget left — every paid run must fit, with a hard cap in code"
metadata:
  node_type: memory
  type: project
  originSessionId: c7ea6648-d230-4c4d-8eab-acba360b8de8
  modified: 2026-10-08T17:27:12.892Z
---

As of 2026-10-09 the user has about $25 of Vertex budget left. This replaces the earlier "Vertex spend is fine" note in HANDOFF.md.

Where the money has gone and what remains:
- CoverUp_concept main seed 1 cost $14.49, and the site-hint smoke $2.30.
- CoSIL_concept swebench_live has spent $12.79 but finished only 28-40 of 225 issues per arm. Finishing it would cost about $70 or more.
- JitVul has finished the base, concept and placebo arms. The callee_code and ide arms are about half done.

**Why:** the remaining money has to cover the main thesis line ([[test-aware-mutants-candidate]]).

**How to apply:**
- Before any paid run, give a cost estimate.
- Enforce a hard USD cap in the harness (about $20, keeping $5 in reserve) and log every call to a ledger.
- Prefer zero-cost reuse, such as the Zenodo mutants instead of regenerating them.
- For test generation, prefer Gemini 2.5 Flash with thinking set to 0 ($0.30 / $2.50 per 1M tokens). Gemini 3 Flash costs $0.50 / $3.00 and thinks about 2k tokens per call even at "low"; a full HumanEval AGENT1-TA run with it costs about $3.
- Don't resume CoSIL, the rest of JitVul, or CoverUp seeds 2-3 unless the user explicitly asks.
