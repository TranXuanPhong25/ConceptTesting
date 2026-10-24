# Plan hoàn thiện fault-hypothesis → input construction → test evaluation

2026-10-24. User yêu cầu **lập plan để implement phần còn thiếu**. Deliverable của lượt này là plan và cập nhật queue; không đổi generator đã chạy, không score private outcomes và không launch experiment mới.

## 1. Điểm xuất phát đã kiểm tra

V57 đã hoàn tất generation tại `out/pipelines/v57_pathfault/ngrok_pilot6_20261024/generation_v2/`: 78 response slots, 77 JSON được parser chấp nhận, 1 `length` (61/plain/probe1), 79 chat attempts. Cả 6 case có `case_result.json`; `generation_frozen.json` có 405 entries, kiểm tra không thiếu/mismatch. Không còn exact-module v57 runner trong process list lúc kiểm tra. Server usage khớp tokenizer preflight ở cả 78 responses. Chưa private scoring.

**Blocker thật: construction tạo 0 verified input trên cả 6 cases.** Model vẫn viết tests, nhưng nhánh solver chưa cung cấp witness cho experiment này.

| Case | Blocker ghi trong CPU artifact | Những construct khác thấy từ source-only inventory |
|---|---|---|
|61|nested function|while, DP list comprehensions, nested subscripts, append/join, ord/chr, bit_length|
|66|ListComp / set|DP lists, indexed writes, append/join, ord/chr, numeric infinity|
|124|ListComp / set|string processing, append/extend, bisect_right|
|58|nested input sequence|2D points, helpers, dict/set, while, recursive DFS, sorting, local randomized search|
|131|nested function|dict/defaultdict, string→int, modular arithmetic, pow, indexed updates|
|85|Dict|items/append, set, integer arithmetic with ceil, infinity sentinel|

Đây là first-blocker report, không có nghĩa sửa một AST node là cả case sẽ chạy. Các số này đo implementation support, không phải concept efficacy. Sáu cases có thể cùng problem; báo riêng PUT/source/problem identities.

Prior versions phải giữ trong interpretation: v31 package 18 vs plain15, qua gate yếu; v34 18 vs placebo12 nhưng fail FA gate; v35 chỉ là fixed-pool ceiling. V17/v19 cho thấy schema/representation dễ chặn semantic work; v21/v30 cho thấy structural inspection không tự thành verified path. V26–v28 đã thử oracle/model controls; v48/v49 có common-mode oracle failures. V57 hiện cho thấy một support gap cụ thể, không bác bỏ toàn bộ ý tưởng a/b.

## 2. Scope và thứ tự version

1. **Khép v57 cũ:** viết evaluator/diagnostics bên ngoài frozen pipeline, dùng nguyên responses.
2. **Repair/completion version mới:** tên dự kiến `v60_pathfault_complete` vì v59 đã thuộc công việc khác; kiểm tra lại tên trống lúc implement. Theo folder rule, copy best v7 và port các module v57 được chọn bằng manifest, không sửa nguồn run v57.
3. **v58 comparison:** giữ v58 là queue entry cho comparison với explicit error-pattern baseline; sửa dependency để dùng implementation repaired đã freeze. Đây không phải chạy lại chính snapshot v57 với 0 solver witnesses rồi gọi là đã kiểm tra construction.

Ngrok-only, serial; không OpenRouter. Không mở rộng N/K để cứu một kết quả yếu. Current dev6 giữ nguyên làm engineering/diagnostic cohort; không đổi tên thành held-out. Trained UTGen, training-data recreation và code-repair/backtracking không thuộc scope.

## 3. P0 — Khép run v57 bằng evaluator độc lập

**Files dự kiến:** `analysis/v57_completion/{PREREG_SCORE.md,score_frozen.py,evaluator_worker.py,report.py}`. P0A là build/verify scorer trên authored fixtures; P0B mới mở private outcomes. **P1 capability/routes/repair budgets phải freeze trước P0B**, để không chọn support packages theo private wins.

- Freeze scoring definitions trước khi mở reference outcomes; đánh dấu retrospective scoring vì generation đã có và một số raw responses đã được xem. Không giả vờ đây là fully prospective efficacy experiment.
- Verify toàn bộ 405 artifact hashes, request/source/arm identities và mapped cohort/problem IDs. Resolve historical code bằng recorded hashes/commit, không yêu cầu current tree phải byte-identical rồi sửa old protocol cho qua.
- Reuse semantics đã có trong v31 `flow_run.Reference`, `parse_expected`, `same` và isolated worker qua adapter có manifest. Kiểm tra portability trước; không import cả generator để scoring vô tình gọi model. Hỗ trợ `encoded` v57 outputs và original comparator policy; ghi khác biệt typed equality/float tolerance nếu cần.
- Reference và private contract chỉ vào scorer sau freeze. Timeout/unsupported evaluator hoặc missing validity checker là **unresolved/validity unknown**, không gộp thành invalid hoặc pass. Tránh lặp lỗi cũ `contract_valid = status == ok` biến evaluator timeout thành invalid input.
- Primary set: lấy first6 entries từ **raw final response** trước parser/replay filtering, không chỉ `case_result.final.feedback` vì feedback đã bỏ malformed items. Mỗi raw item nhận parse/error/timeout/unresolved label; failed/empty slots vẫn nằm trong all-case denominators. Probes và union qua rounds là secondary, không cộng vào primary. Dedupe theo normalized typed input; expected conflicts phải ghi rõ. Không silently rescore rejected/truncated completions như accepted output.
- Báo confirmed tasks/tests, input discrepancy, expected-output correctness, invalid inputs, false alarms, unresolved, writer-admission/format/truncation và costs. Separate all-case denominators với valid/resolved-test denominators; không để abstention làm precision trông tốt lên mà giấu coverage.
- Report attack, output accuracy, joint success và conditional oracle accuracy on valid revealing inputs. Không coi PUT/mutant difference là true attack.
- Giữ `public-witness-only` theo run cũ. Thêm diagnostic `solver-witness-only` từ saved artifacts: hiện empty; không tạo solver inputs mới cho v57 rồi gán công lao ngược lại.

**Done:** reviewed scorer chạy deterministically trên frozen data; mọi final assertion có label hoặc unresolved reason; có per-problem paired table và failure decomposition. Không đòi positive gain. Nếu reconstruction thiếu dữ liệu thì báo missing, không điền bằng run mới.

## 4. P1 — Viết coverage contract trên code thật trước khi mở rộng engine

**Files dự kiến trong version mới:** `support_inventory.py`, `capabilities.json`, `tests/real_source_contracts/`.

- Inventory toàn entry/method và reachable helpers, gồm input topology, calls, local closures, loops, heap writes và output type. Liệt kê tất cả blocker, không chỉ exception đầu tiên.
- Phân biệt `fully_supported_in_bound`, `partially_supported`, `opaque_native`, `unsupported`, `budget_exhausted`, `no_witness_found`, `bounded_unsat`. Chỉ được nói bounded UNSAT khi representation/query domain được chứng minh đầy đủ trong bound đã nêu.
- Native replay phải chạy được public examples của cả 6 cases, giữ same source semantics và provenance. Failures là engineering blockers, không exclusions tự động khỏi cohort.
- Định nghĩa bounds từ public interface/spec và ghi rõ phần chưa biết; không suy sign/minimum length/character set thành normative domain chỉ vì examples. Input type từ empty examples cần declaration/annotation hoặc unknown.
- Lập golden regression cases cho từng supported operation bằng authored functions; thêm integration checks trên real source/public examples. Đây là compatibility tests, không phải đo bug discovery.

**Done:** có capability matrix đủ cho cả 6 cases, backend route và các gaps còn lại; thêm family/label không được tính là thêm support.

## 5. P2 — Hoàn thiện a: semantic hypothesis và executable obligation

**Files dự kiến:** `concept_contract.py`, `binding_graph.py`, `hypothesis_writer.py`, `hypothesis_validation.py`, `hypothesis_ranker.py`.

Một hypothesis phải giữ các field có vai trò rõ:

```text
spec evidence → required relation
AST/data/control bindings → observed relation
fault hypothesis + applicability → trigger obligation
reach condition + local distinction + propagation target
construction recipe + capability/status + evidence/counterevidence
```

- Writer dùng AST IDs do tool cấp (kèm enclosing function/scope), không bắt model tự đếm UTF-8 column offsets. Exact expression/source binding vẫn được kiểm tra. Cho phép chọn site chưa được solver hỗ trợ và ghi status, không chỉ đưa menu site dễ vào model.
- Tách `source_bound`, `spec_quote_present`, `semantically_supported`, `hypothesis_unverified`, `behaviorally_exercised`, `bug_confirmed`. Quote nằm trong spec không chứng minh interpretation đúng; schema-valid không phải concept-correct.
- Graph phải có definitions/uses, enclosing guards, derived quantities và observable output dependencies. Chẳng hạn `required=k+2` phải nối ngược đến k khi construct len(xs), thay vì chỉ nhặt literal2.
- Những normative claims do model đề xuất được giữ như hypotheses; không âm thầm biến thành hard validity filters hoặc bác bỏ một spec requirement vì PUT vi phạm nó. Unknown/conflicting claims phải hiện trong artifacts.
- Không ép mọi hypothesis phải biểu diễn được bằng một mutant sửa đúng code. Giữ alternative edits như một loại behavioral evidence. Obligation-based recipes cho missing case/relational behavior có representation riêng; việc giải được target predicate vẫn chưa xác nhận bug.
- Ranking tách eligibility, exact binding, recorded coverage gap, verified reach/local distinction/propagation và semantic uncertainty. Không gọi survivor count là bug probability. So với deterministic và random-within-same-pool controls trong diagnostic, không chỉ báo rank1.
- Mỗi proposal được validate riêng; lỗi một proposal không xóa các proposal hợp lệ khác. Rejection/fallback reasons ghi rõ, không được gọi catalog fallback là model đã hiểu concept.

**Done:** reviewer truy được requirement→binding→recipe→trace cho từng retained hypothesis; đúng/sai/unknown đều được giữ trong audit. Không yêu cầu model phải luôn tìm ra đúng hypothesis.

## 6. P3 — Hoàn thiện b: recipe có constraints và backend đủ rộng

**Files dự kiến:** `recipe_ir.py`, `construct_symbolic.py`, `construct_native.py`, `trace_obligations.py`, `stdlib_summaries.py`.

Recipe chứa parameters và quan hệ cần đạt, không chỉ `reverse/±1/duplicate`. Ví dụ MULTIPLICITY ràng buộc đồng thời len(xs)=k+2, k>0, repeated values, path đến count site và output sensitivity; toàn tuple được construct cùng nhau.

**Minimal recipe IR trước khi code:** types `Bool/Int/Str(alphabet)/Seq(T)` (nested sequence depth≤2); expressions `InputRef/LocalRef/Literal/Len/Add/Sub/Mod/Index/CountDistinct`; predicates `And/Or/Not/Eq/Lt/Le/InRange/HasDuplicate/AllDistinct`. LocalRef phải có source definition hoặc exact native frame/event, không được giả là input parameter. Một recipe có `input_topology`, `variables`, `input_predicate`, `site_and_frame`, `event_predicate`, `propagation_mode`, `provenance`, `backend`, `budget`, `status`. Model text được compile vào IR allowlisted, không chạy arbitrary model-generated Python.

**Worked native recipe trên source thật, chưa chạy:** case85 `Solution.minimumSeconds`, bind exact AST expression `math.ceil(max_gap / 2)` và method frame bằng source hash/AST ID. Construction chọn q trong[1,2], n=2q+1, nums có n distinct positive integers; n và nums được dựng cùng nhau. Native execution phải đi qua `len(positions)==1`, quan sát `max_gap==n` và odd(max_gap) ở target call. Candidate alternative `math.floor(max_gap/2)` chỉ là behavioral hypothesis; replay kiểm tra output propagation thay vì tin phép làm tròn cục bộ đủ gây bug. Ví dụ nums=[1,2,3] là một planned candidate, chưa phải measured witness hay confirmed test. Dict/items/helpers chạy bằng CPython trong native backend; không cần symbolic interpreter hiểu toàn bộ thuật toán. Nếu local difference bị masking thì reject certificate, vẫn lưu candidate và reason.

Alternative-free relational/missing-case recipes có thể chứng minh `input_predicate`/event realization; khi không có observed sensitivity hoặc independent oracle thì `output_sensitivity=unknown`, `bug_truth=unknown`. Không gán nhãn infection/propagation đã verified cho trường hợp đó.

**Hai backend, cùng một obligation/replay contract:**

- Symbolic backend dùng Z3 cho subset có semantics đã kiểm chứng và pure summaries. Từng extension phải qua differential semantics tests với CPython. Không tiếp tục viết một interpreter tổng quát chỉ để đổi `unsupported` thành một kết quả thiếu chắc chắn.
- Native backend chạy source thực trong sandbox, dùng generators/strategies có constraints và execution feedback để tìm input. Reuse Hypothesis/trace infrastructure đã có trong repo khi phù hợp. Input candidates phải được dựng từ recipe và joint constraints; uniform fuzzing là control riêng, không được đổi tên thành concept-guided. Native search thất bại chỉ là `no_witness_within_budget`, không phải UNSAT.
- Backend native mở đường cho while/helpers/recursion/library code mà symbolic chưa mô hình được. Không freeze một helper output quan sát được thành symbolic constant cho inputs chưa chạy. Opaque calls không được cấp proof claim.

**Native-first packages (dựa trên source inventory, freeze ở P1 trước private scores):** các construct dưới đây chủ yếu được CPython thực thi thật. Không có cam kết viết symbolic summaries cho toàn bộ sáu thuật toán.

1. **Containers/input topology:** nested lists/tuples, fixed-width point records, dict/set, ListComp, element updates, append/extend/items/defaultdict; preserve aliasing và Python equality/order semantics.
2. **Local calls và loops:** local pure helpers/closures với binding đúng scope; bounded while/break/continue/for-else. Recursion/call effects đi native route trước; heap/state effects ghi rõ thay vì inline vô điều kiện.
3. **String/DP operations:** ord/chr, slicing/indexing, join, integer digit conversion, bisect, pow/modular arithmetic, sentinel infinity. Unsupported numeric semantics không được giả là integers. Pure library summaries phải nêu preconditions và có parity tests.
4. **Mutation/alias/state:** object IDs và before/after state trong PUT để phân biệt reset/update/alias effects; independent copies cho PUT/alternative, giữ alias graph bên trong mỗi execution. Cross-argument alias inputs chỉ thêm khi transport format biểu diễn được rõ, chưa mặc định hỗ trợ qua `repr`.
5. **Missing-case/relational recipes:** validity, cross-argument lengths, duplicate/order/tie, state-transition/loop behavior; semantic trigger không bị giới hạn vào literal replacement. Mỗi recipe cần applicability, target predicate và native realization check. Không thêm taxonomy không có executable recipe.

**Nondeterminism policy:** trước certificates, original-original và alternative-alternative phải lặp lại trong isolated workers với paired RNG seeds20261024/20261025 và fixed `PYTHONHASHSEED`. Mỗi input có hai repeats/program/seed. Không rewrite code/RNG constructors để ép thuật toán thành deterministic. Nếu own RNG/time/external state làm observation không repeatable trong protocol, ghi `unstable/unknown`, không coi noise là PUT/alternative distinction. Case58 vẫn được báo trong denominator, không thay bằng case dễ hơn.

**Verification:** exact AST occurrence/call frame, actual branch path, local predicate realization và returned effect; timeouts/crashes không trở thành normal-return witnesses. Exception-testing, nếu thêm, phải là channel riêng với oracle/metrics riêng. Khi final LLM sửa input, phải replay lại obligation: không thừa kế certificate của input cũ. Các tests không còn realize concept vẫn được chấm end-to-end nhưng không được tính là concept-realized.

**Finite first repair package:** (A) typed nested-input constructors + exact event/frame observer/native replay; (B) ba recipe constructors: joint length/guard, multiplicity/distinctness, index/order/rounding boundary; (C) deterministic certificate + explicit symbolic/native routing. Helpers/while/recursion/library code chạy natively; chỉ thêm tối đa ba pure symbolic summaries nếu P1 chỉ ra chúng cần cho các recipe đã freeze. Không triển khai toàn bộ symbolic containers/heap/stdlib trong package đầu.

**Fixed proposed engineering caps:** mỗi case≤3recipes,≤64constructed candidates,≤256native program executions tổng cộng (tính mọi repeat/PUT/alternative/timeout),≤120s wall budget; worker≤2s/call. Hit cap là budget-exhausted, không retry bằng tăng bound. P1 freeze actual limits cùng routes trước P0B; nếu feasibility cần đổi thì amendment engineering trước private outcome, không điều chỉnh theo wins.

**Done/stop:** trên mỗi real case có public native replay và backend route thực thi được, thay vì whole-case unsupported ở entry. Advertised recipes có positive/negative CPython-checked fixture witnesses; masking, alias, invalid-input và infeasible-path controls pass. Chạy đúng một reference-free CPU diagnostic trên fixed6 và báo yield/status của cả6. Nếu construction vẫn zero, hoặc repeatability/realization fail, đóng first package bằng report; không tự thêm family/summary/budget hay launch v58. Một extension tiếp theo cần hypothesis/plan riêng. Không yêu cầu mọi case phải có discriminating input; engineering completion và positive bug gain là hai việc khác nhau.

## 7. P4 — Nối end-to-end và v58 comparison

**Files dự kiến:** `pipeline.py`, `oracle_stage.py`, `freeze.py`, `resume.py`, `evaluate.py`; v58 có `baseline_adapter.py` và frozen prompt diff.

- Lifecycle rõ: public request → hypotheses → binding/capability → recipe construction → replay-certified evidence → LLM probes/final → final-input realization audit → immutable generation freeze → independent evaluator → report.
- No evidence nghĩa là explicit status; không bơm unsupported hypotheses vào prompt rồi ghi pipeline này là solver-guided success. Có baseline generation fallback nhưng tính riêng fallback yield.
- Runtime expected outputs do model suy ra từ spec với status/confidence được ghi nhận; evaluator reference không được dùng để hoàn thiện assertions trong runtime. `oracle_stage.py` thống nhất interface/policy giữa arms, không tự biến independent scoring oracle thành một runtime oracle miễn phí.
- Resume phải kiểm tra file hashes thật, actual PID/process identity, exact request/model identity và source revision; không chỉ tin `runner.pid`. Source thay đổi sau freeze phải chuyển run mới. Tokenizer ChatML serialization phải được xác minh với actual server `usage.prompt_tokens`; v57 hiện khớp78/78 nhưng không suy ra mọi future model/template đều khớp.
- Start/done/error/status artifacts và monitor/keepalive phải đủ để biết run còn sống; health calls có ledger riêng, không đổi budget experiment. Model call thất bại chưa có completion giữ unknown-usage status; không retry completed/truncated slots để cứu arm.

**V58 primary arms:** plain, explicit-pattern, repaired concept, equal-evidence raw, inputs-only. Thêm public-witness-only và solver-witness-only là các no-model input baselines; nếu cần assertions cho solver witnesses thì dùng cùng oracle stage và tính đúng model cost, không gọi là no-LLM assertions.

**Budget proposal để reviewer chốt trước model calls:** 4 logical calls/arm/case (planning hoặc initial generation; 2 probe rounds; final), cùng model/context, ≤1536output tokens/call và ≤6final tests. Với5arms×6cases, upper bound120completed slots; transport attempts cap riêng2/slot. Đây là budget mới được đề xuất cho comparison tương lai, không tự nới cap78slots của v57.

Plain/pattern được dùng first call hữu ích để lập/generate tests; không charge một shared writer mà baseline không nhìn thấy rồi gọi là matched opportunity. Deep/raw/inputs-only dùng cùng writer packet và tool pool; nếu reuse chung một completion thì report physical calls một lần và allocated logical cost mỗi arm. Match model budget không đồng nghĩa match CPU/solver cost: báo execution/solver/wall budget riêng và không claim equal total compute. Final candidate/test caps và duplicate rules chung.

Explicit-pattern giữ logic Appendix H (hypothesis→pattern→input→expected). Dùng author prompt artifact làm nguồn, lưu mọi format adaptation để chung output schema và loop budget; gọi là **format-adapted prompted baseline**, không trained UTGen hay exact numerical reproduction. Verbatim prompt/parser compatibility là artifact check riêng; không để khác parser làm primary comparison có lợi giả.

Deep/raw có same evidence nên chỉ tách structured obligation/instruction effect; không gọi đó là presence/absence of all semantic information. Pattern→deep là package-effect comparison, qualified by raw/input controls. Code visibility, public examples, known-bug premise và oracle output budget phải ngang nhau.

SC chỉ được đưa vào một diagnostic riêng nếu frozen failure decomposition chỉ ra valid revealing inputs nhưng oracle sai. So trên fixed inputs với matched compute, abstention/coverage rõ. Không tự thêm SC vào một arm hoặc trộn oracle gain thành concept gain. Backtracking thuộc repair task, ngoài scope này.

**Done:** evaluator/manifest/recovery tests pass, engineering support/recipe-realization evidence được review, concrete arms/budgets/prereg được freeze trước launch. Experiment có kết quả bất kỳ vẫn hoàn tất; success của implementation không được định nghĩa là phải có positive concept gain.

## 8. Review và handoff

Thứ tự implementation: P0A build scorer và P1 source-only inventory có thể làm độc lập → **freeze P1 routes/finite packages/budgets** → review scorer → P0B score old run → P2 contracts + P3 native-first package → reference-free CPU diagnostic → P4 integration → v58 nếu mechanism đã hoạt động và protocol được review. Không dùng P0B wins để đổi scope P1 đã freeze.

Review trước code cho contract/backend design; review code trước outcome scoring/new model run theo working rules. Mỗi phần có artifact, tests phù hợp và completion criterion riêng. Review phải tìm semantic counterexamples và real-source integration failures, không chỉ đếm unit tests.

Plan này không hứa full Python hoặc một generic bug oracle. Scope được mở theo operation/recipe contract đã kiểm chứng; case58 có random/recursive helpers cần đặc biệt tách repeatability khỏi nondeterministic differences. Final report phải trả lời cả ba câu: implementation có thực thi mechanism không, mechanism có sinh valid revealing inputs mới không, và các inputs đó có thành assertions đúng không.

**Independent plan review:** reviewer v57_review yêu cầu sửa ordering, raw-response denominators, minimal recipe IR/worked real-source example, native-first finite scope và executable repeatability policy. Các điểm này đã được đưa vào bản cuối; review chỉ đọc source/artifacts, không gọi endpoint hoặc mở private outcomes.

Reviewer đã đọc lại và kết luận **PASS cho plan**; đây là readiness để bắt đầu implementation theo phase, không phải code-complete hay quyền launch v58 ngay.
