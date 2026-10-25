---
name: v66-symbolicpath
description: v57 path constructor completed with CrossHair backend; six-case CPU diagnostic PASS 5/6 (84/268 hyp verified, 0 replay rejects); no model/efficacy run
metadata:
  type: project
---

2026-10-25 (Claude, continuing Codex session codex-session-v57.md "hoàn thiện tiếp v57"). Folder created by Codex as
v64_symbolicpath, renumbered v65 then v66 (v64 = Haiku plain-oracle, v65 = other session's evidencegate).
[pipelines/v66_symbolicpath](../trickcatcher_linefacts/pipelines/v66_symbolicpath/RESULTS_V66.md).

Replaced v57's own Z3 interpreter with unchanged CrossHair 0.0.112 explore_paths (venv /tmp/concepttester-v64-venv,
requirements-symbolicpath.txt). Same objective: exact-site reach + first local difference with equal pre-state/branch
prefix + output difference; every witness realized and replayed in 2 separate unshare -rn CPython processes.
Store-subscript index sites, annotation sites excluded from catalog. 12 tests; Sonnet review PASS-with-fixes (Amendment 1);
run 1 crashed on CrossHair shell dicts in JSON (Amendment 2, NoTracing fix).

Run 2 (PREREG_V66 frozen before outcomes): verified hyp 61 20/48, 66 20/48, 124 21/48, 58 0/48, 131 20/48, 85 3/28 →
PASS 5/6; 0 native replay rejections. 54% of hypotheses hit path/time cap. Many witnesses at domain edges ('', [], negatives).

**Why:** v57 had 0/6 verified inputs (unsupported constructs); user wanted v57 completed, not replaced by LLM predicates (v61–v63).
**How to apply:** engineering readiness only — no concept efficacy, no bug labels, spec validity unknown. Next step needs its
own PREREG: verified evidence into v57 prompt controls + spec-validity filter + matched v31 comparison. Related:
[[v57-pathfault]], [[pathfault-completion-plan]], [[v63-scopeguard]].
