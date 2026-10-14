# MR-Coupler

[Full text v2](https://arxiv.org/html/2604.10126v2), FSE 2026. Kiểm §3.1–3.3, §4.3/4.4. [Author website](https://mr-coupler.github.io/) mở được; [Zenodo do paper dẫn](https://doi.org/10.5281/zenodo.19438045) chưa tải/audit.

**Paper facts:** Coupling features gồm signature commonality, function calls và state interaction. LLM tạo metamorphic tests từ coupled methods; amplification và mutation-based filtering giảm false alarms. Evaluation có 100 human-written MTCs và 50 real-world bugs; tests phát hiện 44% bugs. Filtering so pass rates trên original và mutated program. [Nguồn: §3 và abstract](https://arxiv.org/html/2604.10126v2).

**Áp dụng đề xuất:** Conditional relations từ spec cho cùng một function: input transformations và expected output relation. Đây là semantic concept có executable obligation, bổ sung cho line-level dependence.

**Giới hạn:** HumanEval ít method pairs và shared fields. Vì PUT của LineFacts đã buggy, filter yêu cầu relation pass trên original PUT có thể loại bug-revealing relation. Cần independent spec evidence; mutant killing không chứng minh MR đúng. Không gọi adaptation single-function là reproduction MR-Coupler.
