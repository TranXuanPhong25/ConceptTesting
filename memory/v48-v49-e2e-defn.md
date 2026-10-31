---
name: v48-v49-e2e-defn
description: v48 NO-GO 2026-10-23 (every arm ≈6/33 tasks; oracle binds: common-mode 9, no valid variant 7, reach 7); v49 concept NO-GO (defn 12 vs brute 10, paired identical) but family effect (brute-force spec programs ≈0.6 precision, common-mode 3–5% vs tc 28%); rules → R7
metadata:
  type: project
---

(Claude, session started 2026-10-22 22:50) User: read `codex-session-v7-46.md`, find what Codex missed, confirm with
Codex, build the complete pipeline, plan + run the next direction autonomously (stop if Claude quota < 10% or Codex
< 15%).

- Review `trickcatcher_linefacts/analysis/v7_v47_audit_review_claude_20261022.md`: R1 selection prior art under-cited
  (v7_mutref/v18/v35/v36/v41/v42), R2 "perfect 20 vs random 10.1" = max-vs-mean ceiling, R3 metric ignores oracle/FA,
  R4 TC-full wins at matched budget (v11 29.75 vs 42.99, 2/25), R5 v47 gate ignores its own controls, R6–R9 v46/v47.
  Codex verified: R3/R5/R6/R7 agree, rest partly. v47 then finished: LLM picks 16 vs random3 18.25 → no-go (as predicted).
- **v48** `analysis/v48_e2e_oracle/` (PREREG + amendment 1, Codex code, 44 tests): v47 picks → v46 `tc` programs as
  oracle → assertions (cap 20) with random3/kind/menu/pool-matched/heuristic/all-menu controls + failure decomposition.
  Score blocked until v46 `tc` programs complete (owner session concepttester-ca).
- **v49** `analysis/v49_defn_oracle/` (PREREG + amendment 1 after Opus review): `defn` (ENUMERATE/CHECK/AGGREGATE concept
  + brute force) vs `brute` (concept control) vs `plain` vs `tc`; 495 Qwen32B calls running detached (PID file in my
  scratchpad, 1 worker). Primary: defn ≥ brute + 3 on ≥ 3 distinct problems, FA ≤. Based on ALGO (NeurIPS'23).
- Endpoint gotcha: the Kaggle vLLM serves **one request at a time** (~10 tok/s); multi-worker clients livelocked
  v46/v47 (timeouts abort server work). Always 1 worker + 3600 s timeout. Claude quota cannot be read without editing
  the statusline (classifier blocks self-modification); Codex quota from ~/.codex/sessions rate_limits.

- 2026-10-23 00:30: v48 Amendment 2 + v49 Amendment 2 (Opus code reviews applied; 101 tests). Both wait only for
  generation: v46 tc ~10 programs/h (32/310), v49 ~12/h (19/495) on the serial endpoint → ~1–2 days. Then run
  `e2e.py execute; score` and `oracle.py execute; score` (v49 execute after v48 code frozen — it is). Task-3 smoke:
  tc 9 valid variants emit 0 tests (common-mode), plain 0 valid, defn/brute 380 tests (unscored).
  Speed-up needs the user: vLLM `--max-num-seqs` > 1 in the Kaggle notebook (KV cache only ~10% used).

- 2026-10-23 07:26: ngrok tunnel offline (ERR_NGROK_3200, Kaggle session ended?) → v49 gen exited (357 failed calls,
  not cached; 138/495 programs kept), v46 tc 90/310. A detached watcher in my scratchpad polls `/models` every 5 min
  (48 h) and relaunches the gen the same way. Earlier (04:27–05:27) a silently dropped request stalled the client for
  the full 3600 s timeout. Redact logs with the bare-host pattern `s#[a-z0-9.-]+ngrok[a-z.-]*#<url>#g` (errors print the host without https://).
- 2026-10-23 08:10: user closed the session; replaced the watcher with a detached orchestrator
  `~/.local/state/concepttester_v48v49/v48_v49_orchestrate.sh` (moved there 08:26 from the expiring scratchpad; env file chmod 600 there too) (PID in `orchestrate.pid`, log `orchestrate.log`, 7 days): relaunches
  v49 gen when endpoint is back; runs v48 execute+score when v46 tc 310/310; then v49 execute+score (logs
  `v48_*.log`, `v49_*.log`, markers `v48.done`/`v49.done`). It writes no RESULTS and no commits: on resume read the
  logs + score JSONs, write RESULTS (v48 decomposition, v49 manual concept audit of defn-only wins), commit own files.
  v46 tc gen belongs to session concepttester-ca: do not relaunch it.
- 2026-10-23 08:51: endpoint back, v49 gen relaunched by the orchestrator. v46 tc stuck at 90/310 (tc_concept 86): owner
  session concepttester-ca is gone and no v46 process runs; my attempt to relaunch it was denied by the auto-mode
  classifier (Interfere With Workloads) → 09:17 user allowed it. Another Claude session (`--resume 28d298da…`) had already relaunched v46 at ~08:57, so the
  duplicate launch was stopped; the orchestrator now relaunches v46 only when no v46 generate process runs at all.
- 2026-10-23 12:00: `analysis/v49_defn_oracle/PLAN_NEXT_v50.md` fixes the next-branch rules before any output
  (R1 GO→v50-H held-out; R3 <17 defn-eligible tasks or ≥50% wrong-value tests→stop Qwen program oracle, ask user;
  R2 ≥50% exposing inputs with no finishing defn→v50-S shrink-then-judge (Hypothesis shrinker + brute force);
  R5 ≥50% FA invalid_input→v50-V validator concept (AutoCode best-of-3); R4 ≥50% common-mode→report+critique).
  `plan_rules.py` computes them; orchestrator v2 (`v48_v49_orchestrate_v2.sh`) runs it after v49 score (commit e8ee4ef).
- 2026-10-23 19:45: Opus review of plan_rules → Revision 1 (commit b1f8f43): per-task v48 decomposition on the whole
  decisive universe, R1 gated on manual audit, R1b near-GO-FA, R6 family effect, R3 on valid/resolved tests, R5 defn-only,
  guard vs score.json. v50-V overlaps B5/F1b + F4/F4b (RESULTS §11.3). 19:18 ngrok blip killed both gens; orchestrator
  v3 relaunches v46 only after 3 absent ticks (owner session 28d298da relaunches its own; avoid duplicate clients).
- **2026-10-23 22:06 v48 RESULT: NO-GO.** llm_code 6 confirmed tasks vs random3 6.37, menu 6.38, pool 5.87, kind 6.22,
  heuristic 6; FA 152 vs 146.37; same 6 tasks (36,61,121,131,132,164) for every arm. Primary failures: common-mode 9,
  no valid variant 7, no exposing input 7, lost to cap 3, vote wrong 1. FA: put_right 55%, invalid 38%. Commit a6d6b38.
- **2026-10-23 23:15 v49 RESULT:** defn 12 / brute 10 / plain 5 / tc 1 (quorum; tc native rule 7, prec .23, FA 221)
  confirmed tasks; primary NO-GO (margin 2 on 2 problems, FA 145>100; paired on both-eligible tasks 10 vs 10). Concept
  only raises valid-program yield (93 vs 78; 23 vs 18 eligible tasks). Audit 103/124 pass. plan_rules → R7 (8 tasks no
  exposing input). Gap: R6 needs GO incl. absolute FA, so the family effect (report-only) did not route. Commit 4168ad0.
- 2026-10-24 v52 pilot (user asked: Sonnet subagents, does concept help?): 6 Qwen-failure tasks, k=3, v49 prompts/scoring.
  Sonnet defn 5/6, brute 4/6, Qwen 1/0. All Sonnet FA = invalid inputs (oracle correct on valid inputs); misses =
  abstention (brute too slow). Concept win only task 65 (enumerates statement objects vs 26^n). `analysis/v52_sonnet_defn`.
- 2026-10-24 v53 $0 diagnostics (`analysis/v53_validity_smallscope/DIAGNOSTICS.md`, f50a116): all 56 Sonnet FA are
  caught by spec Constraints (20 numeric bounds, 36 relational: equal lengths, k < len, same digit count), 0 confirmed
  removed; exposing inputs of size ≤ 10 exist on 21/23 reachable tasks (not 141, 56). Concept tokens: defn +45% output
  vs brute (comments), no saving. Next: PREREG v53 = validity concept (relational predicates) + small-scope generation.
- 2026-10-24 v53 Stage 1 (dev, 72 Sonnet subagents): validity checks from the statement — concept = lines = open =
  recall 1.000 (12842/12842), 0 valid/exposing rejected; numeric tool 0.144. Concept not promising (ceiling). Any LLM
  filter makes Sonnet defn FA 56→0. Remaining lever: reach/abstention → Stage 2 small-scope (concept = what to enumerate).

**Why:** concept selection is repeatedly ≈ random; the oracle (common-mode variants, FA) is the bottleneck.
**How to apply:** read both PREREGs before scoring; do not reopen input selection; next branch follows v48's
decomposition. Related: [[v47-concept-select]], [[v42-v45-mutoracle]], [[signal-not-more-data]], [[check-version-tree-before-proposing]].
- 2026-10-23 19:35 (Claude session 60644928): user gave a second, separate Qwen32B endpoint (endpoint B, URL only in
  `~/.local/state/concepttester_v48v49/qwen32_env_b.sh`, chmod 600). v49 gen moved there (killed + relaunched the same
  command, 1 worker, cache resumes, pid in `v49_gen.pid`); endpoint A now serves only v46 → v46 `tc` (v48 blocker)
  no longer queues behind v49. If v49 gen dies the orchestrator relaunches it on endpoint A (its own env), which is fine.
