# PBT-Bench: feasibility and known warnings, 2026-10-26

Status: source/documentation assessment only; no author code changed or executed, no paid run. Sources were checked on 2026-10-26.

## Decision

Feasible as a new evaluation setting, conditional on harness readiness and a model-specific hypothesis. It does not by itself supply a new concept method. The next economical action is an audit of released trajectories/ablations and infrastructure readiness, before requesting an experiment budget.

## Technical fit

The [author README](https://github.com/ElliotXinqiWang/PBTbench) specifies 100 problems, 365 injected bugs, 40 Python libraries, documentation-grounded property tests, an OpenHands scaffold, and per-test-function fail-on-buggy/pass-on-fixed scoring. Requirements are Python 3.12+, Docker, uv, library images, and an LLM backend. The current local default Python is 3.12.2 and a Docker binary exists; daemon access, images, SDK compatibility, and actual task execution were not tested. These are not yet a smoke-test pass.

Keep the author checkout immutable in a separate directory and keep experimental wrappers/prompts outside it. Supply keys through the repository's approved environment scripts; the author's example of writing a key into a JSON config should not be copied into a tracked artifact.

## Evidence that changes the previous recommendation

[Paper v4](https://arxiv.org/html/2605.15229v4), sections 5–6 and appendices A.7/A.15/A.16:

- Best original recall is 83.4%, so the benchmark has headroom. In the common-problem prompt ablation, Opus 4.8 full-PBT minus framework-only is +0.2 percentage points, CI [-3.4,+3.7]. Qwen 3.6 Plus gets +6.7 [2.2,11.6]; the latter comparison is indicative because runs used different infrastructure/times. Baseline gains can reflect testing more properties rather than concept reasoning.
- Earlier harnesses exposed `.orig` backups or stopped other runs' containers. Authors repaired these and reran/rescored affected data. Pin the corrected source and distinguish infrastructure failures from model failures.
- Original evaluation used about 200 node-hours and $2,288 API fees for 4,800 trajectories. Post-review runs cost about $1,750 more. These historical costs do not price our pilot.

## Prior results in this repository

- v26 property oracle was worse than exact-output generation, with unsound properties; v27 showed that a stronger oracle model changed precision substantially.
- v41 generic relations did not concentrate bugs. v53/v55h/v64 show strong-writer ceilings in the old setting, not proof of a ceiling on PBT-Bench.
- [Agentic-PBT saved-data audit](../agentic-pbt/REPORT_PATTERN_AUDIT_20261025.md) found flat rubric scores across inferred pattern classes. This is a different paper/benchmark and an observational audit: only 21 reports were manually labeled, rule-label agreement was 11/21, and there was no no-pattern arm. It is a reason to require controls, not proof that concept guidance cannot work on PBT-Bench. Its $5.81/call median must not be imported as the PBT-Bench unit price.

## Required controls and limits

Compare our concept method with both the official full-PBT prompt and framework-only guidance, plus a content/length-matched placebo. Keep model, permitted context/tools, generation budget, test-execution budget, and stop rules matched. Inspect budget usage and number of test functions: a one-bug stopping policy can have high problem coverage but low bug recall.

Use bug recall and valid F→P detections, not just tasks with any failure. Report invalid/fixed-failing tests and abstentions separately; passing the fixed implementation is operational validity under the benchmark, not a mathematical proof of a universally sound property. Multi-bug problems require the author's per-function/per-bug evaluation.

The 365 bugs are injected semantic faults in real libraries. Results do not automatically establish gains on naturally occurring bugs. Agent-visible files must exclude patches, ground truth, fixed-source backups, hidden labels, and evaluator outputs. Keep PBT-Bench out of training data, respecting the benchmark's canary. When evaluating transfer, split by library/problem rather than individual injected bugs from the same problem.

No current API balance was checked. A paid pilot needs an explicit USD budget, an enforced aggregate cap, and a cost ledger; the old ~$25 memory entry is dated, not a current balance.
