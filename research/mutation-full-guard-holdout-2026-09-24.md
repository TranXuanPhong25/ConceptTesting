# Full-guard mutation concept: held-out TestEval pilot

## Method

After the [first 39-mutant pilot](mutation-concept-pilot-2026-09-24.md), we added a `full_guard` arm. For a mutated comparison, it records the containing `if`/`while` guard, the other Boolean terms required for the mutation to flip that guard, an enclosing loop, and the action the original and mutant take. A simple boundary substitution resolves facts like `i = 0` plus `nums[i] == nums[i-1]` into `nums[0] == nums[-1]`. These are static expression requirements, not proof that a concrete input reaches the state or changes the final output.

The held-out slice was the next 14 records in the same official TestEval checkout (`6f67dee71de6ccda1767b8c219a93f4ae0a7ce90`) after skipping the 14 records used to inspect the first pilot. Up to three comparison mutants per record yielded 36 mutants across 13 tasks. Both arms used native Vertex `gemini-3-flash-preview` at temperature 0, maximum 1024 output tokens, the same original program and exact mutant expression, and the same child-process kill oracle. The only prompt addition in `full_guard` was its static concept block. Provider 429 errors were retried; all 36 pairs have generated tests.

We first ran one-shot generation. Then we replayed each arm's saved tests and gave one feedback repair to each surviving mutant, followed by one more repair. Thus kill@1, kill@2, and kill@3 use the same first attempts and the same maximum call budget for each arm.

## Paired results

| Max attempts | Plain killed | Full guard killed | Plain only | Full guard only | Exact McNemar p |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 25/36 | 24/36 | 4 | 3 | 1.000 |
| 2 | 27/36 | 29/36 | 1 | 3 | 0.625 |
| 3 | 28/36 | 29/36 | 2 | 3 | 1.000 |

No reliable improvement is established. The full-guard arm reached more mutant failures in the one-shot run, but 6 of its tests failed assertions on the original, compared with 3 for plain. This cancelled the potential gain in final valid kills. The extra guard detail helped a few cases (`isSelfCrossing`, `removeKdigits`, `updateMatrix`) and hurt others when the model chose an incorrect expected output (`trapRainWater`, `strongPasswordChecker`, `originalDigits`). The feedback loop fixed some errors in both arms; its small full-guard advantage at kill@2 narrowed by kill@3.

The exact p-values are descriptive only: mutants within a task are correlated, the task slice is small, and arms ran sequentially. The benchmark uses synthetic comparison mutants in LeetCode solutions, not real defects. Neither equivalent mutants nor prompt-length effects were controlled. The current evidence does **not** justify scaling this annotator or claiming a concept benefit.

## Next experiment implied by the failures

Separate input construction from oracle construction. The concept can guide an input to the changed guard; execution of the original can provide the observed result or state change before an assertion is finalized. Compare that workflow with plain plus the same oracle-validation step. Otherwise, more detailed concept text may simply increase incorrect assertions.

## Reproduce summary

The one-shot JSONL files are `/tmp/testeval_mutation_holdout_plain.jsonl` and `/tmp/testeval_mutation_holdout_full_guard.jsonl`. The files with saved repair attempts are `/tmp/testeval_mutation_holdout_plain_3round.jsonl` and `/tmp/testeval_mutation_holdout_full_guard_3round.jsonl`. Run:

```bash
.venv/bin/python -m testeval_py.mutation_stats \
  --plain /tmp/testeval_mutation_holdout_plain_3round.jsonl \
  --concept /tmp/testeval_mutation_holdout_full_guard_3round.jsonl \
  --max-attempts 1
```

Change `--max-attempts` to `2` or `3` for the other rows. The raw files are in `/tmp`; this note preserves the method and measured counts.
