# Kiểm tra boundary input trên 44 PUT — 05/11/2026

Có ít nhất **hai PUT có bug tại boundary về hành vi**: HumanEval/99 và HumanEval/124.
HumanEval/83 còn có lỗi `RecursionError` với input hợp lệ; đây là boundary tài nguyên
của implementation/runtime. Chưa tìm thấy witness ở 41 PUT còn lại trong phạm vi
kiểm tra, chưa đủ để kết luận các PUT đó đúng hoặc không có boundary bug.

Audit sử dụng đúng 44 task từ `development_groups.py --group boundary --tier all`,
mỗi task một PUT đã pass base, giữ nguyên PUT2/task83 và PUT1/task103. Các input
được thiết kế thủ công từ public spec, contract và source PUT. Không dùng hidden
plus tests, không gọi LLM, không sửa generator hay kết quả comparison đã freeze.

## Witness và các input lân cận

Tất cả input dưới đây pass contract và reference HumanEval+ v0.1.10 chạy thành công.
Mỗi trường hợp được xác nhận trong **hai sandbox riêng**, bằng cùng harness,
seed/tolerance và timeout 3 giây như pipeline.

| Task | Input | HumanEval+ | PUT | Boundary |
|---|---|---|---|---|
| 99 | `"-0.5000000000000001"` | `-1` | `0` | float ngay dưới -0.5 sau parse |
| 99 | `"-0.5"` | `-1` | `-1` | đúng tại -0.5 |
| 99 | `"-0.49999999999999994"` | `0` | `-1` | float ngay trên -0.5 sau parse |
| 124 | `"01-01-200"` | `False` | `True` | năm 3 ký tự; tổng độ dài 9 |
| 124 | `"01-01-2000"` | `True` | `True` | năm 4 ký tự; tổng độ dài 10 |
| 124 | `"01-01-20000"` | `False` | `True` | năm 5 ký tự; tổng độ dài 11 |
| 83 | `992` | số đếm hợp lệ | pass | sát giới hạn recursion của harness |
| 83 | `993` | số đếm hợp lệ | `RecursionError` | vượt giới hạn recursion của harness |
| 83 | `994` | số đếm hợp lệ | `RecursionError` | phía trên giới hạn |

Task99 dùng sai chiều so sánh trong nhánh số âm, nên chọn sai số nguyên ở hai phía
của nửa đơn vị. Task124 không kiểm tra đúng chiều dài phần năm; `mm-dd-yyyy` yêu cầu
bốn chữ số. Task83 tính lũy thừa bằng đệ quy tuyến tính, còn spec chỉ yêu cầu n là
số nguyên dương. Mốc 993 đo được trong runtime hiện tại, không phải cận semantic
trong spec và không được xem là mốc cố định cho mọi môi trường.

## Vì sao BVA hiện tại bỏ sót

Task99 nhận string nhưng boundary nằm ở giá trị số sau `float(value)`. Candidate
menu chỉ có length/run_length, nên thiếu characteristic cho số đã parse và phần
thập phân. Với task124, menu đã có length; LLM vẫn trả `no_applicable_boundary`
vì đòi spec ghi trực tiếp “length=10”, dù có thể suy ra từ format `mm-dd-yyyy`.
Task này có cả boundary của format lẫn các component month/day/year; chỉ thêm
component template chưa đủ, cần cải thiện cách suy ra boundary từ spec.

Task83 chỉ chọn cận domain n=1 và input n=1/2 đã có trong base. Lỗi recursion cần
kiểm tra implementation/resource limits; cần ghi nhận riêng với BVA của miền
semantic, tránh coi mọi stress input là bằng chứng BVA thành công.

Nhãn “boundary task” cho biết bài toán có characteristic phù hợp để thiết kế test.
Nhãn này không chứng minh PUT được chọn có bug. Nhiều PUT có logic giống reference,
ví dụ task2 cùng công thức `number-int(number)`, task23 cùng `len(string)`, task52
cùng phép kiểm tra `all(x<t)`. Không có bằng chứng cho giả định cả 44 PUT đều có
boundary input làm lộ bug.

## Phạm vi kiểm tra

Đóng băng 15.691 candidate trước khi chạy; tất cả pass contract/reference. Loại
116 input đã thuộc base, còn 15.575 input hợp lệ, mới được đối chiếu với PUT.
Bulk screen chạy trong bwrap; các witness và bộ ba lân cận được chạy lại riêng qua
execution cache với hai repeat slots. Batch observations không được nhập vào
cache của isolated execution. Corpus bao gồm lân cận số nguyên/float, length,
frequency, aggregate, quan hệ giữa input, parsed string, format và resource limit.

Đã liệt kê toàn bộ candidate trong miền public 1..1000 của task107 và156; lần lượt
8 và14 input thuộc base nên không chấm lại trong bulk screen. Các task khác chỉ
được tìm kiếm trong miền hữu hạn đã ghi ở plan. Không dùng kết quả này để ước lượng
recall hay chứng minh các PUT còn lại đúng. Việc chọn case và phân tích source diễn
ra sau comparison; đây là feasibility audit, không phải kết quả của BVA generator.

| Task / PUT | Boundary được kiểm tra | Input hợp lệ mới | Kết quả |
|---|---|---:|---|
| 0 / PUT0 | len 0/1/2; khoảng cách so với threshold | 80 | Chưa thấy witness |
| 2 / PUT0 | float dương sát 0 và sát số nguyên | 17 | Chưa thấy witness |
| 5 / PUT0 | list rỗng/1/2 phần tử; vị trí chèn | 123 | Chưa thấy witness |
| 10 / PUT0 | string rỗng; suffix palindrome | 131 | Chưa thấy witness |
| 14 / PUT0 | string rỗng/1 ký tự; vị trí prefix | 131 | Chưa thấy witness |
| 15 / PUT0 | n=0/1; mốc chữ số | 33 | Chưa thấy witness |
| 18 / PUT0 | độ dài text so với substring; overlap | 882 | Chưa thấy witness |
| 20 / PUT0 | len>=2; khoảng cách bằng nhau | 363 | Chưa thấy witness |
| 21 / PUT0 | len>=2; max-min sát 0 | 111 | Chưa thấy witness |
| 23 / PUT0 | độ dài string 0/1 | 131 | Chưa thấy witness |
| 30 / PUT0 | giá trị phần tử -1/0/1 | 120 | Chưa thấy witness |
| 36 / PUT0 | cận range; bội 11/13; chữ số 7 | 159 | Chưa thấy witness |
| 38 / PUT0 | độ dài nhóm 2/3/4 | 132 | Chưa thấy witness |
| 41 / PUT0 | n>=1; n lớn | 98 | Chưa thấy witness |
| 44 / PUT0 | base 2..9; x quanh base**k | 872 | Chưa thấy witness |
| 45 / PUT0 | a,h dương sát 0; độ lớn số | 48 | Chưa thấy witness |
| 47 / PUT0 | len 1/2; chẵn/lẻ; giá trị giữa | 366 | Chưa thấy witness |
| 52 / PUT0 | x<t tại t-1/t/t+1 | 164 | Chưa thấy witness |
| 60 / PUT0 | n=1; số nguyên lớn | 98 | Chưa thấy witness |
| 69 / PUT0 | count(x) quanh x | 378 | Chưa thấy witness |
| 71 / PUT0 | a+b quanh c; tam giác suy biến | 109 | Chưa thấy witness |
| 72 / PUT0 | sum(q) quanh w; palindrome | 363 | Chưa thấy witness |
| 74 / PUT0 | tổng độ dài hai list bằng nhau | 1599 | Chưa thấy witness |
| 77 / PUT0 | số âm/0/dương; k**3 +/-1 | 213 | Chưa thấy witness |
| 79 / PUT0 | 0; 2**k +/-1 | 170 | Chưa thấy witness |
| 80 / PUT0 | len 2/3/4; cửa sổ ba ký tự | 1095 | Chưa thấy witness |
| 81 / PUT0 | hai float kề mỗi threshold điểm | 34 | Chưa thấy witness |
| 83 / PUT2 | n=1/2/3; recursion transition 992/993 | 76 | Có witness RecursionError |
| 96 / PUT0 | n=0/1/2; cận trên loại prime | 191 | Chưa thấy witness |
| 97 / PUT0 | dấu; đơn vị số tại bội 10 | 1678 | Chưa thấy witness |
| 99 / PUT0 | số parse từ string quanh số nguyên và n+0.5 | 144 | Có witness output sai |
| 103 / PUT1 | n so với m; mean nguyên/bán nguyên; số lớn | 915 | Chưa thấy witness |
| 107 / PUT0 | liệt kê n=1..1000 | 992 | Chưa thấy witness |
| 115 / PUT0 | số ô nước quanh capacity; cạnh grid/capacity | 252 | Chưa thấy witness |
| 120 / PUT0 | len 1/1000; k=0/len; giá trị +/-1000 | 17 | Chưa thấy witness |
| 122 / PUT0 | giá trị +/-99/100; k=1/len; len=1/100 | 84 | Chưa thấy witness |
| 124 / PUT0 | month/day; năm 3/4/5 ký tự; len 9/10/11 | 216 | Có witness output sai |
| 133 / PUT0 | ceil tại hai float kề số nguyên | 55 | Chưa thấy witness |
| 138 / PUT0 | 7/8/9; chẵn/lẻ | 56 | Chưa thấy witness |
| 140 / PUT0 | run space 2/3; đầu/cuối string | 532 | Chưa thấy witness |
| 146 / PUT0 | 10/11; chữ số đầu/cuối lẻ | 134 | Chưa thấy witness |
| 156 / PUT0 | liệt kê number=1..1000 | 986 | Chưa thấy witness |
| 157 / PUT0 | đẳng thức Pythagoras; hoán vị và float kề | 1011 | Chưa thấy witness |
| 159 / PUT0 | 0/1000; need so với remaining | 216 | Chưa thấy witness |

Dữ liệu: [summary](../out/boundary_witness_audit_20261105/summary.json),
[plan/corpus](../out/boundary_witness_audit_20261105/plan.json),
[isolated neighbor confirmations](../out/boundary_witness_audit_20261105/neighbor_confirmations.json),
[JSON review](boundary_feasibility_2026-11-05.json).
Script: [audit_boundary_witnesses.py](audit_boundary_witnesses.py).
Toàn bộ 1.375 artifact của comparison gốc giữ nguyên qua audit và confirmation.
