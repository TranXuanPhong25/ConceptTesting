# Beyond Heuristics? Rethinking Targeted Unit Test Generation in the Era of LLM Agents

Reviewed: 2026-10-15. Full official 21-page PDF read; Zenodo artifact metadata and embedded README checked; implementation inspection partial. Grade: B- for targeted-testing support.

Official paper: [LIPIcs ESEM 2026.47](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.ESEM.2026.47), published 5 October 2026, CC BY 4.0.

The authors evaluate 3 agent scaffolds × 3 LLMs on 210 Java runtime-exception bugs in 66 projects. The input gives the buggy code, exception type and exact target line; success requires the exception to match and the target line to appear at the top of the stack trace. Best is Claude Code + GPT-5 (89.5%); UnitCon 49.6%, EvoSuite 39.4%, Randoop 21.3%. DeepSeek-V3.2 with OpenCode reports 65.2% at $0.04/task. Manual analysis of 200 failures (κ=.76) identifies insufficient exploration, inadequate reasoning, tool misuse and incorrect focus.

Zenodo 20283766 has matching title, CC BY 4.0 metadata, and a 2.16 GB `ESEM-2026.zip`. Read its embedded README via range request: it lists 210 project snapshots, Docker images, `run_evaluation.py`, `build_image.py`, and subset controls. The full archive/code manifest was not inspected because of size. A bounded own-model pilot with an OpenCode endpoint appears plausible, but custom model configuration and runner behavior remain unverified.

Important scope limit: target location/exception are provided; this is targeted exception generation, not issue-report-driven BRT/F2P or a root-cause taxonomy. The failure analysis labels agent failure modes, not software fault causes. No code/model run. See `audit/reviews/069.json` and `public_evidence/source_audit.md`.
