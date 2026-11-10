# Soft examples cho testing arms v2

Hai ví dụ lấy từ production repositories, được viết lại ngắn để gợi ý cách
phân tích; không lấy bài tập từ EvalPlus, ULT hoặc benchmark làm few-shot.
Không dùng expected outputs của model cho benchmark: corrected reference vẫn
là oracle sau input freeze.

- **EP+BVA — dependency version filtering:**
  [packaging SpecifierSet.filter](https://github.com/pypa/packaging/blob/713d0d78924ab2686c513dde058ce6aafc63e766/src/packaging/specifiers.py#L1418).
  Với policy mặc định và specifier final-only, prerelease fallback phụ thuộc vào
  tập candidates **sau khi lọc specifier**. Final không match không được vô tình
  chặn prerelease match. Một thay đổi candidate/policy có thể đổi behavior;
  không chia classes chỉ theo từng version number. Đây là behavior của commit
  đã pin (packaging26.x), không áp dụng ngầm cho mọi version packaging cũ.
- **DT — HTTP preconditions:**
  [Werkzeug Response.apply_conditions](https://github.com/pallets/werkzeug/blob/5f11cd39b40ac03296ab7db446bfb0a737d77590/src/werkzeug/wrappers/response.py#L883).
  Method và validator predicates tương tác; ETag comparison mạnh/yếu và thứ tự
  ưu tiên header quyết định 304/412/tiếp tục. Chỉ dùng preconditions, không kéo
  Range/If-Range/multipart vào example để tránh độ khó không cần thiết.

Mỗi đoạn prompt113words, dùng “possible”, “might”, “test ideas”; không đưa toàn
bộ table, IDs hay JSON để model sao chép. Có vài discriminating pairs để minh
họa dependency/fault rationale, không yêu cầu mọi task bắt chước domain này.
Technique guidance8lines đứng riêng với example và output-schema note.

[provenance.json](provenance.json) ghi commit/path/SHA256/license URLs. Các nguồn
đã được đối chiếu byte với raw file ở pinned commit; original sources tải ở/tmp,
không sửa và không vendor/reimplement vào pipeline. [verification.json](verification.json)
ghi10engineering checks dùng đúng libraries đã pin để kiểm các quan hệ ví dụ;
0LLM calls, không phải một experiment về hiệu quả test generation.

Đã scan109files local benchmark/data theo domain keywords và không tìm thấy
hit; gồm HumanEval/EvalPlus data hiện có và các data roots đã liệt kê trong
provenance. Đây không phải bằng chứng về mọi bản benchmark bên ngoài hoặc
model pretraining. Nguồn example là repo production độc lập.

Độ khó được chọn vừa phải: phải xử lý quan hệ/tổ hợp/precedence, không chỉ nhớ
range. **Chưa đo GPT-5.6 Luna đạt hay không đạt90%**; không ghi “Luna failed” khi
chưa có probe thực tế. Scope người dùng đã chốt là24Qwen smoke generation calls,
không tự thêm Luna inference ngoài budget đó.
