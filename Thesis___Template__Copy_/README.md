# Khóa luận ConceptTesting

[Mở bản PDF](thesis.pdf) · [Sửa bản LaTeX](thesis.tex)

Sau Mở đầu, Chương 1 trình bày HumanEval, MBPP, kiểm thử chức năng và kiểm thử luồng điều khiển. Chương 2 giải thích cách mỗi nhánh dùng khái niệm kiểm thử và dữ liệu của task để hướng dẫn mô hình chọn input. Chương 3 trình bày cách cài đặt hệ thống, các ca demo, kết quả trên hai benchmark và phép chấm lại trên mã GPT-6 Luna, Flint, GPT-4o. Phụ lục trích các prompt sinh đầu vào kiểm thử.

Pipeline đầy đủ gồm EP/BVA, DT và ControlFlow. EP và BVA dùng chung một nhánh. Naive LLM đứng riêng làm baseline. Danh mục tài liệu tham khảo chỉ gồm công bố và tài liệu chính thức bên ngoài.

Chương 2 mô tả cách EP/BVA và DT dùng phản hồi về độ phủ để sinh input ở lượt hai, cùng cách ControlFlow dùng CFG để chọn đích. Chương 3 báo kết quả HumanEval chính với Qwen, gộp EP/BVA và DT hai lượt của VF3 Hybrid với ControlFlow theo nghĩa vụ. Cấu hình EP/BVA, DT một lượt và ControlFlow gốc được dùng trong phần ablation.

Phần chuẩn bị dữ liệu trình bày ý tưởng sinh PUT, lọc trùng AST, chạy base test và lưu tập PUT theo task. Sơ đồ pipeline bắt đầu từ ngữ cảnh và tập PUT đã chuẩn bị. Phần này cũng giải thích prompt theo lô khác với cách lấy completion độc lập của HumanEval chuẩn, cùng lý do chọn tập MBPP+ 164 task và giới hạn về phân bố bài.

Phần coverage so base test với từng arm trên cùng PUT. Các bảng ghi số PUT đạt 100%, trên 95%, p10/p25/p90 và số PUT tăng phủ cho C1 và C2. PUT không có nhánh được báo ngoài mẫu số C2.

## Sơ đồ

Hình 2.1 dùng ảnh sinh viên cung cấp. Các sơ đồ PlantUML dùng tông xám theo [thesis-style.iuml](diagrams/thesis-style.iuml).

| Sơ đồ | Bản để đọc | Nguồn chỉnh sửa |
|---|---|---|
| Đồ thị luồng điều khiển (CFG) | [PDF](diagrams/cfg.pdf) | [PlantUML](diagrams/cfg.puml) |
| Toàn bộ pipeline | [Ảnh Hình 2.1](diagrams/hinh2_1-danh-muc-concept.png) | [Bản PlantUML tương ứng](diagrams/pipeline.puml) |
| Ngữ cảnh chung EP/BVA và DT | [PDF](diagrams/ep-bva.pdf) | [PlantUML](diagrams/ep-bva.puml) |
| Luồng sinh hai lượt của EP/BVA và DT | [PDF](diagrams/ep-bva-dt-flow.pdf) | [PlantUML](diagrams/ep-bva-dt-flow.puml) |
| Ngữ cảnh ControlFlow | [PDF](diagrams/control-flow-context.pdf) | [PlantUML](diagrams/control-flow-context.puml) |
| Vòng phản hồi ControlFlow | [PDF](diagrams/control-flow.pdf) | [PlantUML](diagrams/control-flow.puml) |
| Nghĩa vụ theo đặc tả và đích C1/C2 | [PDF](diagrams/obligation.pdf) | [PlantUML](diagrams/obligation.puml) |
| Oracle và chấm PUT | [PDF](diagrams/evaluation.pdf) | [PlantUML](diagrams/evaluation.puml) |

Trong các sơ đồ ngữ cảnh, mỗi dòng `$block` ghi nhãn và số token. Số token quyết định chiều cao khối. Quy tắc căn chiều rộng, chiều cao và màu nằm trong [mẫu dùng chung](diagrams/context-blocks.iuml).

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

Thông tin bìa nằm trong `metadata.tex`. Phần cam đoan và chữ ký dành cho sinh viên hoàn thiện trước khi nộp.

Lời cam đoan ghi phạm vi Codex hỗ trợ chuẩn bị báo cáo. Dùng bản PDF cuối để lấy báo cáo trùng lặp từ DoiT hoặc công cụ do khoa chỉ định.
