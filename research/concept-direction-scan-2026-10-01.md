# Where can concept guidance actually help? Scan of 11 papers (2026-10-01)

Why this scan: on EvalAndMitigate (Defects4J, 78 methods) none of m1-m6 beat the Advanced-docstring baseline beyond
run-to-run noise. The failure mode was consistent: whenever concept content became the ORACLE and was derived from the
buggy code, it copied the bug (m3: misguided methods 3→16); concepts that only chose WHERE to look were harmless but
added nothing on their own (m4); a blind answerer with independent evidence was safe (m6). Hypothesis for this scan:
concepts pay off where the oracle is independent of the code under test and concepts drive where-to-look decisions.

Method: four read-only research agents (2026-10-01), each read the full text and inspected the artifacts; nothing was
implemented or run. Notes in `research/llm-test-generation-2025-2026.md` and `research/fulltext-batches/` were checked
against full text.

## Ranking

| rank | paper | oracle independent of code under test? | concept plug-in | runs on this arm64 Mac? | pilot feasibility | verdict |
|---|---|---|---|---|---|---|
| 1 | #85 DFUZZ "Your Fix Is My Exploit" (ICSE'25) | yes: crash signals (CPU path; CPU/GPU diff needs CUDA) | already concept-shaped: tool finds `TORCH_CHECK`s, LLM turns them into typed edge cases from OTHER APIs' guards (not the code under test). Untested causal question: blind / placebo / "absent check" arms | yes (CPU, native arm64 torch/TF wheels); repo has 37 `bug.py` reproducers, no license | 4/5, est. < $20 Gemini Flash | promising |
| 2 | #67 AndroB2O, failure-based oracles from Android bug reports (ASE'25) | yes: must fail on buggy APK, pass on fixed; intent from the bug report | concept card (11 oracle categories with human gold labels in the artifact, BEE observed/expected sentences, candidate elements by string match) added ON TOP of the full report (replacing the report hurt: 31% vs 47%) | offline LLM part yes; executing oracles needs an Android emulator API 23 on the host, ABI of the APKs unknown → ask before trying (AGENTS rule 4) | 4/5 offline, 2/5 executed | promising |
| 3 | #36 PBT vs EBT edge cases (arXiv 2510.25297, AIware'25) | yes: prompt has only signature + docstring; invariants + timeout | 4 of 5 PBT misses are input-domain choices → concepts set Hypothesis strategy bounds / `@example` witnesses | yes (pure Python, Zenodo CC-BY-4.0) | 4/5, < $1, but n=16 | promising (cheap, underpowered) |
| 4 | new arm on our Defects4J set: blind property-only oracle | relational assertions only (round-trip, overload agreement, invariants, metamorphic), no literal expected values, m6 blind evidence pack | tools pick the relation family | yes (existing Docker setup) | 4/5 | worth one arm — only direct test of whether property-form oracles escape the copy-the-bug failure |
| 5 | #45 KTester "Knowledge Matters" (ICSE'26) | no: compile/pass/coverage on current code; repair rewrites assertions to match it | branch/throw/boundary inventory (Spoon) + uncovered JaCoCo branches drive case design and repair | yes in principle (JDK 17); Windows-only harness (`;` classpath, `cd && …` via subprocess) would silently fake success on macOS → patching vendor code needs OK (rule 3); no license | 2/5 | maybe (targets generator reach; no bug oracle) |
| 6 | #89 MultiFileTest (ACL Findings'26) | no: pass rate on given code, coverage | tool-computed executability facts (package layout, exports, visibility, stdin) | yes (MIT, HF dataset; Java has 19 projects) | 4/5, $1-3/run | maybe — a rule-based autofix control will likely match it |
| 7 | #84 CKGFuzzer (ICSE-Companion'25) | coverage/sanitizers yes, but bug-vs-misuse triage is an LLM judge (~35% precision) | CodeQL-mined API protocol concepts to cut misuse drivers; deterministic "crash frame in driver" pre-filter | no: OSS-Fuzz `base-builder` image is amd64-only → stopped (rule 4) | 1/5 here, 3/5 on x86 | maybe (needs x86 host; precondition-as-oracle trap) |
| 8 | #115 ARMeta, multi-agent MRs for REST APIs (COMPSAC'26) | yes: MRs from the OpenAPI spec, agents never see code | CRUD groups, inverse operation pairs, enums/required fields → MR templates | no: code host unreachable; SUT images amd64-only → stopped (rule 4) | 1/5 | maybe (cleanest design, not runnable) |
| 9 | #87 abstract pentest cases from Palladio architecture (ICSA-C'26) | no executable oracle; expert yes/no, n=15 per configuration | entry→connector→asset paths, shared servers, zone annotations (present but not serialized) | yes (Java 17; API key hard-coded in `StandaloneRunner` → wrap, don't edit) | 4/5 to run, little to measure | maybe |
| 10 | #51 LLAMAFUZZ (AST'26) | yes (Magma canaries) | gain comes from fine-tuning, not reasoning; our magma/ work already answers it | no: CUDA + 4-bit + amd64 Magma | 1/5 | no |
| 11 | #105 ChekProp, PBT for CPS | no: properties read from code, "executable" = passes on current code, no fault-detection study | invariants over state | yes but no bugs to find | 2/5 | no (negative control at most) |
| 12 | #103 RAG test cases from SRS (IJIES 2026) | no system under test; BLEU + human score | shall-statements, numeric boundaries | runs, data not released | 2/5 | no |

## Cross-cutting conclusions

1. The papers where concepts plausibly help all share two properties: an oracle that does not come from the code under
   test (crash signal, bug report + buggy/fixed pair, spec-only invariants), and a concept that decides where to look
   (which edge case, which GUI element/property type, which input range). That matches every lesson from m1-m6.
2. Several papers are already concept-shaped (DFUZZ, CKGFuzzer, ARMeta, KTester). The open question is causal, not
   architectural: none of them has a blind or placebo arm, which is exactly the design this repo already has
   (magma shuffled placebo, kite_concept McNemar/bootstrap).
3. Traps to carry over: preconditions mined from the library become oracles that encode the bug (CKGFuzzer labels a
   missing defensive null check as driver misuse); repair loops that run "until it passes on the current code" push
   properties toward the bug (ChekProp); test-volume metrics reward copying (KTester, MultiFileTest).
4. Platform blockers found (rule 4, nothing emulated): OSS-Fuzz base-builder, ARMeta SUT images, Magma images are
   amd64-only; AndroB2O needs a host Android emulator with unknown APK ABI.

## Edits already made to the notes by the agents (review before committing)

- #45 / #89 agent: `fulltext-batches/batch-03.md` (#45 numbers, inconsistencies, no license, Windows harness, Drive data,
  extra models), `batch-05.md` (#89: "2,389 tasks" removed, Java = 19 projects, metrics, oracle caveat, repo/version
  mismatch), `artifacts.md` rows 45/89, `llm-test-generation-2025-2026.md` rows 45/89 (#45 method description fixed).
  `llm-test-generation-2025-2026-fulltext.html` still embeds the old text (looks generated, left alone).
- #36 / #105 / #115 agent: `batch-02.md` #36 (spec-only prompt, per-task results, McNemar p=1.00, hand-filter counts,
  Zenodo line); `batch-06.md` #105 (9 programs = 6 Pi apps + gpiozero InputDevice, recall/precision/executable numbers,
  repair loop disabled, no fault-detection study, no license) and #115 (full-text numbers, contract/robustness caveat);
  `artifacts.md` rows 105 and 115.
- #67 / #87 / #103 and #51 / #84 / #85 agents: no edits.

## Pending corrections (not applied; file · current claim · corrected claim · source)

- `llm-test-generation-2025-2026.md` #67 · "Generate properties/invariants plus structured or randomized inputs" · two-step chain: pick failing GUI element, then write UIAutomator assertions; no input generation · paper §V
- `llm-test-generation-2025-2026.md` #87 · "Retrieve … knowledge"; "red/green oracle" · no retrieval: prompting over the serialized architecture model + scenario text; non-executable test cases judged by experts · arXiv 2603.23698 §III-IV
- `llm-test-generation-2025-2026.md` #103 · year 2025 · journal issue 2026 (Vol 19 No 1), received Sept 2025 · PDF header
- `llm-test-generation-2025-2026.md` #51 · "Mutation-guided … surviving mutants" · fine-tuned LLM seed mutation inside AFL++; no mutation testing · LLAMAFUZZ v4 §3
- `llm-test-generation-2025-2026.md` "Directed fuzzing" theme row · LLAMAFUZZ and CKGFuzzer listed as directed fuzzing · both are coverage-guided, no target site · v4 §3, CKGFuzzer §III
- `batch-03.md` #51 · "reached 85 unique bugs … outperformed top competitor by 41 bugs" · 41 bugs triggered on average, 47 unique vs AFL++ 46 / Moptafl 42 / Honggfuzz 37 / FairFuzz 31; "85" is in neither v3 nor v4 · v4 §4.3
- `batch-03.md` #51 · "+27.19% branches" · v1-v3 abstract figure; v4 Table 3 averages ≈ +26%; text says 11/15 significant, table shows p<0.05 on 9/15 · v4 Table 3
- `batch-03.md` #51 · "Magma + 15 real-world targets" · Magma 9 projects / 21 targets + real-world 12 projects / 18 targets (Table 3 lists 15) · v4 Table 2
- `artifacts.md` #51 · add: no license; CUDA + 4-bit + System V IPC; AFL++ fork (Apache-2.0, `StructureFuzzer-stable`); code default temperature 1.25 vs 1.0 in the paper · repo
- `batch-04.md` #67 · ReBL figures omitted · ReBL 19/32 (59.4%); with setup steps 75/136 (55.1%, precision 93.8%); Table IV sums to 169, not 152 (paper inconsistency); full benchmark = 17 + 152 + 16 reports · paper §VI
- `batch-05.md` #84 · "8.73% … 84.4% less review" · +2.3 pp absolute / +8.3% relative branch coverage vs PromptFuzz (Table I); 84.4% is the share of crashes auto-labelled as driver misuse, not measured effort; venue ICSE-Companion 2025 pp. 243-254 · Tables I, III, Crossref
- `batch-05.md` #85 · "no defensible API count" · 1,593 PyTorch / 3,316 TensorFlow APIs; coverage 1,455 / 2,340; 7.1% / 16.8% of TitanFuzz's LLM calls; 132 edge cases / 20 type patterns; 37 bugs (24 abort, 4 segfault, 5 runtime error, 4 CPU/GPU inconsistency) · Tables III, V, VI
- `batch-05.md` #85 · concept schema includes an "expected failure mode" · edge cases are input conditions only; no ablation isolates check-derived edge cases · §III, §V-D
- `batch-05.md` #87 · "no dataset cardinality" · 3 case studies × 5 CWEs = 15 test cases per configuration, 6 configurations; best Gemini-3-Pro one-shot 13/15 correct · Table I
- `batch-05.md` #87 · fields "trust boundary, precondition, test action" · metamodel fields: CWE, violated property, threat, attack vector (name, connector, entry point, asset); zone annotations not passed to the LLM · arXiv §III-B, `PalladioArchitectureSerializer.java`
- `batch-06.md` #103 · source link oaji.net · returns 502; use publisher PDF https://inass.org/wp-content/uploads/2025/09/2026013104-3.pdf; add caveats: held-out ablation repeats 0.72/4.8 exactly, retrieval never ablated, no inter-rater agreement · PDF §4.3
- `artifacts.md` #84 · add: MIT license; OSS-Fuzz base-builder image amd64-only; OpenAI-compatible config · repo, gcr registry
- `artifacts.md` #85 · add: no license (verified 2026-10-01 via GitHub API); torch==2.2.0 pinned; hard-coded model names; 37 `bug.py` reproducers (36 `ori.py`) and initial programs released · repo
- `artifacts.md` #87 · add: GPT results include a cloudInfrastructure scenario not in the paper; per-test-case expert scores not released · Zenodo zip
- `artifacts.md` #103 · models list · add llama3.3:70b; app wires only GPT-4o, mistral, marco-o1; no LICENSE file; `requirements.txt` referenced but missing · Table 2, repo tree
- `artifact-reproduction.md` · header describes a Linux x86_64 host · this machine is arm64 (Apple Silicon), 16 GB RAM

Sources: arXiv 2510.25297, 2505.23549, 2605.28321, 2511.14224, 2603.23698; DOIs 10.5281/zenodo.16434613,
10.5281/zenodo.15556567, 10.5281/zenodo.19170498; github.com/DFUZZ-ICSE/DFUZZ, github.com/security-pride/CKGFuzzer,
github.com/SecurityLab-UCD/LLAMAFUZZ, github.com/SYSUSELab/KTester, github.com/YiboWANG214/ProjectTest,
github.com/khesoem/ChekProp, github.com/bondif/srs-to-testcase-generator, aclanthology.org/2026.findings-acl.1403.
