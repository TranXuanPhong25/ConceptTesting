# Thuật ngữ & phương pháp — giải thích mọi thứ

Bảng tra cứu cho toàn bộ thuật ngữ, tên phương pháp, dataset của dự án. Bài toán cốt lõi: **LLM sinh
*input* (`build()→bytes`) kích hoạt lỗ hổng bộ nhớ thật**, chấm bằng oracle vi-phân trên benchmark CVE thật.

## 1. Dataset & benchmark

| tên | là gì |
|---|---|
| **CVE** | mã định danh 1 lỗ hổng bảo mật đã công bố (vd `CVE-2018-13785`). "Bug thật" = từng có thật trong phần mềm thật. |
| **Magma** | benchmark fuzzing của EPFL. Lấy **138 bug CVE thật** từ 9 thư viện C (libpng, libtiff, sqlite3...), cấy lại vào bản mới nhất + chèn **canary**. Dataset chính (100 bug / 7 lib). *(Không liên quan "Magma" multi-agent của Microsoft — trùng tên.)* |
| **forward-porting** | kỹ thuật Magma: lấy bug cũ (đã vá) → cấy ngược vào code bản mới, kèm cả **bản có bug** lẫn **bản đã vá**. |
| **Juliet** | bộ test tổng hợp của NIST — nghìn hàm C mẫu, mỗi hàm 1 lỗi cố ý (`bad()`) + 1 bản đúng (`goodB2G()`). Dùng làm ví dụ few-shot + bản thử ban đầu. "Tổng hợp" = code nhân tạo, không phải phần mềm thật. |
| **ConceptCoder** | mô hình + dataset tôi tái lập: gán mỗi dòng code **8 "concept"** (buffer allocation, bound check...) rồi phân loại có lỗi/không. Dùng lấy concept "học-được" thay tree-sitter. |

## 2. Cách chấm điểm (oracle & metric)

| tên | là gì |
|---|---|
| **harness / program** | chương trình nhỏ nhận file input rồi gọi thư viện (vd `libpng_read_fuzzer` đọc 1 file PNG). LLM sinh file cho cái này ăn. |
| **build vuln / build fixed** | 2 bản biên dịch cùng thư viện: một **có bug**, một **đã vá**. |
| **canary** | dòng Magma chèn đúng chỗ bug: chạy qua → ghi "reached"; thỏa điều kiện lỗi → ghi "triggered". Đây là **ground-truth**. |
| **oracle vi-phân** (differential) | cách chấm: chạy input trên **cả 2 bản**. Đúng khi trigger trên bản-có-bug **và** không hỏng bản-đã-vá → input nhắm *đúng* bug, không phá bừa. |
| **rendered** | LLM có sinh được bytes hợp lệ không (chạy `build()` ra file). |
| **REACHED** | input có **chạm** hàm lỗi không (canary reached). Tín hiệu mềm. |
| **TRIGGER** | input có **thỏa điều kiện lỗi** không (canary triggered) + sạch trên bản vá. Thước đo thật. |
| **ground-truth** | "đáp án chuẩn hệ thống biết chắc" — ở đây là canary, không phải phán đoán. |

## 3. Các nhãn trong mỗi bug (item)

| tên | là gì | có phải "đáp án"? |
|---|---|---|
| **focal** | tên hàm chứa bug (vd `png_handle_PLTE`) | lấy từ patch — leak nhẹ, đã khai báo |
| **fault_cond** | điều kiện toán học để bug nổ (vd `num > max_palette_length`) | **lấy thẳng từ patch = mách đáp án** |
| **fix_hint** | dòng code bản vá thêm để chặn bug | leak |
| **family** | loại bug: `oob` (đọc/ghi ngoài biên), `null_deref`, `uaf` (dùng sau khi giải phóng), `double_free`, `int_overflow` | suy từ patch |

## 4. Tên các phương pháp (cond)

| tên | dịch nôm na |
|---|---|
| **blind** | "mù" — chỉ bảo "có lỗ hổng, tạo input đi", không cho gì thêm |
| **concept** (leak) | cho thẳng **điều kiện lỗi** từ patch = mách đáp án (chỉ dùng làm trần trên) |
| **concept_static** | cho **source hàm + phân tích tĩnh** (buffer/sink/guard) nhưng **không** cho điều kiện lỗi — model tự suy. "Concept thật" |
| **concept_shuffle** (placebo) | như trên nhưng **nhãn cố tình sai** (xáo trộn). Kiểm: nếu nhãn đúng không hơn nhãn sai → nội dung nhãn vô nghĩa |
| **fewshot_authored / juliet** | thêm **ví dụ mẫu** (tự viết / lấy từ Juliet) để "dạy" model cách suy luận |
| **concept_reach** (C2) | thêm 1 input đã biết chạm hàm lỗi + gợi ý định dạng |
| **byte_sweep** (C3) | dò từng byte, thử vài giá trị (trước gọi nhầm "concolic" — đã đổi tên vì nói quá) |
| **learned** | dùng concept **do ConceptCoder tự học** thay tree-sitter |
| **hybrid_symcc** | concept_static + **gợi ý từ SymCC** (input thật + byte quan trọng) |

## 5. Kỹ thuật nền

| tên | là gì |
|---|---|
| **tree-sitter** | thư viện phân tích cú pháp code. Tự động rút "buffer nào, sink nào, guard nào" từ source — không cần patch. |
| **feedback loop / CEGIS** | vòng lặp: LLM sinh → oracle chấm → **báo lại trạng thái** ("đã chạm nhưng chưa nổ") → LLM sửa → lặp ≤3 lần. Đòn bẩy mạnh nhất. |
| **fuzzing** | ném hàng triệu input ngẫu nhiên/đột biến vào chương trình để tìm bug. |
| **AFL** | fuzzer phổ biến — đột biến input để tạo seed đa dạng. |
| **symbolic execution / concolic** | coi byte input là **biến toán học**, thu "ràng buộc đường đi" rồi **giải phương trình** tìm input đi vào nhánh mong muốn. |
| **SymCC** | công cụ symbolic execution (biên dịch chương trình để nó tự thu ràng buộc khi chạy). |
| **Z3** | bộ giải phương trình logic (SMT solver) SymCC dùng để giải ràng buộc. |
| **SEED_SRC / GUIDE** | tham số SymCC: seed lấy từ đâu (corpus/LLM), có dùng canary dẫn đường không. |
| **bootstrap reaching** | tìm 1 input ban đầu đã chạm hàm lỗi để SymCC có chỗ bắt đầu (chỉ ~34/100 bug có). |
| **LoRA** | cách fine-tune mô hình rẻ (chỉ train vài % tham số) — dùng train ConceptCoder trên Kaggle. |

## 6. Khái niệm khoa học / thống kê

| tên | là gì |
|---|---|
| **teacher / student** | teacher = model mạnh (gpt-oss-120b) sinh test; student = model nhỏ được train. Kết luận "concept không giúp" chỉ đúng ở **teacher**. |
| **placebo control** | nhóm đối chứng "giả dược": cho thông tin **sai** để xem cái *thật* có thực sự hơn không. Không hơn → cái thật vô tác dụng. |
| **leakage (rò rỉ)** | vô tình đưa "đáp án" vào input → kết quả đẹp giả tạo. Vd `fault_cond` từ patch, feedback mách điều kiện lỗi. |
| **McNemar** | phép kiểm định thống kê so 2 phương pháp trên cùng tập bug (đếm bug A làm được mà B không, và ngược lại). |
| **confound (nhiễu)** | yếu tố ngoài ý muốn làm sai lệch kết luận. Vd **prompt tiếng Việt** — đã phát hiện & sửa sang tiếng Anh. |
| **ablation** | thí nghiệm gỡ bỏ/thay từng thành phần để xem cái nào thực sự đóng góp. |

## 7. Kết luận rút gọn (chi tiết ở `magma/RESULTS.md`)

- `blind` ≪ mọi cond → **thông tin bug-cụ-thể là thứ duy nhất quan trọng**.
- `placebo` ≥ `concept đúng`, few-shot ≈ placebo, learned = tree-sitter, hybrid = concept_static →
  **dạng/nguồn/chất của concept KHÔNG nhân-quả ở teacher**.
- SymCC thuần ≤ LLM (bỏ AFL → concolic bị trần bởi seed).
- Đòn bẩy thật = **source + feedback loop**. Mọi lớp thêm vào đều thừa ở teacher.
- ⚠️ Số hiện tại đo với prompt tiếng Việt (đã vá sang tiếng Anh `v3-english`) → cần chạy lại.
