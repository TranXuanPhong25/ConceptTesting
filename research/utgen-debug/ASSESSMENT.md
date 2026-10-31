# UTGen / UTDebug assessment

Read by Codex, 2026-10-24, at the user's request for an opinion. No implementation or model run.

Sources: [paper v3](https://arxiv.org/html/2502.01619v3), [author repository](https://github.com/archiki/UTGenDebug).

The useful distinction is attack rate versus expected-output accuracy; their intersection measures usable bug-revealing tests. UTGen trains on perturbed reference programs, execution-labeled outputs and post-hoc rationales. Gold code is used during training, not required at inference. UTDebug adds output self-consistency and edit validation/backtracking.

On MBPP+Fix Hard, Table 1 Qwen7B joint accuracy is 14.71 prompted versus 20.20 trained. Table 2 Qwen32B debugging accuracy is 40.59 prompted versus 45.29 trained (4.70 percentage points). Comparisons against No-UT or random tests answer different questions. The tested task family is Python function problems; repository-level transfer remains unestablished. Voting cannot guarantee a correct oracle when errors are correlated (our assessment).

Fit to this project: strong related work and a candidate trained-test baseline; not evidence for incremental concept benefit. Relevant local precedents: v48 oracle/common-mode failures, v49 definitional-versus-brute paired null, v54 stronger writer fixes both arms. A concept extension would need matched training data, model and inference budget, and a generic-rationale control. This is an evidence requirement, not a proposed or authorized experiment.

The author repository provides evaluation/debugging scripts and dataset links. Checkpoint/training-artifact completeness and actual executability were not audited.
