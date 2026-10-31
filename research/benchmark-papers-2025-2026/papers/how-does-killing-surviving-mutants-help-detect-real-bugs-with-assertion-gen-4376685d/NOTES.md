# How Does Killing Surviving Mutants Help Detect Real Bugs with Assertion Generation? A Controlled Experiment

Reviewed: 2026-10-15. Full text: read (24 pages, 14,945 words). Source: public author implementation. Reproduction: conditional.

## Why this is promising

This is a strong Defects4J paper for behavioral oracle analysis. It compares runtime states in fixed/buggy versions, generates a single localized assertion to expose a revealability gap, and asks whether assertions aimed at surviving mutants also expose real bugs. The paper reports 642 bugs across 15 subjects, with 104 revealability-gap bugs; mutation-derived assertions expose 63 of those. At a modeled 30% mutant-killing budget, mean detection probability is 84.5% among those 63.

Its main limitation for this project is scope: no issue text, no root-cause classification, and no LLM test generation. It targets observable state/assertion gaps; most studied bugs require new reachability or infection/propagation behavior. Treat it as a close Defects4J oracle/mechanism comparator, then pair it with a repository-level BRT paper.

## Public artifact and rerun feasibility

Author code: [https://github.com/spideruci/Defects4j_for_Coupling_Effect_Analysis_Through_Killing_Surviving_Mutants](https://github.com/spideruci/Defects4j_for_Coupling_Effect_Analysis_Through_Killing_Surviving_Mutants). The public repository identifies itself as the paper artifact, extends Defects4J 3.0.1, contains the assertion-generation pipeline and data, and documents a Docker Cli-2 example plus CI for Cli-2 and Lang-6b. The repository LICENSE is MIT. The paper PDF is CC BY 4.0. A smoke rerun is feasible from the documented example; full-study rerun is expensive (paper reports approximately 1,177 hours). No source was executed or altered.

The paper cites Zenodo 10.5281/zenodo.21328338, while the currently linked README describes the 2.3 GB Cli-2 Docker archive at 10.5281/zenodo.21013232. Exact full-study Zenodo record/data license and immutable repository commit were not resolved, so an exact full reproduction remains conditional.

## Full-text verification

Official author PDF: https://superhangdu.com/publications/issta-26/ISSTA26.pdf. Read all extracted text in consecutive chunks, lines 1–1440; SHA-256 `1d2f3a46880b83a58bb7c97d8b6b389031de7ab0724fd8a5bc9d6ec6a1affcf1`. Sections 1–10 and references read. Experiment details and threats to validity checked. No model calls or code execution.
