# Final comparison protocol

Dataset: humaneval; split: dev; 113 tasks; K=3; sign tests by task (113 clusters).

Development sanity; descriptive only.

Scorer: pipelines/v11_fair/scorer.py; rel_tol=1e-6, trusted task atol.

Random subsets: seed 20261013, 100 draws. No baselines supplied; comparisons skipped.


## ref oracle

| Arm | Samples | Bug/run | D_I | D_IO | Precision | FA rate | Failing | Flag correct % | LLM calls/sample | Tokens in/out/sample | Assertions/sample |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| concept | 339 | 48.0 | 443 | 374 | 0.9100 | 0.0900 | 411 | 12.98 | 1.00 | 661.84/275.66 | 7.84 |
| concept-hybrid | 339 | 66.7 | 788 | 662 | 0.9350 | 0.0650 | 708 | 15.34 | 3.58 | 3012.58/605.15 | 12.54 |
| gen-plain | 339 | 41.3 | 339 | 278 | 0.9424 | 0.0576 | 295 | 7.37 | 2.15 | 1764.60/352.15 | 7.09 |
| placebo-hybrid | 339 | 45.7 | 428 | 378 | 0.9380 | 0.0620 | 403 | 8.85 | 1.27 | 843.01/273.73 | 8.80 |
| plain | 339 | 45.0 | 381 | 325 | 0.9644 | 0.0356 | 337 | 8.55 | 1.00 | 539.12/254.28 | 8.24 |
| plain-hybrid | 339 | 57.3 | 667 | 581 | 0.9447 | 0.0553 | 615 | 11.21 | 3.58 | 2802.53/607.48 | 12.63 |
| toolinput | 339 | 64.7 | 493 | 405 | 0.9101 | 0.0899 | 445 | 14.16 | 1.00 | 584.45/239.58 | 7.62 |
| witness-only | 339 | 43.0 | 165 | 138 | 0.9020 | 0.0980 | 153 | 7.96 | 0.00 | 0.00/0.00 | 1.22 |

### Primary comparisons

- concept-hybrid vs plain-hybrid (detecting): 66.67 vs 57.33; wins/losses/ties 33/17/63; two-sided p=0.032839; 113 paired tasks, 113 clusters, 0 excluded tasks.
- concept-hybrid vs toolinput (detecting): 66.67 vs 64.67; wins/losses/ties 23/20/70; two-sided p=0.760792; 113 paired tasks, 113 clusters, 0 excluded tasks.
- concept-hybrid vs witness-only (detecting): 66.67 vs 43.00; wins/losses/ties 38/11/64; two-sided p=0.000142; 113 paired tasks, 113 clusters, 0 excluded tasks.

### Secondary comparisons

- concept-hybrid vs plain-hybrid (d_i_sample): 77.33 vs 67.33; wins/losses/ties 37/19/57; two-sided p=0.022241; 113 paired tasks, 113 clusters, 0 excluded tasks.
- concept-hybrid vs plain-hybrid (random matched detection): 64.92 vs 55.57; wins/losses/ties 43/24/46; two-sided p=0.027120; 113 paired tasks, 113 clusters, 0 excluded tasks. Matched calls/sample=13.07.
- concept-hybrid vs toolinput (d_i_sample): 77.33 vs 76.67; wins/losses/ties 25/23/65; two-sided p=0.885433; 113 paired tasks, 113 clusters, 0 excluded tasks.
- concept-hybrid vs toolinput (random matched detection): 54.34 vs 63.81; wins/losses/ties 24/48/41; two-sided p=0.006310; 113 paired tasks, 113 clusters, 0 excluded tasks. Matched calls/sample=8.48.
- concept-hybrid vs witness-only (d_i_sample): 77.33 vs 52.00; wins/losses/ties 44/14/55; two-sided p=0.000100; 113 paired tasks, 113 clusters, 0 excluded tasks.
- concept-hybrid vs witness-only (random matched detection): 21.12 vs 43.00; wins/losses/ties 33/43/37; two-sided p=0.301872; 113 paired tasks, 113 clusters, 0 excluded tasks. Matched calls/sample=1.42.
- concept-hybrid vs placebo-hybrid (d_i_sample): 77.33 vs 52.33; wins/losses/ties 47/10/56; two-sided p=0.000001; 113 paired tasks, 113 clusters, 0 excluded tasks.
- concept-hybrid vs placebo-hybrid (random matched detection): 58.94 vs 44.14; wins/losses/ties 41/29/43; two-sided p=0.188216; 113 paired tasks, 113 clusters, 0 excluded tasks. Matched calls/sample=9.40.
- concept-hybrid vs placebo-hybrid (detecting): 66.67 vs 45.67; wins/losses/ties 38/8/67; two-sided p=0.000009; 113 paired tasks, 113 clusters, 0 excluded tasks.

### Witness audit (same definitions as witness_only.txt)

| Arm | Bug/run | Distinct calls/sample | All emitted false alarms/sample |
|---|---:|---:|---:|
| witness-only | 43.0 | 1.4 | 0.09 |
| toolinput | 64.7 | 8.7 | 0.28 |
| concept-hybrid | 66.7 | 14.2 | 0.41 |
| plain-hybrid | 57.3 | 14.3 | 0.33 |

## full oracle

| Arm | Samples | Bug/run | D_I | D_IO | Precision | FA rate | Failing | Flag correct % | LLM calls/sample | Tokens in/out/sample | Assertions/sample |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| concept | 339 | 46.3 | 443 | 366 | 0.9506 | 0.0494 | 385 | 10.62 | 1.00 | 661.84/275.66 | 7.71 |
| concept-hybrid | 339 | 65.3 | 788 | 653 | 0.9589 | 0.0411 | 681 | 12.98 | 3.58 | 3012.58/605.15 | 12.40 |
| gen-plain | 339 | 40.3 | 339 | 274 | 0.9580 | 0.0420 | 286 | 7.08 | 2.15 | 1764.60/352.15 | 7.04 |
| placebo-hybrid | 339 | 43.3 | 428 | 366 | 0.9556 | 0.0444 | 383 | 8.26 | 1.27 | 843.01/273.73 | 8.70 |
| plain | 339 | 43.3 | 381 | 318 | 0.9666 | 0.0334 | 329 | 8.26 | 1.00 | 539.12/254.28 | 8.14 |
| plain-hybrid | 339 | 56.3 | 667 | 574 | 0.9663 | 0.0337 | 594 | 9.73 | 3.58 | 2802.53/607.48 | 12.46 |
| toolinput | 339 | 65.0 | 493 | 405 | 0.9529 | 0.0471 | 425 | 11.21 | 1.00 | 584.45/239.58 | 7.52 |
| witness-only | 339 | 44.0 | 165 | 141 | 0.9592 | 0.0408 | 147 | 5.31 | 0.00 | 0.00/0.00 | 1.21 |

### Primary comparisons

- concept-hybrid vs plain-hybrid (detecting): 65.33 vs 56.33; wins/losses/ties 32/17/64; two-sided p=0.044384; 113 paired tasks, 113 clusters, 0 excluded tasks.
- concept-hybrid vs toolinput (detecting): 65.33 vs 65.00; wins/losses/ties 22/22/69; two-sided p=1.000000; 113 paired tasks, 113 clusters, 0 excluded tasks.
- concept-hybrid vs witness-only (detecting): 65.33 vs 44.00; wins/losses/ties 37/13/63; two-sided p=0.000936; 113 paired tasks, 113 clusters, 0 excluded tasks.

### Secondary comparisons

- concept-hybrid vs plain-hybrid (d_i_sample): 77.33 vs 67.33; wins/losses/ties 37/19/57; two-sided p=0.022241; 113 paired tasks, 113 clusters, 0 excluded tasks.
- concept-hybrid vs plain-hybrid (random matched detection): 63.66 vs 54.84; wins/losses/ties 41/25/47; two-sided p=0.064018; 113 paired tasks, 113 clusters, 0 excluded tasks. Matched calls/sample=13.07.
- concept-hybrid vs toolinput (d_i_sample): 77.33 vs 76.67; wins/losses/ties 25/23/65; two-sided p=0.885433; 113 paired tasks, 113 clusters, 0 excluded tasks.
- concept-hybrid vs toolinput (random matched detection): 52.88 vs 64.38; wins/losses/ties 23/49/41; two-sided p=0.002943; 113 paired tasks, 113 clusters, 0 excluded tasks. Matched calls/sample=8.48.
- concept-hybrid vs witness-only (d_i_sample): 77.33 vs 52.00; wins/losses/ties 44/14/55; two-sided p=0.000100; 113 paired tasks, 113 clusters, 0 excluded tasks.
- concept-hybrid vs witness-only (random matched detection): 20.30 vs 44.00; wins/losses/ties 32/44/37; two-sided p=0.206737; 113 paired tasks, 113 clusters, 0 excluded tasks. Matched calls/sample=1.42.
- concept-hybrid vs placebo-hybrid (d_i_sample): 77.33 vs 52.33; wins/losses/ties 47/10/56; two-sided p=0.000001; 113 paired tasks, 113 clusters, 0 excluded tasks.
- concept-hybrid vs placebo-hybrid (random matched detection): 57.92 vs 42.16; wins/losses/ties 41/29/43; two-sided p=0.188216; 113 paired tasks, 113 clusters, 0 excluded tasks. Matched calls/sample=9.40.
- concept-hybrid vs placebo-hybrid (detecting): 65.33 vs 43.33; wins/losses/ties 39/7/67; two-sided p=0.000002; 113 paired tasks, 113 clusters, 0 excluded tasks.

### Witness audit (same definitions as witness_only.txt)

| Arm | Bug/run | Distinct calls/sample | All emitted false alarms/sample |
|---|---:|---:|---:|
| witness-only | 44.0 | 1.4 | 0.06 |
| toolinput | 65.0 | 8.7 | 0.21 |
| concept-hybrid | 65.3 | 14.2 | 0.36 |
| plain-hybrid | 56.3 | 14.3 | 0.29 |

## Definitions and limits

- Precision and false-alarm rate share the failing-on-PUT assertion denominator.
- Invalid inputs never detect and count as false alarms when failing on PUT.
- Correct-program flags include all emitted wrong/invalid assertions, even PUT-passing ones.
- Witness-only uses zero generation LLM calls/tokens; oracle costs are excluded for all arms.
- Matched counts use distinct candidate calls before oracle abstention, as matched_subsets.py.
- Baseline comparisons pair complete tasks with all K samples; excluded tasks are reported.
- Full is included only when post and cached judge stages exist; no missing stages are generated.
- D_I compares PUT against the trusted canonical reference, independent of oracle abstention.
- Bug/run is contract-valid, oracle-correct assertions failing on PUT, divided by K.
- Secondary D_I sign tests compare samples containing at least one D_I input.
- CPU replays fix PYTHONHASHSEED=12 for every dataset. Historical caches omit hash seeds; task 58 string-set order affects detecting samples. Seed 12 was selected to reproduce its two archived string-set orderings in the witness cache. Executions without this recorded hash seed are replayed, including shared-scorer caches.
- Assertions/sample means emitted replacement assertions; generated count is reported separately.
