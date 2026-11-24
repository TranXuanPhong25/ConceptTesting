# Generated programs under test

Each JSONL line contains a generated Python program under test (PUT). The pair
of task ID and PUT ID identifies a program within its file. Source text and the
saved verdicts are preserved, including failed candidates and any repeated samples
retained by the original generation protocol.

| Benchmark | PUT generation | Tasks with PUTs | PUTs | Original base pass | Official EvalPlus base + plus pass |
| --- | --- | ---: | ---: | ---: | ---: |
| HumanEval | [Qwen 3.5 27B AWQ](humaneval-qwen3.5-27b-awq.jsonl) | 164/164 | 1,634 | 1,465 | — |
| HumanEval | [GPT-6 Luna](humaneval-gpt-6-luna.jsonl) | 164/164 | 1,640 | 1,601 | — |
| HumanEval+ v0.1.10 | [Flint v1.0](humanevalplus-flint-v1.0.jsonl) | 161/164 | 270 | 266 | 255 |
| MBPP+ v0.2.0 | [Saved cohort with a Qwen 3.5 27B AWQ continuation](mbppplus-qwen3.5-27b-awq-continuation.jsonl) | 337/378 | 3,041 | 2,133 | — |

The MBPP+ file records 1,264 PUTs from the Qwen continuation and 1,777
inherited PUTs whose writer model is unverified. Each row records which
generation source it came from.

The HumanEval rows use the original HumanEval base suite for
`original_base_status`. The MBPP+ rows use the public base tests from
the release. Flint additionally records `evalplus_base` and
`evalplus_plus` from the official HumanEval+ evaluator. A dash means the
release has no recorded official full-suite score for that cohort.

The `task_id` and `solution` fields follow the EvalPlus JSONL format.
The other fields retain local IDs, saved verdicts, and MBPP+ generation
provenance. [The manifest](manifest.json) lists coverage, verdict counts,
generation details, and SHA-256 hashes.

Benchmark sources and licenses are available with the original releases.
[HumanEval](https://github.com/openai/human-eval) ·
[HumanEval+ v0.1.10](https://github.com/evalplus/humanevalplus_release/releases/tag/v0.1.10) ·
[MBPP+ v0.2.0](https://github.com/evalplus/mbppplus_release/releases/tag/v0.2.0) ·
[EvalPlus license](../evalplus_LICENSE)
