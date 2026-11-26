# Tra cứu JSON của modular pipeline

Các path dưới đây tính từ thư mục output của run. `tasks/<n>/` là thư mục artifact của một task, ví dụ `tasks/6/` cho `HumanEval/6`. Một số file chỉ xuất hiện khi chọn arm, generator hoặc runner tương ứng.

Khi đọc một task, đi theo `cohort.json` → `packet.json` → `calls/<call>/response.json` → `inputs.json` → `oracle_valid.json` → `result.json`. Xem `modular_summary.json` để đối chiếu các task và arm ở cấp run.

## Dữ liệu đầu vào

| File | Nội dung và nơi dùng |
|---|---|
| `cohort.json` | Danh sách task, PUT được chuẩn bị cho mỗi task và kết quả base tests. `BenchmarkPipeline` / `load_cohort` lấy record theo `task_id`. Đây là file được truyền vào run, có thể nằm ngoài thư mục output. |
| `final/data/humaneval.jsonl` | Đề bài HumanEval, gồm prompt và entry point. Dataset loader đọc từng dòng. |
| `final/data/contracts.json` | Metadata theo `task_id`, gồm contract, input types và các thông tin phục vụ kiểm tra input. |
| `final/data/humanevalplus_v0.1.10_references.json` | Nguồn reference program mà `HumanEvalPlusReferencePrograms` dùng. |
| `fault_oriented_testing/soft_examples.json` | Ví dụ hướng dẫn đi kèm prompt của EP/BVA V2 và Decision Table V2. File này nằm cạnh source code. |

## Cấp run

| File | Nội dung và nơi dùng |
|---|---|
| `modular_manifest.json` | `BenchmarkPipeline.write_manifest()` ghi task IDs, settings, stages, arms, generator, model và package versions. Dùng để xem config thực tế của run. |
| `status.json` | Trạng thái do CLI hoặc runner ghi, có thể gồm phase, PID và thông tin lỗi tùy runner. |
| `progress.json` | Tiến độ do một số worker ghi, ví dụ số task đã sinh input và số task đã evaluate. |
| `modular_summary.json` | Kết quả tổng hợp khi run xong. Replay đếm từ `result.json` và đối chiếu summary khi có. |
| `rescore_metrics.json` | Metrics của output rescore, gồm detection kinds theo arm và union cùng số model calls mới. |
| `manifest.json` | Tên manifest của pipeline cũ. CLI modular nhận diện tên này để chặn ghi vào run cũ. |
| `generation_frozen.json`, `keepalive/*.json` | Có thể gặp trong output cũ hoặc runner khác. File đầu ghi dấu vết generation, file sau ghi observer/keepalive usage. Modular replay hiện tại lấy kết quả từ task results. |

## Cấp task — `tasks/<n>/`

| File | Ai tạo và dùng để làm gì |
|---|---|
| `packet.json` | `load_or_prepare_packet` / `prepare_task_packet` ghi PUT được chọn (`visible_put_ids`), các khối prompt (`prompt_blocks`) và token counts, hoặc lý do skip. Packet cũ lưu prompt dạng chuỗi trong `common`. |
| `inputs.json` | `generate_task_inputs` lưu batch chung gồm `task_id` và `arms`, hoặc `skip`. Mỗi arm có `inputs` và có thể kèm `rejected`, `catalogue`, `concepts` hay metadata riêng. Pipeline đọc lại file có sẵn khi resume và kiểm tra envelope trước khi giao cho oracle. |
| `reference_program.json` | `run_reference_oracle` ghi provenance của reference khi provider bật tính năng đó. |
| `oracle_<repeat>.json` | Kết quả từng lần chạy reference, trước bước tổng hợp input hợp lệ. |
| `oracle_valid.json` | Input đã qua oracle và expected output tương ứng, kèm mapping về arm và thông tin reject. `evaluate_puts` dùng dữ liệu này trong context. |
| `catalogue_measurements.json` | `measure_task_catalogues` ghi kết quả đo class, boundary và rule cho các arm dùng catalogue, dựa trên input đã qua bước kiểm tra của oracle. |
| `evaluation/<put_id>_0.json`, `evaluation/<put_id>_retry_1.json` | Kết quả chạy từng PUT, gồm lần đầu và lần xác nhận khi cần. |
| `result.json` | Kết quả đánh giá của một task, dùng cho reporting và replay. Có `inputs.json` mới xác nhận batch đã được lưu, còn `result.json` là dấu mốc evaluation của task. |

### Model calls — `tasks/<n>/calls/<call>/`

| File | Nội dung |
|---|---|
| `request.json` | Messages, temperature, max tokens, seed, và response format nếu có. |
| `attempt.json` | Request ID, trạng thái attempt, số lần thử và lỗi transport nếu có. |
| `response.json` | `ModelResponse` đã lưu, gồm text, finish reason và token usage. Đây là response thô trước khi parse thành `inputs.json`. |
| `partial_response.json` | Text nhận được trước khi transport lỗi, nếu có partial output. |
| `../<call>_unknown_attempt_*/` | Các thư mục attempt cũ được giữ lại khi retry. |
| `../<call>.retry_extension.json` | Cấu hình retry bổ sung cho một request cụ thể khi được cấp. |
| `../<call>.frozen_request_replay.json` | Directive của một số flow replay chuyên biệt, dùng để chọn request đã lưu và kiểm tra identity của request đó. |

### Artifact theo generator hoặc arm

Các path ở đây nằm trong `tasks/<n>/`, trừ hai file gate ở cấp run.

| Path | Nội dung |
|---|---|
| `control_flow/analysis.json` | Phân tích PUT, baseline coverage, target được chọn và lỗi phân tích. |
| `control_flow/base_<hash>.json` | Trace từ các base calls đã ghi, dùng khi cần bổ sung baseline coverage. |
| `control_flow/response_<round>.json` | Response và thông tin call theo round của CF. |
| `control_flow/generation.json` | Batch riêng của CF, gồm input được chọn, concept, rounds và trace evidence. |
| `<vf3_arm>/round_<n>_feedback.json` | Kết quả đo membership trước oracle cho từng lượt VF3. Batch giữ `call_name` để tra request và response. |
| `boundary_plan.json`, `boundary_arm.json` | Kế hoạch chia input budget theo PUT và kết quả gộp cho arm `boundary`. |
| `boundary/soft_bva/<put_id>/{identity,inputs_prompt,result}.json` | Identity dùng để đối chiếu checkpoint, prompt và kết quả soft BVA theo từng PUT. |
| `tool_generation.json` | Batch của tool generator với candidate ledger, preparation và tool receipts theo arm. |
| `tool_generation_gate.json`, `semantic_controls_gate.json` | Báo cáo điều kiện để vào evaluation. Semantic controls chỉ có khi được cấu hình. |
| `tool_audit/<arm>.json` | Kết quả audit lựa chọn input của tool arm sau evaluation. |
| `pynguin/intent.json`, `pynguin/batch.json` | Provenance và dấu đã nhận quyền dispatch, sau đó là batch và receipts đã lưu. |
| `pynguin/owners/<i>/*.json` | Source của PUT, stdout/stderr và source test được export, tùy kết quả sandbox. |
| `<data_flow_arm>/{baseline,observation_<i>,measurement}.json` | Baseline, từng observation và kết quả đo data-flow nếu dùng đường measurement tương ứng. |

## BVA batch đang mở trong IDE

Thư mục `final/out/bva_batch_matched164_20261108_021740/` là output của runner `run_bva_batch.py`. File `generation/tasks/6/inputs.json` có hai arm `direct` và `soft_bva`. Mỗi arm có `inputs`, `rejected` và `finish_reason`. Prompt context ở `generation/tasks/6/packet.json`, còn request/attempt/response nằm dưới `generation/tasks/6/calls/<arm>/`.

| File ở thư mục batch | Nội dung |
|---|---|
| `launch_plan.json` | Runtime/cohort, settings, task đủ điều kiện, arms và giới hạn logical calls. |
| `request_plan.json` | Danh sách request dự kiến, thông tin chọn PUT hiển thị và số logical calls. |
| `source_snapshot.json` | Danh sách hash của các file nguồn dùng cho batch và metadata archive. |
| `review_receipt.json`, `ready_to_launch.json` | Biên nhận review/tests và điều kiện trước khi launch. |
| `launch_reserved.json`, `worker_started.json` | Marker đặt chỗ launch và marker worker đã bắt đầu. |
| `endpoint_readiness.json` | Kết quả kiểm tra model endpoint trước khi chạy. |
| `status.json` | Trạng thái gần nhất của runner, gồm thông tin lỗi nếu có. |
| `runtime/cohort.json` | Bản cohort trong runtime của batch. |
| `keepalive/*.json` | Record keepalive của runner cũ. |

Phạm vi note là artifact của modular pipeline và batch BVA trên, tính theo mẫu path. Preset, dataset của adapter khác và output của các experiment cũ có thể dùng schema riêng.
