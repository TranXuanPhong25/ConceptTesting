# Cached naiveLLM versus full soft BVA

Stored naive inputs have now been rescored against the same 1,454 base-passing PUTs as BVA, using the same corrected oracle and frozen evaluator. No new model calls or input repairs were made. Both immutable replays and source/input hash checks passed.

| Target scope | BVA | Naive | Shared | BVA-only | Naive-only | Net BVA |
|---|---:|---:|---:|---:|---:|---:|
| Full 1,454 PUTs | 61 | 44 | 31 | 30 | 13 | +17 |
| Historical common 1,437 PUTs | 61 | 44 | 31 | 30 | 13 | +17 |

These are absolute additional detections beyond base tests. The net difference above compares the two generators; it is not bug recall. The historical naive result of 72 used an older oracle/runtime and is superseded here by the unchanged-input rescore.

| Metric | BVA | Naive |
|---|---:|---:|
| Valid novel task inputs | 1,449 | 1,536 |
| Tasks with detection | 22 | 16 |
| Eligible tasks with valid novel inputs | 157 | 82 |
| PUTs with a stable wrong-value witness | 46 | 17 |
| PUTs with a non-timeout failure witness | 51 | 28 |
| Original received writer calls | 1,454 | 156 |
| Original known generation tokens | 1,423,485 | 385,522 |

Failure categories can overlap. A non-timeout witness may be an exception rather than an incorrect returned value. Unknown historical transport attempts are recorded separately in the JSON usage receipts.

Coverage and interface losses matter:

| Unique detection | Other side has no admitted source input | Other side has no novel valid input | Different valid input set |
|---|---:|---:|---:|
| bva_only | 17 | 13 | 0 |
| naive_only | 0 | 0 | 13 |

On the 82 tasks where both generators retain a valid novel input, BVA detects 31 PUTs and naive detects 44. This is a descriptive coverage restriction, not an input-budget or writer-call matched comparison. A gain on tasks with no executable baseline input does not by itself demonstrate better boundary selection.

For example, old task 23 generated Unicode strings but encoded a single argument as `('你好')` instead of `('你好',)`, so the parser rejected it. In tasks 40, 43, 126 and 151, list contents were encoded as the positional argument list; oracle binding/domain checks rejected every admitted record. These records remain unchanged and rejected. Repairing them would be a separate experiment.

All original admitted naive input records were reused unchanged. Empty source batches and the resource-skipped task 160 stay empty. Corrected HumanEval+reference, full two-repeat scorer, 3 s timeout and the exact frozen cohort are the same as BVA.

Both generators nominally request 20 inputs/task. Naive saw multiple PUTs together and omitted 17 resource-risk PUTs from its historical context/evaluation. BVA generated per PUT with fixed shares. Visibility, schemas, generation epochs and writer costs differ, so the raw counts do not isolate boundary guidance.

Secondary expected detections under uniform valid-input budget matching: BVA 31.00, naive 32.39. For each task, k=min(valid_BVA, valid_naive); 75 eligible tasks have k=0 and contribute no detections for either side. The analytical mean 1-C(n-f,k)/C(n,k) is conditional on recorded confirmed failures. It is not another executed trial, a primary result or a superiority test.

PUT identities below are task-local IDs. All unique witnesses and loss-stage classifications are preserved in the JSON report.

| Task | BVA detected PUTs | Naive detected PUTs |
|---|---|---|
| HumanEval/0 | — | — |
| HumanEval/1 | 8 | — |
| HumanEval/2 | 6 | 6 |
| HumanEval/3 | — | — |
| HumanEval/4 | — | — |
| HumanEval/5 | — | — |
| HumanEval/6 | 9 | — |
| HumanEval/7 | — | — |
| HumanEval/8 | — | — |
| HumanEval/9 | — | — |
| HumanEval/10 | 6 | — |
| HumanEval/11 | — | 1, 7 |
| HumanEval/12 | — | — |
| HumanEval/13 | — | 2, 3 |
| HumanEval/14 | — | — |
| HumanEval/15 | — | — |
| HumanEval/16 | — | — |
| HumanEval/17 | — | — |
| HumanEval/18 | — | — |
| HumanEval/19 | — | — |
| HumanEval/20 | — | — |
| HumanEval/21 | — | — |
| HumanEval/22 | — | — |
| HumanEval/23 | 7 | — |
| HumanEval/24 | — | — |
| HumanEval/25 | — | — |
| HumanEval/26 | — | — |
| HumanEval/27 | — | — |
| HumanEval/28 | — | — |
| HumanEval/29 | — | — |
| HumanEval/30 | — | — |
| HumanEval/31 | — | 1, 6 |
| HumanEval/32 | skip | generation_shortfall |
| HumanEval/33 | — | — |
| HumanEval/34 | — | — |
| HumanEval/35 | — | — |
| HumanEval/36 | — | — |
| HumanEval/37 | — | — |
| HumanEval/38 | — | — |
| HumanEval/39 | 0, 1, 2, 4, 5, 6, 7, 8, 9 | 0, 1, 2, 4, 5, 6, 7, 8, 9 |
| HumanEval/40 | 9 | — |
| HumanEval/41 | — | 3, 5, 6, 9 |
| HumanEval/42 | — | — |
| HumanEval/43 | 1 | — |
| HumanEval/44 | — | — |
| HumanEval/45 | 4 | 4 |
| HumanEval/46 | — | — |
| HumanEval/47 | — | — |
| HumanEval/48 | — | — |
| HumanEval/49 | 1, 2, 3, 4 | 1, 2, 3, 4 |
| HumanEval/50 | — | — |
| HumanEval/51 | — | — |
| HumanEval/52 | — | — |
| HumanEval/53 | — | 6 |
| HumanEval/54 | — | — |
| HumanEval/55 | 5 | 5 |
| HumanEval/56 | — | — |
| HumanEval/57 | — | — |
| HumanEval/58 | — | — |
| HumanEval/59 | — | — |
| HumanEval/60 | 3 | 3 |
| HumanEval/61 | 4, 8 | — |
| HumanEval/62 | — | — |
| HumanEval/63 | — | — |
| HumanEval/64 | — | — |
| HumanEval/65 | skip | no_base_pass |
| HumanEval/66 | — | — |
| HumanEval/67 | — | — |
| HumanEval/68 | — | — |
| HumanEval/69 | — | — |
| HumanEval/70 | — | — |
| HumanEval/71 | — | — |
| HumanEval/72 | — | — |
| HumanEval/73 | — | — |
| HumanEval/74 | — | — |
| HumanEval/75 | — | — |
| HumanEval/76 | 0, 1, 2, 3, 4, 5, 6, 7, 8 | 0, 1, 2, 3, 4, 5, 6, 7, 8 |
| HumanEval/77 | — | — |
| HumanEval/78 | — | — |
| HumanEval/79 | — | — |
| HumanEval/80 | — | — |
| HumanEval/81 | — | — |
| HumanEval/82 | — | — |
| HumanEval/83 | 2, 9 | 2, 9 |
| HumanEval/84 | — | — |
| HumanEval/85 | — | — |
| HumanEval/86 | — | — |
| HumanEval/87 | — | — |
| HumanEval/88 | — | — |
| HumanEval/89 | — | — |
| HumanEval/90 | — | — |
| HumanEval/91 | 0, 1, 2, 3, 4, 5, 7, 8, 9 | — |
| HumanEval/92 | — | — |
| HumanEval/93 | — | — |
| HumanEval/94 | — | — |
| HumanEval/95 | — | — |
| HumanEval/96 | — | — |
| HumanEval/97 | — | 3, 6 |
| HumanEval/98 | — | — |
| HumanEval/99 | — | — |
| HumanEval/100 | — | — |
| HumanEval/101 | — | — |
| HumanEval/102 | — | — |
| HumanEval/103 | — | — |
| HumanEval/104 | — | — |
| HumanEval/105 | — | — |
| HumanEval/106 | — | — |
| HumanEval/107 | 2 | 2 |
| HumanEval/108 | — | — |
| HumanEval/109 | — | — |
| HumanEval/110 | — | — |
| HumanEval/111 | — | — |
| HumanEval/112 | — | — |
| HumanEval/113 | — | — |
| HumanEval/114 | — | — |
| HumanEval/115 | — | — |
| HumanEval/116 | — | — |
| HumanEval/117 | — | — |
| HumanEval/118 | — | — |
| HumanEval/119 | — | — |
| HumanEval/120 | — | — |
| HumanEval/121 | — | — |
| HumanEval/122 | — | — |
| HumanEval/123 | — | — |
| HumanEval/124 | 7 | — |
| HumanEval/125 | — | — |
| HumanEval/126 | 5 | — |
| HumanEval/127 | skip | no_base_pass |
| HumanEval/128 | — | — |
| HumanEval/129 | — | — |
| HumanEval/130 | — | — |
| HumanEval/131 | — | — |
| HumanEval/132 | skip | no_base_pass |
| HumanEval/133 | — | — |
| HumanEval/134 | — | — |
| HumanEval/135 | — | — |
| HumanEval/136 | skip | generation_shortfall |
| HumanEval/137 | — | — |
| HumanEval/138 | — | — |
| HumanEval/139 | — | — |
| HumanEval/140 | 7 | — |
| HumanEval/141 | — | — |
| HumanEval/142 | — | — |
| HumanEval/143 | — | — |
| HumanEval/144 | — | — |
| HumanEval/145 | skip | no_base_pass |
| HumanEval/146 | — | — |
| HumanEval/147 | — | — |
| HumanEval/148 | — | — |
| HumanEval/149 | — | — |
| HumanEval/150 | — | — |
| HumanEval/151 | 0, 1, 2, 3, 4, 5, 6, 7, 8, 9 | — |
| HumanEval/152 | — | — |
| HumanEval/153 | — | — |
| HumanEval/154 | — | — |
| HumanEval/155 | — | — |
| HumanEval/156 | — | — |
| HumanEval/157 | 3, 8 | 3, 8 |
| HumanEval/158 | — | — |
| HumanEval/159 | — | — |
| HumanEval/160 | — | — |
| HumanEval/161 | — | — |
| HumanEval/162 | — | — |
| HumanEval/163 | skip | no_base_pass |
