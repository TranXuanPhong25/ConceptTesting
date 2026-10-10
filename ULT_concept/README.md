# ULT_concept — UnLeakedTestBench (ULT) with concept injection

Benchmark: **UnLeakedTestBench** — "Benchmarking LLMs for Unit Test Generation
from Real-World Functions" (Huang et al., arXiv
[2508.00408](https://arxiv.org/abs/2508.00408), TOSEM). 3,909 decontaminated
real-world Python functions (cyclomatic complexity >= 10); `ULT_Lite` is a
200-function subset. Metrics: Pass@k, LCov@k, BCov@k, Mut@k (cosmic-ray).

`vendor_ULT/` is the authors' repo, unmodified
(<https://github.com/huangd1999/UnLeakedTestBench>, commit `d992b2d`).

## Why there is glue code

The authors' repo cannot run as-is: `src/generate_cov_*.py` import a
`data_utils` module that is not in the repo and read a hard-coded
`../dataset/mutation_dataset.jsonl`; generation is OpenAI-only; nothing builds
the `data/*_mods/` trees that `Ray/main.py`'s pytest step expects, and its
`__main__` is wired to the authors' own files. So:

- `generate.py` — the authors' `system.txt` + `template_base.txt` and their
  K-round chat (`testgeneration_multiround`: same follow-up text, history kept,
  temperature 0.2, max_tokens 1024, K=5), on native Vertex Gemini.
- `evaluate.py` — lays out each task and reuses `Ray/main.py`'s `code_import`
  header, `rename_test_functions` and cosmic-ray toml. Its docstring lists
  every scoring choice (per-test files, coverage from passing tests only,
  restricted to the function under test, etc.).

## Known dataset/harness issues

- The datasets are one JSON array per file despite the `.jsonl` extension.
- `ULT_Lite`'s `test_list` is not a trustworthy oracle: many expected values
  are wrong (e.g. task 147 `BinaryFromFraction(1, 2)`), so
  `--ground-truth` only checks pipeline mechanics, not an upper bound.
- The authors' test header `from mod import *` skips `_private` functions;
  `evaluate.py` also imports the function under test by name.

## Run

```bash
.venv/bin/python -m ULT_concept.generate --dataset ULT_Lite --arm baseline \
    --out ULT_concept/out/ULT_Lite_baseline.jsonl --workers 3
.venv/bin/python -m ULT_concept.evaluate --gen ULT_concept/out/ULT_Lite_baseline.jsonl --mutation
```

Generated tests run in `ULT_concept/.venv_exec` (python 3.12, pytest,
pytest-cov, pytest-timeout, numpy, pandas, cosmic-ray), created with
`uv venv -p 3.12 ULT_concept/.venv_exec && uv pip install -p ULT_concept/.venv_exec/bin/python pytest pytest-cov pytest-timeout numpy pandas cosmic-ray`.
