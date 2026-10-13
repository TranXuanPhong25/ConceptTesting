# v11_fair_vp

Held-out copy of v11_fair, with the exact v7_vp class-method tracing/mutation fix.
VERSION = v11_fair_vp; all four fairness flags remain true. No source in the
original pipeline copies or vendor is modified. Outputs are isolated below this
folder's out/<dataset-hash>/.

See [CHANGELOG.md](CHANGELOG.md), [EQUIVALENCE.md](EQUIVALENCE.md), and
[the held-out runbook](../../HELDOUT_RUNBOOK.md) for frozen settings, exact ordered
commands, call bounds, offline evidence and registered Final protocol amendment 1:
tc_full_v2 keeps 10+4 shared generation/task, K=3 resamples and the 20-assertion cap.

From the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest trickcatcher_linefacts.pipelines.v11_fair_vp.test_vp trickcatcher_linefacts.pipelines.v11_fair_vp.test_fair -q
PYTHONDONTWRITEBYTECODE=1 python3 -B -m trickcatcher_linefacts.pipelines.v11_fair_vp.test_equivalence --checks a,b
PYTHONDONTWRITEBYTECODE=1 python3 -B -m trickcatcher_linefacts.pipelines.v11_fair_vp.vp_check --dataset trickcatcher_linefacts/out/heldout_vibepass_real/he --validity evalplus --workers 4
```

Offline replay is the default. `run mine/arms` and `heldout_support references`
need genuine cached responses or explicit --online. CacheMiss is terminal; there
is no scripted pipeline client. The only fake clients are baseline dry checks.
`vp_check --validity evalplus` is an embedded-contract tracing diagnostic, not a
replacement for the final mined-validity mine/facts/specfacts/bundle sequence.

The original inherited modules keep historical subcommands for reproduction.
The final runbook uses heldout_support for complete-cohort ref-only scoring and
final_analysis for witness-only and held-out statistical comparisons.
