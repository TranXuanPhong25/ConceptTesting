# Audit hai unique detections: HumanEval97 và140

Audit saved artifacts của run boundary/all44. Không gọi model,không thay source,
không sửa frozen inputs/results. Đọc canonical_solution của HumanEval+v0.1.10
đã có trong local cache;không dùng plus_input hay hidden tests. Chạy corrected
reference trên đúng hai saved inputs,mỗi input2repeats,bằng harness hiện có.

**Kết luận: cả hai unique detections là false alarms do reference HumanEval gốc.
Ở cả hai case,PUT khớp spec và reference đã sửa của HumanEval+.**

| Task / input | PUT output | HumanEval reference gốc | HumanEval+ reference đã sửa |
|---|---|---|---|
|97: `multiply(-1, 2)`|`2`|`18`|`2`|
|140: `fix_spaces("  ")` — hai spaces|`"__"`|`"_"`|`"__"`|

##97—multiply,raw plain-only

Spec yêu cầu product of unit digits. PUT dùng `abs(a) % 10` và `abs(b) % 10`,
nên input(-1,2) cho1*2=2. Reference gốc dùng `abs(a % 10)`;Python có-1%10=9,
nên reference trả9*2=18. HumanEval+ sửa thành
`int(str(a)[-1]) * int(str(b)[-1])`,trả2giống PUT.

Saved suite của plain có20validinputs,7reference disagreements do negative
numbers. BVA trả no_boundary nên0inputs: selection reason nói không có threshold/
range được spec định nghĩa cho các scalar candidates hiện có. Đây là sự khác biệt
ở applicability/input generation,nhưng raw plain-only detection không phải PUTbug.

##140—fix_spaces,raw BVA-only

Spec yêu cầu mỗi space thành underscore,trừ run có hơn2spaces thì thành hyphen.
Với đúng2spaces,PUT trả2underscores. Reference gốc xử lý trailing run1hoặc2spaces
bằng một underscore cố định,nên trả`"_"`. HumanEval+ corrected reference trả`"__"`
và đồng ý với PUT. Cả hai stored evaluation repeats ghi actual`"__"` ổn định.

BVA selected threshold2,generation giữ2inputs:2spaces và3spaces. Chỉ2spaces tạo
reference disagreement;3spaces đều trảhyphen.

Plain **cũng đã đề xuất2spaces** trong raw response,nhưng dùng
`"args": "('  ')"` thay vì `"args": "('  ',)"`. Literal đầu tiên là string,
không phải positional tuple/list. Cả20records của plain bị parser loại với
invalid_literal,nên plain có0validinputs. Chênh lệch này không chứng minh BVA tìm
được semantic case mà plain không nghĩ ra;nó chứa lỗi đóng gói input của plain.

Còn một binding limitation: BVA prose nói consecutive-space count,nhưng executable
characteristic là len(text). Hai đại lượng chỉ trùng nhau với chuỗi toàn spaces.
Do đó18inputs có surrounding characters bị boundary_not_hit dù có thể chứa một
space run đúng2/3. Quote/schema validation chưa xác minh semantic binding này.

## Ảnh hưởng tới kết luận run

-Giữ nguyên raw recorded counts3vs3để truy nguyên artifacts,nhưng không gọi97/
  140là confirmed PUT bugs hoặc semantic concept wins.
-Sau khi loại hai known false alarms,mỗi arm còn hai task chung44/122chưa được
  audit trong bước này. Không tự suy ra hai task đó là true bugs.
-Pipeline đang dùng original HumanEval canonical solutions cùng contracts/atol
  của EvalPlus. Việc bổ sung contract không tự sửa canonical solution cũ.
-Cần dùng/đối chiếu corrected HumanEval+ references trước khi diễn giải detection
  thành bugfinding. Audit này chưa đổi oracle trong pipeline hoặc rescore toàn run.

Machine-readable evidence: [audit JSON](boundary_unique_task_audit_2026-11-05.json),
gồm source hashes,saved PUT results và hai corrected-reference repeats/case.
4diagnostic native executions được thực hiện;việc lưu audit sau đó dùng cache.
Cache entries của corrected references tách khỏi original do key có source/context.
