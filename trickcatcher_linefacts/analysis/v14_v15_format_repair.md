# v14/v15 Python-format repair: completed exploratory results

2026-10-14. Frozen 20 dev tasks, K=1, common saved v11 spec-only ref oracle.
These runs are separate from the original zero-card smoke. No held-out evaluation.
Execution overlapped CPU-heavy B4, was interrupted by HTTP 404, and resumed from cache.

## v14_obgraph_py

5 accepted cards; 5 shown cards on 3/20 tasks; 0 shown cards with eligible witnesses.

| Arm | D_IO tasks/20 | Precision | Slots with card | Inputs/task |
|---|---:|---:|---:|---:|
| graph-strategy | 6 | 0.733 | 4 | 4.00 |
| card-strategy | 6 | 0.733 | 4 | 4.00 |
| graph-noconcept | 6 | 0.733 | 4 | 4.00 |
| plain-strategy | 7 | 0.800 | 4 | 3.80 |
| placebo-strategy | 6 | 0.765 | 4 | 4.40 |
| toolinput | 7 | 0.824 | 4 | 3.80 |
| new-toolinput | 7 | 0.933 | 4 | 3.25 |
| witness-only | 6 | 1.000 | 0 | 1.50 |
| new-witness-only | 0 | n/a | 0 | 0.00 |

Primary comparisons (nominal exploratory p-values):
- matched=False: graph-strategy vs card-strategy; wins/losses 0/0, p=1.0000; detection means 6.00/6.00.
- matched=True: graph-strategy vs card-strategy; wins/losses 0/0, p=1.0000; detection means 6.00/6.00.

Property checks, distinct from the common-ref detection endpoint:

| Arm | Checked records | Candidate reports | Confirmed | False alarms | Abstentions |
|---|---:|---:|---:|---:|---:|
| graph-strategy | 1 | 0 | 0 | 0 | 0 |
| card-strategy | 1 | 0 | 0 | 0 | 0 |
| graph-noconcept | 1 | 0 | 0 | 0 | 0 |
| plain-strategy | 0 | 0 | 0 | 0 | 0 |
| placebo-strategy | 0 | 0 | 0 | 0 | 0 |
| toolinput | 0 | 0 | 0 | 0 | 0 |
| new-toolinput | 0 | 0 | 0 | 0 | 0 |
| witness-only | 0 | 0 | 0 | 0 | 0 |
| new-witness-only | 0 | 0 | 0 | 0 | 0 |

Recorded physical requests/tokens (keepalive excluded):
```json
{
  "successful": 35,
  "unique_success_keys": 35,
  "cache_hits": 405,
  "failed_attempts": 6,
  "prompt_tokens": 90071,
  "completion_tokens": 16662
}
```

## v15_mrconcept_py

41 accepted cards; 41 shown cards on 16/20 tasks; 8 shown cards with eligible witnesses.

| Arm | D_IO tasks/20 | Precision | Slots with card | Inputs/task |
|---|---:|---:|---:|---:|
| mr-strategy | 5 | 0.714 | 34 | 3.20 |
| mr-blind | 5 | 0.733 | 38 | 2.90 |
| mr-flatfacts | 4 | 0.600 | 36 | 2.80 |
| placebo-strategy | 4 | 0.600 | 39 | 3.20 |
| toolinput | 4 | 0.750 | 36 | 2.70 |
| new-toolinput | 6 | 1.000 | 38 | 3.05 |
| witness-only | 6 | 1.000 | 0 | 1.50 |
| new-witness-only | 0 | 0.000 | 0 | 0.60 |

Primary comparisons (nominal exploratory p-values):
- matched=False: mr-strategy vs mr-blind; wins/losses 2/2, p=1.0000; detection means 5.00/5.00.
- matched=True: mr-strategy vs mr-blind; wins/losses 2/1, p=1.0000; detection means 4.30/3.64.

Property checks, distinct from the common-ref detection endpoint:

| Arm | Checked records | Candidate reports | Confirmed | False alarms | Abstentions |
|---|---:|---:|---:|---:|---:|
| mr-strategy | 14 | 3 | 0 | 3 | 6 |
| mr-blind | 12 | 3 | 0 | 3 | 4 |
| mr-flatfacts | 10 | 3 | 0 | 3 | 2 |
| placebo-strategy | 14 | 2 | 0 | 2 | 6 |
| toolinput | 12 | 1 | 0 | 1 | 6 |
| new-toolinput | 18 | 1 | 0 | 1 | 8 |
| witness-only | 0 | 0 | 0 | 0 | 0 |
| new-witness-only | 7 | 4 | 0 | 4 | 2 |

Recorded physical requests/tokens (keepalive excluded):
```json
{
  "successful": 117,
  "unique_success_keys": 117,
  "cache_hits": 263,
  "failed_attempts": 0,
  "prompt_tokens": 90012,
  "completion_tokens": 12620
}
```

## Interpretation

Format guidance enabled some structurally accepted proposals. Neither primary contrast shows a
detection advantage in this small exploratory cohort. Graph treatment coverage is sparse (3/20 tasks).
MR coverage is broader (16/20), but candidate property violations produced no confirmed reports on
the selected inputs; some were false alarms against the canonical program. Common-ref detections
remain separate from these property-oracle results. Acceptance is not semantic correctness.
Zero-card slots still use the registered generic fallback; card-slot counts describe availability, including controls that hide guidance.
No promotion or claim of universal graph/MR failure follows from this K=1 smoke.
The JSON includes all comparisons, rejection reasons, costs and artifact hashes.
