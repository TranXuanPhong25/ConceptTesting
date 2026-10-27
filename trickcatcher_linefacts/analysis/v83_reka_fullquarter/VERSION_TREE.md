# v83 lineage and live scope

```text
v7 facts → v11 fair hybrid → v77 v7/v31 hint merge (prepared, unrun)
                                  └─ v81 DeepInfra, fixed28/2arms/K1: partial3/28; expired key then task19 canceled
                                      └─ v82 DeepInfra fresh28/2arms/K1: terminal before paired task on three shared-pool429s
                                          └─ v83 Reka fresh28/2arms/K1: running
```

V83 regenerates every task/arm; it does not combine v81/v82 answers. Reka uses a
24k total output budget for both arms to fit the remaining $3.45291084 cumulative
cap. The hard cap can stop early after retries or long prompts. Current status is
in STATUS_V83.json; protocol/cohort/source hashes are frozen under the pipeline's
`out/reka_quarter_final2/protocol.json`. A partial run has no efficacy verdict.
