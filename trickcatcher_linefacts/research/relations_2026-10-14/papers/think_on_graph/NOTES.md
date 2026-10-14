# Think-on-Graph

[Full text v6](https://arxiv.org/abs/2307.07697v6), ICLR 2024. Kiểm methodology và evaluation scope. [Author code được paper dẫn](https://github.com/IDEA-FinAI/ToG), chưa audit source.

**Paper facts:** LLM chọn relations/entities, iterative beam search tìm reasoning paths trên KG; method training-free. Evaluation là knowledge-graph question answering, không phải software testing. [Nguồn: paper v6](https://arxiv.org/abs/2307.07697v6).

**Áp dụng đề xuất:** Model chọn từ valid node/edge IDs, tool kiểm path và truy xuất một subgraph nhỏ. Giảm candidate expansion bằng type/schema và giới hạn depth trước khi gọi model.

**Giới hạn:** QA KG có factual triples; LineFacts graph chứa may-dependencies và uncertain spec links. Path hợp lệ trong graph chưa đủ cho bug hypothesis đúng. Thêm iterative calls có thể thắng chỉ vì compute, nên phải tính proposal/retrieval cost vào matched controls. Graph toàn cục hoặc Neo4j chưa có lý do dùng cho task nhỏ.
