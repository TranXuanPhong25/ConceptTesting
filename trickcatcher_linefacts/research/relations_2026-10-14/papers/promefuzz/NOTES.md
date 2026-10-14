# PromeFuzz

[Full text](https://pvz122.github.io/pdf/25-promefuzz.pdf), CCS 2025. Kiểm method §3, evaluation/ablation §5.3; PDF 21 trang. [Author repo](https://github.com/pvz122/PromeFuzz) mở được; chưa audit source hay chạy artifact.

**Paper facts:** Knowledge có ba phần: code metadata/dependency graph, documentation constraints và consumer API correlations. Retrieval cung cấp context liên quan tới target; sanitizer phản hồi constraint violations. Evaluation trên 22 libraries. Ablation bỏ Comprehender làm branch coverage thấp hơn bản đầy đủ (full/w-o=1.16); đây là component ablation, không cô lập graph topology. [Nguồn: §3 và §5.3](https://pvz122.github.io/pdf/25-promefuzz.pdf).

**Áp dụng đề xuất:** Knowledge cho LineFacts nên chứa conditional obligations ngoài AST/dataflow. Đưa một constraint và slice cần cho target vào prompt, có provenance. Đây là adaptation cho residual semantic bugs, chưa là reproduction paper.

**Giới hạn:** API harness correctness và crash detection khác oracle assertions trên buggy PUT. Không lấy coverage gain làm evidence cho LineFacts detection. Không tự thêm requires/establishes state edges rồi gọi đó là schema của paper.
