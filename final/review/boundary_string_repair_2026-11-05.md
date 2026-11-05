# Bổ sung characteristic cho string trong BVA — 05/11/2026

Sau feasibility audit, module BVA đã được sửa trên code hiện tại để biểu diễn
boundary bên trong numeric string và cung cấp bằng chứng suy ra độ dài từ format.
Pipeline chính vẫn nhận bộ sinh input qua dependency injection.

`parsed_float` đo giá trị số sau khi parse string. Khi spec yêu cầu nearest integer,
guidance cung cấp midpoint đại diện `0.5` và `-0.5`, kèm quy tắc suy ra và quote.
Code tính các float kề threshold rồi dùng `repr` mã hóa lại thành string. Với một
parameter được điều khiển hoàn toàn, module có thể sinh input ngay sau selection.
Spec phải có bằng chứng numeric-string phù hợp; chỉ thấy `float(...)` trong PUT
hoặc một số input trông giống số không đủ để chấp nhận binding này.
Threshold hoặc target số nguyên không biểu diễn chính xác được bằng float sẽ bị
từ chối với lý do riêng, thay vì bị làm tròn âm thầm sang một boundary khác.

Với fixed-width format như `mm-dd-yyyy`, guidance ghi lại field widths `2/2/4`
và tổng độ dài 10. LLM được hướng dẫn dùng bằng chứng suy ra thay vì đòi spec ghi
nguyên văn “length=10”. Đây là boundary hành vi: string sai format vẫn có thể là
input hợp lệ theo contract, với output đúng là False. Các rule có phạm vi hẹp;
không tự suy ra độ dài cố định từ ví dụ, câu phủ định, format biến thiên, optional
suffix hoặc không xác định được parameter. LLM vẫn có thể từ chối selection;
không có bước tự động ép chọn hay fallback sinh test.

205 checks đã pass, gồm 196 modular và 9 development-selection; 40 case mới kiểm finite
parsing, không execute string, signed zero/subnormal/adjacent float, bằng chứng
projection, precision loss, negative declarations, fixed format, parameter rename và domain role.
Một integration case dùng đúng hai PUT đã lưu của task 99/124, đưa qua injected
generator, freeze toàn bộ input, corrected HumanEval+ và hai stability repeats.
Các input mới làm lộ hai bug đã biết. Selection và context trong test là scripted,
nên kết quả chỉ xác nhận cơ chế và integration, chưa xác nhận LLM sẽ chọn đúng.
Canonical solution bị thay bằng marker trong fixture task để kiểm nó không đi vào
prompt và không được dùng thay pinned corrected reference.

Offline inspection trên 44 task cung cấp projection evidence cho 99 và derived
guards cho 99/124. Đây là kiểm tra khả năng biểu diễn, không phải precision hoặc
bug-detection efficacy. Toàn bộ 1.375 artifact của run trước giữ nguyên. Chưa gọi
LLM hoặc chạy lại comparison; protocol/schema mới là version 3 và cần output mới
khi sinh input. Lỗi recursion của 83 được giữ là vấn đề resource/runtime riêng.

Code: [string guidance](../modular/boundary_value_analysis/string_guidance.py),
[characteristics](../modular/boundary_value_analysis/characteristics.py),
[construction](../modular/boundary_value_analysis/construction.py).
Kiểm tra: [regression tests](../modular/tests/test_bva_string_characteristics.py),
[offline44inspection](boundary_string_repair_offline_2026-11-05.json).

Lệnh validation:

```bash
final/.venv/bin/python -m pytest final/modular/tests final/tests/test_development_groups.py -q
```
