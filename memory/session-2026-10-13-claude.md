---
name: session-2026-10-13-claude
description: Digest of the long Claude session 2026-10-12..14 (ID 08a7596f): user requests, decisions, lessons, results, what is still open
metadata:
  type: project
---

Raw transcript (very large JSONL, read only with grep/jq, never whole):
`~/.claude/projects/-home-phong-dev-ConceptTester/08a7596f-fd39-47c8-b7c7-c0ed6ea6f8c3.jsonl`. Per-step notes:
repo-root `CONTEXT.md` (updates 2026-10-13 01:45 … 22:10). Results/decisions themselves are in RESULTS.md §11.23–11.40
and PREREG.md; this file keeps what is NOT there: the user's intent, decisions and lessons. See [[research-state]].

**User requests and decisions, in order (Vietnamese quotes kept):**
- MBPP+ held-out: Haiku wrote blind PUTs; only 12 have real bugs → "thử trên 12 cái đấy" (§11.32, no concept gain).
- "pipeline tốt nhất … win được tool-input chưa" → no: v7 concept-hybrid 67.0 was inflated by free plain calls in round 2.
  "chọn 2 input, rồi Qwen viết expected output … thật hả" exposed that round 2 kept only ~2 inputs and let Qwen add
  tests → "sửa đi cho công bằng" → v8-strict (round 2 = only tool-verified inputs). Oracle work counts as on target
  (better oracle → more detected bugs).
- Concept weakness written to CONCEPT_WEAKNESS.md, re-ranked after the user's SAVIOR and VibePass inputs.
- "nếu thay mà không đổi kết quả thì càng tốt, t đỡ bị vặn" → prefer standard libraries ([[prefer-standard-libraries]]).
- "mỗi khi phát hiện mới thì commit lên … gom best pipeline vào 1 folder … thử gì mới thì copy … folder mới"
  ([[pipeline-folder-workflow]], [[commit-only-when-asked]]); 2026-10-13 late: "mỗi bản folder mới phải có changeLog",
  big changes wait for Codex, small ones I do at once.
- Kaggle pip error pasted as context; I "fixed" the notebook → "fuck you, i do not need you fix that notebook"
  → reverted, never touch it ([[dont-fix-unasked]]).
- Endpoint ping every 20 min so the notebook does not idle-kill; "cho mấy task về chạy background để t end session"
  → detached runs (setsid + pidfile).
- Advisor report: "đừng nói bản gì ra, lấy bản tốt nhất, tập trung vào concept"; format "hướng làm, kết quả, phân tích,
  hướng tiếp theo".
- Baselines: compare with SymPrompt, MuTAP, Meta ACH, CoverUp + VibePass held-out (approved reimplementation of SymPrompt
  and ACH). "codex bị limit rồi kìa, m tự implement đi" → my subagents.
- User-pasted critique of 6 fairness problems → verified true → "đồng ý" → final comparison protocol (PREREG, end).
- User's research notes (2026-10-13 night), to keep as direction: consider covered nodes too; allow fault hypotheses
  without a witness; ablation generic review → flat concepts → typed relations at equal budget, always vs
  witness/toolinput; score witness-only separately vs witness + LLM tests; defensible claim = grounded facts with
  witnesses, not yet "LLM reading concepts beats plain"; missing piece = linking facts into spec-violation hypotheses
  ("value from line A through branch B to line C violates rule R"); "chỉ ra dòng chưa được exercise chưa phải xác định
  dòng có bug".
- 2026-10-14: "mọi knowledge … chuyển giao cho codex … cần một mem chung" → this shared `memory/` folder.

**Lessons (mistakes not to repeat):**
- Manifests pin the PREREG hash → editing PREREG.md while a run is active breaks resumes; use a PREREG_PENDING.md and
  merge later, or fresh output dirs.
- `pkill -f <pattern>` killed my own relaunch; `$!` after setsid is the wrong PID → `echo $$ > pidfile; exec ...`.
- B4 judge in oracle-score needs `--online`; an offline run fails on cache miss.
- Long scoring: per-task sandbox timeout 600 s too short for some tasks (3600 s wrapper); huge inputs → MemoryError guard.
- Codex may delete committed `.pyc` files in vendor clones; check `git status` inside vendor/ and restore.
- Different venvs: baselines tests need `CoverUp_concept/.venv` (httpx); the v4 venv lacks httpx.
- Prefix truncation biases matched-count comparisons (round-2 inputs come last); use random subsets.

**Open at end of session (2026-10-14 ~00:20):**
- 2026-10-14 00:21: dev sanity run registered (PREREG) and launched detached: `trickcatcher_linefacts/out/runlogs_v11/chain_from_arms.sh`
  (PID file ~/.claude/jobs/08a7596f/tmp/v11_chain.pid; waits until the endpoint answers 200, then v11_fair arms ->
  evaluate -> oracle -> 4 baselines gen -> scoring via analysis/score_run_v11.py). Progress: runlogs_v11/steps.txt.
  Amendment 1 (00:45): oracle = ref only (no b1/post/judge; user: improving inputs, not outputs). Relaunched 00:33,
  endpoint up. Keepalive (1-token chat every 10 min) runs separately: runlogs_v11/keepalive.sh, PID in
  ~/.claude/jobs/08a7596f/tmp/keepalive.pid — the notebook idle-died at 00:20 because no ping ran between runs.
  v11_fair pins only its own folder PREREG snapshot, so repo PREREG.md may be appended. tc_full_v2 ref scoring by hand.
- Not run yet: v11_fair "check c" (fresh full CPU execution); tc_full_v2 ref/full rescoring on dev.
- Diagram updated to v14 on 2026-10-14 01:00 (mutref, witness-only, random subset, v11_fair, tc_full_v2, 4 baselines, VibePass/v7_vp). Source: out/diagram/conceptester-v4.html (copy of the live artifact without the publish skeleton).
- `memory/` and AGENTS.md rule 6 not committed (outside trickcatcher_linefacts; ask the user).
- Untracked files of other sessions (do not stage): AUDIT_CONCEPT_RELATIONS_2026-10-13.md, analysis/audit_20261013.*,
  diagrams/*, PIPELINES.md edit, research/mutgen, research/savior, pipelines/v12_outcome_audit/.
