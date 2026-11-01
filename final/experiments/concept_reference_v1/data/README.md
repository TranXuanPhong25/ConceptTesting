# Input-domain metadata

`contracts.json` contains ONLY `contract` and `atol` for all 164 task IDs, extracted
unchanged from the original EvalPlus HumanEval+ v0.1.10 dataset through
`evalplus.data.get_human_eval_plus()` (package 0.3.1). No `plus_input`, canonical
solution, reference output or hidden tests are retained in this file.

Upstream: [EvalPlus](https://github.com/evalplus/evalplus). Original Apache-2.0 license
is included as `LICENSE`. Benchmark input contracts define the accepted evaluation
domain; they may be stricter than the prose or some original base examples.
