# Concept catalog và diagnostic D1

Design ngày 20–21/10/2026; chỉ thiết kế, không có model/API/native-worker run từ design agent. Parent đã nhận authorization chạy exact `qwen2.5-coder-32b-instruct`; metadata endpoint do parent kiểm tra cho context8192. Parent triển khai trong `pipelines/v40_concept_agent`, vì v37–v39 thuộc session khác. Không sửa các pipeline/output frozen.

**Khuyến nghị:** triển khai D1 như một mechanism diagnostic nhỏ. Câu hỏi chính là model có phân biệt premise sai, hypothesis sai và observation chưa đủ hay không; sau feedback có đổi query theo evidence hay không. Không xây thêm semantic chain, template miner, training head hoặc benchmark sweep trước kết quả này. Catalog là vocabulary đề xuất, chưa có evidence rằng nó tốt hơn direct testing.

## 1. Concept, dimension, instance và hypothesis

- **Concept** là reusable semantic relation do human định nghĩa, ví dụ occurrence conservation. Nó nói chính xác điều gì cần được giữ, và điều gì relation chưa kiểm tra.
- **Dimension** là input axis để tạo contrast: multiplicity, eligibility, threshold equality, subset slack, vị trí, tie, aggregate, empty eligible set. `empty` hoặc `boundary` tự nó không phải một semantic concept.
- **Binding** gắn relation vào spec, argument, output projection và domain của một task. Quote là provenance, không phải chứng minh entailment. Một quote đúng có thể đi cùng interpretation sai.
- **Informational concept instance** = bound relation + tool-measured finite gap/contrast/uncertainty. Ví dụ: “trong base rows, mọi eligible value xuất hiện tối đa một lần; chưa quan sát duplicate case”. Đây là thông tin execution/test adequacy. Chỉ lặp lại spec hoặc gắn AST tag không tạo ra empirical fact mới.
- **Hypothesis** là claim falsifiable về implementation, trigger và output, ví dụ “duplicate occurrence có thể bị mất ở returned list”. Nó có thể sai dù normative binding đúng. Claim “set tồn tại ở source” không đủ thành output mismatch.

Catalog có ba nhóm, không coi chúng là mutually exclusive labels:

| Nhóm | Concepts | Vai trò |
|---|---|---|
| Collection content | occurrence_conservation; membership_inclusion | Phân biệt bag semantics với set semantics và direction của inclusion |
| Selection and combination | quantified_decision; eligible_contribution; order_policy; eligible_selection | Phân biệt eligible domain, aggregation, ordering và selection rule |
| Domain outcome | defined_outcome | Quy định allowed return/exception/sentinel trên domain, nhất là degenerate cases |

Mỗi entry trong [catalog.json](catalog.json) có intent, activation/exclusion/ambiguity, parameter/type/domain, dimensions/search moves, observable relation và oracle scope, minimal contrast, measured-gap example, unsupported modes và standard-library implementation phù hợp. Đây là catalog đọc cho human; **không render nguyên entry vào model**.

Các concepts có thể overlap nhưng nghĩa không nhập làm một. Sorting thường cần cả occurrence_conservation và order_policy; count và sum cùng eligible_contribution nhưng weight khác; min-positive cần eligible_selection và defined_outcome. Relation cần thiết chưa chắc là complete oracle: sortedness không giữ multiplicity; subset monotonicity có thể bị constant-True function thỏa mãn; eligibility không chứng minh minimum/first.

Lý do chọn catalog này: mỗi entry chỉ ra input contrast có thể thực hiện và claim nào contrast đó có thể bác bỏ. Nó tách normative relation khỏi local operation, tránh coi MUTANT/STMT/BOUND rename là concept mới. Tradeoff: subset int/list nhỏ có scope dễ audit; sẽ bỏ nhiều Unicode, float, object identity, mutable state và domain phức tạp. Không tăng coverage bằng cách mặc định mọi unsupported binding đều đúng. Generic input exploration vẫn được phép khi binding unknown.

## 2. Ownership và evidence

| Owner | Được quyết định | Không được tự chứng nhận |
|---|---|---|
| Human | Vocabulary, relation semantics, dimension meanings, supported types, diagnostic fixture contract, scoring rules | Không gọi mẫu được chọn là representative benchmark |
| LLM | Spec binding đề xuất, hypothesis, query, prediction, keep/revise/withdraw/unknown | Không tự cấp nhãn đúng cho oracle do chính nó viết |
| Tool | Native values/exceptions, input measurements, trace/reach và finite coverage counts | Không chứng minh spec interpretation, universal correctness hoặc unique cause |
| Evaluator | Fixture truth, relation/binding correctness, bug-revealing input, failure attribution | Không đưa expected output/hidden witness/labels trở lại model context |

`candidate` là chưa kiểm chứng; `keep` giữ claim trong scope được nói rõ; `revise` thay đổi nội dung có evidence; `withdraw` bỏ claim cũ; `unknown` ghi rõ thiếu premise/evidence. Giữ normative unknown không chặn một input exploratory hợp lệ. Không có global concept gate làm các task khác mất generation stage.

Một native observation trái với prediction cụ thể bác bỏ prediction đó. Một valid counterexample trái universal implementation claim bác bỏ claim trong declared scope. Finite passing rows chỉ hỗ trợ hữu hạn. Native output không quyết định intended output; một trace đi qua operation không chứng minh effect tới return. Local dedup không phải bug khi return vẫn dùng original input. Domain filter là operational acceptance với provenance, không tự chứng minh toàn bộ spec domain.

Tool chỉ trả observed output/exception và observation limits. **Không trả `relation_violated`, `bug=true`, expected output, reference output hoặc score**. Nếu model lặp lại tool verdict thì không đo được reasoning; D1 tránh đường tắt đó. Human-authored normative relations trong concept treatment được công khai là supplied semantics của diagnostic, không giả vờ là extraction của model.

## 3. D1: selective revision và execution-query adaptation

Machine-readable plan: [d1_protocol.json](d1_protocol.json), public construction manifest [d1_packets.json](d1_packets.json), evaluator-only [d1_evaluator_private.json](d1_evaluator_private.json). Original fixture source/spec/base lấy từ `v23_concepthyp/pilot_fixtures.py`, evaluator dùng `fixture_oracles.py:expected(case,literal)` của cùng version. Không dùng một evaluator subset của version khác.

| Episode | Nguồn | Challenge | Vai trò injected native row |
|---|---|---|---|
| E1 | f02 | Multiplicity relation đúng; hypothesis overgeneralize theo length | Refute length-only claim, không tự reveal bug |
| E2 | f04 | Equality-boundary hypothesis đúng | Passing non-equality row không bác bỏ hypothesis |
| E3 | f06 | Normative equality binding sai, quote cho phép extras | Supplied revealing row; premise calibration |
| E4 | f08 | Empty-eligible outcome hypothesis đúng | Normal return trên nonempty eligible set không bác bỏ hypothesis |
| E5 | f12 | Sign hypothesis sai; cần tách length khỏi aggregate | Refute sign claim, không tự reveal bug |
| E6 | f16 | Dedup có thật nhưng “only fault” sai | Supplied revealing row bác bỏ exclusivity |
| E7 | f14 | Local set không propagate tới return | Refute output-loss claim trên duplicate case |
| E8 | f13 | “Suitable” undefined | Behavior observation không định nghĩa normative predicate |

Đây là seen authored fixtures, không phải new tasks và không phải generalization result. E3/E6 đã có supplied revealing observations: báo replay/witness-only floor riêng. Chỉ E1/E2/E4/E5 thuộc no-supplied-witness discovery denominator. Một input mới không tạo thành task mới nếu task đã exposed bởi shared row. Novel input phải so với **union toàn bộ public base, injected rows và shared input pool của diagnostic**, không chỉ pool của arm; đối với historical fixtures, không claim chưa từng xuất hiện trong repo nếu chưa kiểm tra historical pools.

Ba arms dùng cùng source/spec/base, fallible initial hypothesis và raw observations:

1. **concept_adaptive:** thêm allowlisted catalog semantics + binding + measured gap; chọn query sau mỗi feedback.
2. **generic_adaptive:** không có catalog/binding/gap summary; vẫn có cùng initial hypothesis, raw input/output và tool budget. Model có thể tự suy ra semantic relation.
3. **concept_committed:** cùng concept packet; commit cả hai query batches trước feedback. Turn2 vẫn được sửa claim; final inputs vẫn adaptive. So sánh này chỉ isolate **intermediate execution-query adaptation**, không phải mọi hình thức adaptation.

Turn1 gửi claims + batch1 queries; committed arm thêm batch2 vào `later_queries`. Sau turn1, mọi arm nhận cùng injected native row và own batch1 results. Turn2 cập nhật claims; adaptive arms chọn batch2, committed arm dùng nguyên batch2 đã lưu. Sau batch2, turn3 nộp final claims và tối đa2 input literals. Không có extra repair turn hoặc model gọi oracle. Predictions phải ghi trước khi query chạy; evidence IDs do controller cấp.

Initial hypotheses là fallible suggestions, model không phải nhận chúng là đúng. **Proactive correction trước feedback là thành công calibration nhưng không được tính feedback-driven revision.** E3 có thể bị bác bỏ ngay từ spec/catalog; không dùng E3 để chứng minh causal feedback use. Với E1/E5/E6/E7, report initial endorsement, proactive rejection, actual unresolved opportunity, post-feedback revision và useful next query riêng. Nếu đã giải quyết từ source/turn1, không ép model làm sai để tạo opportunity.

Budgets: 8episodes ×3arms ×3turns =72 task completion attempts; tối đa1 canary riêng nếu cần. Mỗi arm/episode tối đa6 actions,4 in-round replays,2 final inputs. Actions sai/duplicate vẫn charge theo disclosed contract; valid sibling không bị xóa bởi invalid action. Combined runtime tối đa160 native requests gồm16 shared rows, tương đương320 ordinary+traced worker processes nếu mỗi request dùng cả hai. Preflight CPU bank riêng tối đa64 inputs/episode,512 native requests; report riêng, không gọi chúng là model successes.

Qwen target context8192: proposed prompt ceiling6144 tokens including full history/template, output1536; tokenizer/template phải được parent kiểm tra trước launch. Tổng task ceilings442368 input/110592 output tokens. Nếu packet không fit, stop preflight; không truncate evidence hoặc silently drop caps. No automatic transport/content retry/fallback. Raw unknown usage giữ unknown. Quota threshold mới do user sửa là **remaining<15%**, thay cho20%; parent sở hữu check/schedule.

## 4. Runnable contract và implementation checklist

[reply.schema.json](reply.schema.json) là envelope nhỏ: tối đa3 claims; mỗi claim có kind, statement, stance, evidence; mỗi query có native action, claim link, prediction, why. Action validate bằng exact published v30 tool-specific schema cho allowlist inspect_flow/inspect_data/replay_input. Không expose check_path trong D1: giữ experiment nhỏ, không cần structural path truth cho primary outcome.

Schema **chưa phải runner hoàn chỉnh**. Parent cần thêm những checks sau trước run:

- Enforce turn/arm-specific rules: `later_queries` chỉ có ở committed turn1; turn3 không execute queries; committed batch2 immutable; mỗi batch tối đa3actions/2replays. Không chỉ tin `maxItems` của JSON schema.
- Validate raw single JSON object, bounded literal parsing với `ast.literal_eval`, full positional argument tuple, exact int/list types (bool không là int), arity, resource caps và no executable expressions. Publish caps. Schema `action` intentionally không duplicate v30 validators; cần join tool schema thật và test mismatch giữa prompt/dispatcher.
- Outer parse failure là recorded content failure. Semantic claim failure không thành admission gate cho valid input. Khi action list parse được, validate từng action độc lập; preserve raw invalid payload và valid sibling results. Không silently rewrite invalid claims/actions hoặc fill missing predictions.
- Những claim có evidence ID không tồn tại chỉ là grounding failure. Tool không resolve claim thành đúng/sai. Unknown/retracted claims vẫn cho generic exploration trong budget.
- Output predictions là untrusted model text. Parse/schema validity không phải prediction accuracy. Independent semantic audit kiểm tra prediction→native result→revision; không dùng keyword “revise” hoặc query-string change làm success.
- Public payload là allowlist projection. Catalog `minimal_contrast`, `tool_gap_example`, `unsupported_failure_modes`, `implementation`, full private file, fixture IDs/evaluator fields và reply examples không được render. Private examples chứa concrete witnesses. Production format example chỉ dùng unrelated identity function.
- Recompute gap counts từ base arguments, không tin prose manifest. E3 đo extra-count độc lập với intentionally wrong normative equality. E8 không có predicate nên gap unknown, không phải zero observed eligible cases. Test counts trên base/injected row union và measurement provenance.
- Fresh context per episode/arm, no filesystem/shell/web/reference access. Separate evaluator directory/process from prompt builder; explicit field allowlist + packet snapshot audit. Không flatten source object có nested evaluator metadata vào prompt.
- Freeze source/config/prepared packets trước first completion; freeze generation trước scoring. Parent runtime must journal calls/actions/process reservations and reject drift. Không sửa frozen v30, source fixtures hay old runs.

First supported subset: pure terminating fixture functions trên list[int] và integer limit; actual source nhỏ, declared normative predicates đơn giản. `Counter`, set inclusion, sum, all/any, min/max và existing native worker đủ; không cần expression DSL, symbolic engine hoặc synthesized Python trigger. Resource-limited inputs phải được phân biệt với invalid-spec inputs. Parent chọn/publish finite size bounds trước launch, không dùng invisible filters.

Prompt skeleton cho mọi arm:

> Bạn kiểm tra implementation theo original spec. Initial hypothesis và optional concept binding đều có thể sai hoặc chưa đủ. Native observations là behavior của PUT, không phải expected oracle. Chỉ dùng tools đã công bố. Trước mỗi query nêu predicted observation và observations nào sẽ đổi claim. Có thể keep/revise/withdraw/unknown. Unknown semantics không cấm exploratory inputs. Trả một JSON object theo envelope; mọi action, replay, turn và context cap được ghi dưới đây.

Thêm original spec/source/base, untrusted H, arm-specific projected packet, cumulative observations, exact tool schemas và remaining budgets. Controller không thêm words “correct”, “wrong”, “counterexample” hoặc private roles vào native feedback. Feedback error chỉ nêu contract/error field và quota còn lại. Không biến reasoning instruction thành bắt buộc nhận sai H.

## 5. Metrics và stop

Report đủ24 episode-arm rows,72 completion slots và8 episode denominators. Phân loại not_attempted, transport, parse, action validation, unusable native, wrong premise, wrong evidence interpretation, stale hypothesis, invalid-domain input, search miss và unsupported oracle. Không gộp unattempted generation vào failed synthesis. Record actual requests/tokens/replays/caches/processes riêng; equal maxima không phải actual token parity.

Primary capability checks cho concept_adaptive: final valid8/8; false/overbroad H handled4/4; correct H retained2/2; E3 wrong binding rejected; E8 normative unknown; không false bug flag ở E7/E8; useful replay/contrast và final input ở ít nhất3/4 no-supplied-witness buggy episodes. Đây là engineering gate cố ý nghiêm trên fixture dễ, không phải statistical threshold.

Incremental concept signal: trên E1/E2/E4/E5, ít nhất2 concept-only discoveries,0 generic-only loss, không tăng unsupported bug claims. Adaptive-query signal riêng: ít nhất2 useful evidence-linked adaptations mà committed arm bỏ lỡ trên actual unresolved E1/E5/E6/E7 opportunities. Nếu dưới2 opportunities do source/first queries đã giải quyết, comparison ceiling-limited, không được tự thêm cases. Combined mechanism cần cả hai signals; capability pass một mình không đủ.

Generic bằng hoặc mạnh hơn concept → **không có incremental concept claim**. Đừng tăng n/K, đổi score sau kết quả, đào lại pool hoặc train concept-to-input để cứu kết quả. Committed bằng adaptive → không có observed execution-query adaptation gain. Model bắt đúng task chỉ nhờ supplied witness → witness reuse, không phải discovery. Correct assertion do model viết không phải input gain và được score riêng nếu có; D1 final inputs không yêu cầu model-authored expected values.

Các gates có thể fail vì simple fixtures ceiling. Đó là giới hạn được biết trước; purpose hữu ích còn lại là mechanism capability/failure diagnosis. Không bán pilot này như experiment có khả năng chắc chắn chứng minh thesis.

## 6. Prior art: phần mới thật sự nhỏ

| Proposal/component | Prior art và result | Phần mới / overlap chưa giải quyết |
|---|---|---|
| Relation vocabulary + measured gap | v7/v11 grounded facts/witnesses; v11 concept vs matched placebo26/22, toolinput64.3 vs concept61.0 | Không mới ở grounded fact. Catalog làm semantics/unsupported/domain/search dimensions rõ hơn; chưa evidence tốt hơn |
| Hypothesis-guided generation | v13 hyp46.33 vs flat62.67/toolinput63; v23 Luna concept5/7 vs direct7/7 | Không mới ở đưa hypothesis. D1 đo selective correction với known correct/incorrect/ambiguous packets và precommitted predictions |
| Relational/property concepts | v14 graph rất thưa; repaired v15 có41cards/16tasks nhưng MR5 vs blind5 và3candidate reports đều FA | Không gọi MR là novelty. Human supplied relation scope được công khai; không chứng minh extraction hoặc soundness trên real specs |
| Small typed relations | v16 DSL gate0/20; v17 templates2/20; v18 rule12≥LLM11; v19 no gain, format bottleneck | D1 không build compiler/menu selection; stdlib measurement + small JSON action envelope. Supported subset vẫn hẹp |
| Reach/propagation evidence | v20 narrow CPU mechanism; v24 f06 six novel revealing inputs all gated; v32 CPU48pass, fresh Atrue/Bfalse/Cblocked | D1 không hard-gate generation trên hypothesis support; wrong premise vẫn search được. Không claim concept caused v24 inputs vì hypothesis đã bị ẩn |
| Active agent replay | v21 Qwen pilot replay0/path0; v30 contract54/54CPU, paired10 prepared_waiting_endpoint | V30 là contract basis, chưa model proof. **Active replay không mới**, xem v28 ngay dưới |
| Stronger-model tools/oracle | v26 unsound properties; v27 stronger strict oracle cải thiện; v28 mọi arms16–17/20, agent16/plain16/fixed16/toolinput17 | Parent read-only v28 audit:69actions gồm58replay+10flow+1data;35accepted replays,33native_checked;27action errors;59hypothesis links;3/20 repeated identical query lists. Counts là actions, không unique inputs/processes. D1 novelty chỉ là explicit prediction/evidence/revision + correctness interventions + committed-query control; không phải lần đầu model biết replay |
| Avoid hard semantic admission | v33 chain8 vs direct25 value-equality sensitivity;17direct-only =11terminal unknown/abstain,5mechanical,1search; semantic_accuracy=null | Soft claim states giữ input exploration, nhưng D1 không chứng minh soft policy sẽ thắng trên30 tasks. Chưa biết stopped concepts đúng hay sai |
| Fault location/template | v31–v34 attribution yếu; v35 conditional ceiling14<17, fixedpool exposes17 vs plain19; v36 CFG no-go, inputs2–3/33 | Không làm mutation ranking/localization/template expansion. Unrestricted bounded model queries phân biệt với fixedpool ceiling, nhưng search efficacy vẫn chưa biết |

V29 có reference leakage: không sử dụng số liệu. Parent audit v28 là retrospective evidence từ frozen ledgers, không là new model run; xem `parent_v28_action_audit.json` và parent-owned audit script. Prior-art references chính: central `RESULTS.md`; `analysis/v21_failure_audit/REPORT.md`; `analysis/recent_concept_failure_attribution_20261020.md`; v27/v28/v33/v34 reports; `analysis/v35_concept_ceiling/RESULTS.md`; `analysis/v36_llm_localize/RESULTS.md`.

## 7. Sau D1 và self-audit

Chỉ một next experiment được xếp hạng: **D1 như trên**. Nếu vượt cả gates, mới đề xuất D2 extraction transfer: cùng relation meanings nhưng model tự bind từ spec trước khi xem source; evaluator chấm binding độc lập trước search. D2 phải có natural ambiguous/unsupported specs, rule-first baseline và equal evidence/calls. Đây là proposal chưa đủ packet/cohort/budget và không tự động được launch. D1 supplied concepts không trả lời extraction capability. Không có proposal thứ ba đáng để chạy ngay; v18 selection và v35 template ceiling đã chặn các cách repackaging dễ nghĩ tới.

Self-audit:

- **Practical:** 8source fixtures/evaluator có sẵn; standard libraries đủ; schema không bắt LLM sinh executable predicate/trigger. Runner, strict renderer, budget enforcement và CPU controls vẫn cần parent implement/audit.
- **Consistency:** concept≠dimension≠hypothesis; gap≠bug; normative unknown≠forbidden generation; return relation≠reachable local effect. Correct/incorrect/ambiguous packets có riêng denominators.
- **Validity:** equal raw evidence/call ceilings, shared H, same injected rows, separate witness floor, no private oracle in tools. Concept package thêm semantics và abstraction cùng lúc, nên không isolate hai phần. Actual tokens/calls có thể lệch; report chứ không tuyên bố token parity.
- **Remaining threats:** seen/easy fixtures, only one run/model setting, source alone có thể giải quyết trước feedback, predeclared small denominator, author chọn challenges, free-text revision cần independent semantic audit. Model behavior hữu ích có thể không tạo incremental concept gain. Các limitations này không sửa bằng tăng n sau khi fail.
- **No overclaim:** no universal proof, no unique root cause, no model-generated oracle certification, no whole-pool novelty claim từ arm-local novelty, no hypothesis-use attribution chỉ vì final input đúng.

Handoff complete ở mức design. Parent nên audit public projection và timestep accounting trước CPU/native preparation; sau đó run đúng authorization hoặc stop với full failure denominators. Không cần mở rộng catalog hay thêm pipeline stages để bắt đầu D1.
