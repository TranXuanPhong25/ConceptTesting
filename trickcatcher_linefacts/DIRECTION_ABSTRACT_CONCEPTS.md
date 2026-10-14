# Hướng nghiên cứu để xác nhận: abstract behavioral concepts và model mutation

2026-10-14. Tổng hợp discussion; **đề xuất thiết kế, chưa phải implementation hay kết quả mới**.
Chi tiết kỹ thuật/budgets ở [PLAN_ABSTRACT_CONCEPTS.md](PLAN_ABSTRACT_CONCEPTS.md).

## 1. Hướng người dùng đang muốn tìm hiểu

Concept cần trừu tượng hơn line/code facts: mô tả behavior, relationships, guards và state changes.
Muốn explicit reasoning từ "code đang làm gì" tới "điều kiện nào bị thiếu/sai và input nào làm lộ nó".
Pseudocode, control flow, symbolic expressions và FSM là các cách biểu diễn được bàn tới.

Predicate không chỉ là x<0; có thể là temporal windows, membership, containment, multiplicity/order.
Ví dụ X gồm Y phải phân biệt equality, proper coverage và missing items, với types/applicability rõ.

Muốn tránh search mù/exhaustive over mọi values và paths. Đã bàn BFS/DFS, beam search, MCTS/minimax,
node elimination, finite state abstraction và loop summaries. Muốn quy trình chọn/check hypotheses
có actions/evidence nhìn được, thay vì chỉ đưa prompt rồi nhận test mà không thấy căn cứ.

Ý tưởng phát triển cuối: mutate spec/behavior model để tạo fault hypotheses; bỏ filter/check,
skip/unguard if hoặc move if, rồi sinh test phân biệt behavior gốc với alternative đó.
Đây là các directions để kiểm chứng, không phải kết luận rằng MCTS hay FSM đã được chọn và chứng minh hiệu quả.

## 2. Đề xuất của mình

```text
Spec → quoted candidate obligations → semantic concepts
PUT  → typed behavior IR → guarded/state transitions
                   ↓ align with source/spec evidence
          finite predicate-state abstraction
                   ↓
          typed model mutations / fault hypotheses
                   ↓
          distinguishing constraints / inputs / sequences
                   ↓
          actual PUT replay + recorded effects
                   ↓
          common-ref evaluation after generation freeze
```

Spec gốc là normative. Model từ spec vẫn cần kiểm quotation/meaning; model từ PUT phải ghi đúng
implementation behavior, kể cả behavior sai. Không trộn hai nguồn thành một model mặc nhiên đúng.

Concept instance gồm behavioral rule, applicability, required output/state relation, alternative fault,
distinguishing condition và source/tool evidence. Ví dụ aggregation trên nhóm có thể rỗng có hypothesis
"bỏ empty check"; input class "nhóm rỗng" làm operation thiếu precondition và có predicted exception.

State của abstract model giữ location, relevant predicate classes và obligation monitor.
Không coi source line là một state đủ thông tin. Finite predicate abstraction giúp gộp concrete
cases; một EFSM giữ unbounded values không tự trở thành finite-state.

First-order model mutations có finite grammar và cap: bypass FILTER, delete one CHECK,
skip/unguard IF, change T/F successor, dependency-safe relocation, đổi relation/boundary/output.
Mỗi operator có semantics rõ. Equivalent/invalid/unknown mutants được báo với evidence và scope.

Target là phân biệt một fault hypothesis cụ thể. Với deterministic models, tìm x làm outputs
của model gốc/mutant khác nhau. Với partial specs hoặc abstract graphs, giữ unresolved/spurious
cases và concretize/replay trước khi coi là evidence. Mutant disagreement không tự chứng minh PUT sai.

Ví dụ giả định non-strict containment:
requirement Y⊆X → mutant yêu cầu Y⊂X → discriminator X=Y, time/membership guards vẫn true.
Nếu actual PUT reject trong case này, kiểm original obligation và oracle độc lập để chấm detection.

## 3. Vai trò của LLM, tool và search

| Thành phần | Vai trò đề xuất |
|---|---|
| LLM | Formalize/select candidate obligations/concepts, bind chúng với behavior, prioritize hypotheses |
| Tool | Dựng source/state relations, mutate typed models, check constraints, generate/replay inputs |
| Scheduler | Giữ hypotheses chưa xét, reuse evidence, phân phối finite budget |
| Evaluator | Chấm actual bug detection và false alarms với protocol hiện tại |

MVP dùng direct reachability hoặc budgeted best-first có exploration. MCTS chỉ thử sau khi
state/action/evaluator có chất lượng và frontier đủ lớn. Không prune vì LM self-score thấp,
không dùng minimax khi chưa có một adversarial game/payoff rõ. Logs thể hiện controller decisions,
không phải white-box access tới neural network hoặc chứng nhận internal chain-of-thought.

## 4. Những câu hỏi thực sự phải kiểm chứng

1. Có tạo được behavioral model giữ đủ state/data semantics, nhất là collections/loops, không?
2. Có chọn được semantic concepts và mutations phản ánh plausible spec misunderstandings không?
3. Những hypotheses đó có tạo được valid distinguishing inputs và observable effects không?
4. Cùng budget, concept guidance có tăng actual D_IO hơn cùng behavioral model không?
5. Solver/search có thêm gain ngoài witness pool/tool-only không, hay chỉ thêm chi phí?

Passing một node/input không chứng minh node đúng trên mọi states. Terminating từng execution không
làm toàn bộ input/path family finite. Exhaustive claims chỉ cho declared finite model/domain hoặc
đúng abstraction/invariant assumptions. Mọi original/mutant outputs đều có nguồn và scope rõ.

## 5. Thứ tự kiểm nghiệm đề xuất

1. CPU: typed behavior IR, mutation semantics, state transitions và explanatory artifacts.
2. Proposal smoke: semantic obligations, concept instances, finite mutant set và rejection report.
3. Input smoke: concretize/replay một số discriminators; báo abstraction/feasibility/unknown coverage.
4. Generation comparison: plain, flat facts, behavior model, behavior+concept, matched placebo,
   toolinput và witness-only. Primary: behavior+concept vs cùng behavior model.
5. Chỉ sau đó thử solver/MCTS ablation và external repo benchmark như SWT-Bench.

Metric chính là actual PUT D_IO, cùng ref oracle; semantic-mutant coverage và search coverage là phụ.
Đăng ký scope/budgets trước outputs; initial design cohort 20 dev tasks/K=1, source mới ở folder riêng
khi triển khai. Current request là tổng hợp/confirm direction, chưa phải instruction chạy v16.

## 6. Kết quả research đã có

- [Spec mutation/model checking, NIST](https://www.nist.gov/publications/test-generation-using-model-checking-and-specification-mutation):
  established technique, không phải novelty tự thân của đề xuất.
- [NuSMV finite-state tutorial](https://nusmv.fbk.eu/userman/v21/nusmv_2.html),
  [SLAM](https://www.microsoft.com/en-us/research/project/slam/): finite-state/predicate-model references.
- [CEGAR](research/search_reasoning_2026-10-14/papers/cegar/NOTES.md): refinement khi abstract counterexample spurious.
- [LATS](research/search_reasoning_2026-10-14/papers/lats/NOTES.md): external action search và MCTS/environment feedback.
- [Vital](research/search_reasoning_2026-10-14/papers/vital/NOTES.md): domain-risk-guided symbolic exploration,
  memory-safety setting, không trực tiếp chứng minh hiệu quả trên Python semantic bugs.
- [Discriminator study](research/search_reasoning_2026-10-14/papers/planning_discriminator/NOTES.md):
  search phụ thuộc evaluator quality và có thể tốn chi phí.

Research mới đang ở mức feasibility/design. v14/v15 results hiện tại chưa chứng minh một concept advantage;
những results đó không phải kết quả của FSM/spec-mutation proposal này. Không có paper reproduction mới.
