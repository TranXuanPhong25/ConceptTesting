# Results: replication + concept-guided mitigation attempts (2026-09-29 → 10-02)

Paper: "Evaluating and Mitigating the Misguidance Effect of Buggy Code in LLM-Generated Unit Tests"
(arXiv 2607.22883). Everything outside the upstream files was added by us: `run/` (arm64 Docker pipeline, Gemini shim,
scoring) and `m1_*` … `m7_*` (one folder per method, each with README.md + RESULTS.md).

**Verdict: the replication works; the improvement attempt failed.** On our subset, the paper's Advanced docstring is
the best config. None of the seven concept-inspired methods (ConceptCoder, arXiv 2603.23470) beats it beyond
run-to-run noise. Several of them are clearly worse on misguidance.

## Setup
- 78 focal methods / 60 Defects4J 3.0.1 bugs (Lang 51, Gson 12, Codec 7, Cli 5, Csv 3). This is a subset of the
  paper's 318 methods.
- Gemini 2.5 Flash via Vertex AI, thinking off. Upstream notebooks run unchanged through `run/nb2py.py` in an arm64
  Docker image (`docker/Dockerfile`, Java 11, py3.12).
- M (misguided) = passes buggy, fails fixed. E (effective) = passes fixed, fails buggy. FP = fails both.
  red-prec = E / (E + FP).
- "Clean" scoring: the upstream counters score every test of a run that failed with an empty error report as M or E.
  `run/summarize.py` drops those methods (e.g. raw Advanced M 33 → clean 9). Arms are compared on the intersection of
  clean methods (74-75), with exact McNemar on per-method "≥1 M" / "≥1 E".

## Baselines (`run/BASELINES.md`)
| config | M | E | FP | red-prec | ≥1 M | ≥1 E |
|---|---|---|---|---|---|---|
| Doc W/ Code (buggy body in prompt) | 20 | 70 | 166 | 0.297 | 8 | 20 |
| Only Doc (paper's method) | 10 | 77 | 300 | 0.204 | 5 | 27 |
| **Advanced Doc** (fix-then-describe docstring) | **9** | **95** | 268 | 0.262 | **3** | **30** |

M ranks as in the paper (Advanced < Only Doc < Doc W/ Code; paper, Flash, 318 methods: 1.67% / 2.39% / 3.23%).
E is higher than in the paper and Advanced leads (8.9% vs 6.4% Only Doc); in the paper Only Doc 4.60% ≈ Advanced 4.46%.

## Methods (all vs Advanced Doc unless stated; details in each folder's RESULTS.md)
| folder | idea | ≥1 M | ≥1 E | verdict |
|---|---|---|---|---|
| m1_test_review | blind reviewer keeps/rewrites/abstains generated tests by spec entailment | Only Doc 5→4; Adv 3→2 | Only Doc 27→**18** (p=0.004); Adv 30→27 | hurts: docstrings are silent exactly where bugs live, so the filter drops E tests |
| m2_concept_diag | diagnostic: do C1-C8 concepts cover the bugs? | – | – | concepts cover 90% of bugs; regex labels only P/R 0.56; docstring verdict does not predict E |
| m3_concept_spec | concept-faceted spec (input → expected) written from the buggy code | **16** vs 3 (p=2.4e-4) | 22 vs 30 | worst arm: rules copy the bug, "unspecified" almost never used |
| m4_concept_inputs | m3's input classes only (no outcomes) appended to Advanced | 7 | 30 | +51% tests, same E, red-prec 0.262→0.196; placebo list equal |
| m5_blind_concept_spec | m3 schema without the focal body (A), + original Javadoc (B) | A 9, B 3 | A 24, B 27 | blind halves copying; Javadoc is the useful intent source; B ≈ Advanced |
| m6_agent_oracle | another agent answers intent questions instead of a human | blind 2 / sees-code **8** (p=0.031) | 30 / 28 | blind answerer safe, no gain; code-reading answerer copies the bug |
| m7_property_oracle | relation-only assertions vs example assertions, same info | 4 vs 3 (p=1.0) | 30 vs 31 (p=1.0) | null: Flash ignored the form (57% of "relation" tests still literal) |

## What we learned
1. **An oracle derived from the buggy code copies the bug.** The more a method forces explicit expected behaviour
   from the code (m3 rules, m6 sees-code answers), the more M. Concepts used only to pick inputs (m4) are harmless
   but add nothing.
2. **Only independent intent helps, and only up to the baseline.** Hiding the body (m5 A, m6 blind) cuts copying;
   developer Javadoc is the best independent source (m5 B, m6 blind). The remaining M comes from Javadoc written in
   the buggy era that documents the bug (Lang_35, Gson_4).
3. **Assertion form is not the lever.** Every M test in m7 is a literal or exception oracle, never a relation. But
   relation-only tests find few bugs (strict subset: ≥1 E 12 vs 31, p=7e-5), and Flash does not follow the
   instruction reliably.
4. **The subset is underpowered.** 15-18 of 75 methods flip their ≥1 E status between two single T=0 runs (m4).
   Gson_4 (one bug, 6 methods) and Cli_1 (M in every config) dominate several totals; each RESULTS.md reports the
   numbers without them.
5. Advanced Doc's advantage most likely comes from its "describe the corrected implementation first" step (our
   reading of 10 examples, not ablated), which no concept method reproduced.

## Caveats
- Single runs per config, 78 of the paper's 318 methods, one model (Flash, thinking off).
- Upstream test generation passes no temperature (Gemini default), while the m* generation scripts use T=0. So
  comparisons of an m* arm against a baseline also differ in temperature; each method's primary contrast does not.
- The public release lacks the advanced-docstring prompt code. `utils/prompt_formats/new_prompt_formatter.py` gets
  the base-model postfix copied verbatim from `Prompt_example/Advanced_Docstring_Prompt_Base_Model` (3-line edit).
- Generated prompts, completions and evaluation logs are gitignored (`data/prompts/`, `data/rq1/logs/`); the m*
  folders keep the LLM caches, consoles and analysis outputs.
- Security: evaluation runs LLM-written Java. Run it with `NO_ADC=1 bash run/dock.sh …` (no gcloud mount); m7 did,
  m1-m6 ran before this switch existed.

## Reproduce
`run/BASELINES.md` (baselines), `run/METHODS_BRIEF.md` (shared rules), `m*/README.md` (exact commands).
