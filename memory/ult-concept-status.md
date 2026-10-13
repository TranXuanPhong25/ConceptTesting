---
name: ult-concept-status
description: "ULT_concept (UnLeakedTestBench) ULT_Lite baseline done and committed; the C1–C8 prompt-tag probe was null and that arm is dropped (2026-10-10); execution-verified adequacy-gap arms proposed, awaiting go-ahead"
metadata:
  node_type: memory
  type: project
  originSessionId: 64491ec8-7dc6-4f3d-b072-c82d95874685
  modified: 2026-10-10T04:17:23.381Z
---

`ULT_concept/` runs UnLeakedTestBench (arXiv 2508.00408, authors' repo vendored unmodified as `vendor_ULT/`). The baseline is ULT_Lite (200 functions), using the authors' prompts and 5-round chat on gemini-3-flash-preview with thinking 0.

Baseline results:

| k | Pass | LCov | BCov | Mut |
|---|---|---|---|---|
| 1 | 77.0 | 50.3 | 39.0 | — |
| 5 | 77.9 | 80.7 | 75.2 | 60.7 (cosmic-ray, k=5 only) |

Generation cost about $0.8. Mutation scoring takes about 40 minutes per arm with 15 workers. Committed in 3932285.

Probe, 2026-10-10 (the user asked for it):
- Two blind Sonnet 5.5 agents (the `sonnet` alias; 4.6 can't be pinned) wrote 5 tests × 6 ULT_Lite functions. One prompt had the C1–C8 tags and one didn't.
- They wrote nearly the same tests: BCov@5 90.8 vs 90.3, Mut@5 79.2 vs 79.5.
- The tagged agent's self-report credited the tags for tests the blind agent also wrote, so self-report is unreliable.
- The user's verdict: prompt tags only reflect the code. ConceptCoder's concepts work through a supervised head at training time.
- **The C1–C8 arm is dropped. Don't propose it again.**
- Outputs are in `ULT_concept/out/probe_*`.

Harness facts:
- The authors' repo can't run as-is: `data_utils` is missing, paths are hard-coded, it is OpenAI-only, and nothing builds `_mods`.
- `ULT_Lite` `test_list` expected values are often wrong, so it is not an oracle.
- `from mod import *` skips `_private` functions.

Proposed next step, waiting for the user's go-ahead: the concept is the execution-verified unmet adequacy criteria of the previous rounds' tests, injected into the round-2..5 follow-up with a human-written recipe for each criterion. Criteria covered:
- branch true/false
- comparison boundary (==)
- loop 0 / 1 / many and loop run to completion
- input partitions
- the else/raise partition

Planned arms:
- `gap`
- `placebo`: the same template, with criteria sampled at random from the function's own criterion universe
- optional CoverUp-style `covfb`: uncovered lines only

K=5 fixes the number of tests per arm, so test count is not a confound. Compare arms with per-function paired statistics.

Demo, task 3357 `cigar_prefix_length`: after 5 baseline tests, every surviving mutant maps to an unmet criterion:
- `>=` → `>` (equality boundary never hit)
- the loop never runs to completion
- the invalid-op else branch is never taken

**How to apply:** add a hard USD cap and a call ledger to `ULT_concept/generate.py` before any new paid arm (see [[api-budget]]). This follows [[thesis-concept-requirement]].
