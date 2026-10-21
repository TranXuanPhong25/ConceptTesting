# v40 retry3 — input generation thành công, concept/revision mechanism không đạt gate

**Hoàn tất72/72 responses. Cả ba arms có revealing inputs ở6/6 buggy fixtures và4/4 cases chưa có supplied revealing row. Concept không có task win riêng. Nhưng concept_adaptive không giữ đúng hypothesis sau evidence ở E2/E4/E6 và không sửa đúng normative binding ở E3. Theo prereg: capability fail, incremental concept fail, combined package no-go.**

Đây là8 seen authored fixtures, supplied concepts, không phải benchmark/extraction/transfer test. Kết quả không chứng minh concept nói chung vô ích. Nó cho thấy package này đã có thể sinh input và dùng tool, nhưng chưa chứng minh selective semantic revision hoặc giá trị tăng thêm của concept.

## Run, nguồn và scoring

Run13:20:19–14:07:31UTC ngày21/10/2026 (20:20–21:07Vietnam), exact requested/returned alias `qwen2.5-coder-32b-instruct`; metadata advertises root `Qwen/Qwen2.5-Coder-32B-Instruct-AWQ`, context8192. Metadata/HTTP provenance không phải independent loaded-weight verification. Raw response origin là user_authorized_Qwen32B_endpoint; Luna probe riêng vẫn null, không trộn vào result này.

Root: out/pipelines/v40_concept_agent/humaneval/d1_retry3_20261021. Không relaunch, retry/reset, repair hoặc new model/worker calls trong callback. Parent verify hashes trước saved-data scoring, đọc toàn bộ raw claims/queries/final inputs; hai clean-context reviewers audit riêng E1–E4 và E5–E8, reviewer thứ ba audit integrity/cost. Chỉ ghi analysis. Nguồn review: SEMANTIC_A.md, SEMANTIC_B.md, INTEGRITY_COST_AUDIT.md/.json, results.json, input_metrics.json. results.json giữ automatic pre-review labels; final adjudication nằm riêng ở review_conclusion.json và report này.

Concept/binding/gap là authored treatment được cấp cho CA/CC; Qwen sinh claims, predictions, queries và final inputs. Không có Qwen concept extraction stage ở đây. GA nhận cùng spec/code/base, fallible initial H và raw observations, nhưng không nhận explicit concept/binding/gap package. CC còn phải commit cả hai query batches từ T1; final inputs vẫn adaptive ở mọi arm. Cùng24completion slots/arm, nhưng actual tool use khác nhau.

Fixture expected values chỉ được tính **sau generation freeze**, từ cùng pure fixture evaluator trên saved native observations. Không chạy lại PUT. **Input-only track: không có model-authored assertion/expected-output correctness claim.** `prediction` là dự đoán trước query, không được dùng làm oracle.

## Input yield và controls

|Chỉ số|concept_adaptive (CA)|generic_adaptive (GA)|concept_committed (CC)|
|---|---:|---:|---:|
|Responses / fixed slots|24/24|24/24|24/24|
|Controller-accepted turns|24|23|18|
|Valid final turns|8/8|8/8|8/8|
|Revealing tasks, replay hoặc final|6/6|6/6|6/6|
|No-supplied-revealing-row discovery E1/E2/E4/E5|4/4|4/4|4/4|
|Accepted final inputs|16/16|16/16|16/16|
|Revealing final inputs ở6buggy cases (12candidates)|11/12|10/12|11/12|
|Passing finals ởcorrect E7|2|2|2|
|Normatively unknown finals ởambiguous E8|2|2|2|
|Accepted replay requests|28|27|14|
|Revealing replay rows, có thể repeat|18|18|9|
|Final unsupported bug flags trên E7/E8|0|0|0|

Raw final-input proposals là16/16/18; CC có2premature T2proposals bị reject, nên cả ba chỉ có16accepted finals. Không xóa failures khỏi denominator. Các số revealing trên là input yield dưới common post-freeze fixture oracle; không phải số model đã giải thích đúng bug hay assertion precision. Tổng48accepted finals:32exposing,10matching,6undefined-oracle. Undefined không được tính là đúng/sai; matching có cả useful contrasts.

Toàn bộ16shared rows của v40, không dùng model, đã expose E3/E6: baseline supplied-evidence2/6. Vì vậy6/6 không có nghĩa6new task discoveries. Cả ba arms thêm E1/E2/E4/E5, không có CA-only hoặc GA-only task win trong primary4cases.

## Đủ8episodes và cả3arms

`2/2` dưới đây là final inputs expose theo fixture, không phải claims đúng. Mọi episode-arm có đủ3turns; failed intermediate turns liệt kê ở phần sau và independent reports.

|Episode / concept treatment|CA final input / semantic result|GA final input / semantic result|CC final input / semantic result|
|---|---|---|---|
|E1/f02 occurrence_conservation, correct; initial length-H false|2/2; chủ động narrow sang duplicate fault ngay T1, final đúng|2/2; raw T1 đã đúng nhưng schema reject; T2/T3 đúng|2/2; duplicate fault đúng, không có later batch|
|E2/f04 eligible_contribution, inclusive equality đúng; initial H đúng|2/2; T3 withdraw strict implementation rồi keep false inclusive implementation|2/2; cùng semantic failure như CA|2/2; final giữ equality-exclusion/mismatch đúng, T2 có redundant strict-claim withdrawal sai|
|E3/f06 membership_inclusion nhưng binding equality cố ý sai|1/2; final nói sai chiều implication, why gọi subset False là đúng spec|1/2; final extra-container mismatch đúng; revealing final là shared J0, nhưng T2 đã có novel revealing replay|1/2; explanation sai như CA; T2 replacement rejected|
|E4/f08 defined_outcome đúng; initial empty-eligible H đúng|2/2; native exceptions xác nhận H nhưng T2/T3 withdraw nó|2/2; giữ đúng ValueError hypothesis|2/2; final vẫn withdraw đúng H; T2 replacement rejected|
|E5/f12 eligible_contribution đúng; initial sign-H false|2/2; chủ động thấy length guard T1, final đúng hai branches|1/2; length guard đúng, một query prediction áp short-list claim vào length3 sai scope|2/2; correct main diagnosis; T2 replacement rejected, raw polarity cũng lẫn|
|E6/f16 eligible_contribution đúng; exclusive dedup-H sai|2/2; nhận cả hai faults T1 nhưng cuối withdraw dedup trái replay|2/2; cuối khẳng định sums without dedup trái repeated-value replays|2/2; giữ missed1 nhưng withdraw dedup; T2 replacement rejected|
|E7/f14 occurrence_conservation đúng; program correct, local loss masked|0/2; cả hai outputs đúng. T2 repeat disproven query, T3 mới withdraw false bug candidate|0/2; sửa prediction T2, final no-output-effect đúng|0/2; final giữ sorted-original/preserves-duplicates đúng; T2 premature finals rejected|
|E8/f13 eligible_selection unknown; suitable không định nghĩa|Không có normative oracle; explicit unknown cả3turns|Semantic abstention: keep statement “spec undefined”, không invent predicate|Explicit unknown, không confirmed bug; T2 replacement rejected, original committed inspections vẫn chạy|

E1/E2/E4/E5 chưa có supplied revealing row. E3/E6 đã có revealing J0 được reveal từ T2; không credit lại như new discovery. E7correct không phải miss; E8unknown không phải lỗi model không tìm được bug.

## Prediction, evidence và selective revision

- **E1/E5 là proactive correction.** Model đã bỏ length-only/sign-only story trước new tool feedback. E6 cũng đã nêu cả dedup và `>1` ở T1, nên không credit boundary recognition sau J0 như sửa exclusive-H nhờ feedback.
- **E2 cho thấy expected/observed conflation.** CA thấy `([2,2,2],2)→0`, đúng dự đoán strict `>` của chính nó, rồi T3 withdraw statement đó và keep “implementation counts >=”. Inputs vẫn reveal do evaluator biết required value3. GA cũng mắc lỗi này; CC giữ được equality-exclusion statement ở final.
- **E4 không phải null output bằng return None.** Saved observations ghi `execution_status=exception`, `exception_type=ValueError`. CA/CC vẫn withdraw “may raise ValueError” với citations chính các exceptions. GA đọc đúng.
- **E6 có practical discriminator tốt nhưng kết luận sai.** CA T2 `([2,2],)→2` cùng B0 `([2],)→2` tách dedup khỏi missed1; GA dùng repeated2/repeated3 triples→2/3. Những inputs chỉ có values>1 không lẫn boundary fault. Tuy vậy CA/CC withdraw dedup, GA final nói without dedup. Các final inputs có1 vẫn expose boundary bug, không cứu missing multiplicity understanding.
- **E3 không chỉ thiếu một enum.** Equality True bảo đảm required present, nhưng equality quá chặt và rejects extras. CA/CC dùng câu sai chiều “does not ensure every required present”, nhiều lần gọi strict-subset False là đúng spec. Cả hai cite J0 ở T1 khi mới biết tên ID, chưa có observation body; đây là unsupported citation, không bằng chứng hidden-data leak. GA final nhận đúng extra-container failure dù có rationale sai giữa chừng.
- **E7 là genuine feedback challenge.** CA T1 kỳ vọng duplicate loss nhưng thấy preserved duplicates. T2 vẫn lặp nguyên query/prediction sai; T3 cuối cùng withdraw. GA đổi prediction T2 rồi final nói local set không ảnh hưởng return. Final bug false alarms0 không xóa transient false candidate của CA ở T1/T2.
- **E8 calibration đúng.** CA/CC explicit unknown; GA keep sự thật “spec chưa định nghĩa suitable”, vẫn không suy ra normative behavior. More behavior samples không định nghĩa được predicate còn thiếu.

Trong4potential false-H challenges E1/E5/E6/E7, CA đã proactively xử lý E1/E5 và nhận diện hai faults E6 từ T1. Chỉ E7 là clear unresolved initial false-H feedback opportunity; <2threshold đã đăng ký. E6 còn có opportunities để sửa own prediction/claims, nhưng không thành công và không biến thành unresolved original exclusive-H episode. Không gộp proactive reading với feedback-driven adaptation. Không có2CA evidence-linked useful query adaptations missed by CC; distinct adaptivity inference **inconclusive/insufficient opportunities**, không phải causal proof của adaptation vô ích.

## Novelty: toàn bộ v40 shared pool, không chỉ rows đã thấy

|Unique task/input pairs|CA|GA|CC|
|---|---:|---:|---:|
|Observed, dedup trong arm|38|32|26|
|Exposing|26|20|16|
|Outside ENTIRE same-task v40 shared pool|37|31|25|
|Exposing outside ENTIRE same-task shared pool|25|19|15|
|Exposing outside stricter all-task shared literal pool|23|18|14|

Pool ở đây gồm tất cả2prepared shared inputs/task, cả J0 chưa được reveal lúc T1; global metric còn loại cùng literal ở mọi8tasks. Nó không chỉ trừ shown/history rows. Task discoveries beyond supplied exposing pool vẫn4/4 cho mọiarm. CA/CC có novel revealing final ở6/6buggy tasks; GA5/6 vì E3final repeats J0, dù GA T2 đã independently reveal E3 outside pool.

**Đây không phải novelty ngoài historical v24 whole24+base pool hoặc toàn bộ prior runs/benchmark.** Historical novelty không được đo/claim trong protocol này. Nhiều generated finals cũng chỉ repeat own query; “outside supplied pool” không có nghĩa new after feedback, new fault hay có causal contribution của concept. All concrete records/definitions ở input_metrics.json.

## Format, tool failures và committed control

72raw outputs đều parseable JSON;71schema-valid;65controller-accepted.7failed fixed turns gồm: E1GA T1 missing query-level claim (reply_schema); E3/E4/E5/E6/E8CC T2 replacement_commitment (5); E7CC T2 premature_final_inputs (1). Không transport failure/truncation; mọi finish_reason=stop. Các rejected raw replies được giữ nguyên, không recover/execute proposals bị reject.

Có13third-replay cap refusals: CA5, GA2, CC6. Chúng consume action slots nhưng không chạy workers; không có domain rejection/native disagreement. Ở E4, input notation single-argument không đủ tuple được frozen arm-neutral parser normalize; đây là behavior đã frozen, không post-hoc repair.

CC **7/8episodes không commit later batch** ở T1; chỉ E8 commit2structural inspections. Do đó không thể xem CC là fully compliant two-round committed execution control. T2E8 replacement bị reject nhưng hai original committed actions vẫn chạy theo frozen source. T2failures/emptycommitments hạn chế causal adaptivity comparison, nhưng không giải thích CA semantic errors vì CA24/24accepted và mọi final8/8valid.

## Preregistered disposition

|Gate cho concept_adaptive|Kết quả|
|---|---|
|Valid final8/8|Pass|
|Correct handling false/overbroad H4/4|Fail: E6; E1/E5 chủ động narrow và E7 cuối withdraw|
|Retain correct H E2/E4,2/2|Fail:0/2|
|Reject wrong normative binding E3|Fail coherent explanation despite useful input|
|Keep E8 normative unknown/no unsupported final E7/E8 bug flags|Pass|
|Useful replay/contrast+revealing final ≥3/4 no-supplied cases|Pass:4/4|
|≥2CA-only task wins,0opposite losses among E1/E2/E4/E5|Fail:0wins/0losses; cả hai4/4|
|Distinct execution-query adaptivity evidence|Insufficient opportunities/control compliance; no registered success|

**Combined policy package no-go. Không promote, train concept-to-input, tăng n/K hoặc mở benchmark để cứu result.** Hiện không có input-construction bottleneck trên các fixtures này: mọiarm đều có accepted revealing input ở6/6. Điểm fail quan sát được nằm ở interpreting evidence/maintaining correct implementation claims, cộng committed-policy compliance. Không suy ra bottleneck đó luôn đúng trên real tasks hay model khác; concepts ở đây được cấp sẵn và fixtures nhỏ/seen.

## Costs, workers và frozen integrity

|Arm|Actual prompt tokens|Actual completion tokens|Attempts/responses|
|---|---:|---:|---:|
|CA|75,682|6,273|24/24|
|GA|70,202|7,069|24/24|
|CC|74,708|7,855|24/24|
|Total new|220,592|21,197|72/72|

New actual known usage241,789tokens,0newunknown. Cumulative four owned roots:73completion attempts/72responses/72known usages/**1original unknown usage**. Known subtotal241,789 **plus unknown**, không phải exact cumulative total. Dollar billing không được emit. Tokenizer2359 của original failed request chỉ là request size. New HTTPoperations146 =2GETmodels (one separatepreflight)+72tokenize+72completions; cumulative152 =6GETmodels (including original404)+73tokenize+73completionattempts. Earlier20Octreadiness nằm ngoài scoped ledger, không claim all-time total.

69accepted replay requests +48accepted final requests =117semantic execution requests, all native_checked. Native cache thực sự launch126workers (63ordinary+63traced),116ok/10exception,0failed/unknown. Exceptions là completed PUT outcomes. Copied32sharedworkers/16observations là historical preparation, không rerun/countagain; physicaltotal158once.234inferred cache lookups/108hits. Physicallaunch attribution58/44/24 theo arm order không phải normalized efficiency comparison. Explicit PUT-entry counter không có;126new+32historical entry calls **inferred from source/status**, không phải counter emit. Validity checks126new+32historical riêng.

Parent+independent integrity audit PASS:89source/8prepared/approval/Pythonbinary/dependencies/quota guard, copied136shared files, old inventories162/151/4 và newterminal1404 entries exact. generation_frozen1258entries exact. NewterminalinventorySHA2567b4091908b7001050aa6fd94f7057ac2b14888cb50d741ae6ac6bf1d4ab59046. Artifact written before tools theo source và local mtime checks, không có signed external timestamp/fsync proof. Raw usage/body/model/text match, no edited model output. Callback queue0 và callback đã nhận ở original thread; không active controller/auto retry. Quota66% khi bắt đầu callback,45% ở14:14UTC và33% ở14:23UTC; stop15% chưa chạm.

Finite authored fixture truth không phải reference-free semantic proof. Không benchmark, real20, held-out, paid fallback hay training. Readiness/running history vẫn ở PREREG.md, audit.json, launch_progress.json; report này là terminal disposition.
