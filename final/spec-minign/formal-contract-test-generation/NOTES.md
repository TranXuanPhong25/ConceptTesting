# Automatic test cases generation from formal contracts

Samuel Jiménez Gil,ManuelI.Capel,Gabriel Olea Olea.
Information and Software Technology172(2024)107467.
DOI10.1016/j.infsof.2024.107467.
PDF user cung cấp: `../1-s2.0-S0950584924000727-main.pdf`,13trang.
Đọc method,algorithms,examples,evaluation,limitations2026-11-04.

## Điểm phân biệt chính

Paper này **không mining contract từ natural language**. Đầu vào đã có formal
Spark/Ada specification: parameter types/ranges,global preconditions,
Contract_Cases guards/consequences và postconditions.

Nó giải quyết phần sau: từ contract cases→equivalence classes→constraint solver
→concrete test inputs. Đây là cầu nối tốt nhất trong ba paper từ **điều kiện đã
được biểu diễn chính xác** sang input, không phải bằng chứng rằng docstring mining
đã được giải quyết.

## Algorithm1 và ví dụ(Sec3,pp.3–6)

1. Parse specification thành AST,đọc globals/constants,parameters và types.
2. Tạo constraint set từ type ranges và global preconditions.
3. Với từng contract case,tạo local solver thêm guard riêng. Các case được giả
   định có tính disjoint/exhaustive theo formal specification.
4. Dùng SMT lấy tối đaNdistinct solutions/case; chặn nghiệm trước để lấy nghiệm mới.
5. Có thể thêm parameter-domain boundary values.
6. Gắn local/global postconditions vào test làm oracle. **Không solve postconditions
   để lấy expected values**; khi output không duy nhất,insert predicate/checker.

Implementation dùng Z3py trong bối cảnh GNAT/Spark. Ví dụ Sign có ba guards x<0,
x=0,x>0 nên có ba cells; binary search có sorted-array global precondition và
hai case exists-target/not-exists-target. Universal/existential predicates được
chuyển thành AND/OR trên bounded array trong ví dụ của paper.

Không được suy ra một guard bất kỳ tự nó là equivalence relation; điều cần cho
partition là các cells được định nghĩa rõ,rời nhau và phủ domain. Nếu guards do
LLM tự tạo thì các tính chất này chưa có bảo đảm từ Spark contract.

## Đánh giá(pp.7–11)

8small Spark/Ada subprograms:Sign,In Unit Square,Accept Offer,Compute Speed,
To_Green/To_Yellow/To_Red và Binary Search. Function bodies1–16LOC và đều đã
được GNATProve verify theo contracts trước khi sinh test.

CO thường đạt100%statement coverage; Binary Search91.3%vsrandom21.74%. Paper
giải thích phần chưa đạt của Binary Search là unspecified subpath trong một
contract case quá rộng: **cover contract case chưa chắc cover mọi code path**.

Random baseline chỉ dùng type ranges,không biết global preconditions hay contract
cases,và ghép input với **random expected output**. Nhiều random inputs không
qua precondition để tới functionbody. Vì thế passrate advantage không thể đọc
như bug-finding advantage của method trên PUT sai. Coverage advantage còn chứa
lợi thế valid-domain generation. Paper không đo real-bug detection trên cohort PUT.

Branch coverage không được dùng làm primary do runtime checks/hidden compiler
branches và các checks mâu thuẫn preconditions. Tác giả tự chỉ ra measurement
noise của gcov khi test chưa tới functionbody. Không lấy100%pass làm mục tiêu
benchmark mình: generated test đúng vẫn phải fail nếu PUT có bug.

## Artifact

Data availability p.13: `Data will be made available on request.` Không thấy
direct author implementation release trong PDF. Z3py là thư viện thực có thể
dùng; không có nghĩa parser/Spark contract translator của tác giả đã public.
Chưa triển khai hay tái hiện Algorithm1 trong repo.

## Bài học cho bốn hướng

- Hợp trực tiếp với boundary/equivalence khi đã có đúng guards/domain.
- Không thay CFG reachability hoặc dynamic def-use tracing.
- Boundary kiểu32bit trong Ada không tự trở thành boundary ngữ nghĩa của Python
  arbitrary-precision int; phải lấy giới hạn thực của spec/contract.
- Có thể dùng reference oracle hiện tại thay oracle contract khi chỉ muốn benchmark
  input selection; đó là adaptation riêng,chưa có experiment trong paper.
- Đối chiếu với base inputs để lấy missingcase là bước bổ sung của mình,paper
  chủ yếu generate theo contract chứ không có baseline-gap miner.
