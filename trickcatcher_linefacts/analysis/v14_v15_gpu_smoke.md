# v14/v15 GPU exploratory smoke

2026-10-14. Frozen 20 dev tasks, K=1, Qwen2.5-Coder-7B-Instruct; common saved spec-only ref oracle.
No held-out run. Samples and tasks coincide at K=1; the sign tests are exploratory/nominal.

## v14_obgraph

Proposal stage: 0 shown cards across 0/20 tasks; 0 witnessed cards.

| Arm | D_I tasks | D_IO tasks | Precision | Inputs/task | Generation calls/task |
|---|---:|---:|---:|---:|---:|
| graph-strategy | 6 | 6 | 0.733 | 4.25 | 3.00 |
| card-strategy | 6 | 6 | 0.733 | 4.25 | 3.00 |
| graph-noconcept | 6 | 6 | 0.733 | 4.25 | 3.00 |
| plain-strategy | 7 | 7 | 0.800 | 3.80 | 3.00 |
| placebo-strategy | 6 | 6 | 0.765 | 4.40 | 3.00 |
| toolinput | 8 | 7 | 0.824 | 3.80 | 3.00 |
| new-toolinput | 7 | 7 | 0.933 | 3.55 | 3.00 |
| witness-only | 6 | 6 | 1.000 | 1.50 | 0.00 |
| new-witness-only | 0 | 0 | n/a | 0.00 | 0.00 |

Primary comparisons:
- graph-strategy vs card-strategy, matched=False: 6.00/6.00; wins/losses 0/0; nominal p=1.0000.
- graph-strategy vs card-strategy, matched=True: 6.00/6.00; wins/losses 0/0; nominal p=1.0000.

**No accepted semantic cards.** The concept arms use their registered generic fallback slots.
Their results do not test the usefulness of a grounded graph or conditional MR reasoning.
new-toolinput/new-witness-only have no discovered card witnesses.

Proposal rejection census:
```json
{
  "unknown exact clause ID": 13,
  "path must contain 1..6 existing typed edge IDs": 48,
  "T must be Python source": 47,
  "proposal_parse_failed": 1,
  "invalid syntax (<unknown>, line 1)": 6
}
```

Physical request accounting (includes proposals; excludes model-list keepalive):
```json
{
  "successful": 311,
  "unique_success_keys": 311,
  "cache_hits": 129,
  "failed_attempts": 0,
  "prompt_tokens": 231027,
  "completion_tokens": 39734
}
```

## v15_mrconcept

Proposal stage: 0 shown cards across 0/20 tasks; 0 witnessed cards.

| Arm | D_I tasks | D_IO tasks | Precision | Inputs/task | Generation calls/task |
|---|---:|---:|---:|---:|---:|
| mr-strategy | 6 | 6 | 0.733 | 4.30 | 3.00 |
| mr-blind | 7 | 7 | 0.800 | 3.80 | 3.00 |
| mr-flatfacts | 6 | 6 | 0.733 | 4.30 | 3.00 |
| placebo-strategy | 6 | 6 | 0.765 | 4.40 | 3.00 |
| toolinput | 8 | 7 | 0.824 | 3.80 | 3.00 |
| new-toolinput | 7 | 7 | 0.933 | 3.55 | 3.00 |
| witness-only | 6 | 6 | 1.000 | 1.50 | 0.00 |
| new-witness-only | 0 | 0 | n/a | 0.00 | 0.00 |

Primary comparisons:
- mr-strategy vs mr-blind, matched=False: 6.00/7.00; wins/losses 1/2; nominal p=1.0000.
- mr-strategy vs mr-blind, matched=True: 5.33/6.64; wins/losses 1/2; nominal p=1.0000.

**No accepted semantic cards.** The concept arms use their registered generic fallback slots.
Their results do not test the usefulness of a grounded graph or conditional MR reasoning.
new-toolinput/new-witness-only have no discovered card witnesses.

Proposal rejection census:
```json
{
  "only builtin calls are allowed": 18,
  "one pure function required": 89,
  "unterminated string literal (detected at line 1) (<unknown>, line 1)": 1,
  "invalid syntax (<unknown>, line 1)": 12
}
```

Physical request accounting (includes proposals; excludes model-list keepalive):
```json
{
  "successful": 311,
  "unique_success_keys": 311,
  "cache_hits": 69,
  "failed_attempts": 0,
  "prompt_tokens": 178235,
  "completion_tokens": 29321
}
```

## Interpretation limits

Graph/cards and MR/blind primary contrasts require accepted cards to exercise the intended mechanism.
Schema/purity acceptance is not semantic correctness; finite canonical property checks are reported separately.
toolinput here is the fixed three-strategy-slot adapter, not historical one-call toolinput. Original witness-only
and new witness-pool controls remain distinct. Requests/token usage and generated input counts differ across
comparators; paired random-subset sensitivity is in the JSON. Missing/disagreeing reference outputs abstain.
Raw artifacts stay in each version folder; this tracked summary preserves scope, counts, costs and hashes.
