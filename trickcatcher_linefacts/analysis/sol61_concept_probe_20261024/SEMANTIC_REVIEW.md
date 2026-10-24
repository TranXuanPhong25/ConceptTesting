# Independent clean-context saved-data review

Independent saved-data audit: **generic 6/6, concept 6/6 semantic success; concept-only wins 0, generic-only wins 0; false alarms 0/0. Advantage NOT SHOWN**, theo PREREG. Không có semantic defect hoặc input-prediction error trong 12 final replies.

| Task | Spec → implementation, đúng trong cả hai arms | H decision G/C | Judgment G/C | Evidence đúng |
|---|---|---|---|---|
| T1/E2 | Count `>= limit` → code `> limit`, bỏ equality occurrences | keep/keep | mismatch/mismatch | O5: 0 thay vì 3; O3/O4 và source |
| T2/E3 | `required ⊆ container`, extras allowed → set equality | revise/revise | mismatch/mismatch | O3/O7 đúng direction, extras bị reject |
| T3/E4 | Minimum positive; empty eligible list trả None → unguarded `min` raises ValueError | keep/keep | mismatch/mismatch | O1/O2/O5–O7 exceptions; O3/O4 positive agreement |
| T4/E6 | Sum mỗi positive occurrence, gồm 1 → distinct values `>1` | revise/revise | mismatch/mismatch | O1 isolates excluded 1; O4 isolates dedup; G thêm O6, C thêm O3 |
| T5/E7 | Sorted copy giữ duplicates → unused set, return `sorted(xs)` | withdraw/withdraw | no_mismatch/no_mismatch | O2–O9 giữ duplicates; source establishes unused temporary |
| T6/E8 | “Suitable” undefined → unconditional first element/None | keep/keep | unknown/unknown | O1/O4/O9 + source; cả hai phân biệt hypothetical eligibility với normative requirement |

Tất cả cited IDs tồn tại và support đúng nội dung; không trộn exception với None, không suy requirement từ observed output. E8 abstention là success theo prereg; empty-list base test được cả hai nhận biết.

Input audit bằng source/manual, không execute PUT:

| Task | Generic proposals | Concept proposals | Đánh giá |
|---|---|---|---|
| T1 | `([2],2)`, `([1,2,2,3],2)` | `([7],7)`, `([6,7,7,8],7)` | Đúng predictions 1/0 và 3/1 |
| T2 | `([1,2],[1])`, `([1],[])` | Giống generic | Đúng inclusion True/equality False |
| T3 | `([],)`, `([-2,0],)` | `([],)`, `([-4,0,-2],)` | Đúng None/ValueError |
| T4 | `([1],)`, `([2,2],)` | `([1,3],)`, `([3,3],)` | Đúng isolated faults; G 1/0 và 4/2, C 4/3 và 6/3 |
| T5 | `([0,-1,0],)` | `([2,-1,2,-1,0],)` | Đúng sorted multiset/set predictions |
| T6 | `([-1,2],)` | `([-1,2],)`, `([0,3],)` | Đúng hypothetical discrimination; không resolve missing normative definition |

Literal-tuple novelty đối chiếu đủ eight-case v43 pool: generic **6/10 per-case novel, 5/10 whole-pool novel**; concept **9/11 per-case novel, 8/11 whole-pool novel**. Khác biệt là T6 `([-1,2],)` mới trong E8 nhưng có sẵn E4. T4 concept dùng novel tuples nhưng chỉ restate hai fault đã observed: **không phải concept-only semantic win hay new discovered bug**.

Integrity: `sha256sum` của đủ 12 raw files và `prelaunch.json` khớp `generation_frozen.json`; đủ 12 packet hashes khớp manifest. Raw records đều observed `gpt-6.1-sol`, effort `low`; mỗi agent chỉ có **một tool call đọc đúng assigned packet bằng `cat`**, không dynamic execution/test/feedback. Hai inference responses/episode là delivery + final, không phải 12 single-response API calls.

Giới hạn: generic là **reasoning-checklist control**, không unassisted baseline. Hai arms cùng full saved evidence và supplied fallible H; positive/negative/ambiguous cases đều đã có đủ evidence. Đây là **ceiling trên six seen authored fixtures**, không chứng minh concepts vô ích tổng quát hay model effect so với historical Qwen. Không sửa file, gọi endpoint hay chạy PUT.
