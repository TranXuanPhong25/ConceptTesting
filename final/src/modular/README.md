# Input-generation benchmark

Pipeline hiện tại chạy hai method: `plain` và `boundary` (BVA). Default là `plain`.

```text
frozen PUT cohort → input preparation → input generation
→ freeze tất cả inputs → reference/domain checks → PUT evaluation → report
```

## Code ở đâu

| Module | Trách nhiệm |
|---|---|
| `pipeline.py` | Điều phối stages, freeze, manifest và run lock |
| `generators/` | Interface sinh input có thể thay thế; đọc lại frozen inputs |
| `arms/plain.py` | LLM sinh input trực tiếp |
| `arms/boundary.py` | Chia budget và gọi BVA cho từng PUT |
| `boundary_value_analysis/` | Soft BVA: một completion trực tiếp sinh concrete inputs mỗi allocated PUT |
| `boundary_value_analysis/legacy/` | Flow selection/context/compiler và checked grounding cũ |
| `call_builder.py` | Encode named arguments thành Python literals |
| `dataset.py`, `cohort.py` | Load specs/domain metadata và frozen PUT cohort |
| `references.py` | Chọn corrected HumanEval+ reference |
| `stages/reference_oracle.py` | Kiểm domain, chạy reference lấy expected output |
| `stages/put_evaluation.py` | Chạy PUT một lần; chỉ chạy lại input fail/error/timeout để xác nhận detection |
| `execution_cache.py` | Cache kết quả từng input/program/repeat bằng SQLite |
| `../runtime/execution.py` | Tạo subprocess và sandbox `bwrap` |
| `../runtime/worker.py` | Load Python function và gọi bằng `args`/`kwargs` |
| `../runtime/model.py` | Streaming Qwen transport |
| `../runtime/checkpoint.py` | Ghi request/response và giữ lịch sử retry |
| `calls.py` | Adapter `RecordedModelCalls` / `CachedModelCalls` cho pipeline |

`prompt + canonical_solution` tạo thành reference source hoàn chỉnh. Worker load
source bằng `compile`/`exec`, lấy function theo `entry_point`, rồi gọi với input.
Reference source và output chỉ được dùng sau input freeze.

PUT evaluation dừng sau lần đầu nếu input pass. Input fail/error/timeout được
chạy lại cùng seed; chỉ tính detection khi lần hai cũng fail/error/timeout.
`outcomes.retested` lưu index gốc của các input chạy lại, theo thứ tự kết quả
trong checkpoint `evaluation/<program_id>_retry_1.json`. `unstable` chỉ kiểm tra
status thay đổi trong nhóm này; input pass lần đầu không được kiểm tra stability.
Reference/domain checks vẫn chạy hai lần cho mọi input.

Mặc định execution cache chạy mỗi input trong sandbox riêng. Khi tắt cache,
confirmation batch chỉ chứa các input fail lần đầu; global state từ các passing
calls bị bỏ qua không được tái tạo trong batch này. Historical full-suite repeats
giữ policy gốc, không được xem là cùng protocol với confirmation subset.

## Chạy

```bash
final/.venv/bin/python -m final.src.modular.run --mode run \
  --cohort final/out/development_groups/boundary/all/cohort.json \
  --artifacts final/out/plain_bva_refactored \
  --arms plain boundary --target-programs 1 --input-budget 20
```

Transport đọc configuration từ environment hoặc private env file hiện có.
`--mode replay` là default và chỉ đọc artifacts của một run khớp source/settings.
CLI không còn các option concept/V11 hoặc legacy adapter.

## Input generation và reference

Inject `InputGenerator` hoặc truyền các method bằng `arms`. Interface và ví dụ ở
[generators/README.md](generators/README.md). Method dùng chung base class
`InputGenerationMethod`; optional input annotation là `guidance_id`.

Corrected references mặc định là HumanEval+ v0.1.10, chỉ gồm reference source và
metadata, không chứa hidden input arrays. Xem [reference data](../../data/references_README.md).
`TaskReferencePrograms` chỉ dùng khi được truyền tường minh cho diagnostics hoặc
synthetic fixtures. Rescore giữ nguyên các input đã freeze:

```bash
final/.venv/bin/python -m final.src.modular.rescore \
  --source-run <saved-run> --cohort <cohort.json> --artifacts <new-output>
```

## Execution cache và checkpoint

Cache mặc định ở `final/out/execution_cache/results.sqlite3`; đổi bằng
`--execution-cache <directory>`, tắt bằng `--no-execution-cache`.
Key chứa source/context/contract/input/expected/seed/timeout/tolerance và runtime/
harness/executor identity. Repeat 0 và 1 có entry riêng. Mỗi miss chạy một input
trong sandbox mới. Timeout/infrastructure failures không được reuse.

Run checkpoints là nguồn replay chính. Refactor thay source và executor identity,
nên không ép reuse cache entries cũ và không migrate historical manifests.
Dùng output directory mới cho source hiện tại. Frozen-input rescore có thể đọc
inputs cũ vào output mới mà không gọi model. Cold cache có thể tốn thêm startup;
cache duration lưu lại là thời gian lịch sử.

## Kiểm tra

```bash
final/.venv/bin/python -m pytest final/src/modular/tests -q
```

Tests bao gồm sandbox execution, plain/BVA integration, corrected references,
freeze barrier, cache invalidation/reuse, manifest drift, read-only replay và
transport/retry. Dependency test chặn import historical research packages để bảo
đảm pipeline hiện tại chạy độc lập. Results/checkpoints cũ được giữ để truy nguyên. Code concept và baseline cũ đã
được gỡ; chỉ còn một runtime cho pipeline hiện tại.
