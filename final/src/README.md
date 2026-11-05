# Source map

- `modular/`: current replaceable input-generation pipeline, plain/BVA, corrected
  reference selection, PUT evaluation and per-input execution cache.
- `runtime/`: shared sandbox execution and recorded model transport.
- `audits/`: offline result/source audits; reports go to `final/review`.
- `development_groups.py`: offline grouping/export from frozen PUTs/base evidence.
- `core_model.py`: model interface and compatible backend.
- `modular/program_prompts.py`: specification-only writer prompt.
- `runtime/contracts.py`: shared parsing, fingerprint and sandbox validation helpers.

Use module entry points from the repository root:

```bash
python -m final.src.modular.run --help
python -m final.src.modular.rescore --help
python -m final.src.development_groups --help
```

Input datasets/metadata live in `final/data`; generated results/checkpoints in
`final/out`; reports in `final/review`. Do not write run results into `src`.
