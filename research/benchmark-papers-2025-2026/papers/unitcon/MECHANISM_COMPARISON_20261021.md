# UnitCon — đối chiếu mechanism, 2026-10-21

Đọc lại paper §§2–4, ablation §5.4, limitations §7. Source artifact
`f7ab2e23a57e12060b50af91cf7098dfc347b9ff` pin submodule
`642930a794796977dde62f8ba690aaeeaeea3945`; gitlink xác minh qua GitHub tree API.
Đã kiểm tra error-summary parser và các entry points của generator ở pinned commit.
HEAD mới `84c1d8096cd7ab7eda3c6f24cdd35b3d861f9188` chỉ là supplementary source,
không thay cho paper version. Không build/run.

Paper: https://doi.org/10.1145/3729362
Author overview: https://prosys.kaist.ac.kr/unitcon/

Error condition kết hợp path condition với exception condition khi analyzer hỗ trợ.
Method summaries hướng dẫn enumeration và prune redundancy. §4.3 dùng backward
conditions và forward states để ưu tiên candidate; không loại partial test chỉ vì
hiện tại nó trái condition. Pinned `src/errorSummary.ml` parse pre/post states và
target location; `src/generator.ml:1045` có `satisfy`, `:1446/:1474` có pruning;
`src/generatorDUG.ml:1362` có priority queue.

Assessment: condition → input search và soft prioritization đã có. Target exception
location được cấp; không đồng nghĩa tự tìm functional spec mismatch. LLM semantic
binding chưa được kiểm tra bởi paper này. Thêm LLM hoặc đổi Java sang Python tự nó
chưa đủ contribution.

Synthesis: [đề xuất](../../audit/CONCEPT_GUIDED_PROPOSAL_20261021.md).
