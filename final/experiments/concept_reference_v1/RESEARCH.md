# Research và quyết định — 2026-10-30

## Khác biệt với v7/v11

v7 đã có OUTCOME/STMT/BOUND/REL/SHAPE/NUM/DU cùng fuzz witnesses; v11 sửa fairness.
Kết quả matched-placebo 26–22 không chứng minh concept gain. v44 cũng cho thấy
generic class/boundary pools không hơn random. Do đó không gọi việc thêm CFG,
DFG hoặc đổi tên taxonomy là một method mới.

Thay đổi có thể kiểm tra được ở đây là **fixed PUT cohort + fixed reference
oracle**, tách năng lực chọn input khỏi lỗi expected-output của LLM. Hướng secondary
là tạo concept từ **khác biệt giữa các PUT cùng pass base**: cùng expression input
nhưng operator khác nhau → thử equality/hai phía của relation. Đây chỉ là hypothesis
được grounding bằng source, không chứng minh output disagreement hay novelty so
với toàn bộ differential-testing literature.

## Library selection

- [python-graphs](https://github.com/google-research/python-graphs) có CFG, data-flow
  và composite program graph; dùng package gốc, không viết lại các graph algorithms.
  Repo đã archived từ 2024; pin 1.2.3, kiểm tra syntax support, báo unsupported thay
  vì tạo graph giả. LAST_WRITE từ read/access về previous write được đảo khi hiển
  thị def→use. Đây là static may-flow, không phải dynamic def-use coverage.
- [coverage.py branch coverage](https://coverage.readthedocs.io/en/latest/branch.html)
  cung cấp actual line arcs; map sang static CFG để tìm obligation còn thiếu.
  Static arc không quan sát được có thể infeasible; tránh gọi nó là bug.
- [Hypothesis](https://hypothesis.readthedocs.io/en/latest/reference/api.html)
  tạo pool deterministic từ observed base values. Không dùng `.example()` và không
  chọn input nhờ reference output; witness-only giữ rõ phần tool tự làm được.
- [EvalPlus](https://github.com/evalplus/evalplus) cung cấp domain contracts và
  tolerance metadata. Chỉ trích `contract`/`atol` từ HumanEval+ v0.1.10; không dùng
  plus test inputs. Adapter oracle theo float convention của package 0.3.1 và gọi
  `_poly` gốc cho find_zero; không reimplement pipeline của paper.

## Hướng đã đối chiếu

[SymPrompt](https://arxiv.org/abs/2402.00097) đã dùng path-aligned multi-step prompts;
[CoverUp](https://doi.org/10.1145/3729398) đã dùng coverage feedback để tăng coverage.
Vì vậy CFG/coverage-guided prompting không phải novelty riêng của bản này.
[Design choices made by LLM-based test generators prevent them from finding bugs](https://arxiv.org/abs/2412.14137)
chỉ ra vấn đề oracle được thiết kế để pass code có thể loại bug-revealing tests.
Ở đây LLM chỉ sinh inputs; gold output từ reference, và test fail trên PUT được giữ.

Không triển khai/mô phỏng ba paper này. Chúng là cơ sở đối chiếu để tránh lặp lại
claim cũ. Các source notes nằm riêng tại `final/research/`.
