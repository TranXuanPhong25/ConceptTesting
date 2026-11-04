# Towards the automated identification of data constraints in software documents

Ying Zhou, Miao Miao, Vlad Birsan, Oscar Chaparro, Shiyi Wei, Andrian Marcus.
Requirements Engineering31:22(2026). DOI:10.1007/s00766-026-00472-x.
PDF user cung cấp: `../s00766-026-00472-x.pdf`,22trang.
Đọc2026-11-04: main text, method, tables, evaluation và limitations; Table5 p.7
được kiểm tra bằng ảnh render vì pdftotext không lấy được nội dung bảng.

## Paper thực sự làm gì

Đầu vào là tài liệu tự nhiên: requirements, manuals, tutorials. Đầu ra là fragment
được dự đoán có chứa data constraint, kèm operands và constraint type. Paper không
nhận PUT+base tests để suy ra điều kiện chưa cover; không tạo executable predicate,
không giải input bằng SMT, không đánh giá bug detection từ tests được sinh ra.

Các constraint có data element, một/một tập value và quan hệ giữa chúng. Bốn loại:

| Loại | Ví dụ hình thức | Dùng được cho mình ở đâu |
|---|---|---|
| value-comparison | x so với y hoặc constant | Boundary, relational constraints |
| binary-value | true/false, null/non-null, on/off | Boolean/state partitions |
| categorical-value | x thuộc finite value set | Equivalence classes theo enum |
| concrete-value | x được gán một giá trị cụ thể | Constants/defaults, cần xác định đúng vai trò |

Chúng không tương đương bốn phương pháp kiểm thử của mình. Ví dụ concrete-value
có thể là default configuration, không phải điều kiện mọi input bắt buộc phải thỏa.

## Pipeline của tác giả

1. Chuẩn hóa tài liệu, tách câu, lọc phần không thuộc natural-language prose.
2. S2F dùng spaCy3.4.3 Matcher và token/dependency rules tìm9discourse patterns.
3. Trích operands từ các matched tokens, gán type trực tiếp hoặc theo rule.
4. Encode sentence/fragment/operands bằng TF-IDF hoặc frozen BERT, cộng pattern/type.
5. Classifier phân biệt constraint và non-constraint. Có so sánh LR, LSVM, NB, DT
   và fine-tuned BERT, cùng các cách xử lý class imbalance.

Patterns ở Table3 p.6: NP_BE_BINARY_VALUE, NP_BE_VALUE, NP_CD_TO_CD,
NUM_NP, NP_COMP_NP, NP_IF_BINARY_VALUE, NP_IN_VALUESET, NP_OF_NP, NP_EXIST.
Table5 p.7 mô tả kỹ ba pattern phổ biến nhất. Ví dụ `port number between0and65535`
được nhận diện với operands port number/0/65535; không có nghĩa tool đã tự bind
`port number` vào một parameter/field trong source hay chứng minh predicate đúng.

Đây là NLP trên văn bản, không phải static analysis của chương trình. Có thể chạy
không execute PUT, nhưng phải phân biệt với CFG/data-flow/symbolic tools.

## Evidence và cách đọc số liệu

- Corpus đầy đủ:1560constraint labels/15systems; nghiên cứu chính dùng546explicit
  constraints/9systems, đối với26641negative fragments (tỷ lệ positive≈2.01%).
- S2F sample:374sentences→1211matched fragments;1194được xác nhận đúng pattern
  và operands, accuracy98.60%(Table6,p.10). **Không phải98.6%constraint recall
  hoặc98.6%độ đúng semantic của một executable predicate.**
- Best classifier: frozen-BERT features+Logistic Regression, precision63.63%,
  recall61.40%,F1=62.34%. Fine-tuned BERT tốt nhất F1=61.31%,không vượt LR.
- Feature ablation cho thấy fragment/operands hữu ích; type không giúp, đôi khi
  làm giảm điểm. Các cách balancing không cải thiện kết quả.
- Đánh giá là repeated sentence-level70/30splits trong corpus, không phải chứng
  minh transfer sang HumanEval hay hoàn thành test generation.

## Giới hạn quan trọng với HumanEval

Paper loại791/1560constraint(50.7%) vì nằm nhiều câu hoặc cần pronoun resolution,
loại171GUIconstraints và52constraint của system ít dữ liệu. Nó còn ignore lists,
tables, code, regex/logs ở preprocessing; HumanEval lại chứa rất nhiều examples,
bullet constraints và code signature. Không nên copy nguyên preprocessing này.

NLP/parser và rules có thể sai; ví dụ chính paper nêu `years divisible by100`
không được nhận đúng noun phrase. Một bước cleaner còn bỏ từ như `only`; không
được dùng fragment đã cleaning như một formal source of truth mà mất original quote.

## Artifact và mức có thể dùng lại

Paper nói có S2F và replication package[2], chứa data/results; PDF ref[2] không
đưa một URL trực tiếp. Đã đọc official Springer article page: chưa xác minh được
một direct author-code/package link. Không được gọi đây là thư viện đã sẵn sàng
import trước khi có source/license/dependencies thực tế. spaCy/scikit-learn là
các thư viện nền, không thay thế implementation của9patterns hay trained model.

## Đánh giá cho ConceptTester

Hữu ích nhất như nguồn taxonomy và extractor candidates cho boundary/equivalence.
Chưa giải quyết spec→parameter binding, semantic entailment, role domain/guard/
postcondition, base-test coverage hoặc input construction. Những bước đó vẫn phải
làm riêng. Chưa triển khai/tái hiện paper; chưa chạy model hoặc đổi pipeline.
