# Giữ obligation v1, bỏ validated v2 — 14/11/2026

**V2 giảm61→35detected PUT trên cùng1454PUT/157eligible tasks.** V2 bỏ28PUT v1 bắt
được (21wrong-value,4exception,3resource), chỉ thêm2wrong-value PUT, net−26. Hai PUT
v2 thêm làHumanEval/126 PUT5 vàHumanEval/43 PUT9; cảhai đã nằm trong EP+BVA+DT.
Một PUT chung (HumanEval/76 PUT0) còn đổi từ wrong-value evidence ởv1 sang chỉ resource ởv2.
Đây là so hai complete saved suites, không ablation cô lập checker khỏi prompt/
selection/context. Không coi mọi reference disagreement là confirmed semantic bug.

| Metric | V1 | V2 |
|---|---:|---:|
| Detected PUT /1454 |61|35|
| Wrong-value PUT |52|32|
| Exception PUT |4|0|
| Resource PUT |5|3|
| Task có detection /157 |23|13|
| Novel valid input records |1964|1951|
| Union EP+BVA v2+DT v2, không Plain |84|81|

Baseline Gemini EP+BVA+DT79PUT. V1 thêm5(2wrong+1exception+2resource),v2 thêm2resource.
Gộp baseline+v1+v2 vẫn84: v2 không bổ sung incremental PUT ngoài v1+baseline.

## Các regression quan sát được

1. **Prompt overflow làm mất generation.** V2 có17/157task status prompt_too_large,
   v1 không có task ở status này. V2 thêm checker instructions và giữ full PUT context;
   khi vượt context không trim whole PUT packets nhưv1 mà trả no request.6/28PUT bị
   mất nằm ngay3task này:HumanEval10(2PUT),124(3PUT),39(1PUT). Đây là evidence trực
   tiếp của empty generation, chưa chứng minh checker logic tự nó kém.
2. **Structural coverage cũng giảm.** Trên394targets chung (task_id,target_id),
   v1hit192,v2hit126. V2 selected407targets tổng,126hit. Task76hit6/6→2/6 và mất8PUT;
   task2hit4/4→2/4. Cảhai hướng structural/semantic không được cải thiện đồng thời.
3. **Metadata/checker khó dùng.** Accepted obligations434→327; requirement grounding
   rejects9→76. V2 chỉ127/327checkers supported,200unknown:55expression_names,
   41anchor/scope mismatch,40input-only weakchecks,31unsupported ASTnodes,
   14missingsteps,11unsupportedcalls,3multiline-after,3generator/async,2invalidlines.
   Safe rejections bảo vệ correctness; counts cho thấy LLM/checker interface chưa đủ
   reliable, không nên nới safety checks để làm đẹp coverage.
4. **Candidate budget sử dụng kém hơn.** Candidates5072→5853 trong khi native
   observation receipts6272→6185; native_budget_exhausted rejects448→728.
   Candidate→owner scheduling và scoring cũng đổi trongv2, nên không quy tất cả
   drop cho validation. Nhiều candidates hơn chưa tạo thêm valid yield hữu ích.
5. **Scenario membership không đủ evidence.** V2 new membership40hit/52miss/
   235unknown trên327obligations. V1 là193/146/95 trên434obligations nhưng checker
   semantics khác (predicate+reach vs ordered state), không dùng193→40 làm một phép
   so semantic coverage trực tiếp. Detection/oracle riêng mới là metric chung.

## PUT bị mất theo task

HumanEval10:2;101:1;107:1;11:2;124:3;157:2;161:1;2:1;39:1;45:1;49:4;76:8;99:1.
Task49 valid selected inputs20→2, task45 20→0, task107 3→0; task157và161 vẫn có20
inputs nhưng bỏ witness cũ. Vì vậy không chỉ thiếu số lượng: scenarios/values được
chọn cũng khác và có selection loss. Chưa replay missed input pool để phân biệt
construction-vs-selection một cách causal.

## Provenance và budget

Complete Gemini continuation b6b091ae-6d81-49f0-b6e5-72a4ce7991a4, output
`final/out/gemini_cf_scenario_resume_20261114`. Baseline saved Gemini source
`final/out/gemini_full4_20261112_074012`. Cùng frozen cohort SHA
`2a32bae531c339f2e403d748984ce5775734bdd8fd0fc9a02620392fbc23c7ed`, corrected
HumanEval+v0.1.10 oracle, confirm_first_failures,8s/input;20inputs/task,
4096completion/18192context,temp0.7,seeds314159/271828,Gemini3.1FlashLite/Vertex.
V1 dùng295responses/2839845known tokens;v2264responses/2531446known tokens
+25unknown historicalattempts. Continuation giữ641responses và chỉ gọi76responses
mới để hoàn tất cả3variants; cumulative717responses/742attempts/6188783known tokens.
Source/replay/import hashes verified; không model/native calls mới cho audit này.

Evidence: result_digest.json (gained/lost/shared + confirming inputs),
scenario_measurements.json và từng generation.json của2variants. Prefect:
http://127.0.0.1:4200/runs/flow-run/b6b091ae-6d81-49f0-b6e5-72a4ce7991a4

User chốt bỏ validatedv2 khỏi active source/CLI/Prefect registry, giữv1; lịch sử và
frozen outputs v2 không xóa. Không launch experiment mới hoặc claim causal effect
của checker đã được isolated. Scope commit chỉ v1, shared dependencies/integration
cần thiết, tests và report này; không kéo các thay đổi khác trong workspace vào.
