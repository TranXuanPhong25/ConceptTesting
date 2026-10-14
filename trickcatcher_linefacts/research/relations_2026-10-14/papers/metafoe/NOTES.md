# MetaFOE

[Full text v1](https://arxiv.org/html/2606.14164v1), preprint 2026-06-12; template venue/DOI chưa xác định. Kiểm §4, §5, §6. [Anonymous artifact](https://anonymous.4open.science/r/MetaFOE-3C67) trả HTML shell không có nội dung qua browser; chưa audit source.

**Paper facts:** Tách metamorphic-relation generation và fuzz-oracle implementation. Evaluation configurations sinh 3,475 MRs (77.3% applicable), 12,351 meta drivers (6,228 valid), báo 1,528 unique crashes. MR applicability được manual validation; case study vẫn có false positives. Vì vậy unique crashes chưa là confirmed bugs. [Nguồn: §4–6](https://arxiv.org/html/2606.14164v1).

**Áp dụng đề xuất:** LineFacts cần kiểm riêng semantic relation và code thực thi relation. Giữ cùng oracle để đo input discovery trước, rồi nghiên cứu MR oracle riêng.

**Giới hạn:** Dùng strong models/OSS-Fuzz setting, chưa có evidence cho Qwen 7B. Manual validation cost cần báo. Chạy được assertion hoặc có MR applicability không đồng nghĩa relation đúng cho mọi valid input.
