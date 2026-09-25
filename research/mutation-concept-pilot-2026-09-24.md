# Mutation concept pilot (#17), 2026-09-24

## Question

Does an explicit comparison-boundary concept improve one-shot mutation-killing tests when the model already sees both the original and mutant expressions?

## Protocol

- Source: official TestEval `leetcode-py.jsonl`, checkout `6f67dee71de6ccda1767b8c219a93f4ae0a7ce90`.
- First 14 tasks in file order; first up to 3 single-line comparison mutants per task: 39 mutants total. Operators: `<`, `<=`, `>`, `>=`, `==`, `!=`.
- Model: native Vertex `gemini-3-flash-preview`, `global`, temperature 0, maximum 1024 output tokens.
- Plain prompt: problem, numbered original source, exact original and mutant expression.
- Concept prompt: same information plus operator change, equality boundary, and instruction to predict the original output at that boundary.
- One generated test per mutant per arm (`--rounds 0`). The same test runs in separate processes against original and mutant. A kill requires original pass, mutant failure, and trace evidence that the changed line ran. Mutant timeouts count only when that trace marker was emitted.
- Provider 429/504 failures were retried from checkpoints. The final comparison has 39 complete pairs and zero generation errors. The scoring command re-executes 3 timeout cases per arm because the first harness version lost trace evidence on timeout.

## Result

| Outcome | Mutants |
| --- | ---: |
| Killed by both | 34 |
| Plain only | 1 |
| Concept only | 1 |
| Killed by neither | 3 |
| Plain total | 35/39 (89.7%) |
| Concept total | 35/39 (89.7%) |

Exact paired McNemar p = 1.0 (1 discordant mutant in each direction). This is descriptive: multiple mutants come from the same task and the sample is the first 14 tasks, not a random independent set. There is no observed one-shot gain from the current concept card.

Two of the remaining shared misses are in `threeSum`: `i > 0` → `i >= 0` and `l < r` → `l <= r`. Both arms reached the changed decision but chose inputs or assertions that did not separate outputs. The third is a `spiralOrder` loop guard; equivalence has not been established. The one concept-only kill was `getSkyline` (`n == 1` → `n != 1`); the one plain-only kill was `isNumber` (`c == '.'` → `c != '.'`).

## Focused feedback check

We separately ran both arms with up to two repair rounds on the `threeSum` line-21 mutants. For `i > 0` → `i >= 0`, concept killed it on attempt 3 using `[0, 0, 0]`; plain still did not kill after 3 attempts. The effective condition is the conjunction `i == 0` **and** `nums[0] == nums[-1]`; Python's negative index matters. The current concept card contains only `i == 0`, so this single win cannot be attributed confidently to the card. The other comparison on line 21 was killed by both arms on attempt 1.

The next meaningful concept would state a *whole guard/path relation*, including the other conjuncts, relevant prior state, and the expected output difference. Merely labelling the changed operator or its equality boundary repeats information already present in the plain prompt. Test this only on a larger, held-out paired set after the extractor can produce those relations.

## Reproduce and inspect

```bash
source scripts/vertex_env.sh
.venv/bin/python -m testeval_py.mutation_loop \
  --in /tmp/TestEval-upstream/data/leetcode-py.jsonl \
  --out /tmp/testeval_mutation_pilot_concept.jsonl \
  --arm concept --limit 14 --max-mutants 3 --rounds 0 \
  --resume --request-delay 5 --provider-retries 2 --retry-wait 20
.venv/bin/python -m testeval_py.mutation_loop \
  --in /tmp/TestEval-upstream/data/leetcode-py.jsonl \
  --out /tmp/testeval_mutation_pilot_plain.jsonl \
  --arm plain --limit 14 --max-mutants 3 --rounds 0 \
  --resume --request-delay 5 --provider-retries 2 --retry-wait 20
.venv/bin/python -m testeval_py.mutation_stats \
  --plain /tmp/testeval_mutation_pilot_plain.jsonl \
  --concept /tmp/testeval_mutation_pilot_concept.jsonl \
  --dataset /tmp/TestEval-upstream/data/leetcode-py.jsonl
```

Raw JSONL artifacts currently live under `/tmp`; the summary above is the durable record. Reruns may differ despite temperature 0. The current experiment uses synthetic comparison mutants in isolated LeetCode functions, so it does not establish effects on real defects or repository-level tests.
