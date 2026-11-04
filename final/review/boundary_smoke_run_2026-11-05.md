# Plain + BVA: boundary smoke run readiness

User yêu cầu chạy hai arm trên dataset đã tách theo hướng boundary, ngày2026-11-05.
Theo protocol phát triển theo nhóm đã có, bắt đầu từ smoke6PUT, chưa mở rộng lên
development/check/full và chưa tạo PUT mới.

## Cấu hình đã khóa trước inference

- Cohort: `final/out/development_groups/boundary/smoke/cohort.json`.
- Task order: HumanEval/0,5,18,81,99,120; mỗi task PUT0, saved base-pass.
- Subset cohort hash: `3dce7e980e164f6e161febc08455f0ade571a921297e1755d61a42563cdbccfa`.
- Arms: `plain`, `boundary` (BVA); target_programs1; input budget20/arm/task.
- Model: user-supplied `qwen3.5-27b-awq`, context8192; backend config ngoài repo.
- Plain và BVA construction: temperature0.7, max2048tokens, seed314159+tasknumber.
- BVA selection: temperature0, max2048tokens, tối đa4boundaries/PUT.
- Tối đa18logicalcalls:6plain+6selection+6construction; skip có thể giảm số calls.
- Reference oracle/PUT evaluation: timeout3seconds/call,2repeats, trusted contract;
  all-task generation freeze trước bất kỳ reference outcome nào.
- Output: `final/out/boundary_smoke_plain_bva_20261105/`.

Registration: [PREREG](../modular/PREREG.md), amendment2026-11-05.
Output đã có `run_config.json`, `modular_manifest.json` khóa67sourcefiles,
`readiness.json` và `launch.sh`; không chứa endpoint/keys.

## Kiểm tra trước launch

60targeted checks pass (BVA module, arm integration và generator injection).
Subset checksum/task membership/PUT0/base-pass/generated count đều được verify.
Same-agent read-only review đã kiểm shared schema, prompt data separation,
context/input budgets, early skip, immutable checkpoints, transport retry history,
generation freeze và repeated reference/PUT evaluation. Không claim independent
review trong lần kiểm tra này.

Modern flow của cả hai arm không có classical concept mining/CFG/DFG/witness
sampling. BVA prose constraints vẫn là proposals; chỉ trusted contract/reference
outcomes được dùng cho validity/scoring. Tất cả generated/rejected/skip cases
được giữ lại; không sửa prompt/method theo outputs rồi overwrite run cũ.

## Trạng thái

Stored endpoint `/models` trả **HTTP404**. Chưa tokenize thành công, chưa gửi
completion, chưa launch controller và chưa có task inputs/reference/results.
Đã hỏi user endpoint hiện đang hoạt động. Không dùng paid router thay thế.

Sau khi nhận endpoint: cập nhật private env bên ngoài repo, kiểm expected model/
context/tokenizer, xác minh source hashes rồi launch `launch.sh` detached với
keepalive20minutes. Theo dõi `status.json`, `stage_events.jsonl` và call receipts;
chỉ báo running sau khi thấy controller và request thực tế.

Kết quả sẽ report theo6task: valid novel inputs, detected PUTs, boundary selection/
construction/validation failures, known/unknown calls/tokens. Đây là development
smoke với equal input caps và unequal LLM calls; không claim matched-call efficacy.
