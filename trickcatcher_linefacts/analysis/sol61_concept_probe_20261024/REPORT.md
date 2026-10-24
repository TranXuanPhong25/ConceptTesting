# Sol6.1 native probe: xử lý đúng cả6task, chưa thấy concept giúp thêm

**Generic6/6, concept6/6; concept-only0, generic-only0; false alarm0/0.** Hai nhánh
đều giữ/sửa/withdraw hypothesis đúng, không invent requirement cho ambiguous case.
Independent clean-context reviewer đọc đủ12raw replies và xác nhận kết quả.
Theo rule đã đăng ký, **concept advantage NOT SHOWN** trong probe này.

## Thử đúng những gì

User yêu cầu spawn Sol6.1 làm vài task. Đã chạy12 clean-context solver agents,
mỗi agent một task/arm, requested và observed model đều `gpt-6.1-sol`, effort `low`.
Fork history none; không cung cấp lịch sử thread, reports, gold labels hay per-task
Astra binding. Sáu seen authored fixtures E2/E3/E4/E6/E7/E8, được chọn vì các lỗi
retention/revision/control từng xuất hiện trong v40/v43, không phải held-out sample.

Hai arms có cùng spec/code/base test, fallible initial hypothesis và toàn bộ saved
observations của task. Concept nhận cùng7global concept cards với operational axes;
generic nhận reasoning checklist. Guides235/251words, chênh77bytes mỗi packet;
không claim exact token matching. Generic là checklist control, không phải unassisted
LLM. Một read-only `cat` để giao packet mỗi agent, sau đó không test tools, execution,
network hoặc delegation. Host không disable tools; actual traces xác nhận chỉ12
packet reads. Có12agent episodes nhưng24recorded inference responses: delivery+final.
Không phải12single-inference API calls. Không gọi Qwen endpoint hay paid fallback.

## Đủ6cặp, gồm controls và abstention

|Task|Điểm cần làm đúng|Generic|Concept|
|---|---|---|---|
|E2|Giữ hypothesis code bỏ equality; spec>=, code>|Đúng, keep|Đúng, keep|
|E3|Sửa set equality thành requirement required⊆container; extras allowed|Đúng, revise|Đúng, revise|
|E4|Giữ hypothesis thiếu None fallback; phân biệt exception với None|Đúng, keep|Đúng, keep|
|E6|Nhận đủ hai lỗi: loại1 và deduplicate; bỏ kết luận distinct inputs luôn đúng|Đúng, revise|Đúng, revise|
|E7 correct/masked|Unused set không gây output loss; sorted(xs) giữ duplicates|Đúng, withdraw/no_mismatch|Đúng, withdraw/no_mismatch|
|E8 ambiguous|Suitable chưa định nghĩa; không suy requirement từ code|Đúng, keep/unknown|Đúng, keep/unknown|

Không missing/invalid response, không unsupported evidence ID, không semantic failure
hay input-prediction error được reviewer tìm thấy. E8 có1justified abstention mỗi
arm và được chấm success theo prereg; đây không phải6bugtasks. Bug explanations đúng
4/4 mỗi arm; E7 correct judgment1/1; E8 ambiguity handling1/1. Cả hai arms xử lý được
các cơ chế mà historical Qwen từng sai, nhưng **không phải controlled model comparison**:
prompts, agent harness, schemas, evidence schedule và reasoning budget khác nhau.

## Inputs: concept mới về literal nhiều hơn, không thêm bug

|Chỉ số|Generic|Concept|
|---|---:|---:|
|Proposed input tuples|10|11|
|Hợp lệ và predictions phân biệt đúng hai stated behaviors (manual/source audit)|10|11|
|New literal ngoài toàn bộ per-case saved pool|6|9|
|New literal ngoài ENTIRE8case pool (78rows/67unique literals)|5|8|
|Tasks có whole-pool-new literal|4|6|
|Buggy tasks có discriminator|4/4|4/4|
|Concept-only semantic/task wins|—|0|

E6 generic dùng ([1],),([2,2],), concept dùng ([1,3],),([3,3],). Cả hai cô lập đúng
eligibility và multiplicity; concept thay số thành literal mới nhưng không tìm thêm
fault class. E7 inputs chỉ phân biệt correct implementation với hypothetical dedup,
không phải bug. E8 inputs phân biệt hypothetical predicates nhưng không quyết định
spec muốn predicate nào. 10/11 cũng không matched exact input count vì cho tối đa2
và agent có quyền abstain; không lấy novelty chênh lệch làm efficacy gain.

**0new PUT executions.** Input correctness được reviewer kiểm tra từ source và
arithmetic, không phải runtime-validated discoveries. Predictions là hypothesis,
không exported assertions/model-authored expected-output gain. Saved evidence đã
expose bugs; không có claim new bug discovery hay adaptive query ability.

## Actual usage và origin

|Solver arm|Agent episodes|Recorded inference responses|Input tokens|Cached input (subset)|Output tokens|Total tokens|
|---|---:|---:|---:|---:|---:|---:|
|Generic|6|12|211,975|173,440|2,670|214,645|
|Concept|6|12|212,020|191,488|2,704|214,724|
|Total|12|24|423,995|364,928|5,374|429,369|

Reasoning-output counters26generic/0concept are included in output accounting, not
added again. Actual effort metadata low for all12. Counts come from24unique native
`token_usage_record` response IDs, including tool-delivery steps and harness overhead;
not an estimate from packet lengths. Usage known for all recorded solver responses.
Transport HTTP attempts/retries and dollar cost are not exposed; do not equate these
records with a separately audited provider HTTP count or claim zero cost.

Independent audit agents are separate (observed gpt-6-astra/medium): design7inference
responses/194,478tokens, semantic8/320,652. Solver+two-reviewer total39recorded
responses/944,499tokens, of which806,144cached-input tokens. Parent orchestration
usage is not allocated to this table. Raw solver artifacts remain Sol-origin; no
Qwen/Luna/Astra solver substitution. No Qwen endpoint, separately paid fallback API, native PUT or worker
requests were made by this probe. Quota98% before work,28% at17:09UTC checkpoint.

## Integrity, interpretation and disposition

PREREG + packet builder + manifest + packets frozen before solvers. Independent
prelaunch review verified all6pair parity and public projection. Raw final messages
were exported verbatim from native session logs, with model/effort, exact tool call,
response IDs, usage and provenance hashes. generation_frozen.json precedes saved-data
mechanical accounting and independent semantic audit. Reviewer verified12raw hashes,
12packet hashes and the prelaunch record. No output repairs, retries, extra tasks or
post-hoc scoring changes. Files: SEMANTIC_REVIEW.md, mechanical_results.json,
reviewer_usage.json, raw/, generation_frozen.json, prelaunch.json.

This shows the stronger model can perform the desired reasoning on these six
information-rich seen tasks. The generic control already succeeds everywhere, so
this experiment supplies no incremental concept benefit. Do not enlarge n, repeat
prompts or declare concepts generally useless to rescue/exaggerate this result.
This is not the dynamic concept-identification loop and does not replace v50,
whose endpoint-priority issue remains separate and untouched.
