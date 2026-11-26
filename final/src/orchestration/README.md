# Local run console (Prefect)

> Cập nhật18/11/2026: bộ chính giữ `ep_bva_v2`, `decision_table_v2`, `control_flow` gốc và `plain`. Đã gỡ VF3, reflection/catalogue→inputs, spec-obligation, LargeInput, Data-flow arms và HumanEval-X adapters khỏi đường chạy hiện tại. Shared pipeline, Pynguin thuần/tool pipeline, HumanEval Python/MBPP và historical outputs/checkpoints vẫn giữ. Nội dung bên dưới về các hướng đã gỡ chỉ là lịch sử; không dùng để launch mới.


This uses Prefect's existing web UI, parameter forms, deployments, scheduler,
SQLite history, logs and artifacts. The adapter launches the existing benchmark
with the dedicated `final/.venv` Python; Prefect lives in `.venv_orchestration`.
Starting the server or registering/importing presets makes **zero LLM calls**.

```bash
./final/run_console.sh start
./final/run_console.sh status
./final/run_console.sh reload-presets
./final/run_console.sh clean-stale-history
./final/run_console.sh stop
```

Open <http://127.0.0.1:4200/deployments>. Select a deployment, choose **Run**, edit
parameters and launch now or schedule a custom run. The server and preset listener
must remain running. With no arguments the script defaults to `start`; missing
orchestration dependencies are installed into their separate venv.

## Presets

Presets are stored in `final/presets/run_console.json`. Registration resolves all
defaults into deployment parameters, so queued runs retain their exact values.

| Preset | Allocation | Maximum calls |
|---|---|---:|
| `Full164 · Plain vs EP+BVA v2 vs DT v2 · batch` | 20 inputs/task/arm, 4096 completion tokens/call | 471 |
| `OpenRouter Flint · Plain · HumanEval 0` | 20 input, 4096 completion token/call | 1 logical call |
| `Resume · Tiếp tục run đã dừng` | Continue a stopped Console run with supported arms | Missing slots only |

Preset Full164 mặc định bật `preview_only`. Các preset BVA, EP và DT v1 đã
retire. Lịch sử của chúng vẫn tra cứu được trong Prefect và từ saved artifacts.

Tên run hiển thị scope, arm và kiểu generation; historical run hoàn tất có thêm
số PUT detected. Source directory, JSON fields và flow-run ID giữ nguyên khi đổi
tên. `names.py` quản lý nhãn; run preview có prefix `Preview`. Trang Runs:
<http://127.0.0.1:4200/runs>. Prefect không hỗ trợ rename deployment qua update API
ở version hiện tại; thay tên preset cần đăng ký deployment mới và gỡ bản tên cũ
sau khi kiểm tra parameters/schedules và không có managed run đang hoạt động.

`preview_only=True` creates budget/config artifacts without a model, tokenizer or
native call. Use it to inspect budgets. `preview_only=False` starts real work when
you press Run. No agent launches a new model experiment merely by creating a preset.

Preset Flint chọn `model_backend=openrouter` và `recursive/flint-v1.0:free`,
bật reasoning và khóa provider ở `recursive/bf16` với `allow_fallbacks=false`.
Worker lúc Run nạp key từ `scripts/openrouter_env.sh`. CLI dùng
`--model-backend openrouter` sau khi source script trong shell. Checkpoint
lưu `reasoning_details` để lời gọi tiếp theo dùng `response.assistant_message()`.

## Settings and reproducibility

Forms expose cohort, task subset, mode, arms, inputs/task, output/context tokens,
temperature, generation/reference seeds, native timeout, served model name,
scorer and `catalogue`. Batch supports `plain`, `control_flow`,
`control_flow_4tool`, `control_flow_obligation_v1_repair`, `ep_bva_vf3_hybrid`
and `decision_table_vf3_hybrid`. ControlFlow xếp toàn
bộ target vừa context vào các prompt tối đa sáu target. Với run có ControlFlow,
preview hiển thị `pending` cho tổng logical call và tổng completion token vì
số batch phụ thuộc context thực tế.
Tools and Pynguin have their own modes.
The output token limit is **per call**, and input budget is **per task per arm**.

Hai arm EP+BVA v2 và DT v2 dùng chung visibility, CallBuilder, freeze, reference
và scorer. Mỗi arm sinh catalogue và inputs trong cùng một completion cho mỗi
task. `catalogue=false` là instruction-only ablation và giữ nguyên token cap.

Catalogue sai/thiếu không loại input hợp lệ. Measurement chạy sau global freeze
và domain/reference, trước PUT evaluation; expected outputs vẫn chỉ lấy từ
corrected reference. Declared coverage dùng `covers` của novel valid inputs,
là self-report; mechanical checks cần metadata máy đọc được. Prose, semantic
audit, partition exhaustiveness/disjointness và base-call coverage còn `pending`.
DT denominator là feasible original rules; merged ID không tự phủ mọi original
combination. Strong EP/worst-case BVA có Cartesian cap; `budget_limited` chỉ tính
khi declared design size biết được, feasibility còn `pending`.

Every real run gets a new directory under `final/out/console_<flow-id>/run`:

- Immutable resolved `config_snapshot.json`, offline budget preview and cohort hash
- A read-only snapshot of executing code/data, isolated from future worktree edits
- Registered requests/responses, retry/unknown history, input freeze and native checkpoints
- `status.json`, `progress.json`, `worker.log`, summary and result digest
- Source checks and immutable replay before a successful final status

The runtime's current conditional confirmation scorer and the historical
full-two-repeat scorer are separate explicit options. Both arms of a paired run
always share the chosen scorer. Native jobs use the existing shared execution lock.
The preset listener permits one run at a time and waits for existing external
model writers; this does not take ownership of the already running external batch.

Changing a preset never changes an already submitted run's parameters or snapshots.
After editing the preset JSON or runner code, run `./final/run_console.sh reload-presets`.
It refreshes UI forms/defaults without restarting Prefect's history server; it refuses
while a console-owned flow is queued/running.

## Stop/resume

Use Prefect's **Cancel** for a Console-owned run. Saved responses/checkpoints and
attempt caps remain. Then launch **Resume · Tiếp tục run đã dừng** with the source artifact
directory (`.../console_<id>/run`, not its parent submission directory).
Do **not** use generic Prefect Retry on the same flow ID: snapshot directories are
intentionally immutable. Resume creates a new output and preserves the old one.

Original matched-batch outputs are also supported. A live worker lock blocks
resume. Stale running status after process death can be recovered only with a
free worker lock and a worker-start marker, recorded explicitly in import receipts.
Per-request transport attempts are never reset; received responses are never
regenerated. Path-only reference/identity metadata is rebuilt in the new runtime.

## Historical runs

Để chạy lại **native evaluation** của saved Gemini Plain + EP/BVA V2 + DT V2,
không gọi LLM hoặc sinh lại inputs:

```bash
scripts/reevaluate_plain_ep_dt_v2.sh \
  --output "final/out/reevaluate_plain_ep_dt_v2_$(date +%Y%m%d_%H%M%S)"
```

Mặc định source là `final/out/gemini_catalogue_full164_20261112_193646`;
`--source <run_directory>` chọn run có đúng ba arms đó và task receipts đầy đủ.
Mỗi invocation cần output mới. Script snapshot evaluator/reference hiện tại,
giữ dataset/contracts và inputs gốc, dùng cache mới trong output để chạy lại
reference/PUT; không copy evaluation/cache cũ. Sau mỗi task kiểm read-only replay,
report valid inputs, detected PUT, wrong-value/exception/resource và union.
Prefect local phải đang chạy; flow ID, progress, config và report được lưu cùng
output. Link trực tiếp được in khi hoàn tất. Script không cần API key của LLM.
Reference disagreements vẫn có thể gồm oracle false positives đã biết.

Existing BVA/prompt-style/naive/rescore outputs are indexed read-only into Prefect,
tagged `historical` and `read-only-index`. Config/result/progress/report artifacts
come from their saved files; indexing does not replay or execute the experiments.
They are not owned by Prefect, so use the existing process/checkpoint mechanisms
to control them. Their original directories stay unchanged.

If the historical table needs pruning, `clean-stale-history` makes a timestamped
metadata backup and removes only imported Prefect rows in Failed/Pending whose
source directories are stopped (`interrupted`/`prepared`). It leaves every source
artifact/checkpoint on disk and records a suppression entry so the watcher does
not reimport those rows. It does not clear managed Console runs or an active worker.

UI/server state: `final/out/run_console/prefect_home` (SQLite), logs and process
receipts in `final/out/run_console/`. Persistence is local, with no cloud account.
The service binds only to `127.0.0.1`.

## Endpoint/credentials

The local profile remains outside the repo:
`~/.config/concepttester/final-qwen.env`. Each run copies its routing/credentials
to a unique private file under `~/.config/concepttester/run-endpoints/` (0600).
URLs/API keys never enter Prefect parameters or config snapshots. Resume reads the
current local profile into a new private routing snapshot; benchmark settings stay
unchanged. Update the local profile before resuming if the notebook endpoint moved.

## Validation

```bash
final/.venv/bin/python -m pytest -q final/tests/test_orchestration.py
```

The UI smoke test uses preview-only mode; it makes no model or native calls.


## User-authorized full testing-arms run — 2026-11-09

User yêu cầu full EP+BVA và full Decision Table. Config dùng chung ba arms
`plain`, `ep_bva`, `decision_table`, HumanEval164/157eligible tasks/1454base-pass
PUTs,20inputs/task/arm,4096completiontokens/call,8192context;471logicaltester
calls/9420input slots. Shared Plain baseline giảm từ628 xuống471logicalcalls so với
hai comparison riêng. DT applicability/schema/semanticpending báo riêng,
không claim mọi full task có DT conditions phù hợp. Xem PREREG amendment.

Preset JSON full mới đã chuẩn bị; khi listener đang xử lý managed run khác,
không reload hoặc dừng nó. Run mới được queue bằng deployment generic đang
served với explicit full parameters; Prefect serve limit1 giữ thứ tự, tên run
được cập nhật theo config khi start. Source snapshot được tạo lúc worker nhận
run trước generation. Reload preset JSON mới khi tất cả managed runs kết thúc.


Routing correction2026-11-09: user providedtwo independent servers and asked the
shorter Direct/Soft run to use the new private route. Full3armrun uses its own
privateprofile onoriginalserver. `dispatch --flow-run-id` can claim an unstarted
scheduled record atomically and run it with the same Prefect ID in a dedicated
process. It refuses existing output/startedrecords/rejectedclaims. Generation
wait compares actual private endpoint identities (including nestedconsoleworker
statuses);same/unknownroutes remain serialized,independentroutes may generate
inparallel. Nativeevaluation sharedlock remains. No endpoint selection option is
exposed in UI, and URL/key never enter Prefect parameters/artifacts.


Native timeout default được user đổi thành **8giây/input** ngày2026-11-09.
Continuation có thể truyền `timeout_seconds=8` cho resume flow;chỉ cho phép
amendment khi source chưa có native checkpoints. Newoutput ghi config8/preview
vàamendmentreceipt;source3s/receivedcalls giữnguyên,rootmanifestrebuild. Profile
endpoint lấy đúngprivate route của source khi dedicateddispatch. Không retune
prompt giữa generation;sourceprompt nhắc3s vẫngiữ,executionbudget thực8s.


## Delayed v2 smoke theo user request

`followup.benchmark_after_predecessors` nhận predecessorflowIDs vàresolvedbenchmark
parameters. Nó prepare immutableworker/config/cohort/exampleJSON/privateendpoint
ngay rồichờ30s/poll;không model/tokenizer/nativecalls trước BOTHCompleted vàsaved
finalevaluation/source/replayproof. Progressartifact cậpnhật cùngID. Predecessor
failed/cancelled/crashed hoặcCompletedthiếuproof làmfollowupfail/block,chưa
launchworkload. Dedicateddispatcher dùng samefollowupID;không tạochildflow.

Smokeđãđăngký:6tasks/onePUTeach,fourarms ep_bva/ep_bva_v2/decision_table/
decision_table_v2,max24calls/480records,4096completiontokens/call,timeout8s.
Đây làlệnh userchạy saufulls,khôngphảiautoexpand benchmark.


## Controlled Plain-guidance rerun và V2 overlap

`rerun.plain_guidance_rerun(baseline_packet_source)` tạo baseline mới từ completed
Direct source: copy nguyên frozen runtime và public visibility packets, giữ
completion cap2048, seed/sampling/inputbudget20/native8; chỉ đổi arm/guidance sang
Plain. Không import generation responses, generated inputs hoặc oracle outcomes.
New snapshot bỏ hash stale runtime, ghi hash byte-identical clone/packets và
preparer source. Actual request vẫn được tokenizer kiểm trước completion.

`resume_after_baseline_generation(source_directory, baseline_flow_run_id)` clone
stopped V2 source và giữ received responses/retry ledger. Nó chờ global input
freeze được kiểm hash và baseline thật sự ở evaluation (hoặc verified Completed)
rồi mới tiếp tục V2 generation. Vì vậy GPU generation của V2 có thể chồng thời
gian với CPU evaluation của baseline; native lock vẫn serialize native workloads.
Failed baseline chặn V2; Running-before-output-exists tiếp tục wait. Không thêm
option chọn endpoint, routing vẫn nằm trong private profile.


Combined run `ep_dt_bva` (user2026-11-09) là **một arm một completion/task**:
EPclasses→DTconditions/rules→normalBVAclassedges,cùngcatalogue3sections và một
inputlistbudget20. Khác với unionevaluation pool60/task từ3generators độc lập.
Fullpreset `Full164 · EP + Decision Table + BVA · single combined arm` nằmtrong
presetJSON;runregistered standalone cùnggenericbenchmarkflow,khônglaunchPlain
control mới,max157generationcalls/4096completion/timeout8.

## Full v2 có giờ bắt đầu sớm nhất

Followup nhận optional `not_before_utc` (ISO timestamp có timezone). Snapshot
code/config/cohort/examples/private route được chuẩn bị ngay; workload phải chờ
**cả deadline lẫn predecessor Completed đã verify evaluation/source/replay**.
UI run là Running/Waiting trong lúc chờ; giờ workload nằm trong parameter và
followup progress. Không gọi tokenizer/model/native trước khi gate mở. Deadline
chỉ là mốc sớm nhất: nếu v1 chậm hơn estimate, v2 tiếp tục chờ; v1 failed thì block.

## Tool sampling (implementation 2026-11-10)

Form hỗ trợ `mode=tools`, các arm `tool_direct`, `tool_hypothesis`,
`tool_hypothesis_extra`, `tool_planner` và object
`tool_sampling` gồm explicit budgets + cùng danh sách arms. Preview tính **một
preparation call/task dùng chung**, không nhân theo số sampler. Suite ≤20,
`audit_cap` ≥ suite cap, scorer `confirm_first_failures`. Chưa chọn budget/preset,
chưa reload listener hay tạo run trong phiên implementation.
[Cách gọi và giới hạn](../../../research/testing-tools-ep-bva-dt-2026-11-09/IMPLEMENTATION.md).


## Tool run có producer và CPU consumer chạy chồng lấp

`tool_overlap.py` dùng một producer gọi LLM tuần tự, lưu request/response/attempt
trước khi enqueue task. Một executor thread chỉ giám sát subprocess CPU riêng:
consumer dùng supplied preparation và gate, rồi freeze inputs của
**task đó** trước reference/PUT/audit và read-only replay. Producer tiếp tục
request task kế và không đọc outcomes. Đây là protocol freeze theo task, khác
với global freeze mặc định của `BenchmarkPipeline`; prompt/samplers không đổi.

Coordinator chạy từ immutable `worker.prepare` runtime, cwd/PYTHONPATH trỏ vào
snapshot; giữ native lock. Producer ownership lock lấy trước shared writes và
đến terminal state; duplicate không được overwrite run owner. Observer publish
progress/results/report trên cùng Prefect ID; unsupported/gate failures được
báo thật, metric chưa có pending. Chỉ launch khi user ra lệnh cho run cụ thể.

## Obligation arms — chuẩn bị 2026-11-13

Batch config nhận `control_flow` và `spec_obligation`, với preview cap2logicalcalls/task/arm. Ngày17/11/2026 user yêu cầu gỡ `control_flow_obligation` và evidence v5; registry/form/factory/preset không còn combined arm, generic retry reject arm đã retire. Preset `Full164 · Control-flow vs Spec obligations · chuẩn bị` gồm hai arms,20inputs/task/arm,4096completiontokens/call,8192contexttokens; full157eligible cap628calls và3140inputslots/arm. Đây là upper bounds, không usage/results. Chỉnh code/preset không reload listener hoặc launch workload.

Hai arm còn giữ dùng shared reference/PUT evaluator. Coverage/semantic membership ở generation không phải oracle verdict; unknown giữ riêng và applicability còn hypothesis. [Chi tiết protocol](../modular/spec_obligation/README.md). Endpoint dùng private profile ngoài repo qua `FINAL_ENDPOINT_ENV_FILE`; không đặt URL vào deployment parameters/artifacts. Chỉ chạy khi user ra lệnh hoặc tự bấm Run.

## MBPP adapter

Flow `MBPP inputs` dùng runner/snapshot riêng, tái sử dụng model checkpoint,
native lock và Prefect artifacts. Hai preset MBPP ở
`final/presets/benchmark_adapters.json` có `preview_only=true`, không tự gọi model.
Muốn Run phải nhập repository-local `candidate_path` với PUT complete-source JSONL.
Chưa có cohort thì metric là pending; không tự sinh PUT/copy reference/mutation.
Shared guidance EP/BVA/DT không thay đổi. `detected` là số PUT có reference
disagreement ổn định, không phải confirmed bugs.

## Pynguin baseline

`mode=pynguin` dùng external pinned interpreter, không model/tokenizer/endpoint.
Preset `final/presets/criteria_pynguin.json` giữ baseline preview-only. Search và
extraction dùng sandbox, shared native lock và regular-file bounded reader.
VF4 và mode hybrid/guided dựa VF4 đã gỡ15/11/2026; source/output/checkpoint lịch sử
được giữ, resume lịch sử cần dùng frozen runtime của run đó. VF3 không thay đổi.
Không register/reload listener hoặc launch workload khi gỡ implementation.


## Scenario-validated Control-flow — lịch sử, retired 14/11/2026

User đã yêu cầu bỏ validated v2 sau comparison. Registry/CLI/preview hiện chỉ giữ v1; cấu hình thử nghiệm trước đây dùng `control_flow_obligation_validated`,2logicalcalls/task,
20inputs theo cap arm. New optional native checker ghi operational witness, không
model-judged correctness. User-authorized three-variant Gemini comparison dùng
immutable original/v1/new snapshots và per-task overlap runner hiện có, index cùng
một matrix record bằng observer; union EP/BVA v2+DT v2 không Plain. Không reload
listener hoặc sửa các run khác đang hoạt động; private credentials vẫn ngoài artifacts.

## Retirement 2026-11-17

User yêu cầu gỡ `ep_bva_vf3_replace`, `decision_table_vf3_replace` và `decision_table_vf3_prompt_rollback` khỏi implementation/forms/factories. Historical artifacts vẫn đọc được, generic retry từ source dùng arm đã retire bị reject trước khi chuẩn bị output. Giữ CF/spec, LargeInput, Pynguin và VF3 append. Không reload deployment hoặc đổi run history trong cleanup code này. [Cleanup log](../../review/retired_arms_cleanup_20261117.md).

## Modular evaluation giản lược — 17/11/2026

Worker modular/tool overlap không chạy SourceGuard hay automatic full-pipeline replay sau evaluation. Receipt fields `source_hashes_verified` và `read_only_replay_matches` là `null` nếu không thực hiện checks, không ghi `true`. Prefect vẫn ghi actual config, progress, counts/report và trạng thái lỗi thật. Union flow chỉ tổng hợp saved outcomes; không chạy lại model/reference/PUT. Re-evaluate V2 không ép saved source/runtime hash và không gọi thêm subprocess `--replay`. Source snapshot riêng của run đang active giữ nguyên.
