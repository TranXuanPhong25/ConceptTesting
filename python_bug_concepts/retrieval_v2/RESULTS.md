# HumanEval retrieval results — 2026-10-26

**Primary result: 74/113 (65.5%)** with a correct returned bug-family concept and its first source site correct. Target: at least 57/113. Target met.

This is a development-informed internal engineering result. Labels and faulty sites were manually attributed by one author; native grading confirms input validity and failure, rather than proving attribution automatically. The semantic extension saw all public source. The audit measures a frozen ranker, not unseen corpus/label design.

## Same-input comparison

| System | Correct family top-1 | Correct family top-3 | Family + first site in top-3 |
| --- | ---: | ---: | ---: |
| Original 132 cards + BM25 | 1/113 | 1/113 | Not applicable: no source binding |
| Extended 162 cards + BM25 | 14/113 | 30/113 | Not applicable: no source binding |
| Extended cards + structural v2 | 73/113 | 88/113 | 74 |
| Constant 3 most frequent development labels | 18/113 | 30/113 | Not applicable: no source binding |

V2 correct family plus any of the maximum three returned sites per concept: **83/113**. This secondary score allows more site choices than the primary result.

## Fixed split

| Split | Tasks | Correct family top-3 | Family + first site | Family + any of <=3 sites |
| --- | ---: | ---: | ---: | ---: |
| Development | 73 | 57 | 49 | 54 |
| Frozen ranking audit | 40 | 31 | 25 | 29 |

The 91 labeled tasks have at least one confirmed native witness; the other 22 tasks remain misses in the denominator. There are 94 confirmed witness cases: 78 value mismatches and 16 PUT exceptions. Contract-rejected inputs, equal-valued outcomes, unknown mechanisms and timeouts are not counted.

## What changed

- Added 30 generic semantic contract cards with pinned CPython documentation; the original 132-card corpus is unchanged.
- Extracted actual operations and sites with AST, excluded annotations, and removed generic Python syntax from ranking signals.
- Used separate spec/API BM25 channels to rank structurally grounded candidates; qualified APIs respect common aliases and parameter shadowing.
- Returned at most 3 source sites per concept, with the earlier `values[len(values)]` miss now ranked first.

## Witness examples

| Task | Correct concept | Input | Required | PUT |
| --- | --- | --- | --- | --- |
| HumanEval/16 | Unicode characters versus encoded bytes | `éé` | `1` distinct character | `2` distinct bytes |
| HumanEval/35 | Invalid fixed maximum sentinel | `[-2, -1]` | `-1` | `0` |
| HumanEval/98 | Omitted literal class member | `I` | `1` uppercase vowel | `0` |
| HumanEval/140 | Fixed chunk versus maximal run | `a    b` | `a-b` | `a-_b` |
| HumanEval/152 | Signed subtraction versus absolute difference | `[1]`, `[3]` | `[2]` | `[-2]` |

## Remaining misses

The family-only audit misses include presence/frequency state, ASCII-range classification and first qualifying candidate versus optimum. Some correct-family cases still cite an earlier, correct guard instead of the faulty guard. Those fail the primary metric; examples include HumanEval/2, /56, /57, /114 and /126. These were not used to tune the frozen engine after audit.

## Artifacts

- [Full summary](evaluation/SUMMARY.json), [all 113 scored tasks](evaluation/all_tasks.jsonl).
- [Native witness results](evaluation/witness_grading.json), [strict family labels](evaluation/gold.json), [faulty source-site labels](evaluation/mechanism_sites.json).
- [Development scores](evaluation/development.json), [single frozen audit](evaluation/audit.json).
- [Protocol and amendments](PREREG.md), [review and limits](REVIEW.md), [engine freeze](evaluation/ENGINE_FREEZE.json).
