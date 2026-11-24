# Khóa luận ConceptTesting

[Mở bản PDF](thesis.pdf) · [Sửa bản LaTeX](thesis.tex)

Sau Mở đầu, Chương 1 trình bày HumanEval, MBPP và các kỹ thuật kiểm thử chức năng, luồng điều khiển và luồng dữ liệu. Chương 2 giải thích cách mỗi nhánh dùng khái niệm kiểm thử và dữ liệu của task để hướng dẫn mô hình chọn input. Chương 3 trình bày phần hiện thực, đóng góp của sinh viên, các ca demo và kết quả trên hai benchmark. Mục thực nghiệm dùng lại test trên mã do mô hình khác sinh đang chờ số liệu. Phụ lục ghi cấu trúc phản hồi và ngân sách thực tế.

Pipeline đầy đủ gồm EP/BVA, DT và ControlFlow. EP và BVA dùng chung một lần sinh. Naive LLM đứng riêng làm baseline. Danh mục tài liệu tham khảo chỉ gồm công bố và tài liệu chính thức bên ngoài.

Phần chuẩn bị dữ liệu trình bày ý tưởng sinh PUT, lọc trùng AST, chạy base test và lưu cohort theo task. Sơ đồ pipeline bắt đầu từ context và cohort đã chuẩn bị. Phần này cũng giải thích prompt theo lô khác với cách lấy completion độc lập của HumanEval chuẩn, cùng lý do chọn tập MBPP+ 164 task và giới hạn về phân bố bài.

Phần coverage so base test với từng arm trên cùng PUT. Các bảng ghi số PUT đạt 100%, trên 95%, p99/p95/p90 và số PUT tăng phủ cho C1 và C2. PUT không có nhánh được báo ngoài mẫu số C2.

## Sơ đồ PlantUML

| Sơ đồ | Bản để đọc | Nguồn chỉnh sửa |
|---|---|---|
| CFG và DFG | [PDF](diagrams/cfg-dfg.pdf) | [PlantUML](diagrams/cfg-dfg.puml) |
| Toàn bộ pipeline | [PDF](diagrams/pipeline.pdf) | [PlantUML](diagrams/pipeline.puml) |
| Context EP/BVA | [PDF](diagrams/ep-bva.pdf) | [PlantUML](diagrams/ep-bva.puml) |
| Context DT | [PDF](diagrams/dt.pdf) | [PlantUML](diagrams/dt.puml) |
| Trích def–use | [PDF](diagrams/def-use.pdf) | [PlantUML](diagrams/def-use.puml) |
| Context ControlFlow | [PDF](diagrams/control-flow-context.pdf) | [PlantUML](diagrams/control-flow-context.puml) |
| Vòng phản hồi ControlFlow | [PDF](diagrams/control-flow.pdf) | [PlantUML](diagrams/control-flow.puml) |
| Oracle và chấm PUT | [PDF](diagrams/evaluation.pdf) | [PlantUML](diagrams/evaluation.puml) |

Trong ba sơ đồ context, mỗi dòng `$block` ghi nhãn và số token. Số token quyết định chiều cao khối. Quy tắc căn chiều rộng, chiều cao và màu nằm trong [mẫu dùng chung](diagrams/context-blocks.iuml).

## Biên dịch

Từ thư mục này, chạy `tectonic thesis.tex` để tạo PDF. Các hình vector đã có sẵn. Khi sửa sơ đồ, có thể tạo lại chúng bằng PlantUML và librsvg.

```bash
diagram_build=$(mktemp -d)
plantuml -charset UTF-8 -failfast2 -tsvg -o "$diagram_build" diagrams/*.puml
for svg in "$diagram_build"/*.svg; do
    name=$(basename "$svg" .svg)
    rsvg-convert --format=pdf1.5 "$svg" -o "diagrams/$name.pdf"
done
tectonic thesis.tex
```

Luận văn dùng các hình PlantUML ở bảng trên. Thông tin bìa nằm trong `metadata.tex`. Phần cam đoan và chữ ký dành cho sinh viên hoàn thiện trước khi nộp.

Mục Tuyên bố về sự hỗ trợ của AI ghi các công việc soạn thảo có Codex tham gia và vai trò của mô hình trong thực nghiệm. Dùng bản PDF cuối để lấy báo cáo trùng lặp từ DoiT hoặc công cụ do khoa chỉ định.
