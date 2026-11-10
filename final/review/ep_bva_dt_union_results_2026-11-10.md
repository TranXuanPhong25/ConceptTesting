# Union EP+BVA + Decision Table, không gồm Plain

Union hai arms phát hiện **99/1454 PUTs**, gồm **62 wrong-value, 5 exception, 32 resource**; trên 35/157 eligible tasks. Chỉ lấy inputs EP+BVA và Decision Table từ cùng full v1. Không lấy input Plain.

| Arm | Tổng PUTs /1454 | Wrong-value | Exception | Resource |
|---|---:|---:|---:|---:|
| EP+BVA |89|55|4|30|
| Decision Table |74|57|5|12|
| Union EP+BVA + DT |99|62|5|32|
| Một arm gộp EP+DT+BVA (run riêng) |86|60|4|22|

Hai arms cùng phát hiện 64 PUTs; riêng EP+BVA 25, riêng DT 10. Đây là set union của PUT detections đã confirm, không cộng hai counts. Mỗi PUT lấy strongest kind trong các confirming inputs thuộc hai arms, theo wrong-value→exception→resource.

Union có 4430 unique valid inputs, loại 580 duplicate memberships giữa hai arms; tối đa40/task thực tế,cap40/task so với20 của một combined arm. Upstream314generation calls,1,198,017known tokens. Hai arms nhìn cùng shared packets trong source full3arm; việc Plain cùng xuất hiện trong source không đưa input Plain vào union này. Combined86 ở run riêng có visibility khác, không claim matched comparison.

Phép tính chỉ đọc existing result/oracle/native confirmation checkpoints, dùng classify_arm/observation_kind có sẵn; không gọi LLM, reference hoặc PUT. SourceGuard và source replayproof kiểm tra trước; saved failure observations được xác minh qua classifier. Source kết quả/checkpoints giữ nguyên. Không materialize/replay một input pool mới; vì các confirming outcomes đã có, detection union được tính chính xác bằng hợp hai tập detections.

Chưa làm matched40vs20 hoặc statistical comparison; không suy gain cùng budget. Source: `/home/phong/dev/ConceptTester/final/out/console_resume_d3a095ba-e5d2-46a4-bbe8-44deebdb6073`. Config/result/evidence indices lưu ở `/home/phong/dev/ConceptTester/final/out/ep_bva_dt_union_20261110`.
