# v78 learned concept selection — NO-GO (2026-10-26, CPU, $0 API)

The registered context-dependent selector does not outperform random or a context-free prior on the frozen v47 menu. Stop this feature/menu/estimator package; no wider run or model tuning was performed after outcomes.

## Result

Expected number of PUTs reached by at least one confirmed bug-exposing input in three selected concept bundles. A fraction reflects exact averaging over tied scores, not a partial bug. Same 33 PUTs, **24 distinct specification groups**; all PUT variants of the held-out specification are excluded from training together.

| Policy | Primary spec+code | Secondary spec-only |
|---|---:|---:|
| Context-dependent logistic selector | **18.00** | **21.00** |
| Same logistic model, task context removed | 19.00 | 21.00 |
| Global kind prior, training groups only | 19.05 | 20.62 |
| Subtype prior, training groups only | **20.50** | 21.00 |
| Uniform random3 | 18.25 | 17.96 |
| Per-kind random (historical v47 rule) | 19.07 | 17.02 |
| First three menu items | 18.00 | 18.00 |
| Historical v47 Qwen picks | 16.00 | 15.00 |
| Reference-informed perfect menu | 23.00 | 22.00 |

The primary selector fails all three prospective gates: >=random3+3, >=cost-conditioned-random3+3, and >=strongest context-free control+2. Primary gain over ordinary random is -0.25 PUT, versus context-removed logistic -1, versus subtype prior -2.5. Group-bootstrap 95% intervals for the fixed CV predictions: context-minus-context-removed [-4,2], context-minus-subtype-prior [-6,0.5]; these are descriptive, without refitting models inside bootstrap samples.

Spec-only clears both random-margin gates but equals the context-removed model and subtype prior on **every PUT's reach outcome**. It fails the contextual-benefit gate and cannot replace the registered primary arm. Its improvement over uniform random is explained by reusable candidate preferences in this experiment; it does not establish useful task-context selection.

## Execution cost control

Each bundle has <=32 existing inputs. Union input counts below are summed over all 33 PUTs and averaged exactly over boundary ties. They are replayed input budgets, **not new executions**. The learned and ordinary random policies both choose 99 bundles in total. The historical spec-only per-kind control chooses 89, because some menus have fewer than three kinds.

| Policy | Primary distinct inputs | Secondary distinct inputs |
|---|---:|---:|
| Context-dependent selector | 2682.75 | 2703.00 |
| Context removed | 2481.52 | 2518.00 |
| Subtype prior | 2672.87 | 2449.50 |
| Uniform random3 | 2439.73 | 2397.63 |

Primary context uses 9.96% more distinct inputs than uniform random while reaching fewer PUTs. Random triples restricted to no more distinct inputs than the context policy reach 17.57 in primary and 17.73 in secondary; corresponding context gains are only +0.43 and +3.27. Conditioning on count does not equalize runtime or upstream preprocessing cost.

## Integrity, review, and execution history

- Initial independent review required restoring the original v41 input-pool SHA-256 guard; fixed before outcomes. Repeated-read hash changes are also rejected.
- The first approved invocation stopped at the prospective unique-spec guard **before label reconstruction or model fitting**. Public-source inspection identified six repeated-spec groups, leaving 24 independent problems among 33 PUTs. [Stop record](ATTEMPT1_INTEGRITY_STOP.md), [initial approval](APPROVAL_INITIAL.json).
- A prospective amendment introduced leave-one-problem-group-out and balanced training weights at group → PUT → candidate levels; priors and bootstrap use groups too. New independent review returned GO. [Protocol and amendments](PREREG.md), [final approval](APPROVAL.json).
- Synthetic verification: **11 tests passed**, including typed equality/tolerance, unseen held-out features/labels, group exclusion, group-balanced priors, exact ties, cost-conditioned random, fewer-than-three-kind control, and missing-cache failure.
- All 33 frozen v47 menu sizes, covering-item counts, Qwen outcomes, first3, perfect-menu and random/per-kind expectations reproduced before any model fit. All **1,743 consumed parent files** passed post-run hash verification. No model convergence warnings. No source/protocol edits after successful source freeze.
- Trained only the registered fixed logistic models, without tuning or data expansion. **0 API requests, $0 API cost, 0 new PUT/contract/reference executions, no GPU.** scikit-learn1.7.2; dependency versions in [requirements.lock](requirements.lock).
- Independent post-run [audit PASS](REVIEW.md): source/cache integrity, grouped folds, exact expectations, bootstrap and gates independently recomputed from saved predictions, without refitting models. Result SHA-256 `07d78c9cee453f2982c3d3f7e7ec95c85fb699f2edcc8ea3fa229dbea7ab7220`.

## Reproduce and inspect

Run with Python environment matching `requirements.lock`, repository root as cwd:

```bash
python -m pytest -q trickcatcher_linefacts/analysis/v78_learned_select/test_replay.py
python trickcatcher_linefacts/analysis/v78_learned_select/replay.py --output /tmp/v78-fresh-output
```

The output path must be fresh. `APPROVAL.json` must match all source/protocol hashes and the parent caches must remain available. The [saved result](RESULTS.json) contains per-PUT held-out predictions/labels, training IDs, exact expectations, source fingerprints, and consumed-cache fingerprints; it is byte-identical to `out/analysis/v78_learned_select/run_20261026/results.json`.

This is input-exposure selection on a heavily reused cohort. It does not measure assertion correctness, establish causal value of all possible concepts, reproduce CASCADE, or evaluate online contextual-bandit learning. The fixed feature vocabulary is intentionally simple; a no-go here does not prove all learned selectors impossible.
