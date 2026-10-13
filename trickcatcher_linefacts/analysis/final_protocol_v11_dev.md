# Final comparison protocol

Dataset: humaneval; split: dev; 113 tasks; K=3; sign tests by task (113 clusters).

Development sanity; descriptive only.

Scorer: pipelines/v11_fair/scorer.py; rel_tol=1e-6, trusted task atol.

Random subsets: seed 20261013, 100 draws. No baselines supplied; comparisons skipped.


## ref oracle

| Arm | Samples | Bug/run | D_I | D_IO | Precision | FA rate | Failing | Flag correct % | LLM calls/sample | Tokens in/out/sample | Assertions/sample |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| concept | 339 | 48.0 | 443 | 374 | 0.9100 | 0.0900 | 411 | 12.98 | 1.00 | 661.84/275.66 | 7.85 |
| concept-hybrid | 339 | 61.0 | 595 | 511 | 0.9291 | 0.0709 | 550 | 14.16 | 3.27 | 2838.85/479.69 | 8.76 |
| gen-plain | 339 | 41.3 | 339 | 278 | 0.9424 | 0.0576 | 295 | 7.37 | 2.15 | 1764.60/352.15 | 7.09 |
| placebo-hybrid | 339 | 57.7 | 603 | 545 | 0.9300 | 0.0700 | 586 | 9.73 | 3.46 | 2909.04/560.05 | 10.72 |
| plain | 339 | 45.0 | 384 | 328 | 0.9647 | 0.0353 | 340 | 8.55 | 1.00 | 539.12/254.28 | 8.27 |
| plain-hybrid | 339 | 55.7 | 574 | 493 | 0.9284 | 0.0716 | 531 | 10.03 | 3.36 | 2652.06/529.75 | 10.58 |
| toolinput | 339 | 64.3 | 492 | 404 | 0.9099 | 0.0901 | 444 | 14.16 | 1.00 | 584.55/240.10 | 7.64 |
| witness-only | 339 | 43.0 | 165 | 138 | 0.9020 | 0.0980 | 153 | 7.96 | 0.00 | 0.00/0.00 | 1.22 |

### Primary comparisons

- concept-hybrid vs plain-hybrid (detecting): 61.00 vs 55.67; wins/losses/ties 29/20/64; two-sided p=0.252870; 113 paired tasks, 113 clusters, 0 excluded tasks.
- concept-hybrid vs toolinput (detecting): 61.00 vs 64.33; wins/losses/ties 22/23/68; two-sided p=1.000000; 113 paired tasks, 113 clusters, 0 excluded tasks.
- concept-hybrid vs witness-only (detecting): 61.00 vs 43.00; wins/losses/ties 35/14/64; two-sided p=0.003802; 113 paired tasks, 113 clusters, 0 excluded tasks.

### Secondary comparisons

- concept-hybrid vs plain-hybrid (d_i_sample): 70.67 vs 65.00; wins/losses/ties 33/22/58; two-sided p=0.177001; 113 paired tasks, 113 clusters, 0 excluded tasks.
- concept-hybrid vs plain-hybrid (random matched detection): 59.27 vs 51.58; wins/losses/ties 43/26/44; two-sided p=0.053289; 113 paired tasks, 113 clusters, 0 excluded tasks. Matched calls/sample=9.36.
- concept-hybrid vs toolinput (d_i_sample): 70.67 vs 76.33; wins/losses/ties 23/28/62; two-sided p=0.575849; 113 paired tasks, 113 clusters, 0 excluded tasks.
- concept-hybrid vs toolinput (random matched detection): 54.07 vs 62.13; wins/losses/ties 26/42/45; two-sided p=0.068119; 113 paired tasks, 113 clusters, 0 excluded tasks. Matched calls/sample=8.11.
- concept-hybrid vs witness-only (d_i_sample): 70.67 vs 52.00; wins/losses/ties 41/18/54; two-sided p=0.003794; 113 paired tasks, 113 clusters, 0 excluded tasks.
- concept-hybrid vs witness-only (random matched detection): 23.06 vs 42.67; wins/losses/ties 30/42/41; two-sided p=0.194505; 113 paired tasks, 113 clusters, 0 excluded tasks. Matched calls/sample=1.41.
- concept-hybrid vs placebo-hybrid (d_i_sample): 70.67 vs 65.67; wins/losses/ties 35/25/53; two-sided p=0.245061; 113 paired tasks, 113 clusters, 0 excluded tasks.
- concept-hybrid vs placebo-hybrid (random matched detection): 60.05 vs 54.60; wins/losses/ties 38/27/48; two-sided p=0.214539; 113 paired tasks, 113 clusters, 0 excluded tasks. Matched calls/sample=9.51.
- concept-hybrid vs placebo-hybrid (detecting): 61.00 vs 57.67; wins/losses/ties 26/22/65; two-sided p=0.665466; 113 paired tasks, 113 clusters, 0 excluded tasks.

### Witness audit (same definitions as witness_only.txt)

| Arm | Bug/run | Distinct calls/sample | All emitted false alarms/sample |
|---|---:|---:|---:|
| witness-only | 43.0 | 1.4 | 0.09 |
| toolinput | 64.3 | 8.7 | 0.28 |
| concept-hybrid | 61.0 | 9.9 | 0.34 |
| plain-hybrid | 55.7 | 11.9 | 0.28 |

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
