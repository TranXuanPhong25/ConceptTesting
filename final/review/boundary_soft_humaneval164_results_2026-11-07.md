# Full HumanEval — soft BVA result

Completed evaluation: `final/out/boundary_soft_humaneval164_evaluation_20261107_224720`.
Frozen generation: `final/out/boundary_soft_humaneval164_resume_20261107_195417`.

| Metric | Count |
|---|---:|
| Requested tasks | 164 |
| Eligible tasks | 157 |
| Base-passing PUTs evaluated | 1454 |
| Valid novel task inputs | 1449 |
| Confirmed detected PUTs | 61 |
| Tasks with detection | 22 |
| Eligible tasks with no novel valid input | 0 |

Confirmed outcome kinds can overlap on one PUT:
- value_mismatch: 46 PUTs.
- exception: 5 PUTs.
- timeout: 11 PUTs.
- mixed_failure: 0 PUTs.

15 detected PUTs have no stable value-mismatch witness; their detections involve exceptions, timeouts or mixed failure statuses. Do not describe every detection as a wrong returned value.

Generation: 1454 received logical calls. Of3034encoded calls,1550repeat a call proposed for another PUT of the same task;1484remain before reference/domain/base filtering. Known generation tokens:1,423,485. Imported493responses are included once;unknown transport attempts and historical keepalive receipts remain separate.

Reference/domain/base rejections: `{'domain_or_reference_rejects': 15, 'base_duplicate': 20}`.

Policy: soft BVA only,20inputs per task split across visible base-passing PUTs,typically2–3per PUT. One completion per allocated PUT;unused shares not redistributed. No precision expansion,concept-request writer or legacy selection/compiler.

All164input batches froze before native scoring. The run retains the original full two-repeat scorer,3stimeout and corrected HumanEval+reference/domain checks. Evaluation-only recovery reused33task checkpoints after a sandbox spawn infrastructure error and made0newmodel calls. That infrastructure error is not a PUT detection.

The completed global input freeze matches exactly. All1454generation response hashes match the audit. Immutable read-only replay passed.

This is detection on an existing previously used LLM-generated cohort. Its total bug population is unknown;these counts are not detection recall. There is no call-matched plain control and no held-out superiority claim. Earlier10task/single-PUT diagnostics differ in budget allocation and context.

Explicit task skips:
- HumanEval/32: generation_shortfall.
- HumanEval/65: no_base_pass.
- HumanEval/127: no_base_pass.
- HumanEval/132: no_base_pass.
- HumanEval/136: generation_shortfall.
- HumanEval/145: no_base_pass.
- HumanEval/163: no_base_pass.

| Task | Valid novel inputs | Detected PUT IDs |
|---|---:|---|
| HumanEval/0 | 8 | — |
| HumanEval/1 | 10 | 8 |
| HumanEval/2 | 9 | 6 |
| HumanEval/3 | 12 | — |
| HumanEval/4 | 11 | — |
| HumanEval/5 | 16 | — |
| HumanEval/6 | 8 | 9 |
| HumanEval/7 | 19 | — |
| HumanEval/8 | 10 | — |
| HumanEval/9 | 17 | — |
| HumanEval/10 | 6 | 6 |
| HumanEval/11 | 14 | — |
| HumanEval/12 | 13 | — |
| HumanEval/13 | 8 | — |
| HumanEval/14 | 2 | — |
| HumanEval/15 | 2 | — |
| HumanEval/16 | 9 | — |
| HumanEval/17 | 11 | — |
| HumanEval/18 | 6 | — |
| HumanEval/19 | 12 | — |
| HumanEval/20 | 13 | — |
| HumanEval/21 | 15 | — |
| HumanEval/22 | 8 | — |
| HumanEval/23 | 7 | 7 |
| HumanEval/24 | 5 | — |
| HumanEval/25 | 10 | — |
| HumanEval/26 | 12 | — |
| HumanEval/27 | 10 | — |
| HumanEval/28 | 6 | — |
| HumanEval/29 | 12 | — |
| HumanEval/30 | 16 | — |
| HumanEval/31 | 6 | — |
| HumanEval/32 | skip | generation_shortfall |
| HumanEval/33 | 6 | — |
| HumanEval/34 | 2 | — |
| HumanEval/35 | 14 | — |
| HumanEval/36 | 4 | — |
| HumanEval/37 | 6 | — |
| HumanEval/38 | 5 | — |
| HumanEval/39 | 2 | 0, 1, 2, 4, 5, 6, 7, 8, 9 |
| HumanEval/40 | 13 | 9 |
| HumanEval/41 | 5 | — |
| HumanEval/42 | 9 | — |
| HumanEval/43 | 8 | 1 |
| HumanEval/44 | 7 | — |
| HumanEval/45 | 11 | 4 |
| HumanEval/46 | 4 | — |
| HumanEval/47 | 12 | — |
| HumanEval/48 | 3 | — |
| HumanEval/49 | 7 | 1, 2, 3, 4 |
| HumanEval/50 | 3 | — |
| HumanEval/51 | 14 | — |
| HumanEval/52 | 8 | — |
| HumanEval/53 | 14 | — |
| HumanEval/54 | 6 | — |
| HumanEval/55 | 4 | 5 |
| HumanEval/56 | 5 | — |
| HumanEval/57 | 16 | — |
| HumanEval/58 | 12 | — |
| HumanEval/59 | 5 | — |
| HumanEval/60 | 7 | 3 |
| HumanEval/61 | 5 | 4, 8 |
| HumanEval/62 | 14 | — |
| HumanEval/63 | 2 | — |
| HumanEval/64 | 7 | — |
| HumanEval/65 | skip | no_base_pass |
| HumanEval/66 | 11 | — |
| HumanEval/67 | 7 | — |
| HumanEval/68 | 14 | — |
| HumanEval/69 | 7 | — |
| HumanEval/70 | 12 | — |
| HumanEval/71 | 13 | — |
| HumanEval/72 | 9 | — |
| HumanEval/73 | 5 | — |
| HumanEval/74 | 6 | — |
| HumanEval/75 | 9 | — |
| HumanEval/76 | 8 | 0, 1, 2, 3, 4, 5, 6, 7, 8 |
| HumanEval/77 | 7 | — |
| HumanEval/78 | 7 | — |
| HumanEval/79 | 4 | — |
| HumanEval/80 | 8 | — |
| HumanEval/81 | 13 | — |
| HumanEval/82 | 7 | — |
| HumanEval/83 | 6 | 2, 9 |
| HumanEval/84 | 3 | — |
| HumanEval/85 | 12 | — |
| HumanEval/86 | 8 | — |
| HumanEval/87 | 15 | — |
| HumanEval/88 | 10 | — |
| HumanEval/89 | 10 | — |
| HumanEval/90 | 14 | — |
| HumanEval/91 | 15 | 0, 1, 2, 3, 4, 5, 7, 8, 9 |
| HumanEval/92 | 9 | — |
| HumanEval/93 | 11 | — |
| HumanEval/94 | 12 | — |
| HumanEval/95 | 2 | — |
| HumanEval/96 | 4 | — |
| HumanEval/97 | 15 | — |
| HumanEval/98 | 11 | — |
| HumanEval/99 | 3 | — |
| HumanEval/100 | 3 | — |
| HumanEval/101 | 15 | — |
| HumanEval/102 | 3 | — |
| HumanEval/103 | 13 | — |
| HumanEval/104 | 9 | — |
| HumanEval/105 | 11 | — |
| HumanEval/106 | 3 | — |
| HumanEval/107 | 4 | 2 |
| HumanEval/108 | 8 | — |
| HumanEval/109 | 4 | — |
| HumanEval/110 | 10 | — |
| HumanEval/111 | 14 | — |
| HumanEval/112 | 9 | — |
| HumanEval/113 | 9 | — |
| HumanEval/114 | 13 | — |
| HumanEval/115 | 12 | — |
| HumanEval/116 | 16 | — |
| HumanEval/117 | 14 | — |
| HumanEval/118 | 16 | — |
| HumanEval/119 | 8 | — |
| HumanEval/120 | 13 | — |
| HumanEval/121 | 12 | — |
| HumanEval/122 | 19 | — |
| HumanEval/123 | 3 | — |
| HumanEval/124 | 9 | 7 |
| HumanEval/125 | 6 | — |
| HumanEval/126 | 13 | 5 |
| HumanEval/127 | skip | no_base_pass |
| HumanEval/128 | 12 | — |
| HumanEval/129 | 15 | — |
| HumanEval/130 | 4 | — |
| HumanEval/131 | 4 | — |
| HumanEval/132 | skip | no_base_pass |
| HumanEval/133 | 12 | — |
| HumanEval/134 | 20 | — |
| HumanEval/135 | 11 | — |
| HumanEval/136 | skip | generation_shortfall |
| HumanEval/137 | 18 | — |
| HumanEval/138 | 4 | — |
| HumanEval/139 | 3 | — |
| HumanEval/140 | 7 | 7 |
| HumanEval/141 | 5 | — |
| HumanEval/142 | 9 | — |
| HumanEval/143 | 6 | — |
| HumanEval/144 | 14 | — |
| HumanEval/145 | skip | no_base_pass |
| HumanEval/146 | 15 | — |
| HumanEval/147 | 2 | — |
| HumanEval/148 | 7 | — |
| HumanEval/149 | 13 | — |
| HumanEval/150 | 12 | — |
| HumanEval/151 | 2 | 0, 1, 2, 3, 4, 5, 6, 7, 8, 9 |
| HumanEval/152 | 10 | — |
| HumanEval/153 | 18 | — |
| HumanEval/154 | 12 | — |
| HumanEval/155 | 9 | — |
| HumanEval/156 | 5 | — |
| HumanEval/157 | 14 | 3, 8 |
| HumanEval/158 | 13 | — |
| HumanEval/159 | 3 | — |
| HumanEval/160 | 20 | — |
| HumanEval/161 | 4 | — |
| HumanEval/162 | 7 | — |
| HumanEval/163 | skip | no_base_pass |
