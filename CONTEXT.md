# CONTEXT checkpoint (2026-10-11 ~20:40) — trickcatcher_linefacts thesis work

Read this after a context compaction. Full results/method/threats: `trickcatcher_linefacts/RESULTS.md`.
Every decision/amendment: `trickcatcher_linefacts/PREREG.md` (append-only). Pipeline diagram (private artifact):
https://claude.ai/artifact/7a6yvf5bhiVmZVyt9UvTC8 (source: session scratch `conceptester-v4.html`).

## Standing rules (user)
- Reply in Vietnamese. Implementation → Codex (`codex:codex-rescue`, background); discussion/design → me.
  Codex quota rule (user, 2026-10-11): if Codex's 5-hour limit is exhausted (weekly still left) → temporarily use my own
  subagents for implementation; if the 5-hour window resets within ~30 min → schedule the Codex task (CronCreate) for
  the reset. Quota: latest ~/.codex/sessions/*/*/*/*.jsonl "rate_limits" (primary = 5 h, secondary = week, resets_at epoch). Codex sandbox has
  no network (pip via pre-downloaded wheels) and no real LLM calls; the main session runs real calls.
- NEVER commit/push unless asked (AGENTS rule 1 is format only). AGENTS rule 2: no paper re-implementation without approval —
  approved on 2026-10-11 for: TrickCatcher DPP panel (B2), DeCon postconditions (B3), TrickCatcher full re-run with Qwen
  (only the model changes, dataset = our 133 tasks). Do not edit vendor/ or the pinned TrickCatcher clone.
- Thesis must keep "concept" central; never propose dropping concepts. Raw inputs alone are not a concept.
  Course vocabulary is NO LONGER required for concepts (user, 2026-10-12): property concepts (structural/relational/
  boundary/algebraic/metamorphic) are allowed.
- Do not print secrets; the ngrok URL is never written to repo files (pass via `read -r QWEN_BASE_URL` heredoc; ask the user
  if the endpoint is offline — it has stayed the same across notebook restarts). Paid API budget ~$25 Vertex: ask first.
- Pilot (20 tasks) is reported separately; dev (113) is primary; design tasks {22,33,111,122,123,139} excluded.
- Run GPU work through the user's Kaggle vLLM notebook (Qwen2.5-Coder-7B-Instruct fp16, TP=2, ngrok). Check with
  `curl $QWEN_BASE_URL/models` (header `ngrok-skip-browser-warning: 1`).

## Setting / method (short)
TrickCatcher EvalPlus setting: LLM-written PUTs pass HumanEval base tests but are buggy; labels = HumanEval+ canonical.
Lane A tool computes concept facts (gaps of base tests in course vocabulary) → lane B arms produce test inputs → lane C
oracle (post hoc, never sees PUT code) → lane D scoring (canonical + EvalPlus contract; contract-invalid inputs = false alarm).
Fact versions: v3f (frozen) → v3c (contract-filtered upper bound) → v3m / v3m2 (Qwen-mined preconditions; v3m2 = primary)
→ v4 (Hypothesis+LLM strategy, mutmut 3.8, coverage.py; B5 preconditions) → v4c (v4 + draw-worker arity fix).

## Key results so far (dev, 113 tasks, K=3)
- Offline strong@3: v3f 45, v3c 46, v3m 44, v3m2 44 (random ~45, ceiling 53); v4 (registered) 22 (90/133 strategies fell
  back) → v4c fix reduced fallbacks to 22/133 (facts running).
- v3m2 arms, re-oracled (`out/oracle_b01/report.txt`): ref (B2, Qwen 10 refs, DPP prompt, unanimous≥3) cuts false alarms
  ~30% → 3–5% and raises detection 6–12/sample; concept vs plain significant under good oracle (full: 28/12 p=.017);
  gen-concept vs gen-plain 33/18 p=.049 (o0), 27/16 (full); gen-concept vs gen-placebo tied; toolinput strongest.
- False alarms of LLM-written expected (o0): ~74% wrong value (½ arithmetic/counting, ⅖ spec misreading), 6–17% invalid
  inputs, 8–10% copied PUT behaviour. Budget-matched truncation keeps gen-concept > gen-plain (36/17 p=.013, v3m2).

## Files (trickcatcher_linefacts/)
- Lane A: `facts.py`, `tracer.py`, `fuzz_validity.py`, `preconditions.py` (+`precond_prompts.py`), v4: `run_v4.py`,
  `v4_*.py` (`v4_worker.py` has the arity fix), `v4_offline.py`.
- Arms (v3m2): `run_gen.py`, `gen_prompts.py`, `gen_inputs.py`, `generator_worker.py`, `llm_client.py`, `evaluate.py`,
  `gen_evaluation.py`. Oracles: `oracle_b01.py` (collect / llm / score; constants RUN=out/gen2_qwen7b_v3m2,
  OUT=out/oracle_b01 — must be parameterised to re-oracle other runs; oracle label `C` = "full" in RESULTS.md).
- TrickCatcher full: `tc_full.py`, `tc_full_worker.py`; templates in `tc_templates/` (sha-checked).
- Venv for v4/tc-full: `/tmp/claude-1000/-home-phong-dev-ConceptTester/2dddac78-7845-4887-9c28-b6313bcf7c52/scratchpad/codex_v4/venv/bin/python`.
- Analyses: scratch `analysis/budget.py`, `analysis/fa.py` (+`fa_worker.py`).

## Running now (background) and next steps
1. v4c: facts DONE (6 timeout records, PREREG v4 amendment 4); offline DONE (strong@3 29/112 vs v3m2 44, report
   out/offline_v4c/REPORT.md); arms DONE (2793 rows); first eval aborted at task 41 -> fix in v4_evaluation.worker
   (per-input memo + skip re-trace of timed-out inputs; amendment 5); eval re-running (log scratch run_v4c/6_eval_run2.log).
   User correction 2026-10-11: Hypothesis only 'when stuck' (gaps the v3 fuzz cannot reach), not always -> proposed
   v5 = v3 fuzz + per-gap LLM Hypothesis fallback (+ optional LLM self-declared search in lane B); awaiting user go-ahead. Original v4c facts: `run_v4.py facts --precond-dir out/precond_qwen7b_v4 --strategy-dir out/strategy_qwen7b_v4c
   --facts-dir out/facts_v4c --tasks out/tasks_v4c_all.json` (log scratch `run_v4c/2_facts.log`). Then:
   - offline: `OFFLINE_SKIP_PILOT=1 $V4 -I -B trickcatcher_linefacts/v4_offline.py --python $V4 --workers 8
     --tasks out/tasks_v4c_all.json --facts-dir out/facts_v4c --out-dir out/offline_v4c`
   - arms: `$V4 -I -B trickcatcher_linefacts/run_v4.py arms --python $V4 --workers 16 --k 3 --tasks
     out/tasks_v4c_all.json --out-dir out/gen2_qwen7b_v4c` (cache already copied there), then evaluate.py + report.
   - If facts/offline sandboxes time out (3600 s) on slow numeric tasks, write timeout records like the v4 amendment
     (tasks 8,41,46,55,63,130 timed out in v4; labels for offline copied from offline_v3m2).
2. tc-full: DONE (RESULTS.md §8): dev 44.0 det/sample, FA 5.2%, RQ2 8/113 correct programs flagged; vs arms (ref)
   only toolinput wins per task (28/14 p=.044), concept 29/21 p=.32. Script scratch `analysis/tc_vs_arms.py`.
3. Re-oracle v4c and tc-full inputs with oracle_b01 (parameterise RUN/OUT/FACTS), add budget/FA analyses, update
   RESULTS.md (sections 3/4/7) and the diagram if the architecture changes.
4. Stopped/kept for the record: out/gen2_qwen7b_v4b (stopped, unevaluated), out/facts_v4 + out/offline_v4b (registered v4).

## Open issues
- git index: trickcatcher_linefacts/ became untracked (index reset by unknown step); do not re-stage unless asked.
- Labels of tasks 34/58 are hash-order dependent (PUT returns list(set(...))); kept per version with a warning.
- Approximate "% samples flagging a correct program"; faithful RQ2 exists only for tc-full.
- Possible v4 lane-A improvements not yet done: merge LLM domain strategy with the v3 base-input fuzz; one corrective
  retry with base-test input examples; relax "only def strategy()" rule.

## Update 2026-10-11 ~23:35
- v5 plan APPROVED by user (PREREG "v5 plan"): step 1 mutmut-vs-handwritten mutant ablation on v3m2 (offline, no LLM)
  -> step 2 v5 = v3 fuzz + per-gap LLM Hypothesis fallback (max 10 gaps/task) -> arms; step 3 (parallel) new arm
  `concept-toolinput` (fact sentence + its witness in one prompt) on v3m2 bundle, primary vs toolinput under ref.
  Two Codex jobs running (steps 1-2 build; step 3 build); they return commands for me to run.
- oracle_b01.py now takes --run/--out (copy out/oracle_b01/cache into a new out dir to reuse ref/post responses);
  label C renamed "full" in code (v3m2 report re-scored identical apart from the label).
- v4c eval: hung twice at task 41 (slowness, then SIGALRM-in-coverage deadlock) -> fixes in v4_evaluation (memo, skip
  over-budget inputs, guarded alarm, 600 s x3 retries), PREREG v4 amendment 5 + addendum; eval run3 in progress
  (log scratch run_v4c/6_eval_run3.log).
- NOTE: the v3m2 run used out/tasks_v3m2_all.json (NOT tasks_v3m_all.json; 11 tasks differ). Analyses fixed
  (tool_witness: 77/113 tasks with witness, 41 tasks perfect-oracle, 34 ref). tc-full used tasks_v3m_all.json, only
  PUT/base/split are read there (identical).
- ngrok endpoint OFFLINE at 23:28 (ERR_NGROK_3200): user must restart the Kaggle notebook before any LLM step.

## Update 2026-10-12 ~00:10
- Step 1 DONE: v3mm (mutmut) offline 43/112 vs v3m2 44 -> v5 uses handwritten mutants (PREREG "v5 step 1 result").
- Step 2 RUNNING: run_v5.py mine/facts --mutant-source handwritten, then v5_offline.py v5 (logs scratch run_v5/3-5_*.log).
  Then arms on out/tasks_v5_all.json (six v3m2 arms + concept-toolinput) into out/gen2_qwen7b_v5 + oracle.
- Step 3: concept-toolinput gen+o0 DONE (out/gen2_qwen7b_v3m2_ct; o0 48.3 vs toolinput 51.3, 18/24 p=.44); oracle
  ref/full RUNNING into out/oracle_ct (logs scratch run_ct/).
- v4c o0 eval DONE (run 4): plain 41.7, concept 37.0, toolinput 43.7, gen-plain 33.7, concept-hybrid 49.3,
  placebo-hybrid 39.0, plain-hybrid 46.0; concept-hybrid vs placebo-hybrid raw 33/16 p=.021 but matched 25/24;
  vs plain-hybrid 25/18. Oracle ref/full RUNNING into out/oracle_v4c (logs scratch run_v4c/7_oracle_*.log).
- Codex 5h quota 87% (reset 03:57); rule: fallback to my subagents.

## Update 2026-10-12 ~01:05 — direction: reduce spec-violating inputs
- User direction: use generic "property concepts" to GENERALISE input constraints (concept-guided precondition mining,
  F4) so fewer generated inputs violate the spec. Property-as-oracle (step A done: properties detect 50 dev tasks vs ref
  82, 4 property-only, 13 tasks flag correct program; out/property_oracle/report.txt) is secondary (step B later).
- A general-purpose subagent is auditing taxonomy coverage vs EvalPlus contracts (labels only) + observed invalid
  inputs; additions derived from EVEN dev tasks + pilot, held-out on ODD; outputs scratch constraint_concepts/.
- Validity filters F1 (mined validator: flags 59/12,105 inputs) and F2 (ref crash: 66) are weak; F3 (LLM judge) running
  (validity_filters.py, out/validity_filters/gen2_qwen7b_v3m2/).
- v5 re-run in progress (mine from cache -> facts -> offline). DO NOT EDIT PREREG.md until out/offline_v5/REPORT.md
  exists (run_v5 manifests pin its hash). Then register F4 in PREREG.

## Update 2026-10-12 ~04:50 (user asleep until 07:30; Kaggle GPU ends ~05:00)
- DONE (RESULTS.md §11.1–11.5): concept-toolinput (ref 57.0 vs toolinput 60.0, 11/16 -> not better); v5 (Hypothesis
  when stuck: 10/276 gaps, offline identical to v3m2); filters F1/F1b/F2/F3/F4/F4b (F1b best: concept FA under ref
  4.8% -> 2.6%, flags-correct 14% -> 7%; concept-guided F4/F4b worse than open mining); v4c ref re-oracle
  (concept-hybrid 56.3 top, vs plain-hybrid 26/14 p=.081); F5 (requirements in prompt) NULL: invalid share unchanged
  (concept 5.3->5.0%, plain 2.8->3.5%, toolinput 5.5->6.1%), ref unchanged; concept vs plain still 29/16 / full 30/15.
  F5 paired analysis: scratch analysis/f5_paired.py. Property step A in out/property_oracle/report.txt (not yet in RESULTS).
- RUNNING: v3m2-hybrid chain (bg bomib1nv8): run_v4 arms on out/tasks_v3m2hyb_v4.json -> out/gen2_qwen7b_v3m2hyb_v4,
  then evaluate, then oracle_b01 into out/oracle_v3m2hyb (cache from oracle_v4c). If GPU dies during oracle llm, rerun
  `oracle_b01.py llm --stages ref,post` (cached) then score; b1 will be missing.
- Diagram: scratch conceptester-v4.html updated (filters tree, v5, c+t, hybrid ref, P-A, concept tables); placeholders
  HYB_RESULT / HYB_ROWS / HYB_TABLE await v3m2-hybrid; then republish (same path).
- 04:51: Kaggle endpoint died (HTTP 404) during v3m2-hybrid arms; ~355–367/399 samples per arm finished (result.json),
  LLM cache out/gen2_qwen7b_v3m2hyb_v4/cache kept. To resume after the notebook restarts: rerun the same chain
  (run_v4 arms on out/tasks_v3m2hyb_v4.json -> evaluate -> oracle_b01 --run out/gen2_qwen7b_v3m2hyb_v4
  --out out/oracle_v3m2hyb); finished samples come from cache. Then fill diagram placeholders (scratch
  conceptester-v4.tmpl.html: HYB_RESULT/HYB_ROWS/HYB_TABLE) and republish conceptester-v4.html.

## Update 2026-10-12 ~12:10
- v3m2-hybrid DONE (out/oracle_v3m2hyb): ref concept-hybrid 62.0, toolinput 60.7, plain-hybrid 53.0; concept-hybrid vs
  plain-hybrid 32/14 p=.011 (matched 29/15 p=.049), vs placebo-hybrid 33/11 (matched 21/19), vs toolinput 19/17
  (matched 16/33). RESULTS §11.8, PREREG "v3m2-hybrid result".
- RBCTest step ablation DONE (rbc_ablation.py; validity_filters Rnv/Rnc/Rnn; RESULTS §11.7): verifier is the key step
  (without it wrongly-dropped valid 48 -> 2319), confirmation helps moderately (48 -> 89), exact-quote filter hurts.
- Diagram source moved (old scratchpad retired): trickcatcher_linefacts/out/diagram/conceptester-v4.html (+ .tmpl.html);
  publish with url https://claude.ai/artifact/7a6yvf5bhiVmZVyt9UvTC8 (version 7).
- CORRECTION (RESULTS §11.9): run_v4 round 1 uses the same prompts.build as gen2 (only seeds differ), so the hybrid run's
  concept/plain are a seed replicate. Pooled 6 runs: concept 50.2 vs plain 46.2 (ref), per task 34/26 p=.37 -> single-
  round concept vs plain is NOT robust; strongest evidence is concept-hybrid vs plain-hybrid 32/14 p=.011.

## Update 2026-10-12 ~14:30
- Codex blind bug-finding on the 36 no-fact dev tasks: 33/36 detected (out/codex_nofacts/, scored in score/). Analysis page
  https://claude.ai/artifact/8v4jfJxo9Sjc9z9foNW6G1 (source out/analysis_weak/build_page.py). RESULTS §11.12.
- v6 registered (PREREG "v6"): run_v6.py facts/bundle -> out/facts_v6, out/tasks_v6_all.json, out/tasks_v6hyb_v4.json.
  Offline report running (eval_v3m.py -> out/offline_v6_report). Arms need GPU (endpoint 404 since ~13:00).
- Next (user request): v7 = spec-derived concepts for no-fact tasks (edge input classes: large size, non-ASCII,
  duplicates, whitespace, empty) -> new folder/version; derive classes from even tasks, held-out odd.

## Update 2026-10-12 ~18:45 (user closing the session)
- v6 DONE (RESULTS §11.14): out/gen2_qwen7b_v6hyb_v4, out/oracle_v6hyb. On the 12 changed tasks concept invalid inputs
  15.2% -> 11.0%; detections unchanged; concept-hybrid vs plain-hybrid ref 30/13.
- v7 (spec input-class facts, spec_facts.py; PREREG "v7" + amendment): arms 2789/2793 done in out/gen2_qwen7b_v7hyb_v4;
  GPU stopped 18:08 with 4 plain-hybrid samples missing (46/1, 46/2, 63/2, 160/1). Provisional scoring running detached
  (parent PID 1; progress out/runlogs_v6v7/v7p_chain.out): out/gen2_qwen7b_v7hyb_v4_partial (gen.jsonl built from the
  finished result.json files) -> eval.jsonl -> out/oracle_v7hyb_partial (ref/post from cache, score --no-llm; no b1/judge).
- v4_evaluation.py/gen_evaluation.py now truncate stored input_repr > 2000 chars (task 23 exceeded the 8 MB limit).
- TODO: analyse v7 on the 36 spec-fact dev tasks (concept vs plain, concept-hybrid vs plain-hybrid, even vs odd held-out),
  RESULTS §11.15; when GPU is back rerun out/runlogs_v6v7/chain.sh-style v7 arms (finishes the 4 samples from cache)
  + evaluate + full oracle; update the diagram (out/diagram/conceptester-v4.html, url 7a6yvf5bhiVmZVyt9UvTC8) with
  v6/v7 nodes and the analysis page (out/analysis_weak/build_page.py, url 8v4jfJxo9Sjc9z9foNW6G1).

## Update 2026-10-12 ~22:55
- v7 final DONE (RESULTS §11.21). EvalAndMitigate onlydoc/advdoc DONE (§11.16–11.18); advdoc-hybrid running
  (evalmitigate/run_advhyb.py -> out/gen2_qwen7b_advhyb_v4, out/oracle_advhyb). Property fallback (§11.20).
- Held-out MBPP+ (§11.22, PREREG "Held-out confirmation"): 53 PUTs, only 9 real bugs by manual reading -> decide
  source before running (alternative: fresh HumanEval PUTs from other models).
- User reply style: Vietnamese + simple English terms (spec, property-result) — memory reply-vocabulary.

## Update 2026-10-12 ~23:20
- Qwen endpoint offline since 23:05 (ngrok 404). advdoc-hybrid 797/798 (missing 160/1 advdoc-plainhybrid); provisional
  scoring out/gen2_qwen7b_advhyb_v4_partial + out/oracle_advhyb_partial (RESULTS §11.23: 56.0 vs plainhybrid 51.3,
  13/6; vs advdoc 21/0; vs concept-hybrid 9/20). Final: rerun `run_advhyb generate` (cache) -> evaluate -> oracle
  collect/llm/score. Do not edit PREREG.md between oracle stages (oracle manifest pins its sha).
- Held-out MBPP+: Haiku pass 3 done (58 PUTs, 12 real bugs; puts.json pass3_only). PREREG held-out amendment 3: v7 recipe,
  primary 58, secondary 12 real bugs. Codex is porting the pipeline into trickcatcher_linefacts/heldout/ (no GPU);
  then GPU: heldout run.py mine -> facts/specfacts/bundle (CPU) -> arms -> evaluate -> oracle.
- Diagram v10 published (v6/v7, P-fb, EvalAndMitigate + advdoc-hyb, held-out tree 6, v7 table).

## Overnight plan 2026-10-13 (~01:45; no GPU; Codex quota resets ~05:30)
- Running: Codex pipelines/v7 packaging + equivalence; Codex CrossHair on 276 v5 hard gaps (analysis/crosshair_gaps.py);
  my subagents: rank 2 fault-oriented hint ranking (analysis/hint_rank.py), rank 3 trigger inference
  (analysis/trigger_conditions.py). Codex jobs polled every 20 min by a shell loop (no LLM polling).
- After ~05:30 (Codex quota) and once pipelines/v7 passes equivalence: Codex builds pipelines/v7lib (coverage.py +
  mutmut swap, offline equivalence) and pipelines/v9_callfb (rank 1: round 2 = concrete calls + reach/infect/propagate
  trace feedback, strict, matched plain-hybrid control; fake-client tests; PREREG before any run). Commit after each.
- Do NOT edit the Kaggle serve notebook (user forbade).

## Update 2026-10-13 ~08:10 (user closing the session)
- Done overnight (all committed): VibePass metrics §11.28, rank-2 hint ranking §11.29, rank-3 trigger inference §11.30,
  VibePass feasibility §11.31 (66 LeetCode PUTs), MBPP+ real-12 held-out §11.32 (no concept advantage), CrossHair §11.33
  (10/276, no bug-revealing witness), advdoc-hybrid final §11.34, pipelines/v7 (equivalent), pipelines/v9_callfb (built).
- RUNNING detached (setsid, parent PID 1; survives session close): trickcatcher_linefacts/out/runlogs_v9/detached.sh =
  ping every 20 min (runlogs_v9/ping.log) + chain.sh (v9 dev: bundle -> arms -> evaluate -> report -> oracle collect/llm/score).
  Progress: runlogs_v9/steps.txt (arms was killed once at 08:08 and relaunched; it resumes from cache).
  Outputs: out/pipelines/v9_callfb/humaneval/. When DONE: analyse per PREREG "v9_callfb" (concept-hybrid vs plain-hybrid
  ref, matched count, vs toolinput, kept hint-hitting inputs/sample, D_I), RESULTS §11.35, diagram node, commit.

## Update 2026-10-13 ~19:00 (user ending the session)
- Done today (committed): v9 dropped (§11.36, concrete-call round 2 worse than Hypothesis), rank 5 BEHAV no gain (§11.35),
  pending registrations merged into PREREG (v7_mutref, v10_spechint, v9 result).
- RUNNING detached (setsid, PID in ~/.claude/jobs/08a7596f/tmp/mutref_chain.pid): rank 2 v7_mutref LLM run,
  out/runlogs_mutref/chain_from_eval.sh = evaluate (via analysis/mutref_eval_longtimeout.py, 3600 s scoring sandbox)
  -> oracle-collect -> oracle-llm (GPU) -> oracle-score -> strict; ping every 20 min. Arms finished 16:55 (2793/2793,
  with one GPU outage 13:10–13:24 resumed from cache). Progress: out/runlogs_mutref/steps.txt; outputs under
  trickcatcher_linefacts/pipelines/v7_mutref/out/humaneval/.
- To do when DONE: (1) append to PREREG a "v7_mutref amendments" note: GPU outage relaunch; scoring sandbox 600 -> 3600 s
  (task 83); v4_evaluation MemoryError guard (task 87 oversized input, scored as crash on both programs); (2) analyse per
  PREREG "v7_mutref": ODD dev tasks primary — concept-hybrid vs plain-hybrid (ref), vs toolinput, matched test counts,
  plus the strict (v8-style) construction; compare with v7 / v8-strict; (3) RESULTS §11.37, diagram node, commit.
- 19:30 update: evaluate + oracle-collect finished; oracle-llm failed because the Qwen endpoint is down (404 since ~18:47).
  Resume when the GPU is back: export QWEN_BASE_URL/QWEN_MODEL, V4_PYTHON, PYTHONPATH=repo root, then
  `setsid nohup bash trickcatcher_linefacts/out/runlogs_mutref/chain_from_oraclellm.sh &` (oracle-llm -> oracle-score -> strict).
- 21:10 update: final comparison protocol (six fairness fixes) registered in PREREG_PENDING.md (ea102be); user said
  NOT to implement it yet (quota). TrickCatcher-full adapter fix agent stopped before writing anything. Still running:
  CoverUp/MuTAP baselines (subagent), pipelines/v7_vp tracer fix (subagent), v7_mutref oracle (GPU, detached).
- 22:10 update: v7_mutref oracle-llm finished (21:40); oracle-score failed offline because B4 judge requests need the
  endpoint (needs --online). Endpoint down again (404). Resume when GPU is back:
  `setsid nohup bash trickcatcher_linefacts/out/runlogs_mutref/chain_from_score.sh &` (oracle-score --online -> strict),
  with QWEN_BASE_URL/QWEN_MODEL, V4_PYTHON, PYTHONPATH exported. Then analyse per PREREG "v7_mutref" (odd tasks).
- Subagents for CoverUp/MuTAP and pipelines/v7_vp stopped at the Claude session limit (resets 22:40) with partial,
  uncommitted work in baselines/coverup, baselines/mutap, baselines/common.py|worker.py|tests and pipelines/v7_vp.
