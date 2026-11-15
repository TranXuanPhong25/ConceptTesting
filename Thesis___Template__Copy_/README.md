# Bản thảo KLTN ConceptTester

Mở `thesis.pdf` để đọc; sửa LaTeX trực tiếp qua `thesis.tex`. Tiêu đề làm việc
và các dòng trống thông tin cá nhân tập trung trong `metadata.tex`.

## Nội dung

- Chương 1: Đặt vấn đề, bài toán, mục tiêu, phạm vi.
- Chương 2: Khái niệm, kỹ thuật kiểm thử, LLM, công nghệ và nghiên cứu liên quan.
- Chương 3: Yêu cầu, kiến trúc, interfaces, từng arm, freeze/reference/scorer,
  mô hình dữ liệu, cache/replay/resume; năm sơ đồ có giải thích trong nội dung.
- Chương 4: Môi trường thực tế trong manifest, đóng góp ở cấp đề tài và phần
  reuse, thiết lập, test cases, ảnh Prefect thật, hai ví dụ từ saved artifacts,
  detection/union/coverage và giới hạn kết luận.
- Kết luận, tóm tắt Việt/Anh, từ viết tắt và phụ lục tái lập.

Bản HTML xem riêng: [Luồng pipeline](diagrams/pipeline.html). Source HTML
được render bằng skill `visual-explainer`; sơ đồ trong PDF là TikZ để giữ chữ
và đường nét khi in. HTML mô tả cùng snapshot; các links tới source cần mở
trong cây repository. Log engineering tests mới ở `verification/engineering-tests.txt`.

## Phạm vi phiên bản

Chương phương pháp mô tả snapshot đã tạo ra run Gemini ngày 12/11/2026,
protocol Control-flow `coverage-concept-discovery-v1`, dùng Hypothesis.
Working tree hiện có thay đổi symbolic không thuộc kết quả được báo cáo.
Runner Gemini dùng freeze theo task và producer/consumer; generic pipeline có
thể freeze toàn bộ task batch. Không trộn hai barrier hoặc nói console Prefect
đã có backend Vertex selector. Record của external runner có thể không có
Prefect task graph hoặc logs trực tiếp.

## Nguồn và bằng chứng

Danh mục tham khảo chỉ có 25 nguồn ngoài: slides môn học gốc, paper và tài liệu
chính thức. Không dùng docs/report/README AI viết trong repo làm nguồn học thuật.
Source code dùng để kiểm tra mô tả implementation; JSON/checkpoints dùng để
đối chiếu số liệu riêng của đề tài. Những dữ liệu này được nêu bằng run ID và
vị trí lưu trong chương thực nghiệm/phụ lục, không thành entry BibTeX.

Đã cộng lại các kết quả theo 164 task, kiểm danh tính PUT trong 15 unions và
cộng coverage từ 1.454 records theo PUT. Đã kiểm witness task124/PUT7: input
`02-29-2001`, expected True theo spec của task; actual False ở cả hai lượt.
Đặc tả cho tháng 2 tới29 không xét năm nhuận. Đây là ví dụ đúng protocol,
không tự áp yêu cầu lịch thực tế lên bài toán.

Run nguồn:

- `final/out/gemini_full4_20261112_074012/`.
- `final/out/gemini_full4_coverage_20261112/`.
- [Prefect Gemini](http://127.0.0.1:4200/runs/flow-run/4e3a4d78-1a06-4b07-93cf-7054a0ec1a6c).
- [Prefect coverage](http://127.0.0.1:4200/runs/flow-run/0b1828c7-a222-4a07-a431-2d712a3149c5).

## Kiểm tra và biên tập

Đã áp dụng `no-ai-slop` và rà theo `eval.md`, giữ các tên kỹ thuật như Robust
BVA. Đã kiểm nguồn gốc citations, chữ tiếng Việt, tham chiếu hình/bảng, math,
caption placement và ảnh/sơ đồ. HTML renderer kiểm không overlap/overflow;
PDF được kiểm log và xem các trang sơ đồ/demo.

Engineering checks mới: **69 passed in15.87s** từ năm test modules ghi trong
phụ lục. Tests dùng fixtures/local sandbox; không có model call hoặc benchmark
mới. Đây không phải kết quả toàn bộ codebase và không phải efficacy benchmark.
Không dùng lại con số501pass từng được dẫn từ report nội bộ.

Bản PDF cuối có **51 trang, 6 hình, 5 bảng và 25 tài liệu tham khảo**. Log cuối
không có undefined citation/ref, missing glyph hoặc overfull box. Đã đối chiếu
221 source files với snapshot hashes, cả15unions và các records coverage. Các
kết quả kiểm tra được lưu trong `verification/checks.json`; build log nằm ở
`verification/latex-build.log`. Còn các cảnh báo underfull/package và ICC profile
của ảnh logo mẫu; ảnh, caption và dấu tiếng Việt đã được xem trong PDF.

Bộ LaTeX hỗ trợ pdfLaTeX với `vietnam` và XeTeX/Tectonic với `fontspec` + TeX
Gyre Termes. Chỉ dùng một bibliography style `unsrt`. Có thể biên dịch bằng:

```bash
cd Thesis___Template__Copy_
pdflatex -interaction=nonstopmode -halt-on-error thesis.tex
bibtex thesis
pdflatex -interaction=nonstopmode -halt-on-error thesis.tex
pdflatex -interaction=nonstopmode -halt-on-error thesis.tex
```

Phiên kiểm tra tài liệu dùng Tectonic0.17.0; không chạy inference hoặc benchmark.
Chữ ký/cam đoan cá nhân, tên người và phân công cá nhân được để trống để người
viết xác nhận trước khi nộp; không suy từ tên tài khoản máy. Tiêu đề hiện tại là
tên làm việc. Các file mẫu cũ `chapters/introduction.tex`, `method.tex`,
`evaluation.tex`, `c5/` không thuộc include tree đang dùng.
