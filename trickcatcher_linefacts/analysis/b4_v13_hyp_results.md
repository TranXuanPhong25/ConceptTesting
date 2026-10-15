# B4 v13_hyp completed comparison

Frozen 133-task cohort: 113 dev + 20 pilot, seven exported arms, K=3; common spec-only ref oracle.
2,793 generation/evaluation rows; all 133 execution records present.
One task-level hypothesis proposal is shared across K/arms and accounted separately.

## dev

133 shown hypotheses on 58/113 tasks; 66 witnessed; 15 with surviving-mutant differences.

| Arm | D_IO tasks/run | Precision | False alarms | Generation calls/sample |
|---|---:|---:|---:|---:|
| flat-hybrid | 62.67 | 0.944 | 33 | 3.27 |
| hyp-hybrid | 46.33 | 0.931 | 29 | 1.83 |
| hyp-witness-only | 15.00 | 0.944 | 3 | 0.00 |
| plain-hybrid | 54.67 | 0.893 | 54 | 3.48 |
| rel-hybrid | 63.33 | 0.935 | 36 | 3.37 |
| toolinput | 63.00 | 0.923 | 36 | 1.00 |
| witness-only | 41.67 | 0.899 | 15 | 0.00 |

| Hypothesis contrast | Matched inputs | Wins/losses | Nominal p | Detection tasks/run |
|---|---|---:|---:|---:|
| hyp-hybrid vs flat-hybrid | False | 14/43 | 0.0002 | 46.33/62.67 |
| hyp-hybrid vs flat-hybrid | True | 21/51 | 0.0005 | 44.81/60.42 |
| hyp-hybrid vs toolinput | False | 14/35 | 0.0038 | 46.33/63.00 |
| hyp-hybrid vs toolinput | True | 20/41 | 0.0099 | 43.86/61.52 |
| hyp-hybrid vs rel-hybrid | False | 10/37 | 0.0001 | 46.33/63.33 |
| hyp-hybrid vs rel-hybrid | True | 24/43 | 0.0271 | 45.18/60.28 |
| hyp-hybrid vs plain-hybrid | False | 19/31 | 0.1189 | 46.33/54.67 |
| hyp-hybrid vs plain-hybrid | True | 36/32 | 0.7163 | 46.17/49.65 |
| hyp-hybrid vs witness-only | False | 30/27 | 0.7914 | 46.33/41.67 |
| hyp-hybrid vs witness-only | True | 26/42 | 0.0681 | 17.55/41.67 |
| hyp-witness-only vs witness-only | False | 7/35 | 0.0000 | 15.00/41.67 |
| hyp-witness-only vs witness-only | True | 9/8 | 1.0000 | 11.95/10.02 |

## pilot

27 shown hypotheses on 12/20 tasks; 11 witnessed; 3 with surviving-mutant differences.

| Arm | D_IO tasks/run | Precision | False alarms | Generation calls/sample |
|---|---:|---:|---:|---:|
| flat-hybrid | 10.33 | 0.852 | 13 | 2.22 |
| hyp-hybrid | 9.00 | 0.806 | 20 | 2.68 |
| hyp-witness-only | 3.00 | 0.600 | 6 | 0.00 |
| plain-hybrid | 10.67 | 0.866 | 11 | 2.30 |
| rel-hybrid | 11.00 | 0.911 | 9 | 2.02 |
| toolinput | 10.67 | 0.926 | 7 | 1.00 |
| witness-only | 8.00 | 0.909 | 3 | 0.00 |

| Hypothesis contrast | Matched inputs | Wins/losses | Nominal p | Detection tasks/run |
|---|---|---:|---:|---:|
| hyp-hybrid vs flat-hybrid | False | 3/6 | 0.5078 | 9.00/10.33 |
| hyp-hybrid vs flat-hybrid | True | 4/9 | 0.2668 | 8.38/9.71 |
| hyp-hybrid vs toolinput | False | 2/4 | 0.6875 | 9.00/10.67 |
| hyp-hybrid vs toolinput | True | 2/6 | 0.2891 | 8.74/10.15 |
| hyp-hybrid vs rel-hybrid | False | 3/7 | 0.3438 | 9.00/11.00 |
| hyp-hybrid vs rel-hybrid | True | 4/9 | 0.2668 | 8.39/10.45 |
| hyp-hybrid vs plain-hybrid | False | 3/5 | 0.7266 | 9.00/10.67 |
| hyp-hybrid vs plain-hybrid | True | 5/7 | 0.7744 | 8.67/9.58 |
| hyp-hybrid vs witness-only | False | 3/2 | 1.0000 | 9.00/8.00 |
| hyp-hybrid vs witness-only | True | 3/8 | 0.2266 | 4.33/8.00 |
| hyp-witness-only vs witness-only | False | 1/6 | 0.1250 | 3.00/8.00 |
| hyp-witness-only vs witness-only | True | 2/4 | 0.6875 | 2.70/4.47 |

## Finding

On dev, hyp-hybrid detects 46.33 tasks/run vs flat-hybrid 62.67 and toolinput 63.00.
Primary raw paired wins/losses are 14/43 (p=.000154) and 14/35 (p=.003802).
Equal-input random-subset comparisons also favor flat and toolinput.
This registered hypothesis pipeline does not meet its promotion gate.

Generation calls/sample differ: hyp-hybrid 1.83 vs flat-hybrid 3.27. Matching input
counts does not match LLM requests. The result compares complete methods and does not
isolate hypothesis wording alone; proposal coverage and witness-pool quality also differ.

## Scope and limits

Primary registered contrasts are hyp-hybrid vs flat-hybrid and vs toolinput; pilot stays separate.
P-values are nominal across several exploratory contrasts. No held-out promotion follows automatically.
The frozen seven-arm B4 manifest does not export placebo; hypothesis and original witness controls are present.
Hint budgets use whitespace/punctuation proxy normalization, not equal actual tokenizer counts.
A hypothesis witness or mutant difference is not proof of a specification violation.
Task-44 missing execution was retried with the exact original saved worker/job/timers; other results retained.
Raw assertions with witness-only None are placeholders; report uses ref-replaced outcomes.
