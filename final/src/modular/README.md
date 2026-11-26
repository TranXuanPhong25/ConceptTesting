# Input-generation benchmark

> Cập nhật18/11/2026: bộ chính giữ `ep_bva_v2`, `decision_table_v2`, `control_flow` gốc và `plain`. Đã gỡ VF3, reflection/catalogue→inputs, spec-obligation, LargeInput, Data-flow arms và HumanEval-X adapters khỏi đường chạy hiện tại. Shared pipeline, Pynguin thuần/tool pipeline, HumanEval Python/MBPP và historical outputs/checkpoints vẫn giữ. Nội dung bên dưới về các hướng đã gỡ chỉ là lịch sử; không dùng để launch mới.


Pipeline hỗ trợ `plain`, `boundary` (soft BVA) và các testing arms EP/BVA/DT.
Default của pipeline vẫn là `plain`; `ep_bva` là cấu hình chính trong nhóm arm mới.

Các arm dùng chung `BenchmarkPipeline`, được chọn bằng `arms`. Runtime hiện chỉ
đọc `modular_manifest.json` và `modular_summary.json`; không fallback sang
`manifest.json`/`summary.json` của pipeline cũ.

## Saved inputs và evaluation — giản lược validation (17/11/2026)

Generation lưu inputs trước evaluation; không tạo `generation_frozen.json` hoặc quét source hashes. Manifest ghi task IDs, arms, settings, model và môi trường thực tế; không dùng để reject vì khác run cũ. Treatment/concept diagnostics của `MethodInputGenerator` không chặn evaluation.

Rescore đọc input hiện có, giữ nguyên labels/config metadata mà không khởi tạo generator cũ hay model. Không ép input count theo budget generation cũ. Rescore phải dùng output directory mới ngoài source run. Input sai literal/signature/type/domain được ghi rejection, không tính thành detection và không làm fail cả task. Sandbox, timeout, reference stability và confirmation vẫn giữ.

`--mode replay` và rescore `--replay` chỉ đọc per-task `result.json` rồi tổng hợp counts; không chạy generation, reference hoặc PUT, không so với summary/hash cũ. Union đọc `result.json`, `oracle_valid.json` và evaluation observations để tính unique PUT/input attribution, kinds và comparisons. Các summary này mô tả lần evaluation đã lưu; sửa `inputs.json` không tự thay outcomes cũ.


## Hướng phát triển từ V2 — quyết định 17/11/2026

Giữ `ep_bva_v2` và `decision_table_v2` làm nền cho bước tiếp theo. Saved Gemini
comparison cho thấy feedback hiện tại dùng 2,41 lần known tokens của V2 nhưng
chưa vượt V2 về tổng PUT detections; sửa interface không chứng minh tăng chất
lượng test. Chi tiết: `final/out/gemini_replacement_gate_recovery_20261117_145702/FEEDBACK_V2_VF3_COMPARISON.md`.

Bước đầu chỉ dùng ablation có sẵn `CatalogueSettings(catalogue=False)` / CLI
`--catalogue-off`: giữ V2 technique guidance, fault-oriented reasoning guidance,
soft examples và public visibility; model chỉ cần trả `inputs` với named
`arguments`. Không yêu cầu catalogue, executable predicates, `covers` hoặc
fault-hypothesis annotations. Đây là ablation của V2, không phải method mới.

So với V2 gốc, chỉ đổi yêu cầu output catalogue. Giữ một call/task/arm, cùng
input budget, model, context/completion cap, sampling, frozen data, reference và
scorer. Không giảm token cap cùng lúc để tránh lẫn hai nguyên nhân. `catalogue=off`
nghĩa là concept guidance vẫn có, nhưng mechanical concept coverage không được đo;
không báo coverage là 0% hoặc 100%.

Đánh giá bằng union PUT detections ngoài baseline, gained/lost PUT, wrong-value,
exception/resource, valid inputs, calls và tokens thực tế. Một input mới hữu ích
chưa đủ chứng minh cải thiện ổn định; không mở rộng cohort hoặc retune trên các
PUT vừa biết lỗi để cứu một kết quả yếu. Giữ raw responses và source provenance.

Chỉ thêm feedback sau khi bước đơn giản có evidence: một thay đổi/lần, một gap
cụ thể gắn với kỹ thuật kiểm thử và evidence được kiểm tra, output tiếp tục chỉ
là inputs. Metadata không chặn input hợp lệ; oracle vẫn sau generation. Không nối
replacement/Obligation/CF thành một pipeline mới trong bước này. Các cơ chế đó
và checkpoint lịch sử vẫn giữ để đối chiếu.

Chưa launch run mới. Preparation và prompt check ở
`final/review/v2_inputs_only_20261117.json`; cần snapshot cùng data/reference của
baseline và independent review trước khi người dùng quyết định chạy.

```text
frozen PUT cohort → input preparation → input generation
→ lưu inputs → reference/domain checks
→ catalogue measurement (EP/BVA/DT) → PUT evaluation → report
```

## Code ở đâu

| Module | Trách nhiệm |
|---|---|
| `pipeline.py` | Điều phối generation/evaluation, ghi manifest và run lock |
| `generators/` | Interface sinh input có thể thay thế; đọc saved inputs hiện có |
| `__init__.py` | Registry chọn arm cho CLI và pipeline |
| `plain/` | Naive baseline sinh input trực tiếp |
| `common/` | Interface và cơ chế chung cho các arm dùng model |
| `control_flow/` | ControlFlow và biến thể 4-tool dùng chung engine C1/C2, Hypothesis và coverage feedback. [Contract và budget](control_flow/README.md) |
| `tool_sampling/`, `pynguin/` | Generator, cấu hình và logic riêng cho từng hướng tool |
| `spec_obligation/` | CF Obligation Repaired. [Protocol](spec_obligation/README.md) |
| `black_box/ep_bva.py`, `black_box/decision_table.py` | Guidance, schema catalogue và nội dung feedback riêng của từng arm |
| `black_box/vf3_hybrid.py`, `black_box/vf3_hybrid_schema.py` | Engine VF3 hai lượt và schema response dùng chung |
| `black_box/catalogue.py`, `black_box/catalogue_membership.py` | Kiểm tra catalogue, đo coverage class, boundary, rule và đối chiếu covers |
| `black_box/catalogue_response.py` | Đọc JSON catalogue và phục hồi các input record đầy đủ khi response lỗi format |
| `catalogue_reporting.py` | Report tiếng Việt, matched-budget comparison và token accounting theo arm |
| `call_builder.py` | Encode named arguments thành Python literals |
| `../benchmarks/datasets.py`, `cohort.py` | Load specs/domain metadata/references và frozen PUT cohort |
| `references.py` | Chọn corrected HumanEval+ reference |
| `reference_oracle.py` | Kiểm domain, chạy reference lấy expected output |
| `put_evaluation.py` | Chạy PUT một lần; hỗ trợ `confirm_first_failures` và `full_two_repeats` |
| `../runtime/execution.py` | Tạo subprocess và sandbox `bwrap` |
| `../runtime/worker.py` | Load Python function và gọi bằng `args`/`kwargs` |
| `../models/model.py`, `../models/vertex.py` | Qwen transport và LangChain Vertex AI; CLI chọn `--model-backend qwen\|vertex` |
| `../runtime/checkpoint.py` | Ghi request/response và giữ lịch sử retry |
| `calls.py` | Adapter `RecordedModelCalls` / `CachedModelCalls` cho pipeline |

`prompt + canonical_solution` tạo thành reference source hoàn chỉnh. Worker load
source bằng `compile`/`exec`, lấy function theo `entry_point`, rồi gọi với input.
Reference source và output chỉ được dùng sau input freeze.

PUT evaluation dừng sau lần đầu nếu input pass. Input fail/error/timeout được
chạy lại cùng seed; chỉ tính detection khi lần hai cũng fail/error/timeout.
`outcomes.retested` lưu index gốc của các input chạy lại, theo thứ tự kết quả
trong checkpoint `evaluation/<program_id>_retry_1.json`. `unstable` chỉ kiểm tra
status thay đổi trong nhóm này; input pass lần đầu không được kiểm tra stability.
Reference/domain checks vẫn chạy hai lần cho mọi input.

Mỗi input của reference và PUT chạy trong một sandbox riêng.

## Chạy

```bash
final/.venv/bin/python -m final.src.modular.run --mode run \
  --cohort final/out/cohorts/qwen35_27b_humaneval164/cohort.json \
  --artifacts final/out/plain_ep_dt_v2 \
  --arms plain ep_bva_vf3_hybrid decision_table_vf3_hybrid --input-budget 20
```

Transport đọc configuration từ environment hoặc private env file hiện có.
`--mode replay` là default và chỉ đọc artifacts của một run khớp source/settings.
CLI không còn các option concept/V11 hoặc legacy adapter.

## Testing arms EP/BVA/DT

Các arm dùng chung visibility, input budget, CallBuilder, freeze, corrected
reference và scorer. Mỗi task/arm có tối đa một generation
completion, không có feedback loop. Guidance kỹ thuật dài không quá 8 dòng;
schema catalogue và shared input instructions là phần riêng.

| Arm | Vai trò |
|---|---|
| `ep_bva_v2` | Behavioral equivalence classes và boundary values, với fault hypotheses |
| `decision_table_v2` | Boolean conditions và feasible rules, với fault hypotheses |

Các arm EP, BVA và DT v1 cùng `boundary_value_analysis/` cũ đã được gỡ bỏ khỏi codebase.

Decoder catalogue giữ inputs hợp lệ khi catalogue thiếu/sai, ghi
`catalogue_invalid` thay vì loại toàn response. Expected outputs chỉ do reference
cung cấp sau freeze. Các selector máy đọc được gồm parameter value, length,
count và parsed int/float; float neighbor dùng `math.nextafter` khi không có step
theo spec. Pydantic kiểm schema; `itertools` xử lý combinations/products có cap.
Không dùng solver trong catalogue measurement. Boolean input predicates của model
được kiểm bằng bounded membership evaluator hiện có; extended expressions chạy
trong sandbox, không gọi PUT/reference hoặc dùng expected outputs.

`catalogue_measurements.json` thêm `observed`: EP dùng class `predicate` hoặc
input selector/members/interval cũ; DT dùng `condition_predicates` (condition ID
→ boolean expression trên đúng tên parameters), với condition values là boolean
hoặc `T`/`F`. Điều kiện nhiều giá trị chưa hỗ trợ được ghi `unknown`. Original
rule coverage dùng declared feasible `original_rules`; khi không có metadata
merge, unmerged rules có thể làm originals. Không suy feasibility từ predicate.
BVA kiểm từng target value trong đúng context; boundary chỉ `hit` khi đủ target
values, còn single-fault/nominal được đo riêng trong các field cũ.

Mỗi obligation có `hit/miss/unknown`, `input_indices` trong danh sách survivors
và `source_input_indices` trỏ về index trong batch inputs của arm. `label_checks`
ghi covers sai, covers chưa kiểm được và hits chưa khai. Summary đếm obligations,
không phải inputs; thiếu original denominator ghi null. Predicate lỗi/unsupported,
selector không đọc được hoặc hết budget ghi unknown, không gộp vào miss.
Budget mỗi task/arm: tối đa512predicate checks, ngừng bắt đầu check mới sau5giây;
extended sandbox call đang chạy có timeout riêng2giây. Cache condition checks
để không evaluate lại cùng expression/input. Base coverage vẫn pending.

VF3 giữ nguyên guidance, soft example và fault-hypothesis note của v2. Schema
chấp nhận và lưu annotation. Prompt chung giữ đủ visible PUTs, kể cả khi chỉ
chạy Plain. Arm dùng prompt chung báo `prompt_too_large` nếu vượt giới hạn.
Lượt feedback của VF3 dùng lại toàn bộ prompt ban đầu và cũng báo
`prompt_too_large` nếu vượt giới hạn.

VF3 (`ep_bva_vf3`, `decision_table_vf3`) dùng JSON Schema qua transport có sẵn,
không sửa notebook hoặc cài decoder. Mỗi lượt có budget cố định 20 input. Lượt
feedback bổ sung input mới, đưa trần tổng lên 40 input mỗi task mỗi arm.
Input xác định trùng cohort base_input_keys hoặc input đã retained bị loại trước coverage/quota.
Plain vẫn20inputs. VF4 đã retired15/11/2026; implementation không còn trong active source. Feedback chỉ có trusted
domain admission và membership, không PUT/oracle outcomes. Valid target definitions
được giữ; model đề xuất đổi nghĩa sẽ bị từ chối, nhưng inputs mới hợp lệ vẫn giữ.
Vòng feedback nhận lại public assistant response, kể cả metadata parse lỗi, và
mapping `covers` của retained inputs. Contract yêu cầu lý do cho unresolved/not_applicable;
unresolved không được báo membership_ready. Predicate có checker exception trên input
đã admitted được phép repair; unmeasured/budget unknown vẫn được bảo vệ. Description/
fault hypothesis có thể được sửa mà không đổi predicate/boundary/rule đã đo hợp lệ.
`condition_checks` là diagnostics riêng, không thêm coverage objectives không có căn cứ.

VF3 argument schema dùng annotation hiện có: integer±2^32, list<=30items,
string<=1000characters; kiểu chưa hỗ trợ dùng generic JSON và validation sau decode.
Đây là generation limits, không phải spec/domain boundaries. EP bắt buộc executable
predicate. BVA context/nominal bị khóa theo tên parameters; unsupported selectors
và semantic grounding vẫn phải report riêng, không coi schema là bằng chứng đúng spec.

Treatment gate giữ riêng readiness của method: `spec_obligation` phải trả
`obligations` hoặc explicit reason cho empty result; native observation trên ít
nhất một candidate hợp lệ mới cho `measured`. Không có obligation/native evidence
thì inputs vẫn được lưu để chẩn đoán nhưng treatment không được báo `applied`.
`context:null` chỉ chuẩn hóa thành `{}`; không tạo metadata còn thiếu. Đây là
readiness gate, không phải semantic bug proof hoặc superiority claim.

Ngày15/11/2026, shared prompt và soft BVA khôi phục wording nhỏ/bounded từ Git,
bỏ lời gợi ý large inputs/PUT timeout và câu numeric cap trong prompt. Schema cap
ở trên vẫn giữ; wording cũ “execution under 3 seconds” là hướng dẫn generation,
không đổi native timeout8s. Frozen runtimes/results lịch sử giữ nguyên.

Ngày17/11/2026, user yêu cầu gỡ VF3 replacement và DT prompt rollback.
Implementation, CLI/Prefect allowlist, factories và launcher của hai hướng đã gỡ;
VF3 append catalogue (`ep_bva_vf3`, `decision_table_vf3`) vẫn giữ20+10.
Historical output/checkpoint/source snapshots và read-only comparison readers
vẫn giữ. Các hướng VF4, validated V2, Simple discovery và Native Tool Agent đã
retire từ trước, không có active implementation để khôi phục. Control-flow,
spec obligation, LargeInput và Pynguin chưa được user chọn xóa. Chi tiết phạm vi,
kết quả và lý do: [cleanup log](../../review/retired_arms_cleanup_20261117.md).

DT VF3 chọn số conditionsC1..Cn theo spec, không có hard cap số conditions.
Table object phải có tất cả2^nrowsRbits, được local validator kiểm tra
(R01=C1false,C2true). LLM viết predicate/action/feasibility/reason; code dựng
Boolean assignments và legacyoriginal_rules/rules views. Không có hai bảng
độc lập hay redundant model exclusions để mâu thuẫn nhau. JSON Schema đảm bảo row shape; local validation kiểm tra tên/bit-width/đủ combinations.
Completion token budget vẫn giới hạn độ dài thực tế; bảng lớn có thể thiếu hoặc truncate,
được báo metadata error và có tối đa một lượt repair; không claim catalogue bao hết spec.

Coverage hiện chỉ dùng **novel inputs đã qua domain/reference**. `covers` là
self-report, không phải chứng minh class membership. Mechanical checks chỉ đo
phần có metadata đủ; prose, tính đầy đủ/rời nhau của partition, semantic grounding
và base-call coverage còn `pending`. DT coverage dùng feasible rules gốc;
merged rule ID không tự phủ tất cả original combinations. `budget_limited`
được tính khi declared design/Cartesian size vượt input budget; thiếu dữ liệu
để tính thì giữ `pending`, không suy ra từ coverage thấp. Xem
[plan](../../PLAN_TESTING_ARMS.md) và [PREREG](PREREG.md) trước run mới.

`bva_robust` chỉ gọi model nếu metadata của task có
`testing_arms.out_of_domain_behavior_defined=true` và `testing_arms.spec_evidence`
không rỗng. Không có eligibility này thì `not_applicable` và không gọi model;
shared domain/reference vẫn kiểm mọi generated input.

CLI tự chọn completion cap **4096 tokens/call cho toàn comparison có arm mới**,
hoặc 2048 cho plain/soft BVA cũ; override bằng `--input-tokens` và
`--context-tokens`. `--catalogue-off` là instruction-only ablation, giữ cap chung
và không được xem là technique coverage đã kiểm. Trên console, cùng setting là
`catalogue=false`. Các preset mới ở [run console](../orchestration/README.md)
đã có config offline; người dùng quyết định bấm Run. Phiên implement này chưa
launch experiment/evaluation/inference.

## Input generation và reference

Inject `InputGenerator` hoặc truyền các method bằng `arms`. Interface và ví dụ ở
[generators/README.md](generators/README.md). Method dùng chung base class
`InputGenerationMethod`; optional input annotation là `guidance_id`.

Corrected references mặc định là HumanEval+ v0.1.10, chỉ gồm reference source và
metadata, không chứa hidden input arrays. Xem [reference data](../../data/references_README.md).
`TaskReferencePrograms` chỉ dùng khi được truyền tường minh cho diagnostics hoặc
synthetic fixtures. Rescore giữ nguyên các input đã freeze:

```bash
final/.venv/bin/python -m final.src.modular.rescore \
  --source-run <saved-run> --cohort <cohort.json> --artifacts <new-output>
```

## Sandbox và checkpoint

Mỗi input được thực thi trong sandbox mới. Run mới và rescore tự thực thi reference
và PUT. Resume dùng lại checkpoint của run nguồn. Replay đọc kết quả đã lưu.

## Kiểm tra

```bash
final/.venv/bin/python -m pytest final/src/modular/tests -q
```

Tests bao gồm sandbox execution, plain/BVA integration, corrected references,
freeze barrier, cache invalidation/reuse, manifest drift, read-only replay và
transport/retry. Dependency test chặn import historical research packages để bảo
đảm pipeline hiện tại chạy độc lập. Results/checkpoints cũ được giữ để truy nguyên. Code concept và baseline cũ đã
được gỡ; chỉ còn một runtime cho pipeline hiện tại.


## V2: behavioral rules, Fault Hypotheses và soft examples

`ep_bva_v2` và `decision_table_v2` ghép guidance mới với1soft example/technique.
V1giữ làmcontrol. Examples productionpackaging/Werkzeug có provenance và
verification ở[nguồn examples](../../research/testing_arm_examples/README.md).
Fault Hypotheses làoptionalannotationclass/rule,không phảiconfirmedbug hoặc
executablepredicate. Input expectedoutputs vẫn do correctedreference saufreeze.

Userchọnsmoke6fourarms24logicalcalls,20inputs/task/arm,completion4096/context8192,
nativetimeout8. Followup chờ BOTHfullruns hiện tạiCompleted vàverifiedevaluation/
source/replay;frozenJSON+code snapshot trướcwait,khônggọi model khiwait. Source
prompts v1không đổi;comparison đo cảinstruction+examples,khôngisolatehypothesis.
Xem[planv2](../../PLAN_TESTING_ARMS_V2.md) vàPREREG trước kết quả mới.

## Tool sampling EP/BVA/DT (opt-in)

`ToolInputGenerator` dùng shared catalogue/membership, candidate ledger và Hypothesis.
Planner `allpairspy` đề xuất tổ hợp. Hypothesis tìm concrete input cho các tổ hợp đó.
Các artifact sau freeze ghi nhận selection loss. Template budget nằm ở
[`tool_sampling.example.json`](../../presets/tool_sampling.example.json).
[Cách gọi, artifacts và giới hạn](../../../research/testing-tools-ep-bva-dt-2026-11-09/IMPLEMENTATION.md).

### Independent signed target controls

`ToolInputGenerator(..., semantic_controls=<task-ID → signed controls>)` và CLI
`--tool-config` nhận optional `semantic_controls`. Khi supplied, mọi target phải
qua independent positive/negative membership checks trước freeze/reference/PUT;
missing/unknown/mismatched controls fail gate. Infeasible target không cần fake
positive; full-domain target không cần fake negative nhưng phải có explanation.
Không truyền controls thì legacy protocol vẫn chỉ mechanical/domain checks,
không được báo thành target-semantic validation. Controls/provenance nằm trong
manifest configuration; labels vẫn finite evidence, không phải semantic proof.
Generic helpers thêm distinct_count, bounded sequence membership/type/stride/
congruence và overlap; không có task-ID dispatch trong checker/constructors.

### Membership Python riêng cho tool arms

Protocol `tools-ep-bva-dt-v5-python-membership` giữ helper DSL cũ làm fast path và
nhận thêm Python expressions: `all/any`, generator/list comprehensions, slicing,
`isinstance/type`, arithmetic và các public methods không mutation như
`s.isupper()`/`s.startswith(...)`. Extended expressions chỉ chạy trong persistent
**bwrap subprocess**, không eval trong host: không network/host home/secrets,
clean environment, 256 MiB memory, 100 ms/request alarm và 2 giây parent wall
budget bao gồm pipe write/read. Timeout/runtime error là unknown/error, không
được biến thành false hay coverage. Output bắt buộc exact bool.

Trusted admission compiler và legacy bucket DSL dùng phạm vi cú pháp riêng.
Unsupported target lưu source và error. Selector ưu tiên target có membership
đã kiểm được. Independent signed controls yêu cầu kết quả membership cho từng
target được kiểm tra.

`response_audit` phân biệt preparation dùng được một phần với fully_supported.
Cache protocol mới ngăn replay bằng semantics cũ. Prompt text không đổi; snapshot
run đang chạy không bị patch. Chỉ sửa code không tự cấp quyền rerun experiment.

## Source-bound obligation arms — 2026-11-13

Chọn `control_flow_obligation_v1_repair` để dùng bản repaired lấy từ worktree.
[Protocol hiện tại và lịch sử](spec_obligation/README.md).


## LargeInput stress arm

`large_input` dùng một model call/task, sinh input stress trong contract; không catalogue
hoặc feedback từ PUT. Numeric magnitude cap2^32, string/container length cap1000,
cap nhỏ hơn trong spec/contract luôn ưu tiên. Lọc literal/cap và supported-domain trước
freeze; contract unsupported giữ unknown, không claim valid. Chỉ input qua hai lượt
independent reference/domain checks mới đến PUT scoring. Defaults20inputs/task,
không refill hoặc tự mở budget khi model trả ít input. CLI dùng `--arms large_input`;
backend/model được truyền qua `--model-backend vertex --model-name gemini-3.1-flash-lite`.
Không tự đổi default arm hoặc sửa VF3.

Resource accounting phải đếm mọi confirmedresourcewitness, kể cả PUT đồng thời có
wrong-value/crash; report thêm strict both-resource và subtype. Reference accepted
trong cùng limits không chứng minh asymptotic complexity/time ratio. Full run được
người dùng cho phép15/11/2026 dùng frozen cohort/reference cũ và runtime riêng;
workspace hiện có thể có reference mới, nên comparison tiếp cần pin source rõ ràng.

Catalogue reflection (`ep_bva_reflection`, `decision_table_reflection`) dùng2calls/task và cùng final input budget: catalogue + public rationale + initial inputs ở lượt1; exact history + checklist bắt buộc theo slides ở lượt2,chỉ output final inputs. Không tool/oraclefeedback trước freeze;metadata thiếu/sai không block validinputs. Semantic compliance chưa được kiểm chứng độc lập. [Nguồn và giới hạn](../../../research/catalogue-reflection-2026-11-17/README.md). `scripts/prepare_catalogue_reflection.py` chỉ prepare full157snapshot; chỉ launch khi user yêu cầu. Recovery giữ calls/attempts cũ và không import parsedinputs sai.

`ep_bva_catalogue_then_inputs` và `decision_table_catalogue_then_inputs` tách design và instantiation: lượt1 chỉ catalogue + public rationale; lượt2 nhận nguyên history để sinh final inputs theo weak EP + normal BVA hoặc DT cơ bản. Không V2 fault hypotheses/soft examples hay tự review suite cũ. Accidental inputs ở lượt1 bị bỏ, chỉ lượt2 đi qua decoder/CallBuilder/domain/oracle hiện có. Hai calls/task/arm, final budget không tăng; catalogue sai chỉ diagnostic, semantic compliance chưa được kiểm chứng. Preset mới trong `final/presets/run_console.json` mặc định preview; chưa register hoặc launch. Model theo console hiện tại.
