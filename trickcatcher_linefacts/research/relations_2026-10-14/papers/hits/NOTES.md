# HITS

[Paper](https://arxiv.org/abs/2408.11324), ASE 2024. [Author PDF đã đọc](https://ligechina.github.io/My%20Papers/2024%20-%20ASE%20-%20SlicePromptTest4J-%20High-coverage%20Test%20Generation%20using%20LLM%20via%20Method%20Slicing.pdf). Kiểm §3, §4. [Author repo](https://github.com/eecshope/HITS) mở được, có prompts/procedures; chưa audit implementation.

**Paper facts:** Static analysis lấy dependencies; LLM decomposition tạo slices, rồi test generation theo slice và repair execution failures. Evaluation nhắm complex Java methods, line/branch coverage. Không nên diễn giải LLM-produced decomposition là sound PDG slicing. [Nguồn: §3 và §4](https://ligechina.github.io/My%20Papers/2024%20-%20ASE%20-%20SlicePromptTest4J-%20High-coverage%20Test%20Generation%20using%20LLM%20via%20Method%20Slicing.pdf).

**Áp dụng đề xuất:** Dùng tool chọn một input-to-output slice nhỏ có obligation, giúp Qwen ít phải tự nối nhiều line facts.

**Giới hạn:** HumanEval function ngắn; giảm context có thể bỏ mất behavioral context. So với same evidence trong flat cards, không chỉ full-code prompting, để biết gain từ slice hay từ extra guidance. Coverage chưa xác nhận bug detection.
