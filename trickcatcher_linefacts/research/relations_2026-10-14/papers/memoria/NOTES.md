# MemoRIA — Abstraction-Aware Inference of Metamorphic Relations

[Author-hosted full text](https://mpapad.github.io/publications/pdfs/metamorphic_relation_inference.pdf), FSE 2024, DOI 10.1145/3643747. Kiểm §2–4 và evaluation. [Replication package paper dẫn](https://zenodo.org/records/10683011) chưa audit.

**Paper facts:** Object-protocol abstraction EPA nhóm concrete states theo enabled methods. Graph/grammar hạn chế candidate equivalent method sequences; runtime checking refute relations, SAT giảm redundancy. Evaluation trên 22 Java classes. Paper nói relations mô tả current behavior và báo effectiveness chủ yếu bằng mutation analysis. [Nguồn: §1–4](https://mpapad.github.io/publications/pdfs/metamorphic_relation_inference.pdf).

**Áp dụng đề xuất:** Concept labels quyết định conditional relation nào hợp lệ và giảm redundant obligations. Pure-function LineFacts có thể dùng domain/value classes; đây là analogy, chưa tương đương EPA.

**Giới hạn:** Current behavior của buggy PUT không bảo đảm intended semantics. Finite execution không chứng minh universal equivalence. Class syntax trong VibePass chưa đủ để kết luận có object protocol; kiểm stateful use trước.
