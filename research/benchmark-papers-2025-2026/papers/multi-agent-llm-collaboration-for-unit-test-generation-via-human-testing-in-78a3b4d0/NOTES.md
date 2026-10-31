# Multi-Agent LLM Collaboration for Unit Test Generation via Human-Testing-Inspired Workflows

Reviewed 2026-10-15. Full 14-page arXiv v1 read: 11,090 extracted words. Very high conceptual fit; exact paper replication conditional.

## Why it matches the thesis

TestAgent has an explicit Planner → Generator → Reviewer loop. The Planner derives behavioral test requirements; the Generator uses a test-specific repository knowledge graph and execution feedback; the Reviewer checks coverage and mutation adequacy. If a generated test fails, a root-cause step distinguishes a test flaw from a real defect, with a three-model confirmation vote. The authors manually validate 154 of 167 suspected real defects (92.22% precision) and categorize root causes: insufficient input validation 58.44%, boundary conditions 20.13%, inconsistent state 14.29%, missing exception handling 5.19%, loops 1.95%.

The main evaluation uses 1,454 methods from six Java projects (five projects from Defects4J, but fixed/current code rather than buggy/fixed historical task pairs), plus an internal 658-method industrial set and a 141-method Python set. The paper evaluates Qwen3-30B-A3B on 2×A100 and GPT-4o/DeepSeek V3; local Qwen3 still yields 60.44% mutation score and better results than ChatUniTest GPT-4o, while industrial bug labels are non-public.

## Source/reproduction evidence

Main paper has no source/data availability link. An official FSE tool demonstration by overlapping authors links [iSEngLab/TestAgent-VSCode-Extension](https://github.com/iSEngLab/TestAgent-VSCode-Extension). Its public MIT repo contains a full FastAPI backend, Planner/Generator/Evaluator, graph retrieval, CKG construction JAR and VS Code extension. README reports the same headline coverage and 154-bug result, but authorship differs and the repo is not cited by the arXiv paper; treat it as a related implementation, not proven exact artifact. MIT LICENSE also has placeholder copyright “Your Name”. Main paper’s 1,454 method list, UTXXX data, exact 154 defect cases and result logs are unavailable from the linked source.

A Qwen-compatible endpoint may work: companion backend config uses LangChain `ChatOpenAI` with configurable `OPENAI_API_BASE`; however, no run was performed. Exact reproduction is conditional on resolving artifact version/provenance and dataset access. This is current-code unit testing and bug discovery, not issue-report-to-BRT or historical Defects4J reproduction.

Full text SHA-256 `9e81f59f63f808bedd8ddd226672e0ee9dca0bbfd15fc3de8fa48a74f0671dd1`. Related tool archive SHA-256 `f586bd36345ca00ed586affe796de29156b74fe5e13e25ad9ac528d4bd03a2a7`.
