# Concept-binding ablation (E4 T2) — verdict: **inconclusive** (mixed giữa hai contexts)

Ngày 2026-10-22. PREREG + amendment 1 commit trước calls (cad0bf2, 4b54fb2). 6/6 completions, model
`qwen2.5-coder-32b-instruct`, mọi finish_reason=stop, 0 transport error, 0 native/PUT. Tokens: 18745 prompt + 1519 completion. Local endpoint.

| Context | Fresh control | A1 bỏ `allowed_outcome` | A2 bỏ concept packet |
|---|---|---|---|
| concept_adaptive | wrong, byte-identical v40 | **wrong** (withdraw + "return None" ×2) | **correct**: giữ ValueError claim (`revise`, statement không đổi), predict raise ×3 |
| concept_committed | wrong, byte-identical v40 | **wrong** (giống control) | **wrong**: vẫn withdraw claim, **nhưng** predictions đổi sang "will raise a ValueError" ×2 |

Cả hai contexts valid. CA khớp rule b (packet-level), CC khớp rule c → theo amendment rule d: **inconclusive**.
Manual reading khớp automatic score.

## Đọc mô tả (không đổi verdict)

- Bỏ riêng `allowed_outcome` không đổi gì ở cả hai contexts: giá trị binding đơn lẻ **không** phải nguyên nhân.
- Bỏ cả packet làm predictions "return None" biến mất ở **cả hai** contexts (none_pred 2/2 → 0/2). Ở CA claim cũng
  được giữ. Ở CC model vẫn withdraw dù chính nó predict raise; `why` ghi "raises ValueError ... contradicts the spec" →
  giống polarity-label misuse (withdraw = "behavior này sai spec") hơn là substitution.
- Tức là có hai lỗi tách được: (1) prediction slot bị điền normative value — biến mất khi bỏ packet ở T2;
  (2) stance withdraw trên implementation claim mô tả bug — còn ở CC khi không có packet. T1 carryover chưa loại trừ.
- n = 2 contexts, một fixture, temperature 0. Không thêm contexts/replicates theo PREREG.

Files: `run.py`, `responses/*.json` (không URL), `results.json`.
