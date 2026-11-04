# Grounding AI Agents in Contracts: An Empirical Evaluation of Spec-Driven Test Generation

Michele Tufano et al.,Google,SpecOps2026.
arXiv2608.17177v2; DOI10.1145/3842652.3843195.
PDF user cung cấp: `../2608.17177v2.pdf`,11trang. Đọc main text,method,
evaluation và threats2026-11-04; đối chiếu official arXiv HTML.

## Khớp câu hỏi của user ở đâu

Đây là paper khớp trực tiếp nhất với ý: suy ra điều kiện kiểm thử, đối chiếu với
tests hiện có, ghi rõ điều kiện chưa được thỏa rồi sinh test nhắm vào nó.

Spec block cho mỗi code unit là tuple(description,preconditions,postconditions,
test suggestions). Từng pre/postcondition được đánh dấu Tested hoặc Untested.
Điều kiện Untested sinh một suggestion. Listing1,p.3 minh họa API add_customer:
invalid phone đã có test; empty name chưa có assertion kiểm chứng nên thêm test.

## Cơ chế

PhaseI(Sec3.1,p.3):

1. Agent đọc code,docstrings,comments,requirements,RFCs và repository context.
2. Infer preconditions,postconditions và behavioral boundaries; viết `.spec.md`.
3. Agent cross-reference với assertions/tests tìm được; đánh dấu Tested/Untested.
4. Đề xuất targeted test cho từng Untested condition.

Có optional human curation; experiment bỏ HITL và dùng suggestions tự động.
PhaseII cho cùng agent viết/build/run assertions theo spec. Đây là **LLM/agent
inference và assessment**, không phải một static analyzer hoặc solver tự chứng
minh điều kiện nào đã được test. Không programmatically enforce đủ method coverage.

Ví dụ `Tested` của postcondition liên quan một assertion thực sự kiểm behavior,
khác với chỉ có một input đi qua domain guard. Không được gộp input coverage,
path coverage và oracle/assertion adequacy thành cùng một boolean.

## Thiết kế đánh giá: điểm dễ bỏ sót

90historical Google production bugs,C++/Java/Python/Go; mỗi fix đổi một production
source file. Model Gemini3Flash, same harness/tools, k=5independent runs.

**Agent nhận code ĐÃ SỬA Cf và empty test target sau khi tests cũ bị loại.** Sau
khi sinh test, chạy trên Cf rồi reverse-patch về buggy Cb để đo fail-to-pass.
Agent không được xem bug description/fixdiff/commit message trong generation.

Do đó kết quả không trực tiếp chứng minh rằng:

- mining spec từ buggy PUT sẽ tránh chép lại bug;
- agent đánh dấu Tested/Untested đúng khi đã có base tests;
- concept gap có hiệu quả với một call inputs-only/task và oracle reference.

Framework mô tả khả năng dùng tests cũ; study chính là greenfield, nên gap assessment
đối với base tests nonempty không được isolate như một experiment riêng.

## Kết quả và giới hạn claim

- detect@1:41.1%vs36.9%,+4.2percentage points,p=.3075,không significant.
- detect@5:63.2%vs53.4%,+9.8pp,p=.0352(Table2,p.7).
- Unique bugs tại k5:57vs48,shared45,spec-only12,baseline-only3.
- Branch coverage48.9%vs46.4%,+2.5pp,p=.0034; line74.4%vs74.8%,không tăng.
- Total tokens336.7Mvs243.9M,+38%; tokens/unique bug tăng16.2%(Table4,p.9).
  Same model/harness không phải matched total token budget. Không thể quy tất cả
  gain riêng cho contract content mà bỏ qua extra reasoning/work/context.

ContractCoverage@k(p.6–8) là **bug-specific judge metric**: spec có nêu constraint
bị historical bug vi phạm không. Judge được xem bug description,commit message,
fixdiff để chấm; đây là evaluation-only. Metric này không phải tỷ lệ base tests
cover toàn bộ conditions, không phải formal completeness. ContractCoverage@1=
61.1%,@5=78.9%; association với bug detection không tự chứng minh causality.

Failure analysis tách141spec-generation failures khỏi110test-generation failures:
missingmethods/errorhandling/transforms/constants/ordering ở upstream; downstream
có inadequate inputs37,omittedscenarios36,weakassertions20,flawedlogic12,
invalidcode5. Đây là phần hữu ích cho việc đo riêng extraction và input generation.

## Artifact

PDF và official arXiv HTML đã đọc không cho một direct author implementation/
prompt release. Dataset là Google internal90bugs; chưa xác minh public artifact.
Không được nói có thể clone pipeline tác giả và chạy ngay trên HumanEval.

## Áp dụng có điều kiện cho repo

Có thể học dạng artifact gắn clause→pre/postcondition→evidence→suggestion. Với
benchmark hiện tại, spec HumanEval nên là authority, PUT chỉ để bind/reachability;
reference chỉ dùng sau input freeze. Không đưa canonical fixedcode vào mining để
copy protocol Google, vì đó sẽ đổi information access của benchmark hiện tại.

Không copy Tested/Untested judge thành ground truth. Nên tách có input thỏa guard,
có trace cover structure, và assertion đã kiểm consequence hay chưa; trạng thái
không đủ evidence phải là unknown. Chưa implement hoặc chạy paper này.
