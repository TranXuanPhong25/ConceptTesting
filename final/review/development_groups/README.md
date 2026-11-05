# Bốn hướng development từ test_slides

Đọc [REPORT.md](REPORT.md) để xem nhóm và obligation của đủ164task. File
[task_review.tsv](task_review.tsv) là phần phân loại thủ công để user sửa/review;
[inventory.json](inventory.json) chứa source/base evidence của từng PUT;
[subsets.json](subsets.json) khóa bộ nhỏ và PUT representative được chọn.

`inventory.json` là artifact chi tiết được gitignore, giữ trên máy và tạo lại bằng
`python -m final.src.development_groups build`. Source, phân loại thủ công, báo cáo và
subsets tổng hợp được giữ trong Git. Các checks cần cohort/inventory sẽ skip rõ lý
do nếu checkout không có local artifacts; synthetic checks vẫn chạy bình thường.

Đây là việc phân lớp và chuẩn bị subset, chưa phải4generator mới và chưa chứng minh
hiệu quả của concept. Không chạy model hoặc sinh test mới trong bước này.

## Từ slide sang concept

| Hướng | Nguồn slide, số trang PDF từ1 | Concept/obligation | Cần đo khi phát triển |
|---|---|---|---|
| Boundary | `03. Kiem thu chuc nang.pdf`, p.5–17, đặc biệt p.7 | Min/min+/nom/max-/max; threshold và hai phía khi có chuyển behavior | Input có hợp lệ không, có thực sự chạm boundary không, PUT bị phát hiện |
| Equivalence | cùng PDF, p.19–32 | Các lớp không rỗng, rời nhau, phủ domain; đại diện mỗi lớp/combination cần thiết | Bao nhiêu lớp hợp lệ được kiểm; không mặc định mọi shape là một partition hợp lệ |
| Statement | `04.Kiem_thu_dong_dieu_khien.pdf`, p.22–29 | Statement chưa chạy và điều kiện đi tới nó trong CFG | C1 tăng bao nhiêu; C2/branch nếu thêm phải ghi riêng |
| Def-use | `05.Kiem thu dong du lieu-2-2 (2).pdf`, p.10–16,22,32 | Definition nào tới c-use/p-use nào qua def-clear path | Dynamic all-defs/all-uses; phân biệt initialization/update và không có redef ở giữa |

C1 là node/statement coverage, không phải edge/branch coverage. DFG trong bộ này
là các quan hệ reaching-definition trên CFG, không phải đồ thị tùy ý nối hai dòng.
Coverage cả hai endpoint không chứng minh một DU pair đã được cover. Slide cũng
chỉ ra infeasible paths; static candidate không phải obligation chắc chắn khả thi.

Boundary và equivalence theo spec/domain. Với HumanEval, nhiều task chỉ giới hạn
kiểu/quan hệ chứ không có finite min/max; không được tự đặt max30 của benchmark
thành semantic boundary. Ngoài miền chỉ được dùng khi spec định nghĩa behavior
reject/invalid, ví dụ `valid_date`; không coi input bị contract loại là bug.

## Cách lập nhóm

1. Đọc spec của164task; ghi một primary development group và secondary labels.
2. Đọc frozen source và base outcome của1634PUT; chỉ1465base-pass mới được chọn.
3. Với mỗi base-pass PUT, dùng AST, `coverage.parser.PythonParser` và
   `python_graphs` thật để lấy executable lines/CFG/LAST_WRITE. Không reimplement
   graph algorithms. Phân tích source không execute chương trình.
4. Statement-ready cần graph được hỗ trợ và ít nhất một executable line chưa có
   trong cached base coverage. Đây là **line-level proxy cho C1**; không gọi nó là
   exact statement coverage hoặc khẳng định line đó khả thi trong domain.
5. DU-ready cần static pairs và alternative reaching definitions hoặc loop updates.
   Đây là cơ hội phát triển data-flow concepts, chưa biết dynamic DU coverage.
   Alias/container mutation/interprocedural flow cần mở rộng trước khi claim đủ.
6. Chọn theo primary group để4bộ smoke không trùng task. Với statement ưu tiên PUT
   có nhiều missing lines; DU ưu tiên nhiều alternative definitions; tie theo saved
   program id. Không đọc reference, plus tests, generated suites hay detected labels
   để chọn. Đây là bộ development có chủ đích, không dùng suy rộng defect prevalence.

Một task có thể phù hợp nhiều phương pháp; nhóm chính chỉ để track hướng đang
phát triển. Một PUT one-liner có thể không phù hợp DU dù task được gán primary DU.
Task source cũ của TrickCatcher có sẵn hay không cũng được ghi, nhưng chưa thay
cohort hoặc khẳng định qualification của bộ cũ trên runtime hiện tại.

## Chạy từng bộ nhỏ

```bash
# Offline inventory: không gọi model/reference, không execute PUT.
final/.venv/bin/python -m final.src.development_groups build

# Export6PUT từ6task boundary, mỗi task1PUT đã lưu.
final/.venv/bin/python -m final.src.development_groups export \
  --group boundary --tier smoke --output final/out/dev_boundary_smoke
```

Thay group bằng `equivalence`, `statement` hoặc `def_use`. Tier `development`
gồm smoke và các task bổ sung, tối đa12PUT; `check`≤4task tách khỏi development;
`all` lấy toàn nhóm có source fit. Check là development check, không phải held-out
mới: HumanEval đã được nghiên cứu trước. Statement chỉ còn15task có static/base
gap đủ điều kiện nên bộ development có11task, không cố điền task đã100%C1.

Export giữ nguyên code, program id, base results và parent-cohort hash, không sinh
lại PUT. Chỉ tạo cohort con riêng cho development. Mỗi record representative có
`generated=base_pass=1`; khi dùng với `BenchmarkPipeline` phải chọn task IDs trong
`selection.json` và `PipelineSettings(target_programs=1)`. Đừng dùng mặc định10
vì sẽ bị skip generation_shortfall. Cụ thể:

```python
import json
from pathlib import Path
from final.modular.context import PipelineSettings
from final.modular.pipeline import BenchmarkPipeline
from final.run import load_tasks

directory = Path("final/out/dev_boundary_smoke")
selection = json.loads((directory / "selection.json").read_text())
selected_ids = set(selection["task_ids"])
tasks = [task for task in load_tasks() if task["task_id"] in selected_ids]
settings = PipelineSettings(target_programs=selection["target_programs"])
# pipeline = BenchmarkPipeline(directory / "cohort.json", output_store,
#                              settings=settings, arms=chosen_arms, calls=model_calls)
# pipeline.run(tasks, contracts_metadata)
```

`--all-programs` export nguyên task records với10PUT gốc/task (gồm base rejects),
`target_programs=10`; task shortfall giữ chính sách skip của benchmark cũ. Đây là
option để nâng từ development1PUT/task lên kiểm tra nhiều implementations.

Subset chỉ chọn workload, **chưa lọc guidance của arm classical thành từng hướng**.
Trước khi đo boundary-only/equivalence-only/C1-only/DU-only, cần thêm4arm hoặc
concept providers tương ứng; giữ generator/oracle/budget giống nhau. Không được
gọi kết quả classical mixed hoặc V11 mixed trên subset là hiệu quả riêng của nhóm.

## Lộ trình phát triển rồi ghép lại

- Bắt đầu6PUT/group; mỗi lần sửa chỉ chạy lại nhóm tương ứng và plain cùng budget.
- Lưu obligation→input→coverage evidence→reference disagreement, kể cả invalid,
  unsupported, infeasible/unknown và không có concept; không chỉ giữ test thành công.
- Khi generator của một nhóm hoạt động ổn, chuyển development tối đa12 rồi check4;
  nếu sửa theo check thì check trở thành dev, không còn validation độc lập.
- Sau khi khóa4provider, hợp concept dưới **một tổng input/call budget**; deduplicate
  inputs rồi chấm union. So combined với plain và từng provider; không cộng bốn raw
  detection counts vì cùng PUT có thể bị bắt nhiều lần.
- Lần kiểm tra kết hợp mới dùng bộ rộng/full hoặc bộ TrickCatcher đã qualify.
  Bộ smoke/development chỉ dùng debug và đo tiến bộ tại chỗ, không claim efficacy
  trên164task hoặc held-out generalization.

## Hướng đã có trong repo

V7/v11 đã có BOUND/SHAPE/NUM/STMT/DU; v11 chủ yếu thêm fairness và hybrid. Arm
classical đã gộp boundary/equivalence/CFG/DU trên cohort mới: matched với plain
không chứng minh gain (p≈0.748). Việc này không được gọi là phương pháp hoàn toàn
mới: thay đổi là tách development và đánh giá đúng từng criterion thay vì trộn
cả4rồi chỉ nhìn raw detection. Run concept-v11 hiện tại không bị sửa/dừng bởi audit.

## Kiểm tra

**9 engineering checks pass**, gồm đủ164task/1634PUT, mọi representative base-pass,
global check/development disjoint, exact saved code/id/base reuse, reject stale
inventory, reject overwrite và không gọi line coverage là dynamic DU coverage.
Review độc lập chỉ đọc không thấy blocker; lưu ý dùng task filtering/target1 qua
pipeline API đã ghi ở trên. Không có inference hoặc kết quả benchmark mới.
Source hashes105file của run đang chạy vẫn khớp sau khi tạo các bộ development.
