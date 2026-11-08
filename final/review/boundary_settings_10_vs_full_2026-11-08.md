# Full settings: test 10 case và full HumanEval

Đối chiếu từ manifests, saved requests và frozen runtime; không gọi LLM/native mới.
JSON đi kèm chứa manifests/settings nguyên bản, exact prompts, 1.640 request receipts,
selected PUT source hashes và byte-identity checks. Endpoint/key không xuất ra report.

## 1. Phân biệt các run

| Run | Task/PUT | Generation | Kết quả |
| --- | --- | --- | --- |
| 10 Direct | 10tasks,10PUTs | 10calls×max20inputs | 199valid,6PUT |
| 10 Soft BVA | Cùng10PUTs | 10calls×max20inputs | 192valid,7PUT |
| 10 Worksheet | Cùng10PUTs | 10calls×max20inputs | 189valid,7PUT |
| Full Soft BVA đã xong | 157eligible/1454base-passPUTs | 1454per-PUTcalls;20inputs/task | 1449valid,61PUT |
| Historical naive, rescore | Cùng1454targets khi chấm | 156taskcalls cũ, nhiềuPUT/call | 1536valid,44PUT |
| Naive sửa packaging | Cùng1454targets/responses cũ | 0newcalls; chỉ sửa argument wrapping | 2758valid,82PUT |
| Full matched batch mới | 157eligible/1454targets | Direct+Soft mỗiarm1call/task;max314calls | Chưa hoàn tất; không dùng partial làm kết quả cuối |

Direct của10case là control riêng, KHÁC historical multi-PUT naive. Historical naive72 dùng oracle/runtime cũ; không dùng để so với61/82hiện tại.

## 2. Cohort, scope và budget

| Setting | 10-case diagnostic | Full BVA đã xong |
| --- | --- | --- |
| Requested/eligible tasks | 10/10 | 164/157 |
| Base-pass PUTs được chấm | 10 | 1454 |
| target_programs | 1 trong cohort con | 10 trong cohort cha |
| PUT mới được sinh trong run | 0 | 0 |
| Selection | Outcome-selected known-bug PUTs; không outcome-blind | Frozen full cohort + eligibility skips |
| PUT model nhìn trong mỗi call | 1 | 1 |
| Calls/task/arm | 1 | Bằng số visible base-pass PUTs |
| input_budget cấp task | 20 | 20 |
| Quota SINH cho mỗi PUT/call | 20 | floor(20/P), chia remainder theo thứ tự |
| Tổng input slots tối đa/arm | 200 | 3140 trên157tasks |
| Refill/redistribution | Không thêm call để refill | Không refill quota thiếu/trùng |
| Input nào chạy trên mỗi PUT | Tậpvalid của arm trên PUTduy nhất | Input gộp toàn task chạy trên TẤT CẢ PUT cùng task |
| Novel valid inputs/task | Direct199/10;Soft192/10 | min2,median9,mean9.2293,max20 |

**2–3 là quota SINH/PUT, không phải chỉ2–3input được chạy trên PUT đó.**
Full gộp input từ mọiPUT, khử trùng rồi test tậpvalid chung trên mỗiPUT.
Small cohort là tập con của cùng parent cohort; selected code không thay đổi.
Parent cohort:1634generated/1465base-pass; eligibility còn1454base-pass PUTs.

Danh sách10PUT chính xác theo cohort/result artifacts:

| Task | PUT ID | Base examples visible | Quota small | Quota full |
| --- | --- | --- | --- | --- |
| HumanEval/2 | 6 | 3 | 20 | 2 |
| HumanEval/11 | 1 | 3 | 20 | 2 |
| HumanEval/16 | 4 | 5 | 20 | 2 |
| HumanEval/23 | 7 | 3 | 20 | 2 |
| HumanEval/72 | 4 | 6 | 20 | 2 |
| HumanEval/76 | 0 | 10 | 20 | 3 |
| HumanEval/99 | 1 | 5 | 20 | 2 |
| HumanEval/124 | 0 | 12 | 20 | 3 |
| HumanEval/140 | 7 | 5 | 20 | 2 |
| HumanEval/157 | 3 | 11 | 20 | 2 |

Task16 là PUT4 theo artifacts. Prose report cũ từng ghi PUT0; bảng này lấy trực tiếp cohort và actual result IDs.

Histogram quota full:

| Quota/PUT/call | Số PUT/calls |
| --- | --- |
| 2 | 1280 |
| 3 | 164 |
| 4 | 2 |
| 5 | 4 |
| 10 | 2 |
| 20 | 2 |

Histogram visible PUTs/task: {"10": 92, "9": 44, "8": 12, "1": 2, "7": 4, "6": 1, "4": 1, "2": 1}.

7skips:32/136=generation_shortfall;65/127/132/145/163=no_base_pass. Không skip theo detection outcomes.

## 3. Model, sampler và transport

| Setting | 10-case và completed full BVA |
| --- | --- |
| Served model | qwen3.5-27b-awq; cùng alias, không archive actual weight hash |
| Temperature | 0.7 |
| Completion seed | 314159+task_number; KHÔNG cộng PUT ID |
| Context limit | 8192tokens |
| Completion limit | 2048tokens/CALL, kể cả full call chỉ sinh2input |
| Prompt fit guard | prompt_tokens+2048+128<=8192 |
| Thinking | enable_thinking=False |
| API JSON mode/schema | Không set response_format; schema bằng prompt+parser |
| Tool/API feedback cho generator | Không tools, không oracle/execution feedback |
| HTTP timeout | 180s |
| Streaming deadline/size | 1800s / 16MiB |
| SDK max_retries | 0 |
| Application completion attempts | Max3; lịch sử unknown được giữ |
| Completion backoff | 5s,20s |
| Tokenize attempts/backoff | Max3 /5s,20s |
| Tokenize/models timeout | 60s/25s |
| Runtime keepalive | 1-token completion mỗi20min; receipt tách riêng |

Client không set tường minh top_p/top_k/min_p, penalties và stop sequences; server defaults không được lưu.
Cùng alias/seed không đảm bảo bitwise reproducibility qua các generation epochs.
Model/transport/checkpoint,CallBuilder,native worker/execution giữa10case và full đã kiểm tra cùng SHA256.

## 4. Prompt/context/schema

10-case Soft và full dùng cùng SYSTEM/GUIDANCE và cùng task packet:
`task_id`, `specification`, `domain_contract`, `put_source`, `existing_inputs`.
Mỗi packet có tối đa12base calls của chínhPUT đó, chỉ args/kwargs/bound.
Không đưa canonical_solution, reference outputs hoặc hidden test inputs cho LLM.
PUT source giữ nguyên; không compact như historical naive.

Đã so sánh cả10selectedpackets: task data giống hệt, cùngseed; instruction đổi từ
`up to20` thành `up to2/3`. Exact requests và proof nằm trongJSON.

Schema đầu ra:
```json
{"inputs":[{"arguments":{"parameter_name":"literal value"}}]}
```
CallBuilder encode tên parameter thành Python args/kwargs; không tính targets hoặc sửa giá trị.
Worksheet làm các bước nội bộ trong cùng1completion; không có external selection/compiler.

### SYSTEM

```text
You generate valid Python function inputs to expose implementation bugs. Return JSON inputs only.
```

### Common instruction cho20inputs

```text
Generate up to20small, distinct new calls to find specification violations in the supplied Python implementation. The specification and input-domain contract define correct behavior; the PUT may be wrong. Keep inputs within the contract and avoid existing base calls. All required context is provided below. Do not use tools or execute code. Return inputs only: no expected outputs, assertions, explanations or plans.
Return exactly one JSON object with an inputs list. Each item has only an arguments object mapping the actual function parameter names to complete JSON literal values. Code will only encode your values as a Python call; it will not compute or adjust boundary targets. Return fewer calls if appropriate; do not pad with duplicates. Empty response shape is {"inputs":[]}.
```

### Direct guidance

```text
Choose useful new concrete tests from the supplied task data.
```

### Soft BVA guidance (nguyên văn)

```text
Boundary value analysis is one useful source of test ideas: consider values around changes in behavior, including just below/at/above limits, zero/sign changes, empty/singleton containers and relevant integer crossings. Keep joint input constraints and contexts that let differences affect the result. Use these ideas as suggestions, while retaining other useful tests; no formal boundary classification is required.
```

### Worksheet guidance (nguyên văn)

```text
Apply this worksheet internally before choosing the concrete calls. Do not print the worksheet; return only the common input JSON. There is no separate selection API or constructor.
Apply boundary value analysis (BVA) to one Python function. You decide WHERE to test.
The specification and domain contract define correct behavior. The PUT source may be
wrong: use it to find where to look, never as proof of correct behavior.

STEP 1 ORDER. Keep a candidate only if you can name the value just before and just after
a given value of that quantity, and the rule depends on that order. Measure the quantity
the rule talks about, not the raw input type: a part of a value is not the whole value,
and text may encode a number or a fixed format with its own measure. Booleans and
unordered labels have no boundary.

STEP 2 TRANSITIONS. Consider spec rule changes, PUT behavior changes and natural edges.
- origin "spec": a stated range, limit or cutoff ("from 18 to 60", "at most 255 characters",
  "above 500000", "at least 1 item") or a contract assertion. The minimum and maximum of a
  valid range ARE boundaries. A precondition forbids only the side outside the domain;
  its inside side is still a boundary test.
- origin "code": a comparison, loop exit, index, slice or arithmetic step in the PUT that
  separates valid inputs into different behavior.
- origin "edge": an unstated natural edge of a valid input: zero and the sign change,
  an empty or one-element container, empty text, and both +b and -b when a rule concerns
  size or digit count. Integer crossings can matter for rounding, truncation and fractional
  arithmetic.
  Give the reason behavior may change there.
The spec need not state a numeric threshold for code or edge candidates. It defines the
valid domain and correct behavior; code or a natural edge supplies the testing location.
Observed values are samples, not limits. A type alone is not evidence of a threshold.
Python int has no maximum. Sampling, resource and generation caps are not boundaries.

STEP 3 ALIGN. Compare each spec transition with the code: "match", "operator" (< against
<=), "shifted" (different constant), "missing_in_code", or "code_only". A mismatch is a
hypothesis, not a verdict.

STEP 4 REACH, INFECT, PROPAGATE. For each transition consider briefly:
- reach: what the other inputs must satisfy for execution to get there.
- infect: target values sensitive to incorrect handling. For an operator mismatch this is
  the threshold itself; for a shifted constant, the values between both constants. For
  code/edge candidates with no visible mismatch, give the sensitive neighborhood; an
  actual fault need not already be established.
- side_rules: which rule the specification applies below, at and above, as rule names only.
The same spec rule may apply on every side of a code/edge candidate while implementation
behavior changes. Keep that candidate if you can explain a possible visible difference.
Drop only candidates with no supported reason for any visible difference.

STEP 5 SELECT at most 4, in this priority: mismatches; spec behavior
transitions; domain minimum and maximum; remaining code and edge transitions.
Before choosing several thresholds for one quantity, consider relevant natural edges of
the other parameters. A missing spec threshold alone is never a reason to abstain.
- behavior: target below, at and above. Omit a side only if it cannot exist, such as length -1.
- domain_lower/domain_upper: inside sides only. x >= b: at, above. x > b: above.
  x <= b: below, at. x < b: below. Never target inputs excluded by the contract.
These two kinds require an equivalent input-domain clause. Otherwise use behavior: inputs
for which the result is False or empty can still be valid inputs.
```

## 5. Parser, filtering, dedup

| Setting | 10-case | Completed full BVA |
| --- | --- | --- |
| Envelope | Chỉ object có inputs:list | Cùng |
| Record | Chỉ arguments object | Cùng |
| finish_reason=length | Reject toàn response | Cùng;2calls thực tế |
| Markdown fences | Không strip; strictJSON | Cùng |
| Vượt input quota | Reject envelope | Cùng |
| Within-response duplicates | Loại theo encoded args/kwargs | Cùng |
| Cross-PUT duplicates | Không có nhiềuPUT đểgộp | Loại; không refill |
| Named values | Finite literals;depth<=8,container<=1000items,args/kwargs<=16000chars | Cùng |
| Domain/reference validation | Sau khi tất cả task inputs freeze | Cùng |
| Stable reference | 2runs ok,cùngexpected/inputkey | Cùng |
| Base-input duplicates | Loại qua canonical bound key | Cùng |
| Nhiều arms | Oracle dedup union; arm_indices giữ attribution | Chỉ boundary arm; pooled từ cácPUT |

Full yield:3140allocatedslots →3050parseable within-budget rawrecords →3034encoded
→1484sau cross-PUTdedup →1449novelvalid.1550cross-PUTduplicate rejects;
15domain/reference rejects;20base duplicates. Program statuses:1402generated,
44invalid_generation,8no_inputs.44invalid gồm31fenced,10invalidJSON,1bad envelope,2truncated.

10-case raw/encoded/novel:Direct200/199/199;Soft199/199/192;Worksheet195/192/189.
Cả30responses đều finish_reason=stop.

## 6. Oracle, scorer và sandbox

- Reference:EvalPlus/HumanEval+v0.1.10, exported reference-only; không hiddeninputs.
  SHA256 `7a0a41bdcaa5220dcb4f2e405349678a82853a42f6bbf8db837e520825c8c5af`.
- Spec/entry/contract/tolerance identities phải khớp pinned reference.
- Reference chạy2lần; PUT chạy2lần cho MỌI valid input; cùngseed `271828+task`.
  Count detection khi cả2status thuộc fail/error/timeout; không bắt buộc cùngloại failure.
- Wrong-value subset:ít nhất1input có cả2status=fail; khác với chỉexception/timeout.
- `atol` theo metadata; task2=1e-6,các9task nhỏ còn lại0. Expected float/list-of-floats
  với atol0 sẽ fallback1e-6. NumPy allclose rtol1e-7; find_zero dùng polynomial residual.
- Timeout3s/input. Cache execution isolated từnginput; repeat0/1 riêngcache;
  timeout results không reused. Fresh namespace/process khi cần execute.
- Native `random.seed(271828+task)`,PYTHONHASHSEED0;BLAS/OMP/MKL threads1.
- Bubblewrap unshare-all/networkisolated/read-onlyhost;subprocess disabled.
  RLIMIT_AS1GiB,RLIMIT_FSIZE4MiB,RLIMIT_NOFILE64,RLIMIT_NPROC0,core0.
- Parent wall guard10+3*max(1,input_count)seconds/job. Infrastructure errors không làdetections.
- Input freeze trước scoring; immutable read-only replay/source+data hashes pass.

Không dùng current confirm-first-failures optimization cho10case/fullBVA61/naive44/82.
Full metadata164tasks có161atol0,2atol1e-6,1atol1e-4.

## 7. Runtime/calls/tokens thực tế

Python3.11.14. Runtime/package versions:

| Package | Version |
| --- | --- |
| coverage | 7.17.0 |
| numpy | 2.4.6 |
| scipy | 1.17.1 |
| evalplus | 0.3.1 |
| langchain-openai | 1.6.2 |
| langchain-core | 1.6.3 |
| openai | 3.41.0 |
| httpx | 0.28.1 |

Historical naive generation dùng backend/packages cũ; rescore44/82 dùng cùng frozen runtime với BVA. Exact old manifest cũng có trongJSON.

| Run/arm | Received responses | Prompt tokens | Completion tokens | Known total tokens |
| --- | --- | --- | --- | --- |
| small_direct | 10 | 8433 | 4490 | 12923 |
| small_soft_bva | 10 | 9033 | 4876 | 13909 |
| small_worksheet | 10 | 16913 | 5735 | 22648 |
| full_bva | 1454 | 1311541 | 111944 | 1423485 |
| naive_original | 156 | 291095 | 94427 | 385522 |

10-case30logicalslots=12exact-request reused+18newresponses ở continuation cuối.
Full BVA1454received=493imported+961remaining;1456attemptrecords gồm2unknown.
Naive156received/157attemptrecords gồm1unknown. Token table tính reused đúng1lần,
không gồm keepalive. Observer receipts theo physicalrun ởJSON; không tự phân bổ
shared historical keepalive cho các response reused.

`writer_seed=20261030`,`writer_rounds=10` là dataclass fields kế thừa.
Không sinhPUT mới/không chạy10writer rounds trong các input-generation runs này.

## 8. Historical naive và packaging repair

Historical naive1call/task nhìn nhiềuPUT; common prompt yêu cầu exactly20inputs,
original base tests,spec/contract,compact code có original line labels; generic useful-tests
guidance. SYSTEM cũ không có câu Return JSON inputs only. Schema:
```json
{"inputs":[{"args":"(1, [2, 3])","kwargs":"{}","concept_id":null}]}
```
args/kwargs là STRING Python literals, không named CallBuilder. Max2048output,
8192context,temp.7,seed314159+task giống nhưng prompt/visibility/schema/backend khác.
17resource-riskPUTs bị loại khỏi visibility/eval gốc; source1437targets;
source task160skip. Current rescore đánh giá đủ1454targets,giữ task160empty.

Naive source31generatedemptybatches+1eligible source-skip. Sauoracle filtering,
75eligible tasks không cònnovel valid input; saupackagingrepair chỉ còn11.

Repair riêng:1250slots/64tasks,static signature/annotation/unconditional contract
proof;max20originalrawslots/task;chỉwrapping,khôngđổigiátrị. Khôngoracle-guided fix,
expressionexecution hay ambiguous/default/multi-param/keyword-only repair.
Khôngreparse invalid/truncatedresponses. Originalraw/admittedrecords cònnguyênởsource/receipts.

Saurepair82PUT/29tasks/53wrong-value;BVA61/22/46. Shared61,naive-only21,BVA-only0.
Đây là diagnostic packaging, không phải fresh matched-guidance result.

## 9. Fresh full batch: run riêng chưa hoàn tất

-157eligible tasks,Direct/Softmỗiarm1batchcall/task;max314logicalcalls.
-Cùngspec/domain/base/sourcepacket,visibleIDs/order,namedarguments,CallBuilder/parser.
-Max20inputs/arm/task,không per-PUTquota. Sampler/tokenlimits nhưtrên.
-Direct guidance rỗng,Soft thêmGUIDANCE. Jointtokenizer chọn common visibility
 fit cả2prompts trướccompletion; nếu quácontext thì trim cùnglist.
-Interleave theo task;taskparity đổiarmorder. Tất cảbase-pass targets vẫnđượcchấm,
 kểcảPUTkhôngvisible. Empty/invalidgenerations giữtrongprimarycomparison.
-Shared base parser stripjsonfences,cho namedarguments vàlegacyfallback,lấymax20records.
 Khác strict10case/fullBVAdecoder:nó khôngreject finish_reason=length độc lập
 nếuJSON vẫnparseđược;khôngcấmextraenvelopekeys. Cả2arm dùngcùngpolicy.
-Scorerconfirm-first-failures-v1:firstpassdừng;fail/error/timeout mới confirm1lần;
 reference vẫn2lần. Khác full2repeat của10case/fullBVA61/naive82.
-Frozenisolatedruntime,review/test/deadlinegates,nativelockserialize.
-Lịchpreflight2026-11-07T19:17:40Z=08Nov02:17:40Vietnam;khôngLLMtrướclịch.
 Metadata-onlywait<=6hkhôngsubstitutemodel.

Status snapshot:

```json
{
  "state": "interrupted",
  "pid": 415105,
  "updated_utc": 1794087448.3840857,
  "error_type": "TransportError",
  "error": {
    "operation": "tokenize",
    "error_type": "HTTPError",
    "http_status": 404,
    "retryable": true,
    "completion_started": false,
    "partial_text_characters": 0
  }
}
```

226received(113mỗiarm),1unknowntransportattempt;chưa globalfreeze/chưa nativeeval. Partialgeneration không là finalresult.

## 10. Không có đủ receipts để xác nhận

- Exact model weight revision/hash
- GPU/device and server launch command
- vLLM/server version
- Server-side defaults for top_p/top_k/min_p/repetition/presence/frequency penalties and stop sequences
- Actual deterministic reproducibility across response reuse epochs

## 11. Artifacts và exact requests

- small: `final/out/boundary_prompt_style10_20261107_120909`
- full_bva_generation: `final/out/boundary_soft_humaneval164_resume_20261107_195417`
- full_bva_evaluation: `final/out/boundary_soft_humaneval164_evaluation_20261107_224720`
- historical_naive: `final/out/v11_concept_inputs`
- naive_rescore: `final/out/naive_vs_soft_bva_full164_20261108_000951/evaluation`
- packaging_rescore: `final/out/naive_packaging_audit_20261108_0200/evaluation`
- matched_batch: `final/out/bva_batch_matched164_20261108_021740`

JSON đi kèm chứa exact prompts,full manifests,1640receivedrequestreceipts,samplerchecks,selectedpacketchecks,allocationhistograms vàhashes. Evaluation-onlymanifestmodel=null vìkhôngkhởitạomodel;modelgeneration lấy từ savedrequests/readiness.
