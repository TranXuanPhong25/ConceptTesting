# HumanEval input-generation pipeline

Code nằm trong `src/`, dataset và metadata trong `data/`.

```text
final/
├── src/
│   ├── modular/            # Pipeline hiện tại: plain và BVA
│   ├── runtime/            # Sandbox, worker, model transport và checkpoint
│   ├── audits/             # Audit offline trên artifacts đã lưu
│   ├── development_groups.py
│   └── ...                 # Model interface và plain baseline ban đầu
├── data/                   # HumanEval, corrected references, contracts, inventory
├── tests/                  # Tests cho baseline và development selection
├── out/                    # Run outputs, execution cache và checkpoints
└── review/                 # Reports và phân tích kết quả
```

Pipeline hiện tại: frozen PUTs → sinh input → freeze → reference/domain checks
→ PUT evaluation → report. Default dùng `plain`; `boundary` dùng BVA.

```bash
final/.venv/bin/python -m final.src.modular.run --help
final/.venv/bin/python -m final.src.modular.run --mode run \
  --cohort final/out/development_groups/boundary/all/cohort.json \
  --artifacts final/out/plain_bva_new --arms plain boundary \
  --target-programs 1 --input-budget 20

final/.venv/bin/python -m pytest final/src/modular/tests final/tests -q
```

Chi tiết: [pipeline](src/modular/README.md), [runtime](src/runtime/README.md),
[data](data/README.md). Source đã đổi vị trí nên dùng output directory mới;
không sửa manifest cũ để ép resume. Frozen-input rescore vẫn có thể dùng input cũ:
`python -m final.src.modular.rescore --help`.

Code concept_reference_v1, recovery và V11 cũ đã được gỡ. Documentation lịch sử
vẫn ở các folder cũ; source gốc tra qua Git history, results/checkpoints giữ ở
`out/`. Plain baseline ban đầu còn tại `python -m final.src.run`; pipeline hiện tại
không phụ thuộc entry point đó.
