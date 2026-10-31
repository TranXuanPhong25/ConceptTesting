# RTED — đối chiếu mechanism, 2026-10-21

Đọc lại v2 §III, evaluation setting, ablations §V-B và threats. Author source pin
`ef10c4e1620cb618037a901092d266590e6b80bb`; không chạy implementation.

Paper: https://arxiv.org/html/2507.02318v2

| Evidence | Kết luận đối với proposal |
|---|---|
| §III-A: error-seeking/normal constraints, backward propagation, risk evaluation | Chain constraints → generation đã có; không phải sound symbolic proof |
| §III-B: chain history + method summary → tests | Semantic prompt chaining là prior work |
| §III-C: type consistency, semantic validity, meta-evaluation | False-positive checking và reflective repair đã có |
| `3_run_constraints_inference_buggy.py`, `generate_iterative_prompt` / `generate_type_iterative_prompt` | Callee constraints truyền ngược qua callers; bounded retry khi unsatisfiable |
| `4_run_test_gen.py:266–317`, `:341–451` | Assertion stripping, execution/self-debugging, verifier/coordinator/refinement |

Scope là TypeError; không cung cấp general functional oracle. Benchmark runner có
buggy/fixed execution; source inspection không phải reproduction success. Điểm học
được là constraints phải nối với validity/use context; không thể chỉ đổi tên constraints
thành concepts để claim novelty.

Synthesis: [đề xuất](../../audit/CONCEPT_GUIDED_PROPOSAL_20261021.md).
