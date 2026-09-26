# ConceptCoder labels → separating relations → TrickCatcher inputs

## Result

On a fresh held-out set of 20 C++ TrickyBugs PUTs, an equal-budget generic planner exposed **8/20** bugs and a planner conditioned on ConceptCoder VD labels exposed **7/20**. Generic-only tasks were `p02709` and `p02787`; concept-only was `p02716`; exact paired McNemar p = **1.0**. All discordant witnesses and all witnesses from the six commonly exposed tasks were checked against the published task constraints. This experiment finds no improvement from using ConceptCoder's seven vulnerability labels to first infer test-input relations.

| Measure | Generic relation planner | ConceptCoder relation planner |
| --- | ---: | ---: |
| Gemini calls per PUT | 2 | 2 |
| PUTs with spec-valid exposure | **8/20** | **7/20** |
| Spec-valid exposing inputs | 24 | 25 |
| Reference-agreed inputs | 192 | 187 |
| Parsed inputs | 197 | 190 |

## Design

This is a second experiment after the direct-label pilot's 7/26 tie. The target paper remains [TrickCatcher](https://aclanthology.org/2025.acl-long.20/). For the final generation call, both arms use its released C++ `geninput_direct` template from commit `a0d285a77efff7c93fc280d606497d9de5e1defe`, SHA-256 `26d075a69cc99a00b7ddd6095634cdc0468fcc54c6a7b09bc6f4a87498f2832b`, with the public problem description and buggy PUT substituted normally. Planning notes are appended after that original prompt, so both arms are explicitly prompt extensions rather than unchanged reproductions.

Both arms use two `gemini-3-flash-preview` calls at temperature 0, thinking budget 0 and output cap 1600:

1. Generic planner: infer exactly three valid corner-case relations from the specification and PUT source.
2. Concept planner: infer exactly three separating relations from the same material plus statement-level ConceptCoder VD labels, connecting labeled operations to specification properties.
3. Each planner's result is appended to the same original TrickCatcher direct-input prompt for the second call.

The concept labels come from the released `ConceptCoder_org` VD annotator, with the documented child-count compatibility guard in `cpp_concepts.py`; its source is not edited. No reference solution, fixed code, known test, expected output or differential result enters either generation prompt. Call order was generic→concept for the first ten tasks and concept→generic for the final ten.

## Held-out selection and oracle

The first pilot consumed the first 30 sorted C++ PUTs that produced at least one of ConceptCoder's seven VD labels. This experiment skipped those 30 and exported the next 40 before scoring. Of the 40, 33 had a specification and at least two C++ references in TrickyBugs v2; the first 20 became the fixed set (`p02702` through `p02787`). Thus no prior task from the 26-task direct-label study was reused.

Each input was run against up to three independent reference programs and the PUT under a three-second limit. A raw exposure requires all references to exit and agree after whitespace normalization, while the PUT crashes or returns a different output. The nine tasks with any raw exposure received exact shape/range validators from their published specifications. The sole invalid raw exposing input was in the generic arm on `p02726`; excluding it did not change task exposure.

Representative valid discordant witnesses:

- `p02709`, generic-only: `N=10` with three `10^9` values at each end and small values in the middle; reference `42000000008`, PUT `8525163528`.
- `p02716`, concept-only: `[-5, -10, -15]`; the requirement chooses exactly one non-adjacent element, so reference `-5`, PUT `-10`.
- `p02787`, generic-only: monster health `10000` and one spell `(9999, 1)`; reference `2`, PUT `2000000010`.

The saved plans show why the labels added little. On `p02709` and `p02787`, both planners independently described the relevant off-by-one or overshoot relation. On `p02716`, both discussed negative values and exact-cardinality selection, but only the concept arm's final generation happened to include a distinguishing input. The seven VD labels mostly mark arrays, allocation and bounds operations; Gemini can already infer these code facts from the source, while the benchmark defects are algorithmic relations.

## Reproduce without model calls

Exact cards, plans, raw responses and scored rows are archived in [`research/results/trickcatcher-cpp-relation20`](results/trickcatcher-cpp-relation20).

```bash
.venv/bin/python -m trickcatcher_pilot.cpp_validity \
  --baseline research/results/trickcatcher-cpp-relation20/generic_plan_eval.jsonl \
  --concept research/results/trickcatcher-cpp-relation20/concept_plan_eval.jsonl
```

The supported conclusion is narrow: direct VD labels and a Gemini relation-planning layer both fail to improve this logical-bug test-generation sample. A further C++ experiment should use ConceptCoder's branch-prediction abstract-value concepts with real traces, or switch to a memory-safety benchmark aligned with the VD taxonomy. Repeating more prompt variants on the same TrickyBugs tasks would invite tuning to the observed outcomes.
