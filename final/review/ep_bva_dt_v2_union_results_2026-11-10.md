# Full v2 và union EP+BVA v2 + Decision Table v2

Full v2 đã hoàn tất evaluation/source checks/immutable replay. Union hai arms v2 phát hiện **113/1454 eligible PUTs**, trên **41/157 eligible tasks**; gồm **75 wrong-value, 5 exception, 33 resource**. Chỉ lấy inputs EP+BVA v2 và DT v2; không Plain, không trộn inputs v1.

| Arm | PUTs phát hiện /1454 | Tasks có detection /157 | Wrong-value | Exception | Resource |
|---|---:|---:|---:|---:|---:|
| EP+BVA v1 |89|30|55|4|30|
| EP+BVA v2 |81|32|67|4|10|
| DT v1 |74|25|57|5|12|
| DT v2 |96|34|65|3|28|
| Union EP+BVA v1 + DT v1 |99|35|62|5|32|
| Union EP+BVA v2 + DT v2 |113|41|75|5|33|

V2: EP+BVA có2402 novel reference-valid inputs, DT có2378. Union có **4227 unique valid inputs**, loại 553 duplicate memberships giữa hai arms; tối đa39/task thực tế, cap40/task. Hai arms cùng phát hiện64PUTs; chỉ EP+BVA v217, chỉ DT v232. Mỗi PUT lấy strongest kind trong confirming inputs thuộc hai arms, thứ tự wrong-value→exception→resource. Số chênh counts theo kind không phải paired attribution từng PUT.

Config full v2:164task records/157eligible tasks/1454base-pass PUTs,7cohort skips;20inputs/task/arm,1generation completion/task/arm,cap4096completion/context8192,temp.7,inputseed314159/reference271828+task,timeout8s,corrected reference2runs,confirm_first_failures;global freeze trước nativeevaluation. Model qwen3.5-27b-awq.314received responses/316attempts/2unknown usage;1,328,124known tokens (prompt766,010+completion562,114), keepalive riêng. Theo arm:EP+BVA v2 660,108known tokens;DT v2 668,016. Unknown usage không tính0.

V1-v2 là cross-run descriptive comparison: instruction+examples thay cùng lúc; shared visibility jointlytrim theo các arms trong mỗi run, không bảo đảm packets identical với v1full3arm. Không cô lập Fault Hypotheses hoặc examples. Chưa có paired/matched-valid-budget analysis hoặc statistical significance; không suy formal coverage/correctness chỉ từ detection.

Union chỉ đọc existing result/oracle/native confirmation checkpoints qua classify_arm/observation_kind có sẵn; không gọi LLM, reference hoặc PUT. SourceGuard/replayproof PASS; classification khớp per-arm saved counts. Không materialize/chạy một input pool mới; detections tính bằng hợp hai tập đã confirm. Source/checkpoints giữ nguyên. Comparison với từng arm dùng budget40vs20; không claim gain cùng budget.

Full v2 source/run: `/home/phong/dev/ConceptTester/final/out/console_resume_7557c4df-b77a-47d4-bfc0-8810d6baf73c`; Prefect:http://127.0.0.1:4200/runs/flow-run/7557c4df-b77a-47d4-bfc0-8810d6baf73c. Union output: `/home/phong/dev/ConceptTester/final/out/ep_bva_dt_v2_union_20261110`; config/result/source indices được lưu riêng.
