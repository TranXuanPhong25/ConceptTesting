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
- `RESULTS.md`: every result, numbered sections (§11.x is the latest work; §11.43–11.47 on 2026-10-14).
- `PREREG.md`: append-only registrations, amendments and decisions; the "Final comparison protocol" (six fairness
  fixes) is at the end. Register before running; never edit old entries.
- `CONCEPT_WEAKNESS.md`: why concepts are weak (3-layer loss analysis), ranked plan; section 4 = current fix plan
  (S1–S5 small, B1–B5 large) with progress notes.
- `PLAN_BASELINES.md`: baselines (CoverUp, MuTAP, SymPrompt, ACH, TrickCatcher-full) and held-out (VibePass, MBPP+).
- `pipelines/<version>/`: self-contained pipeline copies, each with `CHANGELOG.md`; `pipelines/README.md` lists stages.
  Best = `v7` (+ v8-strict construction). `v11_fair` = v7 + fairness fixes (dev GPU results complete, §11.41). Dropped: v9_callfb,
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

**Defensible claim now:** the tool yields grounded facts with witnesses and the complete pipeline beats paper
baselines; NOT yet shown that an LLM reading concepts beats plain, matched placebo or toolinput under fair conditions.

**Next steps (CONCEPT_WEAKNESS.md §4):**
1. B3/B4 and repaired v14/v15 completed (RESULTS §11.45–11.47). B4 native score initially lacked task 44;
   unchanged single-worker retry completed it, full 133/133 cohort verified. Hypothesis pipeline lost to flat/toolinput
   on dev; no promotion. All queue jobs ended; see GPU_QUEUE-2026-10-14.md and analysis/b4_v13_hyp_results.md.
2. v14/v15 GPU smoke completed on 20 dev tasks/K=1: both produced zero accepted semantic cards, so only generic
   fallback/control arms ran. RESULTS §11.44 and analysis/v14_v15_gpu_smoke.md/json; see [[linefacts-new-trials]].
3. v11_fair dev and five paper baselines are complete (RESULTS §11.41–11.42). Held-out VibePass 66 + MBPP+ 12 awaits
   final arm choice and Qwen availability, with the frozen protocol and runbook.

**New direction requested (2026-10-14):** user wants more abstract concepts over control/state/input-output
behavior, potentially symbolic execution/pseudocode, and asked for a plan. See [[abstract-concept-direction]]
and PLAN_ABSTRACT_CONCEPTS.md. User authorized implementation immediately on 2026-10-15, overriding the benchmark wait. v18_modelselect selection-only pilot complete (no MCTS):52 tests,13/20 base-consistent menus,12/20 sampled-consistent retained/displayed requirements; LLM11 vs lexical-rule12 vs uniform9.17.119 canonical-confirmed input discrepancies across12 tasks,0 observed property false alarms, no D_IO/generation (RESULTS §11.52). Future matched generation comparison needs a separate protocol; LLM selection gain not shown. See [[abstract-concept-direction]].

2026-10-15 v19_rulegen: user authorized implement/run; code+prereg complete, CPU gate passed. GPU launch attempted but tunnel offline;0 generation requests, no D_IO. See analysis/v19_rulegen_status.md and [[abstract-concept-direction]].

2026-10-15 UPDATE superseding v19 waiting status: v19 generation/scoring complete and frozen hashes verified. No missing work/GPU job. No concept generation gain; output format bottleneck. See RESULTS §11.53, analysis/v19_rulegen_results.md/json and [[abstract-concept-direction]]. New interface experiment not yet authorized/started.

2026-10-15 UPDATE: user requested plan→subagent audit→implementation. v20 narrow CPU multiplicity increment completed after two independent plan/code audits; final folder v20_groundedflow_domainfix, earlier failures preserved. No running GPU job, no D_IO. Read PLAN_GROUNDED_FLOW_V20.md, analysis/v20_plan_review.md, v20_cpu_results.md and RESULTS §11.55 before expanding scope. Real-task requirements remain unreviewed; guards/loops/derived provenance not implemented.

2026-10-15 latest direction correction: user wants Qwen semantic extraction/alignment through prompt chaining, rejects static property/effect text matching as the main method. See PLAN_QWEN_REASONING_CHAIN.md and [[abstract-concept-direction]]. v20 is only a narrow verification prototype. No chain implementation/GPU started; independent plan audit required before code.

2026-10-16: Qwen-chain detailed plan v3 independently audited by two subagents, blockers resolved. PLAN_QWEN_REASONING_CHAIN.md + analysis/qwen_chain_plan_review.md define five stage contracts, direct-tuples first pilot, budgets and separate semantic/observation labels. Plan-only deliverable; no v21 implementation/GPU started.

2026-10-16 scheduled Qwen-chain thread: v21_qwenchain P1 offline interfaces complete/reviewed; source copy from best v7 and final snapshot. No Qwen/GPU/canonical/ref/D_IO; future model run still requires explicit request. See [[qwen-chain-offline]] and analysis/v21_offline_interfaces.md. Parallel flowtools plan unchanged.

2026-10-16 Qwen calls now explicitly authorized; v21_qwenchain_pilot controlled16 running detached with frozen source,74 preflight checks, two independent reviews. Read analysis/v21_qwenchain_pilot_status.md and out/runlogs_v21_qwenchain_pilot/status.json. Human semantic gate pending; no real20/D_IO, do not start duplicate or repair active treatment.

2026-10-16 Qwen-chain update: explicit model-call authorization exercised; two controlled16 pilots complete/frozen. Singlejson adaptation S1 13/16,S2 3/16,S3 three abstentions; gate19/62,probe0/7. Our empty-guard contract gap + f12 semantic alignment miss documented. No generated inputs/real20/D_IO. Read [[qwen-chain-offline]] and analysis/v21_qwenchain_singlejson_results.md; callbacks handled, do not duplicate.

2026-10-16 user-requested v22 fixes + separate S3 replay complete. Guard contract fixed/89 offline checks; full pilot gate24/62,probe1/7,6 S4 inputs/0 S5 final. Old f12 raw mismatch recognized in S3-only replay but invalid status, ambiguity remains weak; no reliable semantic-success claim. See [[qwen-chain-offline]], RESULTS §11.59. No GPU work running; callback already handled.

2026-10-17 v25_interface_gate: user authorized continued implementation and old endpoint when GPU ready. Audited prospective split-output feasibility5,74 source files/prepared data/dependencies frozen; staged A/B/C early-stop only. See [[linefacts-v25-interface-gate]], RESULTS §11.64 and analysis/v25_cpu_audit.md; inspect owned status before any action, never duplicate or auto-expand to comparison/benchmark.

2026-10-17 v25 terminal supersedes launch: transport-incomplete, no task response; A failed, B/C blocked. f02/f04 timeout, f06 completion503→404, f14/f13 tokenizer HTTP errors. Only capability echo42/10tokens known;8task attempts usage unknown. Frozen hashes verified, independent review/callback handled; no retry/reset/auto-expansion. Read [[linefacts-v25-interface-gate]] and RESULTS §11.65.

2026-10-17 user authorized tiny transport retry after10min. Detached probe scheduled14:08:06UTC/21:08Vietnam in fresh out/transport_probes/v25_20261017_140806; max2single-attempt completions, no diagnostic5/benchmark chaining. Frozen original v25 preserved. See [[linefacts-v25-interface-gate]], RESULTS §11.66 and transport probe audit; inspect status, never duplicate.

2026-10-17 transport probe terminal supersedes schedule: models GET404/ERR_NGROK_3200, endpoint offline at21:08Vietnam;0tokenizer/plain/guided completions.0unknown completion usage for this probe; old8unknown attempts unchanged. Source/original hashes verified, independent review/callback handled, no retries/new calls. Read [[linefacts-v25-interface-gate]] and RESULTS §11.67; no active run.

2026-10-18 explicit fresh transport retry complete: v25_20261018_040624 models GET404/ERR_NGROK_3200 at11:08Vietnam,0tokenizer/plain/guided completions. No unknown generation usage for this run. Original artifacts verified unchanged, no automatic further retry/diagnostic5. See [[linefacts-v25-interface-gate]] and RESULTS §11.68; callback handled.

2026-10-18 this Qwen-chain thread: user-authorized Luna subagent diagnostic complete,6/6 valid vs Qwen0/6 on same6 saved targeted messages (3S2/3S3). Strong model-capability signal, harness/budgets unmatched, no full chain or D_IO. See [[qwen-chain-offline]] and analysis/luna_chain_probe_20261018/REPORT.md.

2026-10-18 user-authorized native v23/v24/v25 Luna/low retest launched16:36UTC, fresh model-probe roots; no Qwen endpoint calls. v25 A failed on validator comprehension-scope false rejection despite faithful normative code; v23/v24 still running. Execution host disabled but schemas exposed, no matched harness/causal model claim. Read [[linefacts-luna-version-retest]], RESULTS §11.70 and explicit statuses before action.

2026-10-19 correction/continuation: Luna nativev23/v24 had stoppedquota at73/65accepted+oneunknownattempt each. User explicitly authorizes continue. Fresh continuation root imports acceptedoutputs/caches exactly; max87/25missingstagecalls, quota access confirmedbyfreshv23responses beforev24launch. No original/v25repair or duplicatecalls, externalold+newcost needed. See [[linefacts-luna-version-retest]] and RESULTS §11.71.

2026-10-19 Luna native retest COMPLETE16/9/5: v23C/D/H5/7,7/7,5/7correctassertionbugtasks,FA1/0/0; v24verifiedselected1/3 vscontrols/witness3/3; v25Afailedvalidatorlegitimatecomprehensionreuse, B/Cblocked. No concepttaskgain, rawsemantics largelyfaithful; serialization/scope/gatingmechanismlosses found. Allold/frozenoutputsunchanged, noactivejobs/retries, noauto widercomparison. Cumulative253CLI/251responses/2quotaunknown; read [[linefacts-luna-version-retest]], RESULTS §11.72 and fullreport/verifier/reviews.

2026-10-19 v32_scope_support: user-approved stdlib comprehension scope/cumulative support fixes in separate best-v7+v25-port folder;48 CPU pass, clean-context audits. Fresh Luna seen5 Atrue/Bfalse/Cblocked: all4 contracts calibrated, f02/f04 supported, f14consistent/f13unknown; f06 correct fault condition but wrong trigger signature and misleading evidence sentence. Scope fix exercised, support promotion CPU-only, no model inputs/comparison/gain.22calls163666/4463tokens0unknown,old/frozen inventories unchanged,no active job/retry. See [[linefacts-v32-scope-support]], RESULTS §11.73 and analysis/v32_scope_support_20261019/REPORT.md.

2026-10-19 Qwen-chain thread OpenRouter30dev authorized and completed: v32_qwenchain_or30 exactqwen/qwen3.5-35b-a3b,93completions,$0.05124. S1/S2valid29/28,S3selected3,S4inputs18; canonical any-stage IO3/30,final-S5 IO0/30(all3S5ID/aliasfailed). Promising rawsemantic/input examples, interface stillblocking. All source/gen/evidence frozen/verified; no activejobs/newspend. See [[qwen-chain-offline]] and analysis/v32_qwenchain_or30_results.md.

2026-10-20 Qwen-chain followup: user requests same30 chain vs direct with GPT-5.6 Luna/low; v33_lunachain30 frozen/launched,99 CPUchecks+canarypassed. Max300taskCLIcalls/2workers,no paid API or automatic unknown retry. Read [[qwen-chain-offline]] and own status before action; source frozen, canonical score withheld till generation complete.

2026-10-20 v33 Luna chain/direct30 COMPLETE (supersedes launch): chain8vsdirect25value-unequalcanonical tasks(strictdirect26,type-onlytask130),final8vs21,nochain-only.14terminal+7groundingblocks hurtchaincoverage;6blocks legacy12-refcap not advertised. No gain even equal-input8vs8.37(shared9).253taskCLIresponses,0unknown/tools;noactivejobs or newcalls. Do not promote this hard-gatedchain; see [[qwen-chain-offline]]/RESULTS11.75/report.

2026-10-20 fault-concept line (v31→v34→v35, Qwen3.5-35B OpenRouter, vibepass_half): v31 fault-template 18 vs plain 15 (4–1, weak); v34 vs same-input placebo 8–2 but FA 27>23, rule not met; post-hoc concepts point at the bug in 11/33, 5/8 wins use no exposing concept; v35 CPU ceiling 14/33 < 17 → registered **stop**. Cap = template input pool (exposes 17/33 < plain Qwen 19/33), not site location. See [[v31-faulttemplate]], [[v34-ftplacebo]], analysis/v35_concept_ceiling/RESULTS.md.

2026-10-20 direction review (Claude, user asked): proposal "semantic chain + fault concept/template + property oracle" judged no-go as a new run — prior art v23/v21_flowtools/v28, no complementarity (v33 chain-only 0 tasks, 10/17 direct-only end S3 unknown; template ranking ≈ random; template pool < plain). Use the three-branch table (requirement→mismatch, fault hypothesis→input, property→oracle) as thesis "what was tried" with mechanism-explained negatives. Untracked analysis/v36_llm_localize/probe.py (other session, 22:30) has no PREREG.md and targets localization, which v35 says is not the bottleneck; not touched. See [[check-version-tree-before-proposing]], [[signal-not-more-data]].
