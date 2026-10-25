# Thesis outline — concept-guided test generation (2026-10-25)

**Working thesis:** a controlled empirical map of concept guidance across model
capability, input construction and oracle design. Treat a concept as an explicit
behavioral/definitional abstraction; separate its content from extra calls,
concrete inputs, program yield and abstention. The current evidence supports
conditional findings and failure mechanisms, not a general concept benefit.

## 1. Empirical map: where the intervention acts

Use the [64-comparison synthesis](analysis/concept_effect_synthesis_20261024/SYNTHESIS.md)
as an inventory, with the version reports below overriding its earlier open
questions. Its weak/strong explanation is a hypothesis, not a causal model-size
result; model, provider and task packages differ across versions.

- **Matched controls remove broad input-guidance claims.** v11_fair: concept
  61.0, placebo 57.7, plain 55.7 bugs/run; concept–placebo paired 26–22,
  p=.67. v31/v34: fault-template 18, plain 15, placebo 12 tasks/33;
  concept–placebo 8–2 detection but FP tests 27>23, so v34 rule not met.
  [Synthesis](analysis/concept_effect_synthesis_20261024/SYNTHESIS.md),
  [v34 report](analysis/v34_ftplacebo_results.md).
- **Strong-model ceiling is protocol-specific.** v53 Sonnet tester: every
  arm 5/6, FP 0; v54 Sonnet variants: both arms 6/6; Codex v28: arms
  16–17/20. v55h Haiku oracle: defn=interpretation=placebo 21/33,
  411 confirmed tests each, FP 0. These compare task packages, not controlled
  capacity tiers. [Synthesis](analysis/concept_effect_synthesis_20261024/SYNTHESIS.md),
  [v55h](analysis/v55h_haiku_interpretation/RESULTS.md).
- **Construction success does not supply a correct oracle.** v68: concept,
  plain and equal-evidence raw each 1/6, inputs-only 0/6; FP 9/8/6/2.
  On case 131, 3 constructed inputs expose a bug; concept and inputs-only
  copy displayed PUT outputs into expected values on 2 shown witnesses.
  [v68](pipelines/v68_symbolicgen/RESULTS_V68.md).
- **Separate interface failure from efficacy.** v69 saved-response replay:
  22 realized case-124 inputs, all invalid empty strings, 0 sensitive;
  v70 domain repair: 8 valid realized inputs, 0 sensitive, gate 0/6.
  Fresh v70: 4 outer-schema failures + 2 abstentions; v71 schema repair:
  6/6 valid explicit abstentions, 0 hypotheses, gate 0/6. These gates never
  instantiate an efficacy treatment. [v69](analysis/v69_typedwriter/RESULTS.md),
  [v70 CPU](analysis/v70_domainwriter/RESULTS_CPU.md),
  [v70 fresh](analysis/v70_domainwriter/RESULTS_FRESH.md),
  [v71](analysis/v71_writercontract/RESULTS.md).
- **Writer burden and semantic correctness remain distinct.** v72 diagnosis:
  raw 2 prose/full 2 abstentions; 0/2 fully supported diagnoses, 1 useful
  input. v73 GPT-OSS-120B repeats these 4 requests: raw case 85 supported,
  raw 124 incorrect, full 2 abstentions. v72 symdiff is a separate CPU
  experiment: 0/10 targeted new confirmations; solver alone 12/33,
  union remains 25/33. [v72 diagnosis](analysis/v72_diagnosisprobe/RESULTS.md),
  [v73](analysis/v73_ossdiagnosis/RESULTS.md),
  [v72 symdiff](analysis/v72_symdiff/RESULTS.md).

## 2. Oracle-side concepts: precision, yield and abstention

A defensible limited claim: a literal definitional oracle can reduce false
positives with a weak/mid writer, while task detection and coverage can fall.
This is not a claim that concept headings reliably improve the oracle.

- **v49, Qwen-32B, 33 PUTs:** defn/brute/plain-implementation confirm
  12/10/5 tasks; FP 145/100/86, precision .59/.62/.48; valid programs
  93/78/38 of 165. Concept vs brute is NO-GO; where both have at least
  2 valid programs, detection is 10/10. The 2 defn-only tasks follow
  program yield. TC native comparison is 7 tasks, precision .23, FP 221;
  family comparisons are secondary and fail the absolute-FP rule.
  [v49](analysis/v49_defn_oracle/RESULTS.md).
- **v56 fresh LiveCodeBench, Qwen-32B, 11 tasks:** defn vs brute gives
  **5 vs 47 FP, precision .918 vs .510** (rounded .92 vs .51), but
  confirms **5 vs 6 tasks**, paired 0–1: primary NO-GO. Plain confirms
  4, FP 36, precision .410. The reduction partly reflects abstention
  (e.g. problem 3771), partly better oracle values (3562: 20 defn
  confirmations vs 1 brute). Report emitted-test denominators 61 vs 96,
  validity limitation on 3784, and generator failures on 4/11; do not
  claim task-level replication. [v56](analysis/v56_lcb_fresh/RESULTS.md).
- **v64 Haiku caveat:** defn=brute 21/33, FP 0, precision 1.00;
  plainimpl 25/33, FP 19, precision .96. Paired defn–plainimpl 0–4;
  brute programs fail to finish on exposing inputs for those 4 tasks.
  No-vote exposing inputs: defn 1297/5155, brute 828/5155, plainimpl
  6/5155. Registered verdict: inconclusive. The family ranking reverses
  with writer strength; precision must be reported alongside abstention
  and task detection. [v64](analysis/v64_haiku_plainoracle/RESULTS.md).

## 3. v76/v77 results placeholders — prepared, not run

[PREREG_V76](pipelines/v76_ossmodel/PREREG_V76.md): GPT-OSS-120B and DeepSeek-V4-Flash/OpenRouter, separately reported,
33 fixed PUTs, K=1, 3 LLM arms × 3 calls = 297 logical calls, frozen v34
prompts/tools/scorer, $3 hard cap. Fill once after authorization: per-arm
confirmed tasks / FP tests / schema failures / abstentions / tokens / cost;
primary fault-template–placebo paired wins–losses and FP comparison; descriptive
comparisons with plain. If plain >=28/33, label **ceiling, uninformative about
concepts**. No enlargement, K increase or rerun to rescue an outcome.


v76 was registered as v74_ossmodel, renumbered before any output. Each model has
its own $3 cap, freeze, cache and ledger; no pooling. Both remain prepared only.

[PREREG_V77](pipelines/v77_combined/PREREG_V77.md) (registered as v75_combined,
renumbered before any output) tests the full v11 strict/matched K=3 machinery
with a <=3-hint v7/v31 merge, fixed HumanEval dev113 and VibePass half33.
For each dataset AND model, primary combined vs placebo requires paired
wins>losses AND FP<=placebo. Report concept-hybrid/plain-hybrid/toolinput as
secondary controls. This is a combined-package comparison, not isolation of
fault-type content alone. No enlargement or rerun. Task-major complete paired
prefixes after a cap stop are descriptive, not efficacy verdicts. DeepSeek's
reasoning-inclusive planning estimate exceeds the $10 cap, so full completion
is not promised. No v76/v77 efficacy data exist.
