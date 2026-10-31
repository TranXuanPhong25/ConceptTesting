---
name: kite-vs-template-paper
description: 2026-10-25 KITE not usable as paper-swap base (no code/KB, Java, ~200k tok/method, repeats v7/v31/v54); agentic-pbt (2510.09907) is the public concept-template candidate
metadata:
  type: project
---

User asked (2026-10-25): assess the KITE direction, or find a paper that defines concept-like templates so we can
swap its template part or test the paper's version on another metric. Assessment only, no run.

**KITE (arXiv 2607.11573):** no author code, no 1,325-mechanism KB, no 172-task manifest (re-checked web 2026-10-25).
Using it = reimplementation (AGENTS rule 2, needs approval) and would be our version, not the paper's. Java/Defects4J,
GPT-5.4, ~177k–225k tokens per method. Generation sees the correct version (oracle given); our setting is a buggy PUT.
Core loop mechanism → synthetic bug → kill feedback already tried: v7 MUTANT, v31/v34 fault templates, v37 Mokav-mutant,
v42/v46 mutant oracle, v54 Sonnet mutant concept. At that audit date, retrieval from a real-bug KB remained untried.

**Template paper with public code:** Agentic PBT (Maaz, DeVoe, Hatfield-Dodds, Carlini; arXiv 2510.09907,
github.com/mmaaz-git/agentic-pbt, no LICENSE file). `paper/hypo.md` (Claude Code command) lists 8 property patterns:
invariants, round-trip, inverse ops, multiple implementations, mathematical (idempotence/commutativity), confluence,
metamorphic, single entry point. Paper metric: valid/reportable bug reports on 100 PyPI packages (Opus 4.1 rubric +
manual). Swap idea: copy hypo.md, replace only the pattern list (none / placebo / our concept), measure on ground-truth
benchmark (bug-revealing tasks, FA, abstention). Prior art risk: v26 property oracle (Qwen) negative, v27 Codex×strict
prec 1.0, v41 IO relations no-go, strong writers at ceiling (v53/v55h/v64). Rejected: property-templates paper
2607.09072 (PySpark/Lean, no code), ACH Meta (no code).

**$0 check done 2026-10-25:** research/agentic-pbt/REPORT_PATTERN_AUDIT_20261025.md. List shapes ~64% of tests, but rubric score is flat across patterns (9.8–11.6), ~7/18 valid bugs come from unlisted docstring claims, crash checks have the top yield; saved run cost $5,474 (median $5.81/call, Opus 4.1). NO-GO for a paid swap.

**How to apply:** do not propose the agentic-pbt pattern swap again without a new hypothesis; the first step was the $0 check on agentic-pbt's saved `paper/results` (which pattern produced valid
reports) before any paid run; ask budget. Related: [[concept-priorwork-proposal]], [[v26-proporacle]], [[signal-not-more-data]].

2026-10-28 (Codex), user-requested comparison with KTester 2511.14224 (current HTML v3)
and KITE 2607.11573v1: re-read primary methods/baselines and local source/results.
The external-pattern retrieval gap has now been partly addressed by
[`python_bug_concepts`](../python_bug_concepts/VERSIONS.md), through v6; do not repeat
the old assessment as if no external concept retrieval exists. Its sources are lint
rules/language documentation plus curated semantic cards, not a historical bug/fix-pair
KB. Its `how` describes mechanism/trigger, whereas KITE's `how` is injection intent.
V6 is conditional concept/site retrieval on buggy source, not the complete KITE
correct-code → injected-bug → iterative-test workflow. V6 utility is unmeasured;
v2/v3 have a separate completed 40-task utility diagnostic, with no placebo/holdout.
See [[python-bug-concept-base]] and the linked results for numbers and limitations.

KITE's evaluated baselines are Direct LLM, ChatUniTest, CoverUp, MutGen, KTester,
and EvoSuite. Local linefacts has plain controls and an executed adapted CoverUp;
MuTAP is executed but is NOT MutGen. MutGen has a source/protocol audit only
([note](../research/mutgen/ORACLE_PROTOCOL.md)). No named ChatUniTest/KTester/EvoSuite
baseline run was found in linefacts source/reports. Generic feedback/mutation
experiments are partial mechanism overlap, not reproductions of those methods.
Baseline evidence: [final dev comparison](../trickcatcher_linefacts/analysis/final_protocol_v11_dev.md).
KTester's other baselines are ChatTester, HITS, and Deljouyi et al.'s SBST/readability
UTGen; that UTGen is distinct from the UTGen/UTDebug paper audited in this repo.
HITS has a literature note, not a recorded baseline run.
