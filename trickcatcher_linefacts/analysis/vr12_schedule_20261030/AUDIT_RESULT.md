# Audit VR12 — 30/10/2026, 03:15 Vietnam

Run đã hoàn tất 11/11 task. Events ghi launch 00:45 và controller exit 00:57:54 Vietnam; audit xác nhận 11 scored receipt, generation freeze và RESULTS, không suy từ PID/status. Controller PID không còn, RUN.lock free. Không inference, endpoint poll, retry, worker execution hoặc timer mới trong audit.

79 source/input hash, 64 parent hash và review approval khớp; 1.542 file trong GENERATION_FREEZE khớp, target_reference_used=false. Ledger có 39 physical attempt/39 received response, identity khớp request body, dưới cap132; 118 logical round2 call dùng shared cache. New usage: 27.674 prompt +12.204 completion =39.878 token, 0 unknown. Reuse11 R1 +110 reference call:50.918 historical token,0 unknown; không tính là new spend. Không suy current quota từ screenshot.

| Oracle confirmed task | strict | retain | applicable | generic |
|---|---:|---:|---:|---:|
| Saved R1 ref |7|7|7|7|
| Final ref |9|9|9|8|
| Saved R1 o0 |5|5|5|5|
| Final o0 |6|7|7|5|

Recompute từ saved scored receipt xác nhận toàn bộ confirmed-task set. Ref gain so R1: strict/retain/applicable thêm27,118; generic thêm27. R1 có4 task headroom nhưng cohort chỉ2 OBS-uncovered target; không có held-out claim. Applicable không thắng retain/strict trên ref; thắng generic1 task118, sign-test p=1.0. Không đủ evidence để promote concept/applicability.

Strict/retain draw pool bằng nhau trên toàn11 task (20 cặp draw receipt; task89 không có draw). Selected exposing call theo task cộng lại: strict10, retain7, applicable7, generic7. Trong đó không có correct expected failing assertion:4/2/2/4; không có assertion:0/1/1/0. Vì vậy input exposure không đồng nghĩa oracle success, dù mechanism.missing_expected đều0.

**Limitation cần giữ:** RESULTS.json không khớp hoàn toàn scored receipt. Recompute ref abstained_calls của retain/applicable là11, report ghi10. Recompute o0 false-alarm task của retain/applicable có thêm27 (10 task thay vì9). Confirmed-task set không đổi; strict/generic và R1 khớp. Chưa xác định nguyên nhân; không sửa frozen artifact, không rerun scorer. Không coi bảng false-alarm/abstention trong RESULTS là đã fully verified.

VR12 là experiment riêng, không tích hợp vr13 retriever. Audit dùng saved execution receipt, không tái thực thi PUT/reference. Frozen sources/results và mọi dirty/staged change khác được giữ nguyên.

Artifact: [RESULTS.json](../../pipelines/vr12_expanded/out/humaneval/diagnostic/RESULTS.json), [GENERATION_FREEZE.json](../../pipelines/vr12_expanded/out/humaneval/diagnostic/GENERATION_FREEZE.json), [scored receipts](../../pipelines/vr12_expanded/out/humaneval/diagnostic/scored/), [events.jsonl](events.jsonl). Các out artifact là local ignored files; SHA256 được lưu trong [AUDIT_CHECKS.json](AUDIT_CHECKS.json), cùng score differences, exposure losses và usage. [audit_saved.py](audit_saved.py) chỉ đọc saved artifact.

Đây là local CLI follow-up, không bảo đảm tự gửi message về original chat.
