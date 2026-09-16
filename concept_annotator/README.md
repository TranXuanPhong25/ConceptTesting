# concept_annotator

TEstEval-inspired concept annotator for this repo's vulnerability-triggering experiments.

The idea copied from TEstEval is the task split: overall coverage, targeted line/branch coverage, and targeted path coverage. Here we adapt that into de-leaked C memory-safety annotations:

- `target_lines`: dangerous sink lines such as `memcpy`, array access, deref-after-free, or repeated `free`.
- `blocks`: branch/control lines that gate a sink.
- `sampled_paths`: ordered waypoints such as guard -> sink, or free -> guard -> later deref.

It does not use `fault_cond`, `fix_hint`, `func_fixed`, or CWE labels. If `lines_concept` already exists, it merges those tags with a small stdlib heuristic so quick ablations can run without tree-sitter.

## Annotate a JSONL

```bash
.venv/bin/python -m concept_annotator.run \
  --in bench/items/gold_juliet.jsonl \
  --out concept_annotator/juliet_targets.jsonl \
  --limit 5
```

Each row gets a `concept_annotation` object with:

- `family_pred`
- `concept_lines`
- `targets`
- `testeval.target_lines`
- `testeval.blocks`
- `testeval.sampled_paths`

## Run the prompt ablation

```bash
LLM_PROVIDER=router ROUTER_API_KEY=... ROUTER_BASE_URL=... \
CONDS=bench_concept_en,concept_testeval_en \
.venv/bin/python -m concept_annotator.experiment
```

This reuses `bench/lab.py` and compares the existing English concept prompt against `concept_testeval_en`.
