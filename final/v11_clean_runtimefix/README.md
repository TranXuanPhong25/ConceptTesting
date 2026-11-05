> Archived documentation. Executable code was retired on 2026-11-05. Current entry point: `python -m final.src.modular.run`. Original source remains in Git history; saved outputs/checkpoints remain unchanged.

# Runtime fix continuation

Trạng thái mới nhất: full-V11 đã dừng theo user ở288case, giữ checkpoint. Run
hiện tại là `final.modular` arm concept-only; nó import mining/facts/sandbox từ
folder này. Các PID/lịch launch bên dưới là lịch sử, không phải trạng thái live.

Bản tiếp tục sau deadlock coverage collector ở cases151/156. Dùng supported
`COVERAGE_CORE=pytrace`, có CPU-inactivity watchdog120s và một native retry trong
scratch sạch, giữ nguyên overall wall budget. Xem [RUNTIME_FIX.md](RUNTIME_FIX.md).

14engineering checks pass;4439completed results/responses được import đúnghash.
V11 source, prompts, seeds, toolversions, cohort và oracle không sửa. Worker idle
lặp lại là infrastructure failure, không tự biến thành concept/test thất bại.

# V11 clean: pipeline gốc trên cohort PUT mới

Đây là family/arm `v11`, gồm concept-hybrid và các control matched. Mỗi PUT được
phân tích, sinh input và chấm bằng **suite của chính PUT đó**. Không gộp10suite
thành một super-suite để làm tăng số lỗi của arm.

| Module | Class / trách nhiệm |
|---|---|
| `mining.py` | `V11MiningStage`: B5 observation→confirmation→code→verifier, domain strategy |
| `facts.py` | `V11FactsStage`: coverage/mutmut/fuzz/ranking và spec fallback gốc |
| `round_one.py` | `V11RoundOneStage`: assertions round1 với prompt/seed v11 |
| `hybrid.py` | `V11HybridStage`: missed hints, strategies/retry, strict selection/caps |
| `arm.py` | `V11Arm`: concept/plain/placebo hybrids, toolinput và witness controls |
| `evaluation.py` | `V11ReferenceEvaluationStage`: gold từ reference, chạy raw owner PUT |
| `run.py` | `V11BenchmarkRunner`: per-PUT stages/checkpoints và tổng hợp |
| `supervisor.py` | Lịch launch, health checks30s, transient recovery và source guard |

V11 kernels/prompts được import từ bản gốc read-only, không viết lại mutation,
coverage, ranking hay predicate/strategy checker. Sandbox dùng đúng pinned versions:
Hypothesis6.169.0,mutmut3.8.0,coverage7.16.2,libcst1.9.0. Môi trường worker riêng
`final/.venv_v11`; gold oracle giữ environment của benchmark final hiện tại.

Các adaptation được ghi rõ trong PREREG: model Qwen3.5-27B, K1, seed alias theo
PUT, khôi phục spec metadata vào view, và reference oracle thay expected output do
LLM đoán. Function bodies/raw source giữ nguyên; canonical không vào preparation
workers/model prompts. Cả1634view đã compile và khớp AST body gốc.

**Không đổi cohort:** giữ manifest1634PUT;169PUT fail base được log skip,1465pass
base được chạy. Kết quả v1/recovery trước đó vẫn nguyên vẹn.

## Lịch và theo dõi

Endpoint sớm nhất từ14:05:32ngày01/11/2026(Vietnam), theo yêu cầu user25phút.
Supervisor còn chờ review/tests/hash readiness trước khi gửi bất kỳ completion.

- Lịch/monitor: `final/out/v11_clean_runtimefix_schedule/status.json`, `heartbeat.json`.
- Run: `final/out/v11_clean_runtimefix/status.json`, `summary.json`, `run.log`.
- Từng PUT: `cases/<task*10+program_id>/progress.json` và stage checkpoints.
- Physical requests: `requests/<content_hash>/`; failures/partial usage giữ đầy đủ.
- Keepalive20phút nằm riêng trong `keepalive/`, không gộp vào arm costs.

Supervisor kiểm tra mỗi30giây; lỗi transport/read-only retry từ cache với cap cũ.
Lỗi chuẩn bị không sửa được được ghi rõ trong denominator; không tự đổi taxonomy,
prompt, oracle hay source giữa run. Source drift dừng và yêu cầu version tiếp theo.

Supervisor được quản lý bởi user service `concepttester-v11-clean-runtimefix.service`, có
restart khi process mất. Trạng thái complete/user-stopped/source-drift/needs-review
không tự mở lại. Cấu hình endpoint nằm ngoài repo, quyền0600. Khi user yêu cầu dừng,
tạo `final/out/v11_clean_runtimefix_schedule/STOP` rồi stop service để không tự resume.

```bash
systemctl --user status concepttester-v11-clean-runtimefix.service
```

`V11BenchmarkRunner(stage_factories=...)` cho phép thêm/thay stage classes mà
không sửa vòng điều phối. Đây là một pipeline family nhiều-call/per-PUT; không
đưa nó vào arm một-call/task cũ rồi mặc định coi hai call budgets là tương đương.

```bash
final/.venv/bin/python -m pytest final/v11_clean_runtimefix/tests -q
```

Review và10engineering checks đã pass:5profile đối chiếu generation với v11 gốc,
native kernel fixture pinned, view/future-import/body preservation, reference dùng
raw owner source, bridge failure accounting và sampling top_p.

So sánh nội bộ v11 có matched logical strategy requests; matched-valid diagnostic
khớp **task-total** input count, không phải từng owner. So với arm một-call/task của
run cũ chỉ báo descriptive vì call/input budgets khác nhau. Không coi raw gain là
concept gain nếu chưa qua comparison/control phù hợp.

Bản mới giữ local, chưa commit/push.
