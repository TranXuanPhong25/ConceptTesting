# KITE — đối chiếu mechanism, 2026-10-21

Đọc lại §II, evaluation/ablations §III và limitations §V từ saved full text; kiểm tra
primary arXiv record. Chưa xác minh author implementation/KB; không chạy hoặc reimplement.

Paper: https://arxiv.org/html/2607.11573v1

| Evidence | Kết luận đối với proposal |
|---|---|
| §II-A: semantic constraint, applicability, injection direction; AST-anchored units | Mechanism abstraction và code grounding đã có |
| §II-C: dual recall, fusion/ranking, local injection plans, execution gates | Xếp hạng mechanisms có structural/semantic evidence đã có |
| §II-D: injected-method feedback, patch summary, trigger recipe | Không được claim prior work chỉ có code variants, chưa hướng dẫn triggering inputs |
| §II-D3: promotion giữ correct-side validity và historical detections | Feedback có executable acceptance criterion, không chỉ prose |
| §III-A1: generation chỉ thấy correct version | Không chuyển trực tiếp oracle assumption sang buggy-input testing |

Assessment: absence của explicit reusable input-template library không đủ mạnh làm
contribution; KITE đã nối mechanism với input/oracle guidance. Khác biệt có thể kiểm
tra là semantic concepts tổ chức exploratory queries khi không có correct implementation,
nhưng chưa chứng minh có lợi. Không có artifact là reproduction limitation, không làm
method của mình mới hơn.

Synthesis: [đề xuất](../../audit/CONCEPT_GUIDED_PROPOSAL_20261021.md).
