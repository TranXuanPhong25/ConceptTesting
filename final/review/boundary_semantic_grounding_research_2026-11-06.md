# Cải thiện BVA semantic grounding sau protocol 5/6

Phạm vi: đọc lại `final/spec-minign`, đối chiếu failure traces và lịch sử repo,
tìm primary papers/source trên mạng. Không implement/reproduce paper, không sửa
pipeline, không gọi model task hoặc chạy benchmark. Một user-requested endpoint
ping nhận 1 completion token, tách khỏi nghiên cứu. Original PDFs giữ nguyên.

## Đề xuất chính

Ưu tiên kiểm tra **quantity, scope, decision polarity và context obligations**
trong BVA hiện có. Không coi thêm prose contract hoặc thêm một LLM judge là lời
giải cho các false mismatch vừa thấy. Đây là đề xuất engineering có phạm vi;
chưa có bằng chứng sẽ tăng bug detection.

Ba paper local giúp từng phần, nhưng không cung cấp một package giải trực tiếp
buggy PUT + HumanEval spec → đúng semantic boundary → input làm lộ bug.

| Nguồn | Học được | Chưa giải quyết |
|---|---|---|
| S2F, local | Constraint fragments, operands, constraint types | Executable binding, scope/polarity, proof của NL intent |
| Grounding AI Agents, local | Clause/pre/postcondition artifacts và targeted suggestions | Study dùng fixed source + empty tests; không chứng minh tránh copy bug từ PUT |
| Formal contracts→tests, local | Type/domain/guard constraints được solve đồng thời | Giả định formal guard đã đúng; không sửa upstream semantic interpretation |
| [Jdoctor](https://homes.cs.washington.edu/~mernst/pubs/comments-specs-issta2018.pdf) | Bind NL subject/predicate vào typed program elements | Java/Javadoc; heuristic matching, yếu hơn với complex postconditions |
| [nl2spec](https://arxiv.org/abs/2303.04864) | Sub-translation traceability giúp localized correction | Temporal logic/human interaction, không phải autonomous Python grounding |
| [VeriSpecGen](https://arxiv.org/html/2604.10392) | Requirement-level tests và localized repair của candidate spec | Cần output-labeling oracle trong generation/refinement; khác protocol hiện tại |
| [ISLa](https://github.com/rindPHI/isla) | Generate grammar-constrained strings thỏa semantic constraints | Không tạo đúng constraints từ HumanEval NL; không phải general Python solver |

## Vì sao VeriSpecGen sát vấn đề nhưng không thể áp dụng nguyên chuỗi

Paper §3.1–3.3 nối atomic requirement với validation cases và sửa clause liên quan.
Positive cases, negative-input cases và negative-output cases giúp kiểm cả việc
giữ behavior đúng lẫn loại behavior sai. Đây là phần mạnh hơn `source_quote`
có thật hoặc thêm lời giải thích của cùng model.

Nhưng §3.2 label output bằng reference implementation, được cung cấp hoặc LLM
sinh. Thêm vòng reference query trước input freeze sẽ chuyển pipeline thành
oracle-assisted generation. Nó phải có protocol/control riêng; không thể so với
plain/current BVA rồi gán gain riêng cho concept. LLM-generated surrogate oracle
cũng không tự trở thành ground truth. Lean proof đúng với một predicate không
chứng minh predicate dịch đúng câu tiếng Anh.

Do đó, có thể học evidence/traceability và positive/negative calibration; không
thay reference provider thành một tool mà generator tự hỏi trong run hiện tại.

## Những hướng tương tự repo đã thử

| Lịch sử | Kết quả/giới hạn | Ràng buộc cho đề xuất này |
|---|---|---|
| v7 SPEC classes | Đã có LARGE/DUP/NONASCII/SPACE và transforms | Thêm Unicode/space families không phải novelty mới |
| v10_spechint | Spec quote→predicate→base gap; 7 hints/5 tasks, không tăng good@3 | Chỉ thêm bước LLM viết condition là lặp ý cũ |
| v47 | LLM chọn menu không hơn random | Không kỳ vọng menu lớn hơn tự sửa ranking; cần random/menu control |
| v57/v66 | Constructor khó triển khai; CrossHair sau đó verify được 5/6 case ở CPU | Solver giúp realization, chưa chứng minh semantic relevance |
| v68 | Concept/plain/raw cùng 1/6; hypothesis/oracle còn sai | Không dùng solver witness như bằng chứng bug/spec correctness |
| v69 | Typed IR cải thiện interface nhưng chưa có sensitive witness trong diagnostic đó | Có IR/type checks không tự giải NL intent |
| v33 chain | Final chain 8 vs direct 21; gating/interface mất nhiều input | Không thêm hard gate theo một LLM semantic verdict chưa được kiểm chứng |
| BVA compact | 23 nhận ra byte/character nhưng context chỉ empty/ASCII; 72/157 vẫn sai | Rút prompt hữu ích cục bộ; binding/context vẫn phải kiểm riêng |

Đây là sửa các điểm quan sát được trong module hiện tại, không claim một phương
pháp mới hay lặp lại generic spec→predicate→solver như hướng chưa từng thử.

## Thiết kế cụ thể nên ưu tiên

### 1. Tách dữ liệu spec khỏi dữ liệu implementation

Spec clause giữ `source_quote`, role, operand, measure, scope/quantifier và relation.
Domain assertions phải giữ role domain; một behavior trả False không thành input
precondition. Source PUT chỉ tạo implementation facts, không được đổi nghĩa clause.

Nếu phải dùng LLM để dịch clause, semantic pass chỉ đọc public spec/signature/
contract. Freeze kết quả đó trước bước xem PUT. Đây là information separation,
không phải bằng chứng model đã dịch đúng; cần trạng thái supported/unknown.
Không thêm vòng đọc lại prose của model làm confirmation độc lập.
Information separation thật cần tách request hoặc dùng deterministic extraction;
không đạt được chỉ bằng yêu cầu “đọc spec trước” trong cùng prompt đã chứa PUT.
Nếu phát sinh model call bổ sung, chi phí đó phải có matched control riêng.

### 2. Quantity cần expression identity và scope

Một binding nên chỉ tới expression/AST location và các biến phụ thuộc, ví dụ:

```text
len(s)                    : string_length(code_points)
len(s.encode('utf-8'))     : encoded_length(bytes, utf-8)
ord(ch)                   : element_code_point
sum(q)                    : aggregate_sum(full_sequence)
weight@iteration_i        : aggregate_sum(prefix), nếu recurrence đã được xác nhận
```

Không chỉ dùng tên parameter hay một constant. Khi thấy `ord(char) < 256`,
không được gắn constant 256 vào `length(string)`. Với `.lower()` trước `ord`,
transform phải được giữ trong binding; raw code point và transformed code point
cũng không mặc định giống nhau.

Một catalog nhỏ của Python primitives có semantics rõ có thể dùng làm cơ sở;
AST/source analysis chỉ xác nhận các pattern được hỗ trợ. Không nhận diện được
loop recurrence thì ghi unknown, không tự tuyên bố weight là total sum.
Jdoctor cung cấp bài học typed binding, không phải implementation có thể import
trực tiếp để làm các việc này trong Python.

### 3. Tính decision polarity trước khi so operator

Với finite built-in numeric values trong phạm vi pipeline đang hỗ trợ:

```text
spec: accept iff x > 0
PUT : if x <= 0: return False
normalized PUT acceptance: not(x <= 0) ≡ x > 0
```

Đây là match tại domain edge, không phải operator mismatch. Phải đưa assumptions
vào receipt; không áp quy tắc này mù quáng cho NaN hoặc overloaded comparisons.

Task 72 còn cần kiểm quantity: accept `sum(q) <= w` và reject `weight > w` không
được so dấu trước khi biết `weight` ở iteration nào. Nếu đó là prefix sum, loại
khác biệt là scope/timing của aggregate, không phải dấu `>` sai với `<=`.

Chỉ gắn nhãn operator mismatch khi operand/measure/scope/polarity đã tương thích.
Đây là kiểm cơ chế của nhãn; không tự kết luận PUT đúng hay task không có bug.
Unknown không nên trở thành lý do loại toàn bộ input như các hard-gated chain cũ.

### 4. Chuyển context cần thiết thành obligation executable

Prompt hiện nói “hãy thử negative/non-ASCII” nhưng code không yêu cầu family đó
phải xuất hiện. Context property được khai báo thì validator làm đúng; model có
thể không khai báo property quan trọng và chỉ đưa context ordinary.

Obligation nên gồm target, joint domain constraints, context family và predicate
để kiểm input sau construction. Không chỉ kiểm đã đạt sum/length.

Ví dụ mechanism ở 72, sau khi spec binding và prefix recurrence đã được xác nhận:

```text
palindrome(q)
and sum(q) <= w
and exists k, 1 <= k < len(q): sum(q[:k]) > w
```

Đây mới là condition phân biệt total-check với early prefix-check. Chỉ thêm
`all_negative` không đảm bảo nó, dù có thể hỗ trợ search. Với bound nhỏ có thể
dùng lại bounded solver; mọi nghiệm vẫn phải qua exact Python checks và contract.
SMT trên số thực không tự chứng minh behavior của Python floats.

Với 23/16, cần code-point/encoding-aware context family; string-length target
không đủ để điều khiển code point. Không chỉ tạo `''`/`'x'`. Với 157, giữ dependency
giữa các cạnh khi perturb một cạnh; không thay a bằng 1 rồi hy vọng b,c từ một
Pythagorean example vẫn gần đúng relation.

Các ví dụ trên được thiết kế sau khi nhìn lỗi, chỉ minh họa obligation. Không
hardcode task ID hoặc đưa witness đã biết vào prompt rồi tính là generation gain.

### 5. Sửa các capability gap có thể kiểm độc lập

- Contract cho phép float thì không thu hẹp controlled neighborhood thành int
  chỉ vì base inputs có toàn int. Giữ provenance của declared/observed types.
- Domain boundary đã nhận diện phải prune các side bị contract loại trước khi
  dành context budget, thay vì sinh 14 invalid candidates như task 157.
- Mở characteristic code-point/encoding và arithmetic relation dưới scope rõ;
  unsupported phải được báo đúng, không ép dùng length thay thế.
- Các enum/interface constraints nên có structured producer/validation rõ;
  `origin: contract` không được âm thầm coi là semantic success.

## Thứ tự thực hiện và kiểm chứng được đề xuất

1. Audit offline các selection artifact hiện có bằng quantity/role/polarity/type
   checks; ghi rõ detected contradiction và unknown. Không cần gọi model để làm
   lại bước rút prompt. Đây là mechanism audit, chưa có efficacy score.
2. Sửa những phần deterministic và bổ sung capability còn thiếu trong module;
   test bằng cả match và genuine mismatch, không chỉ các task miss đã nhìn thấy.
3. Chỉ sau đó xét spec-only clause extraction và context obligations có kiểm tra.
   Nếu dùng reference-driven calibration như VeriSpecGen, phải tách setting đó
   khỏi benchmark inputs-only hiện tại.
4. Trước run mới cần review/PREREG và controls phù hợp: plain, structured binding
   không semantic selection, random từ cùng pool/family. Giữ input/call budgets
   để tách gain của pool rộng hơn với gain của chọn đúng semantic condition.

Các task đã trace chỉ dùng để kiểm cơ chế. Không mở rộng run để cứu kết quả và
không gọi việc bỏ được false mismatch là đã tăng detection rate.

## Cái còn chưa giải quyết

Không có nguồn nào đã đọc chứng minh một tool có thể tự động, đáng tin cậy, dịch
mọi HumanEval spec thành đúng formal condition mà không dùng oracle/human input.
Quote/type/AST checks giúp loại lỗi xác định được, không chứng minh toàn bộ NL
intent. Existing base examples cũng có thể không phân biệt hai semantics, như
ASCII examples ở 23. Cần giữ ambiguity/unknown và không thổi phồng mức guarantee.

Notes riêng từng paper nằm dưới `final/spec-minign/`. Nguồn đọc bổ sung:
[Beyond Type-checking](https://arxiv.org/html/2610.10604) cho phân biệt formal
validity với behavioral adequacy; đây là evaluation framework, không phải một
generator tự sửa các lỗi trên. Chưa chạy author code hoặc sửa source của tác giả.
