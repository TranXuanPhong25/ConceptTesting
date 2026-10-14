# Plan: concept trên biểu diễn hành vi trừu tượng

2026-10-14. Trạng thái: **plan**, chưa tạo pipeline mới hoặc chạy experiment mới.
Người dùng muốn concept trừu tượng hơn line facts, có control flow, symbolic reasoning và pseudocode.

## Mục tiêu và câu hỏi nghiên cứu

Dựng một biểu diễn cho biết chương trình biến đổi input thành output như thế nào, dưới điều kiện nào.
Từ biểu diễn đó và spec, tạo concepts về hành vi, gắn với một fault hypothesis và điều kiện phân biệt.

Hai câu hỏi độc lập:
1. Behavioral abstraction có giúp sinh test hơn danh sách code facts không?
2. Trên cùng abstraction, thêm semantic concepts/obligations có giúp nữa không?

Control-flow graph là cấu trúc hỗ trợ. Concept cần có ý nghĩa dùng lại giữa nhiều chương trình,
chẳng hạn giữ multiplicity, chọn đúng phần tử khi tie, bảo toàn thứ tự, hoặc độ lệch tuyệt đối.
Không lấy tên nhãn AST làm bằng chứng rằng semantic concept đã được tạo thành công.

## 1. Tool dựng biểu diễn trung gian về control và state

Input: PUT, public spec và base tests; dùng lại B5/domain metadata từ foundation hiện tại.
Python `ast` phục vụ parsing. Dựng IR nhỏ, giới hạn rõ các constructs được hỗ trợ:

- Branch: guard và successors; early return kết thúc path và ảnh hưởng continuation.
- State: symbolic expressions cho assignments, versions của biến và merge có guard.
- Collections: object identity cho local containers; append/index update tạo state version mới.
- Return: liên kết expression hoặc container state được trả về.
- Loops: giữ loop guard/body/effect; chỉ dùng loop summary khi pattern và side conditions phù hợp.

MVP tập trung deterministic Python với bool/int, lists của scalar, assignments, if/else,
for-range/iteration và một whitelist builtin operations. Float semantics, arbitrary calls,
recursion, exceptions chưa model được, alias/escape không phân giải được: ghi `opaque/unknown`
và ranh giới phụ thuộc output. Không nối edge suy đoán để lấp chỗ thiếu.

Artifact `behavior_ir.json`: blocks, guards, symbolic states, heap effects, returns,
source mappings, type assumptions và unsupported regions. Phạm vi type từ base observations
phải được ghi là assumption; không tự coi đó là toàn bộ miền input hợp lệ.

## 2. Nén thành behavioral blocks và pseudocode

Các block ban đầu: MAP, FILTER, FOLD/ACCUMULATE, SELECT, ORDER và CASE.
Nhận diện pattern theo rule có side conditions; các phần còn lại giữ structured statements.
Ví dụ vòng lặp ghi vào list mới có thể thành MAP nếu không có tác động khác cản trở việc nén.

Pseudocode được render từ IR. Mỗi block phải truy ngược về source và state effect.
Tách trạng thái evidence: `structural_supported`, `replayed`, `bounded_symbolic`, `unknown`.
Replaying một số inputs không được ghi thành chứng minh tương đương trên mọi input.

Sửa đúng hạn chế task 152: append tạo state mới, và return sử dụng state sau append.
Các phiên bản hiện tại chỉ ghi definition của list variable nên mất quan hệ này.

Output: `behavior_summary.json` và `pseudocode.txt`; mục tiêu mỗi task có khoảng 3–8 blocks,
nhưng giữ phần chưa nén khi việc nén có thể làm mất semantics.

## 3. Từ spec và behavioral blocks tạo semantic concepts

Hai bước model có budget riêng:

1. **Spec-only extraction:** từ toàn bộ docstring, tách atomic candidate obligations gồm
   source quote/span, applicability, output relation và exceptions/special cases. Tách narrative,
   examples và requirements. Tool kiểm quotation/schema; semantic entailment vẫn là candidate.
2. **Binding:** nhận obligations và behavioral summaries để đề xuất concept instances,
   fault hypotheses và điều kiện phân biệt. Tool kiểm block IDs, data/state links và type compatibility.

Dùng typed templates/DSL cho predicate và relation; tool compile thành executable checks.
Tránh yêu cầu Qwen viết nhiều Python function strings lồng trong JSON như v14/v15.
Không ép mọi obligation vào một template: unsupported được ghi riêng.

Nhóm concepts MVP:
- Elementwise correspondence: quan hệ giữa từng input element và output element.
- Multiplicity: giữ/loại duplicate, count theo số lần xuất hiện hay distinct values.
- Ordering/selection: thứ tự, extremum, tie-breaking và stability.
- Boundary/special-case behavior: strict/non-strict, empty, zero, singleton.
- Symmetry/invariance: chỉ áp dụng khi có căn cứ trong spec; MR là một dạng relation của concept.

Mỗi instance gồm: family, quoted obligation, domain D, behavioral block bindings,
expected relation O, alternative behavior, distinguishing condition, support và unresolved assumptions.
Concept không bắt buộc phải ở một uncovered line; covered paths có thể sai với giá trị khác.

## 3.1 Explicit reasoning: từ behavior tới điểm yếu

Pseudocode cần một bước suy luận tiếp theo. Mỗi candidate phải chỉ ra **điều kiện mà operation
hoặc output relation yêu cầu**, **điều kiện path thực sự bảo đảm**, và **khoảng thiếu giữa hai điều kiện**.
Một đoạn nhận xét chung như "hãy thử boundary cases" không đủ để thành reasoning record.

Hai loại obligation:
- Operation requirements do tool biết: min/max không có default cần nonempty input; index cần
  nằm trong bounds; division cần denominator khác zero. Áp dụng đúng type và semantics của operation.
- Semantic requirements từ spec: giữ multiplicity, dùng absolute difference, chọn đúng extremum/tie,
  v.v. Chạy operation thành công vẫn có thể vi phạm các requirements này.

Với domain D và path PC, câu hỏi là D AND PC có kéo theo required condition Q hay không.
Nếu không, tìm một feasible input class thỏa D AND PC AND NOT Q. Query/replay hữu hạn chỉ
chứng nhận trong scope đã model; các semantic Q từ LLM vẫn cần kiểm tra spec support riêng.

Reasoning record gồm:

```text
code_claim:              operation/state/output thực sự của block
required_condition:      điều kiện để operation an toàn hoặc output đáp ứng spec
path_guarantees:          các guard và state relations đã có trên path
unresolved_obligation:    phần required_condition chưa được path bảo đảm
candidate_input_class:   constraints làm khoảng thiếu đó xuất hiện
predicted_effect:         exception hoặc output relation cụ thể bị vi phạm
evidence:                 source/IR IDs, spec quote, bounds, replay/solver status
```

Tool dựng operation requirements và kiểm các IR references/state claims. LLM ánh xạ requirements
sang semantic concept và đề xuất gap/discriminator trong typed DSL. Tool kiểm feasibility và
predicted behavior khi supported. Không dùng một đoạn prose do LLM viết làm proof của claim.
Hai proposal calls đã chốt vẫn giữ vai trò spec-only extraction rồi binding/derivation; không
thêm một agent hay một reasoning call không được tính vào budget.

Ví dụ thật, task 136 largest_smallest_integers (fragment; path có len(xs)>1):

```text
neg = FILTER(xs, x < 0)
pos = FILTER(xs, x > 0)
IF EMPTY(neg):
    RETURN (None, MIN(pos))
```

MIN(pos) yêu cầu pos nonempty. Guard chỉ bảo đảm neg empty, chưa bảo đảm pos nonempty.
Hai filters không bao hết miền integer: zero thuộc cả hai complement. Vì vậy constraints
len(xs)>1, count_negative(xs)=0, count_positive(xs)=0 là khả thi với xs=[0,0]. Fragment
sẽ gọi min([]), gây ValueError; spec R2 yêu cầu các thành phần thiếu dấu được trả về None.
Không cần canonical code để hình thành candidate này: source operation và quoted spec đủ làm căn cứ.
Đây là ví dụ đã xem để giải thích design, không phải task evaluation mới.

Semantic concept dùng lại ở đây là **aggregation trên các nhóm có thể rỗng**, kèm partition
coverage: membership của mỗi nhóm, nhóm nào có thể đồng thời rỗng, operation nào đòi hỏi
nonempty, và output phải thế nào khi nhóm rỗng. Nhãn MIN hoặc EMPTY đơn lẻ không chứa derivation đó.

Phase C phải báo bao nhiêu concepts có đầy đủ derivation/discriminator và bao nhiêu chỉ có
name/description. Gate "grounded nontrivial concept" yêu cầu reasoning record có gap và
computable candidate condition; chưa yêu cầu solver phải tìm được witness cho mọi concept.

## 3.2 Predicate khó: relational abstraction và temporal context

Ví dụ người dùng: dữ liệu trong 90 ngày gần đây, A thuộc B, X gồm Y. Cần xác định type,
quantifier, thời điểm tham chiếu và boundary policy trước khi formalize. Với record eligibility,
giả sử fixed clock T0, interval inclusive và X/Y là sets, có thể dùng các predicates:

```text
within_window(r):  T0 - 90 days <= event_time(r) <= T0
membership(r):    A(r) in B(r)
coverage(r):      Y(r) subset_of X(r)
```

Nếu rule áp dụng cho mọi record trong window, biểu diễn obligation thành
within_window(r) => membership(r) AND coverage(r), không tự đổi thành điều kiện phải
từ chối mọi record ngoài window. Eligibility và universal validation là hai semantics khác nhau.
Calendar days/duration, timezone và tính inclusive của endpoints phải lấy từ contract.

Concept giữ abstract relation classes. Với containment:

```text
missing = Y minus X
extra   = X minus Y
equality:          missing empty AND extra empty
proper coverage:   missing empty AND extra nonempty
missing required:  missing nonempty
```

Nếu spec cho phép non-strict coverage, equality là valid. Nếu code yêu cầu proper coverage,
discriminator là equality; giữ window và membership true để test tới đúng decision.
Một ví dụ minh họa là age=30 days, A in B, X=Y={p,q}. Đây là giả định thiết kế, không phải
kết quả benchmark. Spec yêu cầu proper coverage thì equality bị từ chối là đúng.

Temporal classes gồm inside, đúng endpoint, ngoài endpoint và future; membership gồm
member/nonmember/unknown. Không enumerate mọi timestamps hay mọi set elements.
Nếu list/multiset semantics yêu cầu multiplicity, dùng count_Y(v)<=count_X(v), không silently
chiếu sang set. Nếu order có ý nghĩa, bổ sung order predicates. Calls tới DB/service phức tạp
cần contract hoặc snapshot/replay; predicates chưa model được giữ unknown.

Predicate abstraction có thể làm mất thông tin. Nếu abstract candidate không replay được
hoặc dự đoán sai branch, bổ sung predicate cần thiết rồi kiểm lại. CEGAR là reference cho
nguyên tắc coarse abstraction rồi refine, không phải một engine đã được implement ở đây.

## Ví dụ chạy xuyên suốt: compare(game, guess)

```text
DOMAIN FROM SPEC:
    two equal-length score/guess sequences

IMPLEMENTATION SUMMARY:
    MAP aligned elements (a, b): EMIT a - b
    RETURN emitted sequence

CONCEPT INSTANCE:
    elementwise absolute difference
    expected element relation: y = abs(a - b)
    alternative behavior: signed subtraction
    distinguishing condition: a < b
```

`a < b` là điều kiện phân biệt hypothesis, không phải một branch đã có trong PUT.
Với input một phần tử, implementation expression là `a-b`; condition phân biệt yêu cầu
`a-b != abs(a-b)`. Một model của condition là a=1, b=2. Tool phải chạy lại input cụ thể
để xác nhận actual PUT behavior. Đây là ví dụ minh họa đã biết, không phải evaluation task mới.

## 4. Symbolic reasoning có phạm vi

MVP biểu diễn guard/state bằng symbolic expressions và giới hạn số paths; solver là module
bổ sung cho feasibility hoặc tìm candidate input. Query tổng quát trên miền hỗ trợ:

```text
D(x) AND path_condition(x) AND NOT O(x, implementation_summary(x))
```

D là candidate applicability/domain; path_condition là guard từ code; O là candidate obligation.
Giữ ba nguồn này riêng trong artifact. SAT không tự chứng minh bug vì O có thể sai.
Mọi candidate phải replay trên actual PUT và validator; canonical/ref chỉ vào bước đánh giá cuối.
UNSAT trong scope bị chặn hoặc timeout/unknown không được coi là program đúng.

Ưu tiên API Z3 cho IR expressions đã hỗ trợ; CrossHair contracts là lựa chọn cho Python
counterexample discovery, không dùng API nội bộ của nó làm nguồn AST/CFG. Dùng tool gốc,
không tái hiện một paper. CrossHair không tìm thêm bug ở thử nghiệm gap cũ (§11.33), nên
không giả định solver tự mang lại gain cho lần này.

Giới hạn dự kiến để preregister: tối đa 8 bounded paths, unroll 4 iterations, symbolic list
length 0–4 và scalar integer -100..100; 5 s/query và 30 s/task. Hypothesis vẫn sinh được
inputs ngoài scope nhỏ này. Một SMT result phải ghi đầy đủ bounds/assumptions.
MVP GPU đầu tiên dùng behavioral summaries với Hypothesis; bật solver discovery ở một
ablation riêng sau đó, để đo được phần gain của representation và của solver.

## 4.1 Search trên obligation contexts, không gán đúng/sai toàn bộ node

Một node search có key gồm obligation ID, program block, abstract relation classes,
path constraints, symbolic state/heap context, domain assumptions và analysis bounds.
Cùng block có thể an toàn với context này nhưng sai với context khác. Discharging một
obligation tại một context không cho phép xóa block hoặc các obligations khác.

Giảm search trước khi đổi traversal algorithm:
- Backward slice từ output/operation liên quan tới obligation, giữ mọi relevant state effects.
- Cache verified queries/context equivalence; không merge chỉ vì cùng source line hoặc cùng
  abstract label. Loop summaries có assumptions; bounded unfolding không chứng minh mọi iterations.
- Prune infeasible constraints khi có đúng semantics; unknown/timeout vẫn là pending.
- Bắt đầu từ discriminator classes: equality, empty partition, exact boundary, missing member.
  Giữ các predicates khác true để isolate một decision; sau đó thử interactions nếu evidence cần.
  Single-rule cases không bảo đảm bắt được mọi lỗi phối hợp nhiều predicates.

MVP scheduler là budgeted best-first với một phần exploration dành cho obligations chưa
kiểm tra. Priors có thể do LLM đề xuất, nhưng low prior không phải proof để prune.
MCTS là extension cần đối chứng riêng sau khi state/action/evaluator đủ dùng; không tự
thay kế hoạch 400 calls thành một agent loop gọi model không giới hạn.

Actions đề xuất: chọn obligation, split một relation class, refine predicate, solve candidate,
replay input, hoặc kiểm propagation tới return. Cần log choices, alternatives, tool observations,
rejected constraints, costs và certificate scopes. Đây là observable controller behavior;
không phải truy cập white-box nội bộ model hay chứng nhận chain-of-thought là causal reasoning.

Nếu dùng MCTS: selection cân bằng accumulated evidence và exploration; expansion tạo một số
actions mới; rollout thực hiện bounded solver/execution checks; backprop cập nhật evidence/cost.
Không coi coverage hoặc LLM self-score là bug reward. Search có thể dùng feasibility, unmet
operation requirements, actual PUT candidate-obligation violations và supported propagation;
canonical/gold/ref scoring của run chỉ sau generation freeze. Candidate O sai vẫn gây reward
giả, nên đo false hypotheses và predicate validity riêng. Minimax không tự phù hợp vì chưa
có một adversarial opponent với payoff được định nghĩa trong bài toán test generation này.

So sánh dự kiến: random/round-robin, best-first tool-only, best-first với concept priorities,
rồi MCTS nếu được triển khai/đăng ký riêng; cùng action vocabulary, predicates, model-call,
solver/execution/time budgets và caches. Như vậy mới tách được gain của search khỏi concept
selection, verifier và chi phí thêm. Đây là proposal, chưa tái hiện code của paper nào.

## 4.2 Finiteness, mutation scope và loop invariants

Finite source/CFG không có nghĩa finite concrete execution traces. Một lần chạy trên input
hợp lệ có thể kết thúc sau hữu hạn bước, trong khi số bước không có upper bound chung cho
mọi input. Count trên finite boolean lists là ví dụ: list length n có 2^n branch histories;
mọi input đều kết thúc nhưng family của histories qua mọi n là unbounded.

"Mọi mutations" cần định nghĩa scope: operators/locations/constant candidates cố định tạo
một mutant set hữu hạn; mọi integer/string/collection values trong unbounded domain thì không.
Integer width cố định cùng bounds cho collections/state/time có thể tạo finite domain,
nhưng finite không bảo đảm enumeration khả thi. Boolean list length 30 đã có hơn một tỷ values.
Window 90 ngày không tự đặt bound cho số records hoặc kích thước các sets.

Nếu mục tiêu exhaustive, register finite input/type/heap/time/loop bounds và semantics của
unsupported operations. Chỉ ghi bounded completeness khi đã kiểm completeness obligations
(ví dụ loop không thể tiếp tục qua unwind bound). Đạt cap hoặc không thấy counterexample
không chứng minh rằng đã bao hết domain. Các SMT results phải mang scope này.

Loop summaries/invariants có thể thay việc enumerate histories bằng proof obligations:
invariant holds initially, one iteration preserves it, and exit implies the output obligation.
Termination cần một lập luận riêng, chẳng hạn decreasing nonnegative measure. Finite proof
obligations không có nghĩa tool luôn tìm được đúng invariant hoặc solve được chúng.

Concept-based relation classes là proposal để giảm exploration. Một representative input
không chứng minh mọi concrete value cùng abstract class đều đúng; nếu abstraction chưa đủ,
refine predicate hoặc giữ unknown. Một bug cũng có thể là missing case hoặc relation giữa
operations dù từng operation chạy hợp lệ. Correctness chỉ gán cho scoped obligation/state,
không gán toàn cục cho một source node. MCTS chỉ phân phối budget, không làm domain unbounded
trở thành finite hay cung cấp completeness guarantee.

References: [CBMC bounded verification](https://diffblue.github.io/cbmc/background-concepts.html),
[loop contracts](https://diffblue.github.io/cbmc/contracts-loops.html).

## 4.3 Finite abstract state machine là biểu diễn ứng viên

Người dùng đề xuất FSM. Mình ưu tiên xem một finite predicate abstraction là cách biểu diễn
behavioral IR: states giữ program location, obligation và truth values của một finite predicate
vocabulary. Predicates do semantic concepts/spec requirements định hướng; không giữ mọi raw value.

Phân biệt ba mức:
- CFG/FSM chỉ có control locations: finite nhưng có thể mất data/state relations gây bug.
- EFSM với guards, updates và variables: control locations finite; concrete configurations có thể
  infinite nếu integers, heap hoặc stack không bị chặn.
- Finite abstract machine: data được chiếu thành finite relation classes hoặc predicate valuations.
  Với m locations và k Boolean predicates, có tối đa m*2^k valuations trước feasibility pruning,
  nhân thêm finite monitor/obligation states. Unknown được model rõ bằng nondeterminism hoặc status,
  không tự đổi thành false. Unbounded stacks/calls cần summary hoặc giới hạn scope.

Vocab cho ví dụ 90 ngày/containment: window_valid, membership_valid, missing_empty, extra_empty.
Một lớp equality có missing_empty=true, extra_empty=true. Spec non-strict coverage cho phép accept;
code chỉ cho proper coverage lại reject. Mismatch xuất hiện ở transition/output của một state class,
không cần enumerate mọi sets hoặc every execution history.

Artifact dự kiến: `abstract_machine.json`, gồm predicates/source bindings, initial abstract states,
locations, guarded transitions/state updates, output observations, evidence và unresolved semantics.
Tool lấy transitions từ implementation IR; spec-only extraction cung cấp partial obligation monitors.
Kiểm mismatch bằng composition của implementation model và obligation monitor, không để LLM tự
vẽ một machine rồi coi là semantics thật của code. Monitor về output cũng phải giữ đủ thông tin
để phân biệt lỗi arithmetic/order/count mà chỉ branch coverage không thấy.

Một abstract graph finite cho phép reachability/fixpoint trên states đã visited; không cần đi
lại mọi loop history nếu abstraction/transition relation đáp ứng assumptions của analysis.
Thế nhưng family của paths vẫn có thể infinite. History-dependent properties phải nằm trong
monitor state; raw source line hoặc predicate labels không đủ để merge states đúng.

Abstract counterexample cần concretization: solve bounded transition constraints, tạo input rồi
replay actual PUT. Nếu spurious, refine vocabulary/state relation hoặc giữ unknown. Một path chỉ
được observed cho testing là under-approximation; model over-approximating toàn bộ supported
semantics có claim khác. Phải ghi rõ loại và scope, không suy completeness từ vài concrete traces.
State explosion vẫn có thể là 2^k; chọn predicates theo obligation, phân tích từng relevant slice,
cache queries và tránh full Cartesian enumeration khi có symbolic representation.

Vai trò LLM: đề xuất relevant predicates/concepts, interpretation có spec evidence, và ưu tiên
abstract mismatch candidates. Tool: source-to-state transitions, feasibility, replay và trace logs.
MCTS chỉ cần khi abstract frontier lớn và evaluation đủ tin cậy; finite graph nhỏ ưu tiên direct
reachability hoặc budgeted best-first. Đây là preferred design candidate, chưa implement model checker.
Giữ các comparisons behavior vs facts và behavior+concept vs cùng behavior model như đã chốt.

References: [NuSMV finite-state tutorial](https://nusmv.fbk.eu/userman/v21/nusmv_2.html),
[SLAM project](https://www.microsoft.com/en-us/research/project/slam/), và CEGAR notes ở research folder.

## 4.4 Spec/model mutation: xóa, bypass và di chuyển semantic nodes

Người dùng đề xuất mutate spec, rồi hỏi bỏ filter/check/block if hoặc dời if trong tree.
Dùng một finite mutation grammar trên typed behavioral models để tạo fault hypotheses.
Spec gốc vẫn normative; mutant là một cách hiểu/thi hành sai cần phân biệt bằng test.

Phải ghi origin của tree:
- Spec/requirement model: thay quan hệ/guard/output để tạo alternative behavior, ví dụ
  non-strict coverage thành equality/proper coverage, inclusive boundary thành exclusive.
- Implementation IR: xóa/dời operation tạo code-behavior alternatives. Khác PUT hiện tại
  không chứng minh PUT sai; cần actual PUT vi phạm original obligation trên input hợp lệ.
  Một mutant sửa được candidate violation chỉ là repair support, chưa là universal oracle.

Các operator ứng viên:

| Operator | Semantics phải định nghĩa | Discriminator thường gặp |
|---|---|---|
| Bypass FILTER | Thay output filter bằng input collection, giữ downstream binding/type | Một element không thỏa predicate nhưng ảnh hưởng output |
| Delete CHECK | Bỏ một guard của conjunction hoặc cho một explicit check luôn pass | Guard bị bỏ false, các guards còn lại true |
| Skip IF body | Không chạy body của một conditional | Condition true và body tạo state/output effect |
| Unguard IF body | Chạy body dù condition false | Condition false và effect của body quan sát được |
| Select opposite branch | Explicitly đổi T/F successor | Input thỏa một guard và output effects của hai branches khác nhau |
| Move CHECK/IF | Dời node sang vị trí có data available, ghi order/state context mới | Check bị dời sau operation cần nó bảo vệ, hoặc đọc state đã đổi |
| Change relation/output | Typed swaps như <=/<, subset/equality, min/max, count/distinct-count | Exact boundary, extra elements, ties hoặc duplicates |

"Delete if" không phải một operator có nghĩa duy nhất. Removing whole block, promoting then,
promoting else và deleting one conjunct là fault models khác nhau. Bỏ assignment mà làm
downstream name undefined không phải default cho filter deletion; dùng typed bypass rõ ràng.
Invalid bindings/types được báo riêng. Reordering pure checks có thể equivalent; đổi order
chỉ là test target khi state, exceptions, effects, early returns hoặc decision priority khác.

Ví dụ requirement model: chọn số dương nhỏ nhất, không có thì trả None.

```text
positive = FILTER(xs, x > 0)
IF EMPTY(positive): RETURN None
RETURN MIN(positive)
```

Bypass filter phân biệt bằng xs=[-1,2] (model gốc 2, mutant -1). Bỏ empty check hoặc dời
check sau MIN phân biệt bằng xs=[0] (model gốc None, mutant gọi min([])). Đây là illustrative
models/spec, không có experiment hoặc implementation mới được chạy.

Với typed deterministic decision models M0 và Mi, tìm input trong original admissible domain
D0 làm outputs khác nhau. Với stateful machines, tìm distinguishing sequence trong product
của original/mutant state models rồi concretize/replay. Paths trên abstract machine có thể
spurious; từng edge feasible chưa bảo đảm toàn sequence feasible.

Nếu spec chỉ có partial postcondition, không tự tạo một unique expected output. Phải dùng
allowed output relations hoặc giữ unresolved: weaker mutant có thể bao toàn bộ original
allowed behaviors, nên một original-passing trace chưa chắc phân biệt được nó.
Original input preconditions giữ nguyên; thay spec trong mutant không cho phép test ngoài D0.
Eligibility/output requirements phải tách khỏi admissibility/type constraints.

MVP: first-order mutations (một node/operator mỗi mutant), fixed candidates, cap và provenance.
N nodes/K compatible operators tạo finite candidate set; relocations có thể O(N^2), nên lọc
bằng dependencies và cap. Equivalent mutants chỉ loại khi có evidence đúng scope; không thấy
khác ở vài examples hoặc solver timeout không chứng minh equivalent. Base-distinguished
mutants được báo riêng; không coi tests đã có là detection mới.

Concept là requirement + semantic fault model + distinguishing condition, không chỉ tên operator.
LLM formalize/select requirement và prioritize plausible alternatives; tool mutate DSL/IR,
compile model transitions, solve/replay distinguishing tests. Guided tests luôn theo spec gốc.
Spec mutation coverage là metric phụ; metric chính vẫn actual PUT D_IO dưới shared-ref scoring.
Killing nhiều abstract mutants chưa chứng minh phát hiện được bug thật.

Đây là đề xuất cho framework LineFacts, chưa implement hay reproduce paper. Spec mutation/model-based
test generation đã có prior work; novelty phải nằm ở semantic abstraction, grounded LLM selection,
input-discrimination và evidence/empirical gain chứ không ở tên kỹ thuật spec mutation.
[NIST reference](https://www.nist.gov/publications/test-generation-using-model-checking-and-specification-mutation).

## 5. Test generation và đối chứng

Mọi generation arm đọc cùng spec, PUT, base tests, cùng model/seeds/request/output caps.
Primary comparisons dùng cùng validity/size filter và cùng cách chọn input; không thêm
concept-specific acceptance filter chỉ cho arm concept. Target activation đo riêng sau selection.

| Arm | Guidance thêm vào prompt | Câu hỏi |
|---|---|---|
| plain | Hướng dẫn boundary chung | Baseline không có evidence thêm |
| flat-facts | Frozen code facts | So với cách hiện tại |
| behavior | IR/pseudocode về behavior | Abstraction có giúp hơn flat facts? |
| behavior+concept | Cùng IR + semantic concepts/obligations/hypotheses | Concept có giúp hơn IR? |
| placebo | Base-covered facts, khớp số requests | Kiểm soát budget và guidance không nhắm gap |
| toolinput | Common witness pool, cùng strategy adapter | So với cung cấp thẳng input |
| witness-only | Chạy common witnesses, không generation LLM | Đóng góp của tool |

Primary = behavior+concept vs behavior. Secondary = behavior vs flat-facts, rồi plain,
placebo, toolinput và witness-only. Nếu thêm solver, mọi arm dùng chung discovery artifacts;
báo cả solver/witness-only và incremental LLM contribution. Guided prompts không lộ concrete
solver witnesses; toolinput/witness-only được thiết kế để nhận chúng.

Budget dự kiến cho smoke: 20 dev tasks/K=1; 2 proposal calls/task, tối đa 6 candidate concepts,
chọn 3; 3 strategy calls/sample, 1024 completion tokens/call, tối đa 2 selected sources/slot,
12 distinct PUT calls/sample nếu có pairs. Không retry repair nội dung. Với sáu LLM-generation
arms + witness-only, ceiling là 40 proposal + 360 strategy = 400 logical calls, chưa tính transport
retries. Proposal caps dự kiến 2048 completion tokens/call. Báo actual tokens và mọi CPU discovery cost;
không dùng punctuation padding để giả lập tokenizer equality.

Metric chính: D_IO task detection với cùng ref oracle. Báo D_I, precision/false alarms,
paired task effect, random-subset equal-count comparisons, input/token/time costs.
Mechanism metrics: usable behavioral summaries, grounded concepts, activation rates,
candidate-vs-confirmed violations, opaque/abstain rates. Canonical property checks chỉ sau
generation freeze; kết quả không được dùng để chọn cards cho chính run đó.

## 6. Thứ tự triển khai và gates

| Phase | Deliverable | Điều kiện chuyển bước |
|---|---|---|
| A — CPU foundation | IR schema, supported semantics, source mapping, pseudocode; state-write/early-return/loop cases | Không có sai khác đã biết ở các replay thuộc subset hỗ trợ; unknowns được giữ rõ |
| B — representation audit | Cùng 20-task design cohort đã dùng, không xem là held-out mới | Ít nhất 16/20 tasks có một supported input-to-output behavior summary; báo full denominator |
| C — concept proposal smoke | 40 proposal calls tối đa, typed concepts và rejection report | Ít nhất 10/20 tasks có grounded nontrivial concept; không có base contradiction đã biết |
| D — generation smoke | Bảy arms, common-ref scoring, mechanism/cost report | Đánh giá contrast đã chốt; không promote chỉ từ p-value của K=1 |
| E — larger comparison | Freeze lại scope/config trước full dev K=3, rồi xét external evaluation | Chỉ mở rộng sau khi cơ chế hoạt động và có lý do rõ từ phase D |

Gates B/C là coverage/engineering gates, không phải chứng minh semantic correctness.
Task thiếu summary/card vẫn nằm trong denominator và dùng fallback rõ ràng nếu chạy phase D.
Không chọn lại tasks theo detection scores để đạt gate. Những thay đổi sau một gate thất bại
phải tạo copy/amendment mới trước outputs tiếp theo.

Implementation dự kiến ở `pipelines/v16_behavior/`, copy foundation `v11_fair`, có CHANGELOG
và provenance cho helpers được tái sử dụng. Kết quả/analysis/report nằm riêng. Preregister scope,
budgets, gates và comparisons trước model outputs. Đây là plan; hiện chưa tạo implementation.
SWT-Bench là bước sau khi abstraction có bằng chứng hữu ích ở cấp function.

## Căn cứ và nguồn

- [Audit extraction hiện tại](METHOD_V14_V15.md): sentence segmentation, binding-level DU, mutation gap,
  AST guards và co-execution không đủ để mô tả causal propagation.
- [v14/v15 format-repair results](analysis/v14_v15_format_repair.md): graph treatment thưa; accepted MR
  không bảo đảm relation đúng.
- [CrossHair how it works](https://crosshair.readthedocs.io/en/latest/how_does_it_work.html): symbolic
  Python values, path constraints và Z3; không phải AST analysis.
- [CrossHair limitations](https://crosshair.readthedocs.io/en/latest/limitations.html): deterministic
  scope, identity/alias limitations; không có counterexample không bảo đảm property đúng.
- [Programming Z3](https://z3prover.github.io/papers/programmingz3.html): solver API và logical models.
- [Thử nghiệm CrossHair trước đây](analysis/crosshair_gaps_report.md), RESULTS §11.33.
- [Search/relation research note](research/search_reasoning_2026-10-14/REPORT.md): LATS, Vital,
  discriminator quality và CEGAR; primary sources, each paper in a separate folder.
