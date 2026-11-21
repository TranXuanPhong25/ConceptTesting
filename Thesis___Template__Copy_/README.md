# Khóa luận ConceptTester

[Mở bản PDF](thesis.pdf) · [Sửa bản LaTeX](thesis.tex)

Chương 2 trình bày kiểm thử chức năng, kiểm thử luồng điều khiển và kiểm thử luồng dữ liệu, với ví dụ CFG và DFG. Chương 3 ghi cách sinh bộ PUT, lọc trùng và chạy base test, rồi giải thích cách sinh input bổ sung và chạy xác nhận. Chương 4 trình bày kết quả theo ba câu hỏi nghiên cứu về điểm HumanEval, đối chiếu với Naive LLM và đóng góp từng nhánh. Bảng ablation dành cho phép đối sánh cùng ngân sách có các ô kết quả để trống. Phụ lục ghi hợp đồng phản hồi và ngân sách thực tế.

Pipeline đầy đủ gồm EP/BVA, DT và ControlFlow. EP và BVA dùng chung một lần sinh. Naive LLM đứng riêng làm baseline. Danh mục tài liệu tham khảo chỉ gồm công bố và tài liệu chính thức bên ngoài.

## Sơ đồ PlantUML

| Sơ đồ | Bản để đọc | Nguồn chỉnh sửa |
|---|---|---|
| CFG và DFG | [PDF](diagrams/cfg-dfg.pdf) | [PlantUML](diagrams/cfg-dfg.puml) |
| Toàn bộ pipeline | [PDF](diagrams/pipeline.pdf) | [PlantUML](diagrams/pipeline.puml) |
| EP và BVA | [PDF](diagrams/ep-bva.pdf) | [PlantUML](diagrams/ep-bva.puml) |
| DT | [PDF](diagrams/dt.pdf) | [PlantUML](diagrams/dt.puml) |
| Trích def–use | [PDF](diagrams/def-use.pdf) | [PlantUML](diagrams/def-use.puml) |
| Vòng phản hồi ControlFlow | [PDF](diagrams/control-flow.pdf) | [PlantUML](diagrams/control-flow.puml) |
| Oracle và chấm PUT | [PDF](diagrams/evaluation.pdf) | [PlantUML](diagrams/evaluation.puml) |

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

Bản HTML và các hình TikZ trong thư mục ghi lại lần chạy Gemini ngày 12/11. Thông tin bìa nằm trong `metadata.tex`. Phần cam đoan và chữ ký dành cho sinh viên hoàn thiện trước khi nộp.
