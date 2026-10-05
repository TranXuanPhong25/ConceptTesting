# m8_concept_mutants: results (2026-10-05)

**Verdict.** The pre-registered gate passed: concept mutants are bug-touching on 49/60 bugs. The arm still does not
help. Generic (PIT-style) mutants touch more bugs and point in the fix direction more often. The blind arbiter sides
with the current code in 91-95% of its decisions. Adding the m8 tests to the Advanced-Doc tests therefore adds
**misguided** methods (≥1 M 3 → 11, p=0.008) and no new ≥1 E method (30 → 30). The concept and generic arms do not
differ significantly (≥1 E 5 vs 10, ≥1 M 8 vs 13, both p=0.18), and where they differ, generic is ahead.

## Phase 0 (offline, no LLM; numbers from `out/phase0_analysis.txt`)
### Mutants per concept (78 methods; ≤80 candidates per method and arm)
"Smoke-equivalent" = no outcome change on the bug's trigger tests or on the developer tests that invoke the focal
method. This is an upper bound on true equivalence.

| concept | candidates | compiled | compile rate | smoke-equivalent (of compiled) |
|---|---|---|---|---|
| C1 null | 578 | 572 | 99% | 48% |
| C2 empty/blank | 170 | 162 | 95% | 61% |
| C3 boundary | 808 | 795 | 98% | 38% |
| C4 error contract | 356 | 331 | 93% | 53% |
| C5 format/escaping | 167 | 163 | 98% | 19% |
| C6 numeric | 303 | 207 | 68% | 98% |
| C7 chars/locale | 35 | 33 | 94% | 36% |
| C8 state | 149 | 149 | 100% | 60% |
| all concept | 2566 | 2412 | 94% | 49% |
| generic (PIT-style) | 2929 | 2006 | 68% | 29% |

- Before the 80-per-method cap there were 3097 concept and 5447 generic candidates.
- No concept mutant compiled to the original's bytecode; 9 generic mutants did.
- C6 is almost always smoke-equivalent: the overflow guards and int↔long changes never trigger on the existing tests.
  C7 rarely applies: 35 candidates in total.
- Selection with an **equal number of mutants per method** (min of usable concept, usable generic, 40): 1536 per arm,
  median 17 per method. In 51 methods the equal-n rule cut the concept set, which has 1823 usable mutants when only the
  cap of 40 applies.

### Mechanism check (per bug, n=60; trigger tests, run offline)
| mutant set | bug-touching | fix-direction |
|---|---|---|
| concept (selected, equal n) | **49 (82%)** | 13 (22%) |
| generic (selected, equal n) | 56 (93%) | 22 (37%) |
| concept, all usable (≤40/method) | 52 (87%) | 17 (28%) |
| generic, all usable (≤40/method) | 56 (93%) | 22 (37%) |

- Concept vs generic (selected sets), exact McNemar:
  - bug-touching: only concept 2, only generic 9, p=0.065.
  - fix-direction: only concept 3, only generic 12, **p=0.035, in favour of generic**.
  - With all usable mutants: p=0.29 and p=0.27.
- Timeouts change nothing: no bug becomes touching only through a timeout.
- Cli_1 and Lang_64 are touched by no usable mutant of either arm.
- The validation (`phase0.py base`) holds:
  - Every trigger test fails on the recompiled buggy original and passes on the fixed checkout.
  - The recompiled original gives the checkout's own per-test results in 77/78 methods. The exception is Lang_12, whose
    random tests are flaky; flaky tests are handled as pre-registered.
- Cross-tab with the m2 manual labels (selected sets): a mutant of the labelled concept touches the bug for:

  | label | touched | of n bugs |
  |---|---|---|
  | C1 | 8 | 8 |
  | C2 | 1 | 3 |
  | C3 | 14 | 18 |
  | C4 | 4 | 13 |
  | C5 | 3 | 7 |
  | C6 | 1 | 4 |
  | C7 | 2 | 7 |
  | C8 | 2 | 6 |

  Matching-concept mutants are in the fix direction on only 2/8 C1, 4/18 C3, 0/13 C4 and 0/7 C5 bugs. The catalogue
  finds the right place, not the right alternative behaviour.

**Gate (pre-registered: ≥ 30% of 60 bugs bug-touching): 49/60 = 81.7% → PASS, Phase 1 run.**

## Phase 1 (Gemini 2.5 Flash via Vertex, thinking off, T=0; numbers from `out/analysis.txt`)
### Main table: intersection of clean methods (75)
Cli_8, Lang_11 and Lang_4 are excluded because their Advanced run glitched. Cli_8 also glitched in both m8 arms, again
on the one allowed redo.

| config | generated / compiled | M | E | FP | red-prec | ≥1 M | ≥1 E |
|---|---|---|---|---|---|---|---|
| Advanced Doc | 1239 / 1069 | 9 (0.84%) | 95 (8.89%) | 268 (25.07%) | 0.262 | 3 | 30 |
| m6 blind oracle | 1341 / 1136 | 10 (0.88%) | 90 (7.92%) | 303 (26.67%) | 0.229 | 2 | 30 |
| m8 concept (alone) | 502 / 502 | 16 (3.19%) | 5 (1.00%) | 12 (2.39%) | 0.294 | 8 | 5 |
| m8 generic (alone) | 618 / 617 | 41 (6.65%) | 18 (2.92%) | 39 (6.32%) | 0.316 | 13 | 10 |
| Advanced + m8 concept | 1741 / 1571 | 25 (1.59%) | 100 (6.37%) | 280 (17.82%) | 0.263 | 11 | 30 |
| Advanced + m8 generic | 1857 / 1686 | 50 (2.97%) | 113 (6.70%) | 307 (18.21%) | 0.269 | 16 | 32 |

Exact McNemar on methods with ≥1 E / ≥1 M:

| comparison | ≥1 E | ≥1 M |
|---|---|---|
| **primary: m8 concept vs m8 generic (alone)** | 5 vs 10, only concept 2 / only generic 7, p=0.18 | 8 vs 13, 2 / 7, p=0.18 |
| Adv + m8 concept vs Adv + m8 generic | 30 vs 32, 0 / 2, p=0.5 | 11 vs 16, 2 / 7, p=0.18 |
| Adv + m8 concept vs Advanced | 30 vs 30, p=1 | **11 vs 3, 8 / 0, p=0.0078** |
| Adv + m8 generic vs Advanced | 32 vs 30, 2 / 0, p=0.5 | **16 vs 3, 13 / 0, p=0.00024** |
| m8 concept alone vs Advanced | **5 vs 30, p=6e-8** | 8 vs 3, p=0.23 |
| Adv + m8 concept vs m6 blind | 30 vs 30, 9 / 9, p=1 | 11 vs 2, p=0.0039 |

**Sensitivity without Gson_4 and Cli_1** (68 methods):
- concept vs generic alone: ≥1 E 5 vs 7 (p=0.69), ≥1 M 5 vs 8 (p=0.38).
- Adv + m8 concept vs Advanced: ≥1 M 7 vs 2 (p=0.0625), ≥1 E 25 vs 25.
- Adv + m8 generic vs Advanced: ≥1 M 10 vs 2 (p=0.0078).

New M-methods from Adv + m8 concept: Cli_32, Gson_4 ×3, Lang_12, Lang_28, Lang_38, Lang_63.

### Where M and E come from
- Every M test asserts the current output (concept 16, generic 41).
- Every E test asserts the mutant's output (concept 5, generic 18).
- The arbiter picked the mutant's output in only 26/552 concept decisions (5%) and 59/676 generic decisions (9%).

### Arbiter accuracy (offline: chosen output vs the fixed version's output on the same probe input)
| arm | items | UNDETERMINED | decided | accuracy where fixed equals one side | bug-relevant items* | decided relevant: correct / wrong / neither | relevant UNDETERMINED |
|---|---|---|---|---|---|---|---|
| concept | 619 | 67 (11%) | 552 | 0.975 (512 / 525) | 60 | 7 / 0 / 27 | 26 |
| generic | 717 | 41 (6%) | 676 | 0.932 (586 / 629) | 102 | 19 / 20 / 47 | 16 |

\* Bug-relevant item: the fixed output differs from the current one on that input.

The high overall accuracy is dominated by inputs where nothing is wrong: the current code is right, and the arbiter
keeps it.

On bug-relevant inputs, the concept mutant rarely offers the fixed behaviour:
- In 27 of the 34 decided concept items, the fixed output equals neither side. In 21 of these 27 the arbiter keeps
  the current (buggy) output, and the test becomes M; the other 6 become FP.
- That is the misguidance the method was meant to remove: the arbiter judges A vs B, and neither is right.
- Generic mutants offer the fixed behaviour more often: 39 relevant items have the fixed output on the mutant side,
  against 7 for concept. But the arbiter picks it only half the time (19 correct, 20 wrong).

### Pipeline internals
- **Probes** (LLM-written):
  - 72/78 compile within the 3 allowed attempts (50 on the first, 20 on the second, 8 reached the third). No probe
    for Cli_15, Cli_1, Csv_4, Gson_8, Lang_30.indexOfAnyBut(String) or Lang_64.
  - 1600 cases (median 19 per method); 3 nondeterministic cases dropped (Lang_55).
  - The probes reveal a buggy/fixed difference in 41/72 methods (offline knowledge).
  - A probe case distinguishes 913/1500 selected concept mutants and 1226/1500 generic ones.
  - No probe quotes the focal body.
- **Items** (≤10 per method and arm): concept 619 in 70 methods, out of 3295 distinct differences; generic 717 in 72
  methods, out of 6253.
- **Tests:**
  - concept: 552 built, 26 of them assert the mutant side;
  - generic: 667 built, 59 assert the mutant side, and 9 more were dropped by the self-check;
  - none dropped for compile errors.
  - The pipeline kept 527 concept and 641 generic tests. Its own filter drops @Test methods whose focal call it does
    not recognise (e.g. some Gson_4/Gson_14 cases).

### LLM calls and cost (`out/llm_calls.jsonl`, every billed response)
| step | calls | input tok | output tok | USD |
|---|---|---|---|---|
| probe (shared by both arms) | 114 (78 + 28 + 8 re-asks) | 618,856 | 182,444 | 0.642 |
| arbiter concept | 73 (70 used + 3 smoke v1) | 477,592 | 106,173 | 0.409 |
| arbiter generic | 75 (72 used + 3 smoke v1) | 492,423 | 122,453 | 0.454 |
| **total** | **262** | | | **1.50** (cap 8) |

The concept arm made 70 arbiter calls and the generic arm 72, because 2 methods had no concept item. The arms have the
same budget: one call per method with ≥1 item, ≤10 items each. Tests are generated without an LLM.

## Caveats
- **Noise.** 15-18 of 75 methods flip ≥1 E between two single T=0 runs (m4). The concept vs generic differences
  (2 vs 7 methods) are inside that noise.
- **Union arms.** The "Advanced + m8" rows reuse the Advanced baseline run, which was generated without a temperature
  (Gemini default); the m8 calls use T=0.
- **Gson_4 dominates.** One bug with 6 methods accounts for 3 of the 8 new M-methods of Adv + concept (sensitivity
  above).
- **Probe inputs are LLM-chosen and blind.** Mutants only filter them. When no probe input reaches the bug (31/72
  methods), no arm can produce E there.
- **A/B forces a choice between two alternatives.** "UNDETERMINED … or neither is" was offered, but used in only
  6-11% of items. In 21 (concept) and 30 (generic) bug-relevant items where neither side is the fixed output, the
  arbiter picked the current output instead of answering UNDETERMINED.
- **Mutant generation.** It is first-order and text-level (tree-sitter, no types), so compile failures filter
  ill-typed edits. Some operators rarely apply: C7 as a whole (35 candidates), C4 catch narrowing (3 candidates, none
  compiled), C6 rounding (2) and special values (7). The Phase 0 "equivalent" share is an upper bound from a smoke run.
- **Deviations after the smoke, applied to both arms before the full run** (details in README.md):
  - the prelude (shared locals) is carried into items and tests;
  - the Java 7 test template;
  - tests that fail the self-check are dropped;
  - outputs are exempt from the body-window guard (Csv_2's exception message).

## Outside this folder
- New files only:
  - `data/prompts/rq1/*m8_*`;
  - `data/rq1/logs/*m8_*`;
  - `data/rq1/results_test/chatgpt/*m8_*` (and the upstream `buggy_gen_test_results.json`, which every evaluation
    rewrites);
  - `run/out/eval_m8_*`;
  - the docker volume `m8scratch`.
- `docker pull alpine` happened once by mistake (arm64 image, used for one `ls`).
- Shared checkouts:
  - Phase 0 and the probes mounted them read-only.
  - After everything, the main sources of all 120 checkouts are unmodified (`git diff --quiet HEAD -- <src>`), and
    `git diff HEAD` is byte-identical before and after.
  - `git status` differs only by untracked files the upstream evaluation writes (EmptyTests, junit properties) in
    Codec_8/buggy, Codec_9/buggy and Codec_9/fixed.
- Security:
  - Evaluation container (`NO_ADC=1`): no gcloud mount and no credentials variable (`out/no_adc_inspect.txt`).
  - Sandbox: network none, repo and checkouts read-only.
- No git commits.
