---
name: v64-haiku-plainoracle
description: 2026-10-25 Haiku plain-impl oracle 25/33 (prec .96, FA 19) vs defn = brute 21 (1.00, 0 FA); paired 4–0 for plain → v49 family effect reverses with stronger writer; registered "inconclusive"
metadata:
  type: project
---

2026-10-25 (Claude). User asked to check on dev before amending v56 whether the v49 oracle-family effect
(defn/brute 10–12 vs plain-impl 5, Qwen-32B) holds with a stronger writer. `analysis/v64_haiku_plainoracle/`
(copy of v55h; defn/open/plain answers reused from v55h; 18 Haiku subagents for brute + plainimpl, k=3).

Result: plainimpl 25/33 prec .96 FA 19 (4 tasks, 3 problems, all wrong value); defn 21 = brute 21, prec 1.00, 0 FA.
Paired defn vs plainimpl 0–4 (61/65/66 one problem, 141): defn programs abstain on every exposing input (brute force
too slow). Registered decision "inconclusive" (net −4, precision gap .037 > .02). Headings = nothing (defn = brute).

**Why:** v49 gap was weak-writer plain-impl yield (38/165 valid); with Haiku plain programs are valid and fast.
**How to apply:** do not claim "definitional oracle family is better" — it is a precision (brute) vs abstention
(plain) trade-off that flips with writer strength; do not spend v56 confirming it as stated. Related:
[[v48-v49-e2e-defn]], [[v55h-haiku-interpretation]], [[concept-effect-synthesis]], [[v56-lcb-fresh]].
Haiku subagent gotchas: stray/temp files, wrong-id writes then overwrite, a missing closing fence → audit
transcripts (tool names + paths) and entrypoints before scoring.
