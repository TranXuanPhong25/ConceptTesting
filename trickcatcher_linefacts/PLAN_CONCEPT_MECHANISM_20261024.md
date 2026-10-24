# Plan: concept có semantics, điều khiển generation và tạo lợi ích đo được

Ngày: 2026-10-24. Trạng thái: **plan theo yêu cầu của user; chưa triển khai hoặc launch experiment mới**.

Mục tiêu: tìm một cơ chế concept-guided test generation có evidence, hoặc đóng rõ cơ chế không hiệu quả. Không mặc định rằng sửa parser, thêm taxonomy hoặc tăng model strength sẽ tạo concept gain. Không mở rộng cohort/K để cứu một kết quả âm.

**Phạm vi và thứ tự**

`Xác minh artifacts → audit cơ chế → chốt bottleneck → thiết kế tối thiểu → independent review + freeze → diagnostic nhỏ → fresh-cohort confirmation có điều kiện`.

Các gates dưới đây là đề xuất cho công việc tương lai, không thay PREREG hoặc verdict cũ. Phân tích lại outcomes đã biết là retrospective/exploratory. Không coi plan này là quyền chạy paid API, dùng endpoint của session khác hoặc tái hiện paper.

**Snapshot làm cơ sở**

- Đã đọc memory, audit v7–v47 ngày 22/10, source v7/v34/v43/v44/v47, RESULTS v49, và code/PREREG v53 trong cuộc trao đổi này. Không audit từng dòng toàn bộ v7–v54.
- Local v50 `out/pipelines/v50_binding_revision/humaneval/revision8/status.json`: `state=complete`; có `generation_frozen.json`. Đây là trạng thái artifact, chưa phải semantic review PASS hay GO. RESULTS/memory trước đó còn mô tả pending/launch.
- Local v53 `out/analysis/v53_validity_smallscope`: 72 prompt files, 72 answer files; root hiện có `problems.json`, `diag_d1_d2.json`, chưa thấy final score ở root. File count không chứng minh answers hợp lệ, transcript sạch hoặc score chưa tồn tại ở nơi khác.
- `out/` có trong workspace này, bị gitignore. Nhận xét “clone không có out” thuộc môi trường của audit được paste, không áp dụng ở đây.
- V53 PREREG đã có Amendment 1: `concept`, `lines`, `open`, `tool`. Taxonomy comparison với `lines` hiện là report-only. User đã cho phép develop trên dev cohort ở thread đó; fresh claim dự kiến dùng cohort mới, VibePass held-out66 giữ nguyên.
- Repo đang ở `main` với nhiều thay đổi của sessions khác. Chỉ ghi/stage artifacts thuộc plan này.

**Những gì đã thử — phải kế thừa đúng kết luận**

| Nhánh | Điều đã biết | Hệ quả cho plan |
|---|---|---|
| v7/v11, v7_mutref | Facts + witnesses chạy thật; chưa có gain rõ trên matched controls; ranking chưa giúp | Không làm lại một prompt chứa facts rồi đổi tên |
| v12–v20 | Relations/obligations/MR; nhiều lỗi support, binding, interface; một số repairs vẫn null | Không mặc định DSL/card/schema phức tạp hơn sẽ tốt hơn |
| v24/v26/v27 | Contracts/properties có thể sai; model strength thay đổi oracle quality | Spec grounding, validity và oracle phải được kiểm tra riêng |
| v31/v34/v35 | Fault types/templates yếu; alternative outputs không cân bằng; pool ceiling thấp | Tách semantic content, evidence và generator; không cứu template package cũ |
| v40/v43/v50 | Semantic judgment/binding/revision diagnostics trên seen fixtures | Hoàn tất review v50; không coi fixture success là transfer hoặc input-generation gain |
| v41/v44/v47 | Pool có inputs tốt nhưng selection chưa hơn random; menu representation bị giới hạn | Chỉ làm selector mới nếu có failure mechanism cụ thể và evidence cho thay đổi |
| v48/v49/v52/v54 | Oracle family/model strength/validity có tác động lớn; concept effect chưa rõ | Dùng cùng oracle cho input arms; valid-program yield là mediator có thể hợp lệ, không tự loại bỏ |
| v53 validity | Đang kiểm tra taxonomy/extraction với controls tốt hơn | Hoàn tất đúng protocol hiện có trước khi đề xuất phiên bản thay thế |

Đây không phải tuyên bố novelty. Trước implementation mới phải đối chiếu báo cáo prior work trong `research/benchmark-papers-2025-2026/audit/CONCEPT_GUIDED_PROPOSAL_20261021.md` và original sources của những method thực sự liên quan. Không tự reimplement paper.

**1. Xác minh và đóng sổ các runs hiện có — ưu tiên đầu tiên**

Việc cần làm:

- Xác định owner/lifecycle của v50 và v53; đọc status, inventories và callbacks trước khi thao tác. Không duplicate scorer/controller đang chạy; không restart model calls dựa trên thiếu file.
- V50: kiểm tra source/prepared/generation hashes; đối chiếu slots, raw responses, blocked/missing/unknown usage; semantic review theo `analysis/v50_binding_revision_20261023/EVALUATION.md`. Giữ nguyên rubric và gate đã freeze.
- V53: đối chiếu 24 distinct problems × 3 model arms với từng answer; kiểm tra transcript restrictions, syntax/duplicate definitions, strict bool, public-input drop rule và excluded-problem policy. Không suy valid từ số file.
- Tìm final score/verifier hiện có trước khi chạy score mới. Chỉ replay/scoring sau khi review cần thiết đã xong và owner không còn chạy cùng output. Reuse caches, không phát sinh model calls để “làm đầy” mà chưa xác định quyền retry của run đó.
- Báo cáo riêng missing/unparseable/unsupported và số denominator ban đầu; paired exclusion theo protocol vẫn phải hiện rõ attrition. Không biến exclusion thành efficacy success.
- Cập nhật RESULTS/memory trạng thái terminal từ artifacts đã xác minh. Không sửa các log/PREREG cũ để làm chúng trông nhất quán từ đầu.

Deliverables dự kiến: `analysis/concept_mechanism_20261024/ARTIFACT_INDEX.md`, `STATUS_RECONCILIATION.md`; link tới v50 review và v53 result gốc. Chưa tạo các report này trong bước lập plan.

Gate G0: **ready** khi provenance và denominators đủ để kết luận; **incomplete** nếu artifacts còn thiếu; **invalid** nếu integrity/leakage hỏng. Incomplete không được đổi thành negative scientific result. V50 negative không tự dừng audit v53 và ngược lại.

**2. Audit cơ chế từ saved data, không gọi model mới**

Không đọc lại tất cả versions với mức độ như nhau. Các nhóm chính: v7/v11 fairness, v34/v35 attribution/ceiling, v40/v43/v50 semantics, v47 selection, v49/v52/v54 oracle, v53 validity. Versions khác chỉ truy lại khi giải thích một lỗi hoặc tránh lặp ý tưởng.

Tạo một bảng có provenance đến source/run/record cho từng đơn vị problem × PUT × arm × candidate:

| Field | Câu hỏi cần trả lời |
|---|---|
| concept_role | Đây là validity, behavioral requirement, observed relation, coverage gap, hay fault hypothesis? |
| source_and_status | Từ spec, public tests, execution hay model inference? Justified/observed/hypothesized/unknown? |
| semantic_binding | Variables, argument roles, quantifiers, precondition và relation có đúng không? |
| evidence_parity | Arms có cùng input/output/mutant alternatives/tool access không? |
| obligation | Concept yêu cầu tạo tình huống hoặc cặp inputs nào? |
| realization | Generated inputs có valid và thực hiện đúng obligation không? |
| discovery | Input mới hay replay supplied witness? Có đi tới target behavior không? |
| oracle | Correct/incorrect/abstain/timeout? Verdict runtime khác hidden evaluation thế nào? |
| outcome | Confirmed bug, false alarm, no discovery hoặc unresolved? |
| resource | Calls/tokens/PUT executions/oracle executions/CPU time thực tế và cap |

Quy tắc audit:

- Aggregate trên toàn bộ saved cohort thích hợp; semantic deep-review gồm mọi discordant win/loss và một mẫu deterministic của ties/blocked cases, chọn rule trước khi đọc từng case. Không chỉ kể các success examples.
- Tách problem và PUT: nhiều PUT cùng problem không phải nhiều semantic transfers độc lập.
- Mask arm khi thực tế cho phép; independent reviewer ghi bất đồng, adjudication và unknown. Không ép unknown thành đúng/sai.
- “Input khớp obligation” là alignment evidence; chưa chứng minh concept gây ra input. Model tự viết rationale cũng không phải causal proof.
- Hidden reference chỉ ở evaluator. Nhãn audit có thể dùng cho thiết kế dev, nhưng không được chuyển gold relation/expected value/bug location thành prompt và gọi đó là automated discovery.
- Dùng aggregate intention-to-treat làm kết quả tổng; phân tích conditional trên admitted/valid outputs là diagnostic. Không suy zero total effect từ subset hậu-treatment.
- False alarms: cùng cap và refill policy; ghi cả absolute counts, precision và task-level burden. Không đổi verdict v49; chỉ báo cáo retrospective normalized comparison riêng.

Deliverables: `MECHANISM_MATRIX.jsonl`, `MECHANISM_AUDIT.md`, `EVIDENCE_PARITY.md`, `FAILURE_TAXONOMY.md` trong analysis folder mới. Chỉ lưu artifacts nhỏ không chứa secrets; raw responses giữ ở run gốc.

Gate G1: mỗi hướng chỉ được tiếp tục nếu có **failure mechanism quan sát được, một thay đổi cụ thể giải quyết nó, và một phép đo có thể bác bỏ giả thuyết**. Nếu chỉ có “concept chưa hay”, “model yếu”, “thêm tasks” hoặc “thêm taxonomy”, dừng hướng đó. Không cần tạo version mới chỉ để hoàn tất audit.

**3. Chốt định nghĩa concept và phạm vi hỗ trợ**

Concept = abstraction có ý nghĩa cho con người, dùng lại được trong một phạm vi công bố, bind vào task bằng evidence. Handwritten vocabulary và tool-derived instances đều hợp lệ; exact answer template cho từng task không chứng minh generality.

Contract tối thiểu của một concept instance:

| Thành phần | Yêu cầu |
|---|---|
| Semantic definition | Một property/relation có quantifiers và typed roles; category label chỉ là metadata |
| Applicability | Spec clauses và điều kiện khiến relation áp dụng; ambiguous/unsupported trả unknown |
| Binding | Task parameters/values nào đóng vai trò gì; không dựa vào tên biến cố định |
| Evidence | Spec evidence tách khỏi finite PUT observations và inferred hypotheses |
| Gap | Obligation nào chưa được suite kiểm tra, đo bằng execution/input relations khi phù hợp |
| Test obligation | Điều cần thay đổi, điều phải giữ, outcome relation cần quan sát |
| Verification | Kiểm tra validity và obligation realization riêng; behavior checker không chứng minh spec entailment |

Phân biệt năm vai trò ở trên trong schema. Không dùng agreement với PUT để xác nhận normative requirement. Passing public examples chỉ là sanity check, không chứng minh validator/relation sound.

Deliverable: `CONCEPT_CONTRACT.md` với một vài worked examples và counterexamples, supported/unsupported domain, traceability. Không xây universal ontology hoặc toàn bộ symbolic engine. Không thêm một operator riêng cho mỗi failing benchmark task.

Ví dụ minh họa có điều kiện: spec yêu cầu tổng đóng góp của các cặp `(value[i], weight[i])` và không phụ thuộc thứ tự cặp. Khi đó simultaneous permutation bảo toàn pairing và output; permutation một array riêng không phải relation hợp lệ. Example này là minh họa contract, không phải evaluator fixture để claim success.

Gate G2: từng admitted concept phải có spec justification và checker semantics được review; không có known unsound admitted rule. Unsupported/unknown giữ trong denominator end-to-end. Đo breadth thật trên eligible dev set, không chỉ correctness trên supported subset. Nếu abstraction chỉ giải đúng authored fixtures, giữ nó là diagnostic và dừng promotion.

**4. Quyết định implementation tối thiểu theo bottleneck thực tế**

| Failure đã được xác nhận | Thay đổi được xem xét | Bằng chứng phải có trước run |
|---|---|---|
| Parser silently hiểu sai bound | Parser/library nhận đúng hoặc explicit unsupported; test cả partial-token rejection | Các phản ví dụ cũ pass; unsupported không biến thành bound sai |
| Sampler phá cross-argument constraints | Joint construction theo dependency, constrained sampling khi phù hợp | Validity + diversity + exposing-input retention trên saved data |
| Binding sai dù syntax đúng | Role-aware contract và semantic validation; unknown khi thiếu evidence | Review các raw failures; test argument swap, scope, quantifiers, unsupported |
| Generator không thực hiện obligation | Generate strategy/pair theo relation; executable obligation check và bounded feedback | Relation coverage thực sự thay đổi, không chỉ wording |
| Interface loại output đúng | Item-level admission, parser repair có giới hạn, errors hiển thị | Regressions từ raw failures; malformed item không xóa valid siblings |
| Oracle sai/common-mode | Cùng oracle độc lập PUT cho mọi input arm; validated spec-only programs khi phù hợp | Existing oracle diagnostics; abstention/FA tách khỏi generation |
| Không có exposing input trong pool | Xem construction/value abstraction, không chỉ selection | Reach diagnostic; resource feasibility; không suy reachability ngoài pool từ finite failure |

Chỉ chọn các hàng thực sự cần sau G1, không mặc định làm tất cả. Engineering fix chưa phải concept contribution.

Small-scope search cần cap cả structure size, value domain và số candidates. Ví dụ length ≤10 với mỗi phần tử có D giá trị vẫn có D^10 arrays; chưa kể relational combinations. Dùng spec boundaries/equivalence classes chỉ khi justification phù hợp, khai báo phần domain bị bỏ. Exhaustive chỉ trong finite domain đã ghi rõ; random/constraint sampling và exhaustive phải có equal-budget control.

Mọi sửa pipeline ở folder version mới, số version được kiểm tra lúc tạo để tránh collision; copy parent theo workflow repo, ghi `PARENT`/ports và CHANGELOG. Không sửa source frozen v50/v53, best pipeline hoặc vendor. Reuse thư viện hiện có khi phù hợp; không viết mô phỏng paper.

Deliverables nếu G1/G2 cho phép: implementation plan, changed-hypothesis statement, code trong version mới, CPU regressions từ failures thật, resource estimate. Không cần bộ tests chỉ kiểm tra lại constants/schema đơn giản.

**5. Protocol để tách semantic content, structure và tool evidence**

Hai câu hỏi khác nhau: (a) semantic abstraction có giúp trên cùng evidence không; (b) typed/structured representation có giúp thêm trên cùng semantic content không? Không yêu cầu labels phải thắng để công nhận một semantic relation hữu ích.

| Arm đề xuất | Nội dung |
|---|---|
| D — direct | Spec/public tests/PUT và tool interface chung, không supplied concept packet |
| R — raw evidence | D + raw tool evidence dùng để tạo concept; gồm cùng mutant alternatives/outputs nếu có |
| S — semantic text | R + cùng semantic propositions, conditions và obligations như C, viết dạng prose không taxonomy/typed organization |
| C — structured concept | R + contract ở bước 3, bind đúng roles và explicit obligation |
| W — tool/witness-only | Replay hoặc generate bằng tool chung, không generation LLM; report toàn bộ preprocessing/oracle cost |

C−R là semantic-package effect; S−R kiểm tra semantic content ở dạng prose; C−S kiểm tra thêm structure/taxonomy. C−D đánh giá practical package. Nếu C≈S>R, có thể có semantic content effect mà taxonomy không giúp. Nếu C chỉ hơn D nhưng không hơn R/W, chưa chứng minh concept adds value.

Same evidence: R/S/C phải nhận cùng observations, PUT outputs, mutant outputs, source context và feedback access. C/S không được có extra oracle label hay gold binding. Shared concept extraction dùng public/runtime evidence và được tính cost; gold cards chỉ dùng ở một diagnostic được gắn nhãn gold-assisted, không đưa vào efficacy headline.

Matched budgets: cùng model/config, maximum calls/output tokens, input/execution/oracle caps, timeout, retry/repair policy và candidate cap. Ghi token lengths và actual usage; không giả vờ prompts dài khác nhau có actual cost bằng nhau. Primary claim ở fixed declared budget; cost sensitivity report riêng. Không ép cùng generated inputs khi đang đo generation, nhưng dùng same-input replay để diagnostic oracle.

Intervention diagnostic: bỏ semantic relation hoặc gap khỏi packet, giữ raw evidence và mọi resource cap; đo thay đổi về obligation realization và distribution của generated inputs. Đây là diagnostic attribution riêng; không dùng intentionally false relation làm main control rồi claim thắng baseline. Nó không chứng minh causal bug mechanism nếu nhiều semantic dimensions cùng thay đổi.

V53 hiện có giữ nguyên registered `concept/open` decision; `concept/lines` report đúng vai trò. Nếu muốn taxonomy là primary hypothesis của run mới, prereg trước outputs mới. Không sửa retrospective threshold của v53.

**6. Review, freeze và diagnostic nhỏ có stop rule**

Chỉ đến đây khi G1/G2 có bằng chứng và implementation cần thiết đã pass CPU checks. Independent read-only review theo working-rules trước tính outcomes mới: practicality, semantic correctness, library use, evidence parity, evaluator isolation, plan adherence. Fix must-fixes bằng prospective amendment; freeze source/prompts/cohort/seeds/metrics/dependencies sau đó.

Diagnostic budget đề xuất cho protocol mới, chưa được launch:

- Tối đa 6 distinct dev problems, chọn deterministic theo supported domain và coverage strata, không chọn theo Qwen fail/concept win. Nếu không đủ eligible problems, báo limited support; không bù bằng authored fixtures.
- D/R/S/C: tối đa 2 calls/problem/arm = 48 generation calls; cùng một bounded feedback opportunity. Shared automated extraction nếu cần: tối đa 1 call/problem = 6 calls, tổng cap 54. W không generation call. Không thêm model sweep.
- Intervention diagnostics dùng saved outputs trước; nếu cần inference riêng phải có explicit budget/PREREG riêng, không lén cộng vào 54.
- Chọn model sau artifact/capability audit; ưu tiên model đang được phép dùng và chứng minh thực hiện được task. Trước launch phải điền exact model/version, token caps, PUT/oracle execution caps, wall time và dollar ceiling. Chưa biết giá/capability thì chưa launch, không substitute âm thầm.
- Không trả thêm calls để cứu semantically wrong answers; transport unknown ghi riêng và theo retry policy đã freeze. Reuse complete cached slots khi được protocol cho phép.

Metrics và gates phải chốt trước outcomes của diagnostic mới:

| Lớp | Metric / quyết định |
|---|---|
| Semantics | Binding correctness, known-unsound/unknown rate, supported breadth; sai normative rule gây FA là must-stop của rule đó |
| Action | Valid-input rate, obligation realization, newly exercised obligations; invalid input không nhận coverage credit |
| Discovery | Confirmed bug tasks theo problem/PUT, new beyond supplied witnesses, false-alarm tasks/tests; include all assigned tasks |
| Cost | Actual tokens/calls/time/PUT+oracle executions, abstention và resource failures |
| Attribution | R/S/C contrasts; alignment của wins với obligation; intervention evidence nếu có |

Gate G3 đề xuất cho promotion, **không phải significance claim**: C có positive net confirmed-task gain so với R trên ít nhất 3 distinct problems (net gain ≥3), không kém D hoặc W về confirmed tasks ở budget đã định, không tăng false-alarm task/test burden ở matched emission cap; gains có obligation realization và không chỉ replay witness. Không cần C>S nếu S cũng dùng đúng cùng semantic content; khi đó claim về semantics, không claim structure. G2 vẫn phải đạt; mọi exclusions/unsupported giữ được truy vết.

Nếu C cải thiện obligation coverage nhưng chưa tăng confirmed bugs, đó là mechanism signal chưa đủ promotion; phân tích saved data xem oracle hay reach chặn, không tự tăng N/K. Nếu C≈R hoặc các wins không gắn với obligation, đóng mechanism hiện tại. Chỉ mở lại khi có hypothesis khác cụ thể và evidence, không chỉ sửa prompt rồi thử tiếp.

Các con số G3 là operating rule đề xuất cho feasibility, phải được reviewer xem xét trước registration; không diễn giải 6 problems thành ước lượng hiệu quả tổng quát. Fixed-budget decision và uncertainty đều phải report.

**7. Fresh-cohort confirmation — chỉ sau G3**

- Cohort phải chưa dùng để viết vocabulary, templates, gates hoặc xem hidden tests. Giữ grouping theo problem, deduplicate với dev, ghi selection dates và exposure history; “fresh với mình” không chứng minh model chưa từng training trên nó.
- Theo hướng user đã chọn trong v53: kiểm tra tính phù hợp của fresh LiveCodeBench trước, gồm public/hidden separation, plausible buggy PUTs và evaluation contract. Tên benchmark mới một mình không đủ; không đụng VibePass held-out66 của protocol cũ.
- Freeze taxonomy, binding/generation policy, oracle, budget, eligibility và unsupported policy trước khi nhìn outcome. Cohort size lấy theo minimum useful effect và analysis plan, không theo việc run trước đang gần đạt gate.
- Chạy một registered confirmation với matched controls và independent evaluation. Cluster theo problem, report paired wins/losses + uncertainty, false alarms, support breadth và cost. Thay method sau xem outcome thì cohort đó thành dev; không tiếp tục gọi held-out.
- Nếu không transfer hoặc control ngang/tốt hơn: kết luận negative theo phạm vi, không mở benchmark tiếp để tìm bảng đẹp.

**8. Artifacts, thứ tự bàn giao và định nghĩa hoàn thành**

| Ưu tiên | Deliverable | Phụ thuộc | Tình trạng lúc lập plan |
|---|---|---|---|
| P0 | Artifact index + v50/v53 terminal reconciliation | Existing run ownership/integrity | Chưa làm; mới kiểm tra inventory tối thiểu |
| P1 | Mechanism matrix, evidence parity, failure taxonomy, go/no-go theo hướng | G0 | Chưa làm |
| P2 | Concept contract + implementation choice hoặc STOP report | G1 | Chưa làm |
| P3 | Minimal implementation + CPU checks + independent review + PREREG/freeze | G2, quyền triển khai/run tương ứng | Có điều kiện |
| P4 | Diagnostic report với all-arm denominators và G3 verdict | P3, budget đã chốt | Có điều kiện |
| P5 | Fresh-cohort protocol/confirmation và final research claim | G3 | Có điều kiện |

Hoàn thành plan này khi đã chỉ rõ đường đi, deliverables và stop rules; hoàn thành research không đòi hỏi positive result. Một STOP có evidence và attribution rõ là kết quả hợp lệ. Nếu có positive result, claim phải nói rõ concept role, domain, model, controls, budget, transfer và limitations.

Sau mỗi finding: cập nhật memory index, RESULTS/CHANGELOG thích hợp và version tree khi có variant mới; commit/push chỉ own files lên `main`, không AI attribution. Không ghi secrets hoặc endpoint URLs. Không chỉnh lịch sử để che negative results.

**Việc tiếp theo khi bắt đầu thực hiện:** P0, sau đó P1. Chưa tạo v55, chưa launch calls, chưa sửa frozen source, chưa chọn benchmark mới để cứu kết quả.

**Execution checkpoint — 2026-10-24, sau khi user nói "làm đi"**

P0 và P1 hoàn tất; P2 concept contract đã được independent review như evaluation specification. Artifacts nằm ở
`analysis/concept_mechanism_20261024/`:331matrix rows với scope rõ, full v50 semantic review, v53 source/transcript/
reference/postscore review, historical discordant-case audit và evidence-parity/failure reports. V50 registered
NO-GO (0tool-onlywins,E8fail); v53 primary not promising (concept/lines/open masks identical trên32,311inputs,
recall margin0). Original gates và verdicts lịch sử giữ nguyên. Không có new generic concept-guided input mechanism
đạt G1 để mở P3–P5; các bước có điều kiện này không được launch. Những engineering hypotheses về joint validity
construction/oracle enumeration chưa phải concept contribution. Xem MECHANISM_AUDIT.md để biết STOP/CONTINUE theo
từng hướng. Không phát sinh model calls/paid API/held-out use; CPU scoring chỉ dùng72answers có sẵn.
