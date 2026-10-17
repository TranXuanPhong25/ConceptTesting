---
name: research-state
description: Hub for the thesis direction (concept-guided LLM test generation, TrickCatcher setting): where everything lives, current status, next steps
metadata:
  type: project
---

**Thesis:** LLM test-case generation guided by **concepts** (must stay central, see [[thesis-concept-requirement]]).
Setting = TrickCatcher EvalPlus: LLM-written PUTs pass the HumanEval base tests but are buggy; the generator gets
spec (docstring) + PUT code + base tests and must write assertions that reveal the bug. Model: Qwen2.5-Coder-7B-Instruct
(fp16, vLLM 0.7.3) served from the user's Kaggle notebook through ngrok (see [[working-rules]] for how to use it).

**Where things live (all under `trickcatcher_linefacts/`):**
- `RESULTS.md`: every result, numbered sections (§11.x is the latest work; §11.37–11.40 on 2026-10-14).
- `PREREG.md`: append-only registrations, amendments and decisions; the "Final comparison protocol" (six fairness
  fixes) is at the end. Register before running; never edit old entries.
- `CONCEPT_WEAKNESS.md`: why concepts are weak (3-layer loss analysis), ranked plan; section 4 = current fix plan
  (S1–S5 small, B1–B5 large) with progress notes.
- `PLAN_BASELINES.md`: baselines (CoverUp, MuTAP, SymPrompt, ACH, TrickCatcher-full) and held-out (VibePass, MBPP+).
- `pipelines/<version>/`: self-contained pipeline copies, each with `CHANGELOG.md`; `pipelines/README.md` lists stages.
  Best = `v7` (+ v8-strict construction). `v11_fair` = v7 + fairness fixes (not yet run on GPU). Dropped: v9_callfb,
  v10_spechint, v7_mutref (as main rule). `v7_vp` = v7 working inside class methods (VibePass).
- `baselines/`: symprompt, ach (reimplementations, approved), coverup, mutap (adapters), tc_full_v2 (TrickCatcher-full,
  repr serialisation). `heldout/`: MBPP+ and VibePass builders. `analysis/`: analysis scripts and outputs.
- `out/`: runs (`out/gen2_qwen7b_v7hyb_v4_r2` + `out/oracle_v7hyb` = v7 run of record; `out/gen2_qwen7b_v8strict_est`).
- Repo root `CONTEXT.md`: older checkpoint notes (2026-10-11..13) with run commands; `HANDOFF.md`: 2026-10-07 state
  of the other (earlier) projects.
- Diagram (private claude.ai artifact, Claude can update): https://claude.ai/artifact/7a6yvf5bhiVmZVyt9UvTC8
  ([[version-tree-diagram]]).

**Method (v7, best):** tool computes concept facts (code facts: MUTANT/STMT/OUTCOME/BOUND/REL/DU…, mined input validity,
spec input-class facts) → picks 3 hints with fuzz witnesses → arms (plain, concept, toolinput, gen-plain, concept-hybrid,
placebo-hybrid, plain-hybrid; K = 3) → round 2 = Hypothesis strategy per missed hint (strict: only tool-verified inputs)
→ oracle ref (10 spec-only DPP programs, unanimous) / full (+ judge + postconditions) → per-task sign tests.

**Key results (dev, 113 HumanEval tasks; numbers = bugs found per run under ref):**
- v8-strict: concept-hybrid 61.0 vs plain-hybrid 55.7 (per task 29/20 n.s.); vs placebo-hybrid 33/13; toolinput ≈ 64.
- Random-subset matched count (§11.38): concept-hybrid vs toolinput 54.2 vs 62.5 (26/40, p=.11); vs plain-hybrid 43/26
  (p=.053); vs placebo 42/23 (p=.025).
- Witness-only, no LLM (§11.37): 43.0 with 1.4 calls; toolinput 64.7 → ~2/3 of toolinput's bugs are already in the
  fuzz witnesses. Witness-only is now a mandatory baseline.
- Rank-2 hint selection (mutref, §11.39): no gain on odd tasks (13/10 vs old rule). Rank-5 BEHAV (§11.35), v9 concrete
  calls + feedback (§11.36), CrossHair (§11.33) gave nothing. MBPP+ real-12: no concept advantage (§11.32).
- Main loss = fault-hypothesis gap (VibePass metrics §11.28): Qwen follows hints poorly; round 2 is where hints help.

- v11_fair dev sanity (§11.41, real strict, matched placebo): concept-hybrid 61.0, toolinput 64.3, placebo-hybrid 57.7
  (was 45.7 with fewer round-2 requests), plain-hybrid 55.7; concept vs placebo only 26/22 → most of the old "beats
  placebo" came from the extra round-2 requests, not hint content.

**Defensible claim now:** the tool yields grounded facts with witnesses and they help generation (beat placebo and
paper baselines); NOT yet shown that an LLM reading concepts beats plain/toolinput under fair conditions.

**Next steps (CONCEPT_WEAKNESS.md §4):**
1. GPU: run `pipelines/v11_fair` + CoverUp/MuTAP/SymPrompt/ACH/tc_full_v2 on dev (sanity), then held-out once
   (VibePass 66 PUTs via v7_vp code, MBPP+ 12) with the frozen config — awaiting the user's go-ahead.
2. B3 `v12_rel`: ablation generic review → flat concepts → concepts with typed relations, equal calls/tokens/budget,
   always with witness-only and toolinput. B4 `v13_hyp`: link facts into spec-violation hypotheses ("value from line A
   through branch B to line C violates rule R"), allow hypotheses without a witness, consider covered sites
   (~1/3 of bugs lie on paths every base test already runs). Large → Codex.

2026-10-17 v25_interface_gate: user authorized continued implementation and old endpoint when GPU ready. Audited prospective split-output feasibility5,74 source files/prepared data/dependencies frozen; staged A/B/C early-stop only. See [[linefacts-v25-interface-gate]], RESULTS §11.64 and analysis/v25_cpu_audit.md; inspect owned status before any action, never duplicate or auto-expand to comparison/benchmark.

2026-10-17 v25 terminal supersedes launch: transport-incomplete, no task response; A failed, B/C blocked. f02/f04 timeout, f06 completion503→404, f14/f13 tokenizer HTTP errors. Only capability echo42/10tokens known;8task attempts usage unknown. Frozen hashes verified, independent review/callback handled; no retry/reset/auto-expansion. Read [[linefacts-v25-interface-gate]] and RESULTS §11.65.

2026-10-17 user authorized tiny transport retry after10min. Detached probe scheduled14:08:06UTC/21:08Vietnam in fresh out/transport_probes/v25_20261017_140806; max2single-attempt completions, no diagnostic5/benchmark chaining. Frozen original v25 preserved. See [[linefacts-v25-interface-gate]], RESULTS §11.66 and transport probe audit; inspect status, never duplicate.

2026-10-17 transport probe terminal supersedes schedule: models GET404/ERR_NGROK_3200, endpoint offline at21:08Vietnam;0tokenizer/plain/guided completions.0unknown completion usage for this probe; old8unknown attempts unchanged. Source/original hashes verified, independent review/callback handled, no retries/new calls. Read [[linefacts-v25-interface-gate]] and RESULTS §11.67; no active run.
