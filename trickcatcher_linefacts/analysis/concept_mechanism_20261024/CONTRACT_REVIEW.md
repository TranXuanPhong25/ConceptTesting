# Independent review: concept contract và v50 G1 decision

Ngày 2026-10-24. Read-only review của `CONCEPT_CONTRACT.md`, source `pipelines/v50_binding_revision/revision_protocol.py`, frozen evaluator rubric và toàn bộ v50 semantic review. Không execute/model/HTTP và không sửa pipeline/contract trong pass này.

**Verdict sau fix:** **PASS như documentation/evaluation contract**, chưa phải method có evidence hiệu quả. M1 bên dưới đã được root sửa và reviewer xác nhận bằng cách đọc lại contract. Không có cơ sở launch lại v50 hoặc mở rộng cohort từ kết quả này. v50 branch tại G1 nên **STOP** đối với current semantic-revision package.

**Overlap với implementations cũ**

| Contract element | Prior art trong repo | Assessment |
|---|---|---|
| Human-defined vocabulary + tool-computed test gap | v7/v11 | Phù hợp định nghĩa user đã chấp nhận; không phải contribution mới |
| Spec-grounded requirement, explicit applicability và executable obligation | v14–v26 | Formalization của cơ chế đã thử, chưa giải quyết semantic support/generation failures bằng việc ghi schema |
| Typed roles/bindings, normative status tách finite observations | v40/v43/v50 | Phù hợp lessons cũ; v50 đã cho full revision, item-level admission và explicit separation instruction nhưng vẫn fail |
| Raw/prose/typed comparisons và intervention | Earlier packet ablations + plan hiện tại | Cách đánh giá attribution; chưa phải bằng chứng representation hay new generator hoạt động |

Contract tự ghi rõ các overlaps và không claim novelty. Việc định nghĩa record hoàn chỉnh không có nghĩa các fields được tự động khai thác đúng hoặc một tool kiểm tra được entailment. `CONCEPT_CONTRACT.md` đã tránh phần lớn lỗi này bằng câu “documentation contract, not an enforced output schema”.

**M1 — explicit status-transition rule trước implementation**

Hiện contract nói finite agreement với PUT không thể justify một requirement; cần thêm chiều ngược lại, đúng với failure mới quan sát được:

> A PUT violation of a specification-justified requirement does not reject that requirement. Keep normative status and observed satisfaction separate. Revise or reject the task binding only when specification/applicability/binding evidence warrants it; record a valid-input relation violation as evidence about implementation behavior, not as a reason to erase the requirement.

Mục đích: E1 reject conservation dù spec nói rõ; E3/E5/E6 leave required relation unknown/rejected trong khi prose nói implementation sai. Nếu chỉ có một shared status enum hoặc transition dựa trên observed agreement, schema mới vẫn lặp lỗi. Đây là clarification cho semantics của contract, không phải proposed efficacy treatment.

Closure: root đã thêm “PUT disagreement cannot demote a spec-justified requirement: record a potential implementation violation separately.” Reviewer đọc lại và xác nhận M1 resolved. Không còn must-fix đối với vai trò documentation/evaluation contract này.

**Các lưu ý không chặn documentation**

- `gap.covered_count=0` trong sample chỉ hợp lệ nếu measurement thực sự diễn ra. Future machine schema nên dùng null khi `measurement_status=unknown`; unknown coverage không được mặc định thành zero hoặc “reachable gap”.
- `bindings` cho phép “justified expression”. Trước executable use phải công bố supported expression grammar/type/role scope và cách xử lý unsupported; không tự thay output/local variables thành input roles. Chưa cần thêm DSL vào documentation này.
- Public inputs là sanity checks, không chứng minh validator soundness. Contract đã ghi đúng. Finite relation observations cũng không chứng minh entailment hoặc universal correctness.
- Worked permutation example có explicit order-insensitive spec premise, paired permutation, distinguishing data và counterexamples; không oversell thành universal transformation hoặc demonstrated success. Chưa cần thêm authored fixtures để chứng minh nó.
- Prose có thể chứa same semantic concept; C≈S không tự phủ định content effect. Comparison với raw evidence và witness-only cần giữ thông tin/runtime resources như plan. Contract đã phân biệt đúng.

**G1 từ v50: failure có evidence nhưng chưa có changed mechanism đủ để run**

Failure được thấy trực tiếp là normative-status confusion, unsupported/unendorsed correct bindings, và false confidence trên ambiguous E8. Tuy nhiên source frozen đã có system warning rằng observed behavior không establish normative requirement; `revision_protocol.final_packet()` còn ghi:

> “A relation violated by code may still be the correct REQUIREMENT. Code agreement cannot define missing spec rules. Judge observed mismatch separately.”

Vì vậy thêm cùng lời nhắc vào contract/prompt, đổi labels, hoặc sửa interface lần nữa không phải changed hypothesis có signal. Admission repair đã có trong v50: readable siblings không bị xóa bởi bad item; no new semantic wins vẫn là zero. Một diagnostic mới cần evidence riêng rằng một thay đổi cụ thể xử lý được failure này và có falsifiable measurement; contract tự nó không cung cấp evidence đó.

Không yêu cầu loại concepts khỏi đề tài. Quyết định chỉ đóng current v50 package và chặn promotion/scale-up; independent v53 validity branch vẫn phải theo kết quả và gate riêng. Không suy zero utility của mọi concept từ 8 seen fixtures.

**E2 và scoring sensitivity**

Strict label-compatible complete success là 2/8 mỗi final arm (E4/E7); label-neutral relation+truthful-judgment coverage là 3/8 mỗi arm (thêm E2). Rubric có câu concrete label phải semantically compatible và đồng thời yêu cầu fully-labelled coverage report riêng, nên trình bày cả hai tránh che ambiguity. Root đã được cung cấp nguyên raw E2/canonical mapping để adjudicate. Không cách nào tạo tool-only win; E8 fail independent, nên NO-GO robust. Không cần model rerun hoặc sửa score lịch sử để giải quyết điểm này.

**Điều kiện đóng review**

M1 đã được xử lý bằng documentation edit vào contract. Contract được chấp nhận cho admissibility/measurement design, với trạng thái **chưa có demonstrated efficacy**. Không yêu cầu launch mới; tiếp tục P0/P1 audit và dùng gates của từng branch.
