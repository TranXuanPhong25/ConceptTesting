# DBcover

[Full text v1](https://arxiv.org/html/2608.25573v1), submitted 2026-08-26; arXiv comment nói accepted ICSE 2026 Industry Challenge Track, chưa xác minh proceedings độc lập. Kiểm §3 và §4.3. Chưa xác định author artifact từ bản đã đọc.

**Paper facts:** KG gồm SQL-query, execution-path và function nodes; edges Execution, Contain, Call. Chọn seed gần target trong call graph, rồi dùng global/local context để sinh SQL. Coverage full 80.1%/82.3%; bỏ global context cùng seed selection còn 75.7%/77.2%. Đây là bundled ablation. [Nguồn: §3.2 và §4.3](https://arxiv.org/html/2608.25573v1).

**Áp dụng đề xuất:** Nối witness/base input với observed path và concept sites; chọn seed gần obligation rồi biến đổi input. Không cần bê SQL KG sang LineFacts.

**Giới hạn:** Coverage trên DBMS lớn khác residual bugs ở hàm nhỏ. Ablation bỏ cả context lẫn seed chưa chứng minh topology riêng. Bài học phù hợp hơn là execution provenance và seed selection; không lấy tỷ lệ coverage làm detection estimate.
