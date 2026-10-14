# B3 v12_rel completed development comparison

2026-10-14. Qwen2.5-Coder-7B-Instruct, original frozen seven-arm manifest/K=3; spec-only ref oracle.
Complete: 2,793 evaluated task/arm/sample rows and 133 execution records. Dev and pilot stay separate.
Task-44 exact original-worker retry succeeded; the first missing-result cause remains undetermined.

## dev: 113 tasks

| Arm | D_IO samples | D_IO tasks/run (mean over K) | Precision | False alarms |
|---|---:|---:|---:|---:|
| flat-hybrid | 187 | 62.33 | 0.941 | 34 |
| placebo-hybrid | 173 | 57.67 | 0.947 | 29 |
| plain-hybrid | 169 | 56.33 | 0.898 | 54 |
| rel-hybrid | 190 | 63.33 | 0.933 | 38 |
| rel-nospec-hybrid | 184 | 61.33 | 0.918 | 45 |
| review-hybrid | 182 | 60.67 | 0.915 | 43 |
| toolinput | 187 | 62.33 | 0.925 | 34 |

| Relation contrast | Equal-count subsets | Wins/losses | Nominal sign p | D_IO tasks/run |
|---|---|---:|---:|---:|
| rel-hybrid vs flat-hybrid | False | 16/15 | 1.0000 | 63.33/62.33 |
| rel-hybrid vs flat-hybrid | True | 25/33 | 0.3581 | 61.13/60.76 |
| rel-hybrid vs rel-nospec-hybrid | False | 15/10 | 0.4244 | 63.33/61.33 |
| rel-hybrid vs rel-nospec-hybrid | True | 26/25 | 1.0000 | 61.06/59.98 |
| rel-hybrid vs plain-hybrid | False | 32/22 | 0.2203 | 63.33/56.33 |
| rel-hybrid vs plain-hybrid | True | 49/25 | 0.0071 | 62.58/51.45 |
| rel-hybrid vs toolinput | False | 20/17 | 0.7428 | 63.33/62.33 |
| rel-hybrid vs toolinput | True | 27/36 | 0.3135 | 60.02/60.62 |
| rel-hybrid vs placebo-hybrid | False | 25/20 | 0.5515 | 63.33/57.67 |
| rel-hybrid vs placebo-hybrid | True | 41/27 | 0.1143 | 61.94/53.60 |

## pilot: 20 tasks

| Arm | D_IO samples | D_IO tasks/run (mean over K) | Precision | False alarms |
|---|---:|---:|---:|---:|
| flat-hybrid | 29 | 9.67 | 0.888 | 10 |
| placebo-hybrid | 30 | 10.00 | 0.904 | 8 |
| plain-hybrid | 25 | 8.33 | 0.795 | 15 |
| rel-hybrid | 33 | 11.00 | 0.898 | 10 |
| rel-nospec-hybrid | 32 | 10.67 | 0.870 | 13 |
| review-hybrid | 31 | 10.33 | 0.878 | 10 |
| toolinput | 31 | 10.33 | 0.934 | 6 |

| Relation contrast | Equal-count subsets | Wins/losses | Nominal sign p | D_IO tasks/run |
|---|---|---:|---:|---:|
| rel-hybrid vs flat-hybrid | False | 2/0 | 0.5000 | 11.00/9.67 |
| rel-hybrid vs flat-hybrid | True | 5/4 | 1.0000 | 10.70/9.53 |
| rel-hybrid vs rel-nospec-hybrid | False | 4/1 | 0.3750 | 11.00/10.67 |
| rel-hybrid vs rel-nospec-hybrid | True | 6/4 | 0.7539 | 10.70/10.48 |
| rel-hybrid vs plain-hybrid | False | 5/1 | 0.2188 | 11.00/8.33 |
| rel-hybrid vs plain-hybrid | True | 7/3 | 0.3438 | 10.88/7.68 |
| rel-hybrid vs toolinput | False | 6/2 | 0.2891 | 11.00/10.33 |
| rel-hybrid vs toolinput | True | 8/2 | 0.1094 | 10.62/10.13 |
| rel-hybrid vs placebo-hybrid | False | 5/2 | 0.4531 | 11.00/10.00 |
| rel-hybrid vs placebo-hybrid | True | 9/3 | 0.1460 | 10.86/9.47 |

## Finding and limits

The primary relation-vs-flat contrast does not show a clear improvement on dev: raw 16/15 (p=1),
equal-count 25/33 (p=.358). Removing spec links also shows no clear difference. The mean raw D_IO advantage
over plain is 7 tasks/run, but its raw paired comparison is not significant (32/22, p=.220). The equal-count
plain comparison is nominally significant (49/25, p=.0071); placebo and toolinput comparisons are not.
This supports further hypothesis testing, not promotion of relations under the registered relation-vs-flat gate.

The original seven-arm B3 manifest omits exported witness-only; B4 includes both original and hypothesis
witness controls. Prompt budgets use a whitespace proxy and punctuation padding; they are not tokenizer-equal.
All p-values are nominal, with several comparisons. No held-out run or config/source tuning followed these results.

Full counts, all comparisons and artifact hashes: [b3_v12_rel_results.json](b3_v12_rel_results.json).
