# v25 feasibility5 — terminal transport failure (2026-10-17)

Pilot dừng đúng early-stop ở **A=false; B/C=blocked**. Controller exit0 nghĩa là hoàn tất
failure accounting, không phải semantic diagnostic thành công. Wall time14m32.48s
(12:36:17–12:50:49UTC). **Không nhận được task completion body nào**; chỉ capability echo
thành công. Vì vậy chưa đánh giá được concept extraction, executable obligations,
behavior/hypothesis, trigger, discriminator hay hiệu quả concept. Không relaunch,
repair/reset attempts, sửa frozen source hoặc gọi endpoint trong completion audit.

## All5 cases và coverage

|Case|Vai trò|Metadata terminal cause|Completion attempts|Predicate/calibration|B/C|
|---|---|---|---:|---|---|
|f02|Multiplicity bug|3×ReadTimeout; completion_attempt_budget_exhausted|3|Blocked metadata failure; chưa calibration|Blocked|
|f04|Inclusive count bug|3×ReadTimeout; completion_attempt_budget_exhausted|3|Blocked metadata failure; chưa calibration|Blocked|
|f06|Inclusion bug|HTTP503 rồi HTTP404; non-retryable404|2|Blocked metadata failure; chưa calibration|Blocked|
|f14|Correct code, unused set operation|3×tokenizer HTTPStatusError; tokenizer_attempt_budget_exhausted|0|Blocked metadata failure; chưa calibration|Blocked|
|f13|Ambiguous suitability|3×tokenizer HTTPStatusError; tokenizer_attempt_budget_exhausted|0|Blocked metadata failure; chưa calibration|Blocked|

5 logical metadata slots có failure records;3 slots gửi completion. Không có predicate,
behavior, hypothesis, trigger hay generation call. Defined-contract calibration0/4
**reached**, không phải4 predicates bị semantic bank bác bỏ. f13 không có response,
nên ambiguity abstention unobserved; không thể kết luận model suy luận ambiguity sai.
Predicate/code slots đều blocked; chưa có observed unknown decision để gọi f13 code
slot là legitimate abstention/NA. Semantic accuracy, calibration accuracy, hypothesis
support và generation success rate đều unavailable.

Client giữ cumulative attempt ledger: timeout cũng tiêu thụ attempt; f02/f04 dừng ở3,
f06 dừng ở non-retryable404 sau2, không dùng lại remaining attempt. f14/f13 chưa gửi
completion vì tokenizer budget đã hết. Không có protocol quarantine, tokenizer count
mismatch, parsed task schema rejection hay predicate counterexample. Tokenizer error
records không lưu HTTP status code/body; không được tự gán404 cho hai case này.

Không đủ server logs/body để xác định GPU crash, tunnel/session offline, guided decoder
stall hoặc nguyên nhân nội bộ khác. Tiny echo pass trước đó không loại trừ các nguyên
nhân này và không chứng minh task schema sẽ chạy. Frozen timeout/retry policy giữ nguyên.

## Capability và actual raw provenance

OpenAPI advertisement được ghi bằng boolean+digest; raw OpenAPI body không lưu nên
không thể independently re-parse advertisement từ artifacts. Echo request/response
hashes và final snapshot khớp. Adversarial prompt yêu cầu NOT_JSON, schema buộc
`{"schema_gate":true}`; actual bare response đúng object đó, origin=`qwen_endpoint`,
finish_reason=`stop`,42 input/10 output tokens,1 attempt. Mode được cố định
`guided_json` trước task calls, wire payload của3 sent task slots có schema tương ứng.
Đây chỉ là capability observation cho tiny schema, không phải task performance.

Task artifacts chỉ có request_hash/state/reason, không response/text/parsed value.
Vì vậy không có actual task concepts/behaviors/hypotheses/tests để semantic review.
Không có Python/code envelope hay task JSON envelope để đánh giá decoder trong run này.
Whole-single-fence decoder là protocol đã prereg riêng cho v25; không áp dụng hay recover
bất cứ historical v24 response nào.

Cả5 phase-A exports giữ6 native rows/case giống nhau trong verified_hyp/text_hyp/toolinput.
Text meta giữ failed state, đúng request hash và terminal reason;
raw_text/origin/response_hash=null vì **không nhận response**, không phải parser làm mất
text như hạn chế ở v24. Predicate/hypothesis/trigger được ghi missing/not_requested.
Verified contract/hypothesis=null và support=unverified đúng với evidence hiện có.
Các contexts chỉ được export để review; không có GPU generation arm comparison.
Không kết luận đã chứng minh raw-vs-verified concept contribution.

## Costs: known usage khác unknown usage

|Loại|Số lượng|Usage/calls xác minh được|
|---|---:|---|
|Task logical slots|5|Metadata only;3 sent completions,2 blocked at tokenizer|
|Task physical completion attempts|8|6 ReadTimeout +1HTTP503 +1HTTP404; tất cả usage unknown|
|Capability physical completion attempts|1|42 input +10 output tokens, received|
|Run metadata HTTP calls|13|2 models +1 OpenAPI +10 tokenizer; tokenizer4 received/6 errors|
|Prelaunch metadata calls|11|Models-only HTTP200, tách khỏi run completions|
|Native worker launches/PUT calls|248/248|124 pool inputs ×ordinary+traced; không failure/unknown/rerun|
|Qwen predicate/trigger workers/evaluations|0/0|Không task code nào được nhận|
|Separate authored CPU preflight|10 PUT calls;22 predicate workers|2776 authored predicate evaluations; không Qwen semantics|

Tổng recorded HTTP attempts gồm prelaunch=33; trong đó chỉ9 là completion attempts.
Số0 task input/output tokens trong runtime report là **sum của usage nhận được**,
không phải actual consumption=0. Chỉ42/10 echo usage là known; không có total actual
Qwen token count cho run. Wire prompt counts384/385/391 cho f02/f04/f06 là tokenizer
counts của requests, không phải server-reported consumption cho các timeout/error.
Không paid fallback hoặc model calls bổ sung trong audit.

## Witness-only và practical discriminators: cached tool results only

Read-only reconstruction từ124 cached ordinary/traced result pairs, kiểm tra signature
parity/native validity và score bằng independent fixture oracle sau output freeze;
không execute PUT hay predicate worker mới. Đây là baseline, không Qwen output.

|Case|ENTIRE pool inputs|Witness-only bug inputs|Ví dụ actual pool input và actual/required observation|
|---|---:|---:|---|
|f02|25|14|xs=[3,-1,2,-1]: actual[-1,2,3], required[-1,-1,2,3]|
|f04|25|14|xs=[0],limit=0: actual0, required1|
|f06|25|8|container=[0],required=[]: actualFalse, requiredTrue|
|f14|25|0|Unused set operation không ảnh hưởng returned sorted(xs); cached pool không discrepancy|
|f13|24|NA|"suitable" chưa được định nghĩa; không normative oracle|

Witness-only3/3 bugs với36 bug-revealing inputs,0 discrepancies trên correct f14,
ambiguous f13 unscored. Pool đã bão hòa3 bugs. Không coi36 inputs này là model discoveries.
Generation calls0, proposals0, assertions không thuộc input-only track. Raw/gated
input yield, practical LLM discriminators, correct-case contrasts và ambiguity abstention
chưa đo; novel input/task yield ngoài ENTIRE pool cũng unavailable. Runtime report
zeros/false mặc định cho blocked stages không phải efficacy result. Emitted contract
flags0 với0 qualified predicates không xác lập precision/false-alarm rate; unknown
coverage gồm cả4 defined cases và ambiguous reasoning không quan sát được.

## Verification và disposition

Read-only recomputation xác minh74 source files, dependencies/worker binary identity,
authored preflight, regenerated prepared pool/bank,770 run_frozen hashes, best-v7 parent
và v24 origin manifests. Mọi request hash, wire schema/tokenizer record, attempt ledger,
capability response và raw-control parity được đối chiếu. Original run_frozen không
bao gồm transport/status/report/logs; analysis JSON ghi thêm **analysis-time hashes**
của các ledgers này, không gọi chúng là original freeze-bound. Runtime
semantic_review=pending là hardcoded; terminal task review thực tế là unavailable.

Root và clean-context `v25_terminal_review` independently đọc terminal evidence và xác
nhận các caveats trên. Không có task text để đánh giá semantic correctness. Source và
raw artifacts giữ nguyên; không restore endpoint/retry, không model-authored expected
output claim. Separate Luna probe cũ vẫn null, không pooled.

**Disposition: transport-incomplete diagnostic; chưa biết interface/semantic feasibility
của v25 và chưa kiểm nghiệm concept contribution.** Không promote best-v7, không
comparison/benchmark/real20/held-out/paid calls tự động. Callback đã xử lý; không còn
run để resume hoặc duplicate. [Read-only verifier](v25_interface_gate_results.py),
[verified data/provenance](v25_interface_gate_results.json).
