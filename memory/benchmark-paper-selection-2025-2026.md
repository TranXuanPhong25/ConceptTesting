---
name: benchmark-paper-selection-2025-2026
description: Ongoing audit of 500 screened 2025–2026 papers; 48 full texts read, 53 source checks, timers disabled, no reproduction
metadata:
  type: project
---

2026-10-14 (Codex): User added criteria to Defects4J/BugsInPy comparison: find **500 papers from
2025/2026**, prioritize modifiable author source, reproducibility, or evaluation with the authors'
own models. Research only; no new method implementation or model run authorized by this request.
User explicitly confirmed including SWT-Bench and APR/fault localization, separated by suitability.

Results and limitations: [report](../research/benchmark-papers-2025-2026/REPORT.md),
[500 screening records](../research/benchmark-papers-2025-2026/CATALOG_500.md),
[primary-source shortlist](../research/benchmark-papers-2025-2026/SHORTLIST.md).
Discovery union: 1,142 OpenAlex records; 842 normalized paper-like titles. Final corpus: 500 candidates,
36 primary-source-reviewed papers + 464 metadata-only candidates; 1 additional artifact-only record
reviewed separately. **Not 500 verified suitable papers.** No baseline reproduced or author source modified.

Recommendations only, not user-confirmed selection: EvalAndMitigate/Defects4J for buggy-input
test generation; AssertMate for assertion generation with the paper's small DeepSeek-Coder model
(Apache-2.0 source, exact served checkpoint/logprobs still need audit); RTED/BugsInPy for Python
type-error constraints (paper uses DeepSeek-V3; no Qwen backbone verified). fcd4j supplies MIT manual
control/data-flow classifications for 488 bugs as support taxonomy, not a test generator.

**How to apply:** first pin source/model/dataset and reproduce an original pilot before adding a
concept extension. Keep buggy-input, fixed-input regression and supplied-prefix/scenario tasks distinct.
SWE-Tester has a public training dataset but released SFT weights/scaffold were not verified.
New KITE mechanism-feedback preprint (2607.11573) is close prior work but no public source verified;
generation uses correct-version code + GPT-5.4. Do not confuse with other KITE paper in earlier research.

2026-10-15: User authorizes full audit of all 500 candidates, append report and refine selection;
schedule continuation near quota resets at 02:20/07:20 Vietnam time. Conditional: if completed before
07:00, publish root report stating actual 500/500 read+verified. Root progress report now lives at
[PAPER_AUDIT_500_REPORT.md](../PAPER_AUDIT_500_REPORT.md); do not claim 500/500 based on downloads.
Systemd user timer `concepttester-paper-audit.timer` installed, sequential same-session Codex resume;
instructions/state under research/benchmark-papers-2025-2026/audit/. Machine/user manager must run.
First retrieval attempted 500 records; actual full-text reviews continue, separate from retrieval.
New artifact-ready adjacent candidate: CASCADE (2604.19400), MIT source + public archive/data/evaluator,
GPT-4.1-mini paper config; mined documentation-fix dataset, not standard Defects4J bug tasks.

2026-10-15 08:24 corrections: overnight exec-resume failed active-writer conflict; scheduler now queues into owning app (enqueue rc0 verified), not a second writer. Do not equate queued status with completed work. Root report actual counts derive from audit/reviews. RTEDv2 DOES evaluate Qwen3-Coder; earlier no-Qwen statement superseded. SWE-Testerv2 now has public author source; mainSFT weight availability unresolved. DISTINCT/PANTA/AssertMate/AdverTest source audits added; inspect their ledger for model/config/evaluator discrepancies before choosing a base. Public source alone is not exact reproduction.

2026-10-15 08:40: shortlist re-evaluated in audit/PAPER_SELECTION.md. Important audit correction: anonymous.4open root401 can coexist with direct file200; test exactREADME/source paths before blocked verdict. Tratto exactCodeLlama source confirmed but3trainedweightshards404. Doc2OracLL laterauthorarchive supplies actual16MBCodeLlamaLoRA(verifiedformat/hash), partialoriginalmodelroute. NeuroTestGen documentedbatchrunner disables symbolic/LLMpathsolver/verifier. No reproductionexecution.

2026-10-15 08:43 checkpoint:17fulltextsread,19sourcechecksincluding2access-blockedunreadpapers,0reproduced. Livequota90%primary/91%weekly;primaryreset10:00:06.One-shotqueue-continuationtimer10:00:20installedandactive. Rootreportactualcounts;no500/500completion.

2026-10-15 10:30 checkpoint:21fulltextsread/23sourcechecks(2accessblocked)/0reproduced. Newlyaudited030BugsInPyAPRcost,016KITE,014IntTestGen,018cognitive;seereviewledger. Weeklyquota98%,reset2026-10-20 13:22:13Vietnam;one-shottimer13:22:30installed. Weeklyguard98%prevents5hresetfrommistakenlyresuming.Sameinheritedmodel,noAPIspend/agents/reimplementation/commit.


2026-10-15 12:56 checkpoint (Codex): user explicitly stopped all quota timers; do not recreate or schedule. Telemetry summarizer now reads the newest quota-only `rate_limits` event from recent Codex session logs and preserves provenance; user reported a reset at 12:34, but the later live event is the value in the report (87% primary/14% weekly at 12:56). Do not replace measured values with reset assumptions. Audit totals: 47/500 full texts read, 52 source/review checks, 5 access-blocked unread, 0 reproduced; 23/50 distinct full-text reads since the user’s quota refresh, 27 remain. Root report: `PAPER_AUDIT_500_REPORT.md`; ledger and checkpoint in `research/benchmark-papers-2025-2026/audit/`.

New comparison: #47 TestPrune/TestLoc is currently the easiest source-backed issue-test reuse baseline (Apache-2.0, pinned author repo, precomputed results; Python SWE-Bench Lite/Verified, not SWT-Bench/Defects4J/BugsInPy). #48 DPIAgent has the strongest explicit root-cause handoff and direct SWT-Bench Verified fit, but no public implementation. #49 CoHarden adds a strong rigorous-vs-lax oracle metric on the SWE/SWT intersection, but its project page says code is under review. #50 LTER is directly Defects4J-relevant by official abstract but full text is blocked. #51 goal-based EvoSuite objectives has public modified source/data and Defects4J 2.0.1, but is a non-LLM supporting baseline; paper/Zenodo DOI discrepancy remains unresolved. Per-paper evidence and exact counts are in the audit ledger.


2026-10-15 12:58 checkpoint update (Codex): live usage 88% primary /14% weekly; pause paper reading at this near-quota checkpoint. Audit still 47/500 full texts, 52 source/review checks, 5 unread blocked, 0 reproduced; 23/50 distinct post-refresh reads complete, 27 remain. #52’s official author PDF has just been downloaded/extracted (14,945 words) after ACM 403, but is still unread and does not count. #52 also has author-linked Zenodo artifact records with public data/code; audit later after reading. Timers remain disabled.
## Continuation checkpoint — 2026-10-15 13:13 +07

User corrected quota reading: UI percentages mean quota remaining. Local `rate_limits.*.used_percent` means consumed usage; telemetry now stores both and derives `remaining_percent = 100 - used_percent`. Latest event at 13:13 +07 reports primary 0% used / 100% remaining and weekly 0% used / 100% remaining. A 90% remaining quota is ample headroom, not a stop condition. All audit timers remain disabled; manual continuations only.

Paper #52 (“How Does Killing Surviving Mutants Help Detect Real Bugs with Assertion Generation? A Controlled Experiment”) was fully read (24 pages, 14,945 words) and author artifact verified. Public MIT source, Docker/CI examples; smoke replay feasible, full study conditional/heavy (~1,177 paper-reported hours). Strong Defects4J assertion/revealability comparator, not issue-level root-cause or LLM generation. Ledger now 48 full-text reads, 53 source/review checks, 5 unread access-blocked, 0 reproduced. 24/50 distinct new reads since user-reported reset; 26 remain. See `research/.../audit/reviews/052.json`.



2026-10-15 13:39 checkpoint (Codex): completed high-fit #63 TestExplora after reading its full 16,836-word arXiv v2 and verifying official Microsoft/TestExplora MIT source at commit `11e6952261f58d3ceb9f4d2571e03aa35dad9523`. Strong proactive-discovery match with documentation oracle and F2P testing, but benchmark JSON/output files are absent, default subset loader has an author-local absolute path, and Qwen3 paper baseline differs from Qwen2.5 wrapper. Exact rerun and own-Qwen evaluation are conditional on obtaining/building data and resolving model config. Counts: 57/500 read, 62 source checks/reviews, 5 unread-access-blocked, 0 reproduced; 33/50 new reads since quota reset, 17 remain. #62 test-smell paper was started but not completed and is not counted; prioritize high task-fit candidates. Timers remain disabled.


2026-10-15 13:42 checkpoint (Codex): completed high-fit #98, “Reproduction Test Generation for Java SWE Issues.” Full 9,651-word arXiv v2 read. Verified official IBM/TDD-Bench-Verified Apache-2.0 artifact at commit `3df8be066e486789d0b8e0d2865a3a4422b4560f`; the public Java CSV has 250/250 task IDs, all with issue/base commit/fix/test patch and Docker metadata. Public prediction JSON + Docker evaluator enable straightforward evaluation of a local model on Java issue-to-BRT. The paper's generator is explicitly proprietary, so e-Otter++ cannot be faithfully reproduced; this is own-model benchmark evaluation, not exact method replication. Current ledger 58 full texts / 63 source reviews / 5 blocked / 0 reproduced; 34/50 new full texts since quota reset, 16 remain. Prioritize #89 Multi-SWT-Bench next for broad SWT-style multilingual reproduction tests. Timers disabled.


2026-10-15 13:51 checkpoint (Codex): completed high-concept #75, “Dynamic Cogeneration of Bug Reproduction Test in Agentic Program Repair.” Read all 10,618 words; verified 120 Google-internal GITS issues, six languages, Gemini 2.5 Pro, Passerine cogeneration. No public source or dataset exists; no Defects4J/BugsInPy/SWT task experiment. Keep as conceptual evidence on Freeform/TDD/TLD, test-aware patch selection and failure causes, not as a reproduction/model-evaluation candidate. Counts: 60/500 full texts, 65 source checks/reviews, 5 access-blocked, 0 reproduced; 36/50 new full texts since reset, 14 remain. Next prioritize #79 oracle/assertion evaluation on real bugs. Timers disabled.


2026-10-15 13:53 checkpoint (Codex): completed #79 “From Business Requirements to Test Assertions.” Full 4,938-word arXiv v1 read; uses 10 Defects4J Lang bugs and compares manually derived REQ oracle vs actual SUT across five hosted models. Strong oracle concept fit (DeepSeek-V3 F1 0.8179 REQ/0.7476 SUT; Qwen3-480B 0.7779/0.7030), but pilot only, and linked 171.51 MB MIT Figshare share is explicitly private; direct file access returned 403/202-empty. No public package contents verified; don't count as ready Qwen baseline. Counts: 61 full texts, 66 source checks/reviews, 5 access-blocked, 0 reproduced; 37/50 new reads since reset, 13 remain. Next read high-fit #92 SWE-Doctor for runtime diagnosis + BRT. Timers disabled.


2026-10-15 13:56 checkpoint (Codex): completed high-fit #92 SWE-Doctor; full 9,646-word arXiv v1 read. Official paper-linked SWE-Doctor GitHub repo is MIT and includes BRT generation, runtime debugger RCA (PDB/Delve), patch repair and benchmark graders. LiteLLM endpoint configuration makes local Qwen possible in principle. Exact rerun conditional: only GitHub commit Oct 2 postdates the July paper and README calls it an FSE 2027 artifact; paper-specific task lists/results absent; hosted model revisions unpinned. Method does not score RCA correctness against labels. Counts:62/500 fulltext,67 source checks/reviews,5 access-blocked,0 reproduced;38/50 new reads after reset,12 remain. Timers disabled.


2026-10-15 14:02 checkpoint (Codex): completed full #69 ESEM 2026 PDF, 21 pages/9,997 words. Verified Zenodo 20283766 title/CC BY 4.0 and 2.164 GB `ESEM-2026.zip`; read embedded README by HTTP range. It claims 210 Java exception-trigger benchmarks/66 projects, evaluator, Docker/JDK images and subset commands; full runner source was not inspected, so artifact verdict partial/conditional. Task gives exception and target line (not issue→BRT/F2P); top Claude Code+GPT-5 89.5%, OpenCode+DeepSeek-V3.2 65.2%/$0.04; failure causes include exploration/reasoning/tool use. Current counts 63/500,68 source checks,5 access-blocked,0 reproduced;39/50 new reads,11 remain.


2026-10-15 14:08 checkpoint (Codex): completed #86 AG-RAG. Full 13,872-word arXiv v2 and substantive author source at `iSEngLab/AG-RAG` commit `47d69677e371209d9b6665ae879df3708886b1bb` inspected. Public 74 MB dataset, experiment code and cached results; repo no LICENSE, fine-tuned weights are external Google Drive, main implementation is CodeT5/T5 and Qwen2.5-Coder decoder-only is not drop-in. Main assertion exact-match 64.59%/56.33%; Defects4J EvoSuite-prefix bug detections 41 vs EditAS 21 across 835 bugs. Strong oracle comparator, not issue-to-BRT/RCA. Counts 64/500 read,70 source checks,6 unread blocked,0 reproduced;40/50 new reads since reset,10 remain. Next #90 mutation-guided unit testing. Timers disabled.


2026-10-15 14:11 checkpoint (Codex): completed #90 MutGen. Full 13,489-word arXiv v8 read; verified author GitHub at `69dd37ddfab16b8c5efd22117dc3d213ab05418d`, 74 MB dataset, code, PITest integration, prompts and cached results. LiteLLM router supports `model`+`api_base`, paper uses local Ollama Llama3.3, so local Qwen endpoint appears plausible. Main data are method-level HumanEval-Java + Leetcode-Java mutants; Defects4J only separate 835-bug EvoSuite-prefix detection (41 vs EditAS 21), not issue-to-BRT. Repo lacks LICENSE; model weights external Drive; README extraction command possibly erroneous. Counts:65/500 fulltext,71 source checks/reviews,6 unread blocked,0 reproduced;41/50 new reads,9 remain.


2026-10-15 continued: completed the high-priority #74 Defects4J coverage/mutation validity replication. Read all 13,276 words and checked paper-linked MIT author source at commit `4bc2ed63917557a8c879e6c733b8fa41c15b9871`, including processed fixed/buggy CSVs and analysis notebooks. Analysis can be rerun without API or Defects4J; full generation is conditional/heavy, original model snapshots unpinned, a few plot cells transcribe paper values. Strong evaluation-method paper: use direct F2P rather than proxies for buggy-code test generation. Not a concept/RCA method; BugsInPy only related-work. Current totals 66/500 full texts,72 source checks/reviews,6 unread blocked,0 reproduced; 42/50 distinct new reads,8 remain. User clarified UI quota percentages are remaining (90% means ample). No timers. Next continue with highest-fit unread papers, within the remaining cap.


2026-10-15 continued: completed #111 ORACLE-SWE full article and appendices (12,542 words). Paper finds gold F2P test is strongest single SWE-agent signal but uses only SWE-bench Verified/Live/Pro, not Defects4J/BugsInPy/SWT-Bench. No author extraction source, dataset or result cache; oracle arms leak gold test/patch information, and original model snapshots are unpinned. Supporting conceptual evidence only; do not implement under current instruction. Totals 67/500 full texts,73 source checks/reviews,6 access-blocked,0 reproduced; 43/50 new reads after user quota refresh,7 remain. Timers disabled; continue with high-fit unread papers only.


2026-10-15 continued: completed #73 CATGen full paper and paper-linked public repo check at `b60476d34fb3b130dea653588810e482d30fa13d`. Defects4J Chart/Math/Lang/Time, Qwen2.5-Coder-7B/32B, coverage/compile/pass/mutation outcomes; no direct F2P/RCA. Public package is partial docs/examples/parser/wrapper; README explicitly withholds full source/data, no Defects4J cohort manifest/evaluator and no code license. User's Qwen2.5-Coder-7B matches a paper model but cannot faithfully run CATGen without implementing missing stages. Counts:68 full texts,75 source checks/reviews,7 access-blocked,0 reproduced;44/50 post-reset distinct reads,6 remain. Continue high-fit papers only; timers disabled.


2026-10-15 continued: completed #65 XRepoTest full arXiv v2 and verified public MIT author repo + public MIT-tagged HF dataset. 3,642 focal methods across Rust/Go/Julia/PHP/Ruby, 14 models incl Qwen3, Docker eval/contexts, and novel Invocation Rate metric. Custom user's OpenAI-compatible Qwen2.5-Coder-7B evaluation is straightforward on a bounded language/mode, but differs from paper's Qwen3 models. Dataset ~105 MB base, ~1.69 GB with LSP/RAG; raw repos omitted, Docker `latest` images. No Java/Python, only Defects4J related work, no issue F2P/RCA. Supporting benchmark, not primary bug reproduction. Totals 69/500 read,76 source checks,7 blocked,0 reproduced;45/50 new reads after reset,5 remain. Timers disabled; continue high-fit papers only.


2026-10-15 continued: completed #91 final 2026 EMSE full paper via ORBilu author manuscript (58 pages/22,895 words). Final paper uses Defects4J for class-level compilation/coverage but explicitly no F2P buggy/fixed detection, exception fault detection or mutation. A §6.5 sentence contradicts explicit Limitations; no mutation result table. Earlier 2024 arXiv predecessor did report bug detection, but is a different prior version. Linked MIT 4open package snapshot/README from 2024; visible tree partial and doesn't include full generation/RQ3/RQ4. Counts 70 full text,77 source checks/reviews,7 access blocked,0 reproduced;46/50 fresh reads,4 remain. Timers disabled; prioritize remaining direct oracle/BRT papers.


2026-10-15 continued: completed #93 Test Oracle Automation full 5,912-word perspective paper. Key concepts: assertion/contract/metamorphic oracles, false-positive/negative oracle deficiency, assurance, and public benchmark oracle leakage. Defects4J is only an illustration; no experiment, model, dataset/code artifact or reproduction route. Useful foundational related work, not baseline. Current totals 71/500 full texts,78 source checks,7 access-blocked,0 reproduced;47/50 fresh reads,3 remain. Timers disabled.


2026-10-15 continued: completed #81 Go-UT-Bench full paper and HF artifact check. Public ungated dataset has 5,264 Go code/test pairs, but HF has no license metadata; the paper says upstream repos are permissive. Fine-tunes DeepSeek-Coder-V2-Lite / Llama-3.2 and reports only GPT-4o-mini pairwise judge wins; paper admits no human, runtime/compile/coverage/mutation validation. No training code or model weights. Go-specific SFT data only, not F2P/Defects4J/SWT. Counts 72 full texts,79 source checks,7 blocked,0 reproduced;48/50 new reads,2 remain. Timers disabled.


2026-10-15 continued: completed #82 CANDOR full paper + public source. Strongest concept/oracle fit: natural-language description and Requirement Engineer/Panelist/Curator fix assertions on synthetic Pitest-mutant HumanEvalJava/LeetCodeJava code. Public complete source/data in paper-linked GitHub, but no root LICENSE, 70B Ollama models hardcoded, README/tree layout mismatch. Explicitly excludes Defects4J/SF110, and mutants are synthetic—not historical real bugs. Counts 73/500,80 source checks,7 blocked,0 reproduced;49/50 reads,1 remain. Timers disabled.

2026-10-15 continued: completed #76 EvoOtter full paper/source audit. Direct F2P BRT method; reports SWT-Bench-Verified 77.8%, but main evaluations are TDD-Bench-Verified/SWE-Rebench. No Defects4J/BugsInPy or root-cause labels. Official author page and exact searches yielded no attributable public implementation/evaluator/data package; exact Claude models and no pinned source make reproduction infeasible. High-priority conceptual comparator, not runnable base. #74 remains better for actionable Defects4J analysis. Counts 74/500 fulltexts,81 source checks,7 unread blocked,0 reproduced; fresh-quota 50/50 cap reached. Timers disabled. User says UI shows 90% quota remaining; do not misread as near exhaustion. Stop full-text reading at cap.
