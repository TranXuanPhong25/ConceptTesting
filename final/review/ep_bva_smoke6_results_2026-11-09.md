# Smoke6 Plain vs EP+BVA — kết quả

Plain và EP+BVA cùng phát hiện **1/6 eligible PUTs**, trên cùng **1/6 task** (HumanEval/99, PUT0), đều là wrong-value. Smoke này chưa cho thấy lợi ích detection của EP+BVA. Chỉ có 6 task/6 representative PUTs; không suy ra kết quả benchmark đầy đủ. Catalogue mới chỉ qua schema ở 2/6 task; mechanical single-fault và semantic grounding vẫn pending.

| Metric | Plain | EP+BVA |
|---|---:|---:|
| Generated input records | 120/120 slots | 120/120 slots |
| Novel reference-valid inputs | 118 | 109 |
| Confirmed detected PUTs / evaluated eligible PUTs | 1/6 | 1/6 |
| Task có detection / evaluated tasks | 1/6 | 1/6 |
| Wrong-value PUTs | 1 | 1 |
| Exception-only PUTs | 0 | 0 |
| Timeout/resource-only PUTs | 0 | 0 |
| Generation calls nhận response | 6/6 | 6/6 |
| Prompt tokens | 5,243 | 7,187 |
| Completion tokens | 4,469 | 11,422 |
| Total tokens | 9,712 | 18,609 |

EP+BVA dùng **1,92× total tokens** của Plain (+91,6%) trong run này. Tổng12logical calls/12physical attempts nhận đủ12responses, 0unknown,0transport retry,0truncated response; tổng28,321tokens (12,430prompt +15,891completion). Keepalive0calls. Một PUT có nhiều confirming inputs vẫn chỉ tính một detected PUT. Hai arm có23novel inputs trùng nhau; union có204unique reference-valid inputs.

Matched-valid-input-budget: 107inputs mỗi arm sau subset ngẫu nhiên có seed theo task/pair. Cùng phát hiện1/6PUT, không có arm-only task win; paired permutation p=1,0. Raw và matched đều hòa trong smoke này.

## Config và source

- Prefect: http://127.0.0.1:4200/runs/flow-run/a143aa28-f017-4ab8-a536-09f7816e3149
- Source/output: `final/out/console_a143aa28-f017-4ab8-a536-09f7816e3149/run`; config/source/cohort snapshot nằm trong cùng run.
- Task IDs: 0,5,18,81,99,120; một representative PUT/task từ boundary smoke cohort.
- Arms: plain,ep_bva. Mỗi task/arm20input slots,1generation call; tối đa12logical calls/240records.
- Model:qwen3.5-27b-awq; shared completion cap4096tokens/call,context8192tokens,temperature0.7.
- Input seed314159 cộng task number; reference seed271828 cộng task number; timeout3giây/input.
- Corrected HumanEval+ reference,reference2runs; PUT scorer confirm_first_failures. Inputs global freeze trước native evaluation.
- Kết thúc qua source checks và immutable read-only replay; không có generation/evaluation bổ sung để viết report.

## Theo task

| Task | Plain novel valid inputs | EP+BVA novel valid inputs | Plain detected PUTs | EP+BVA detected PUTs |
|---|---:|---:|---:|---:|
| HumanEval/0 | 20 | 20 | 0 | 0 |
| HumanEval/5 | 20 | 18 | 0 | 0 |
| HumanEval/18 | 18 | 20 | 0 | 0 |
| HumanEval/81 | 20 | 19 | 0 | 0 |
| HumanEval/99 | 20 | 12 | 1 | 1 |
| HumanEval/120 | 20 | 20 | 0 | 0 |

Plain bị loại2base-duplicate inputs. EP+BVA bị loại6base duplicates và5domain/reference rejects; 5rejects ở task99 là strings không thuộc domain như abc/empty/nan/inf/-inf. Không có task bị skip.

## Catalogue: interface và semantic limits

- Schema-valid2/6catalogues:task0,120. Cả hai thiếu nominal nên single_fault/normal_design vẫn pending;18class measurements của hai task này đều pending.
- Task5,81:boundary thêm lower_inclusive/upper_inclusive ngoài schema. Task18:context là prose string thay dict. Task99:lower/upper là string và context là prose. Bốn catalogue_invalid không làm mất120generated input records của EP+BVA.
- Audit nhận thấy task0 tự đặt một số giới hạn không có căn cứ trong spec; task120 dùng selector không phù hợp cho scalar/list. Task18 có labels phủ class sai. Vì vậy covers chỉ là self-report, không được coi là verified coverage.
- Field uncovered_boundary_values trong raw measurement đang bằng0 vì sum bỏ qua mọi missing_values=null. **Giá trị diễn giải đúng ở đây là pending**, không phải đã kiểm và thấy thiếu0boundary values. Report này không sửa raw frozen artifacts.
- Chi tiết ở `final/review/ep_bva_smoke6_catalogue_audit_2026-11-08.md`. Chưa có semantic certification hay base-call coverage.

## Giới hạn và bước sau

Run hoàn tất đúng scope smoke6. Kết quả input-based detection là hòa; catalogue interface/semantic quality chưa đủ để claim đã thực hiện normal BVA có kiểm chứng. Không tự chạy ablation,DT,dev/check/full hoặc rerun; người dùng quyết định lần chạy tiếp theo.
