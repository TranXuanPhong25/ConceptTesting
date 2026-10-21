- [Shared memory README](README.md) — how Claude + Codex read/write this folder (format, rules)
- [HANDOFF 2026-10-14](../HANDOFF-2026-10-14.md) — READ FIRST when resuming: results, running jobs, next steps
- [LineFacts relational research](linefacts-relational-research.md) — 9 primary papers; grounded obligation graph và conditional metamorphic concepts, proposal only
- [LineFacts new trials](linefacts-new-trials.md) — B3/B4/repaired v14/v15 complete; no concept promotion, all queues ended
- [Research state](research-state.md) — START HERE: thesis direction, where files live, key results, next steps
- [Working rules](working-rules.md) — all user rules: Vietnamese replies, git, secrets/ngrok, GPU runs, folders+CHANGELOG, PREREG
- [Session 2026-10-13 (Claude)](session-2026-10-13-claude.md) — digest of the long session: user requests/quotes, decisions, lessons, open items, transcript path
- [CoverUp concept verdict](coverup-concept-verdict.md) — seed 1 null; site-hint smoke p=7e-6 is an artifact (truncation + clustered mutants)
- [Thesis concept requirement](thesis-concept-requirement.md) — thesis MUST have a "concept" guiding tests; never propose dropping concepts
- [Test-aware mutants candidate](test-aware-mutants-candidate.md) — ESEM'26 base paper, artifact/Zenodo facts, proposed gap-concept test-gen extension
- [STELLAR-D candidate](stellar-d-candidate.md) — 2609.23209 fits concept direction (MIT artifact, open CarQA/NaviQA-I); 2609.28130 NEATEST rejected (no LLM, code unreleased)
- [API budget](api-budget.md) — ~$25 Vertex left (2026-10-09; ULT baseline spent ~$0.8 since); hard cap, reuse Zenodo, freeze CoSIL/JitVul/CoverUp seeds
- [ULT concept status](ult-concept-status.md) — ULT_Lite baseline done (BCov@1 39, Mut@5 61); C1–C8 tag probe null, arm dropped; adequacy-gap arms await go-ahead
- [CKGFuzzer paper facts](ckgfuzzer-paper-facts.md) — KG = call graph + summaries (no state edges); +8.73% claim rests on lcms typo, corrected ≈4.25%
- [ConceptCoder paper facts](conceptcoder-paper-facts.md) — gain from concept-supervised training; NVC keeps ~3/4; concept prompting (A.4) hurts GPT-5.2
- [Hybrid C1 verdict](hybrid-c1-verdict.md) — diff hints sig. only vs harmful rnd placebo; vs plain/checklist n.s.; C2 can't reach 33/50/111
- [Line concept checklist](line-concept-checklist.md) — tester line-level concepts; only OUTCOME-GAP/STMT/mutant facts beat base offline; top-3 ~1/5 PUTs
- [Commit policy](commit-only-when-asked.md) — trickcatcher_linefacts: commit+push own files after each finding; elsewhere only when asked
- [Course vocabulary](course-vocabulary.md) — test_slides/ criteria are the default vocab, no longer required (lifted 2026-10-12; property concepts OK)
- [Codex quota fallback](codex-quota-fallback.md) — Codex 5h quota out → my subagents; reset within ~30 min → schedule Codex
- [Version tree diagram](version-tree-diagram.md) — after every new variant update the artifact: version tree, results + glossary, concept kinds, papers
- [Reply vocabulary](reply-vocabulary.md) — Vietnamese sentences, all technical terms in English (task, input, hint, oracle, false alarm…)
- [Pipeline folder workflow](pipeline-folder-workflow.md) — best pipeline in pipelines/<ver>/; new experiment = copy folder + CHANGELOG.md, edit the copy; big changes wait for Codex
- [Prefer standard libraries](prefer-standard-libraries.md) — swap own code for libraries when results equal (user: fewer reviewer objections)
- [Do not fix unasked](dont-fix-unasked.md) — pasted errors are context; never edit the Kaggle notebook unless asked
- [Held-out final readiness](heldout-final-readiness.md) — CPU ready; amendment 1 fixes shared 10+4 TC pool; GPU waits for dev review and VibePass mining
- [SWT-Bench feasibility](swt-bench-feasibility.md) — reproduction tests; Defects4J for root-cause analysis, BugsInPy for Python compatibility (recommendations only)
- [Benchmark paper selection 2025–2026](benchmark-paper-selection-2025-2026.md) — ongoing full-text audit; 74/500 read, 81 source checks; prioritize high-fit papers; UI quota percentage means remaining; 50/50 cap reached; timers disabled; root actual-count report
- [LineFacts method grounding](linefacts-method-grounding.md) — exact clause/edge extraction and real mutation-propagation limits
- [Abstract concept direction](abstract-concept-direction.md) — Qwen five-stage chain plan v3 audited 2026-10-16; no v21 code/GPU yet; tools verify
- [Benchmark completion schedule](benchmark-watch-schedule.md) — hourly checks from 05:00 15/10; then authorized abstract concept work
- [Flow hypothesis + fuzz witness](../trickcatcher_linefacts/analysis/flow_hypothesis_witness_direction_2026-10-16.md) — existing concept-toolinput/v13 audit; proposed verified hypothesis+trace+input package
- [Flow hypothesis/tool plan](../trickcatcher_linefacts/PLAN_FLOW_HYPOTHESIS_TOOLS.md) — P1 CPU implemented 2026-10-18 in pipelines/v21_flowtools; online/pilot gated
- [Qwen chain pilots](qwen-chain-offline.md) — v33 Luna chain vs direct30 complete:8vs25value-unequal IO,final8vs21; hard-gated chain not promoted
- [LineFacts v23 diagnostic](linefacts-v23-diagnostic.md) — latest: Qwen160/160 complete; all schema-valid, correct assertions2/7 each arm; no concept gain; callback handled
- [LineFacts v24 obligations](linefacts-v24-obligations.md) — latest:90/90 complete; contract0/9, generation0/54; interface failure, witness-only3/3; callback handled

- [LineFacts v25 interface gate](linefacts-v25-interface-gate.md) — 18/10 fresh retry models404/endpoint offline,0completions; old runs preserved, callbacks handled
- [LineFacts v21 flowtools](linefacts-v21-flowtools.md) — 2026-10-18 full plan run: diag16 ceiling, pilot20 1–4/20 confirmed, FA 19–38; negative, not promoted
- [v26 property oracle](v26-proporacle.md) — 2026-10-18 property/metamorphic oracle worse than exact (prec .15/.18 vs .21); 19% properties unsound; negative
- [v27 codex oracle](v27-codexoracle.md) — 2026-10-18 model vs prompt: Codex≫Qwen; codex×strict property oracle prec 1.0 (pilot20); Qwen not fixable by prompt
- [v28 Codex full pipeline](v28-codexflow.md) — 2026-10-18 tool-less Codex: all arms 16–17/20 FA 0–3 (ceiling, no concept gain); oracle result holds without tools

- [Luna version retest](linefacts-luna-version-retest.md) — complete16/9/5: no concept task gain; JSON, comprehension-scope validator and frozen-support gating losses
- [v29 VibePass Codex](v29-vibepass.md) — INVALID: prompts leaked the reference (`_plus` test field); numbers unusable
- [Flowtools contract audit](flowtools-contract-audit.md) — v21 tool-use/source-trigger gaps; audited v30 CPU repair54/54, no new model run
- [v31 fault templates](v31-faulttemplate.md) — 2026-10-19 explicit fault-type concepts + templates vs plain, Qwen3.5-35B; rule met but weak: 18 vs 15 confirmed /33, 4–1, FA 27 vs 32, $2.56
- [v34 fault-concept placebo](v34-ftplacebo.md) — v34 rule not met; v35 stop; v37 Mokav-mutant no-go 3/20; v38 HumanEval spec programs = canonical; v39 VibePass spec programs no-go (C' 12/33, H' 2); paper route closed
- [Signal, not more data](signal-not-more-data.md) — borderline result → mechanism check on existing outputs for go/no-go; never enlarge runs to salvage
- [Check version tree first](check-version-tree-before-proposing.md) — before any new direction, name the earlier v-number that tried the core idea + result; v31 repeated v7 MUTANT

- [v32 scope/support](linefacts-v32-scope-support.md) — 48 CPU pass;fresh Luna Atrue/Bfalse,f06 signature block;scope fix exercised,support model promotion untested

- [Concept training evidence gap](concept-training-evidence-gap.md) — recent losses mainly upstream/gates/oracle/pool; concept-to-input training proposal premature

- [Astra concept-agent diagnostic](astra-concept-agent-diagnostic.md) — v40 complete72:allarms6/6buginputs,0concept-onlywins; semanticcapabilityfail/no-go,callbackhandled

- [v43 concept-identification tools](v43-concept-identify.md) — implemented core, audit/CPU pending; quota15 checkpoint, scheduled continuation,0newcalls
