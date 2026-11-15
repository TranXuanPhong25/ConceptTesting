# HumanEval input-generation pipeline

Code nằm trong `src/`, dataset và metadata trong `data/`.

Local run console: `./final/run_console.sh start`, mở
<http://127.0.0.1:4200/deployments> để chọn preset, chỉnh settings và tự bấm Run.
Prefect chạy trong venv riêng; đăng ký preset không tự gọi LLM.
[Hướng dẫn presets/history/resume](src/orchestration/README.md).

[Slides HTML: cách chạy full pipeline và luồng code từng stage/module](slides/pipeline.html).

```text
final/
├── src/
│   ├── modular/            # Pipeline hiện tại: plain và BVA
│   ├── runtime/            # Sandbox, worker, model transport và checkpoint
│   ├── audits/             # Audit offline trên artifacts đã lưu
│   └── core_model.py       # Model interface
├── data/                   # HumanEval, corrected references, contracts
├── tests/                  # Tests cho pipeline
├── out/                    # Run outputs, execution cache và checkpoints
└── review/                 # Reports và phân tích kết quả
```

Pipeline hiện tại: frozen PUTs → sinh input → freeze → reference/domain checks
→ PUT evaluation → report. Default dùng `plain`; `boundary` dùng BVA.

```bash
final/.venv/bin/python -m final.src.modular.run --help
final/.venv/bin/python -m final.src.modular.run --mode run \
  --cohort final/out/cohorts/qwen35_27b_humaneval164/cohort.json \
  --artifacts final/out/plain_bva_new --arms plain boundary \
  --target-programs 10 --input-budget 20

final/.venv/bin/python -m pytest final/src/modular/tests final/tests -q
```

Chi tiết: [pipeline](src/modular/README.md), [runtime](src/runtime/README.md),
[data](data/README.md). Source đã đổi vị trí nên dùng output directory mới;
không sửa manifest cũ để ép resume. Frozen-input rescore vẫn có thể dùng input cũ:
`python -m final.src.modular.rescore --help`.

Các bản concept và baseline cũ đã được gỡ; source và tài liệu cũ có thể tra qua
Git history. Reports và checkpoints phục vụ truy nguyên vẫn được giữ.
