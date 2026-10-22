# OBS-null probe — kết quả: H_obs **not supported**

Ngày 2026-10-21. PREREG: [PREREG.md](PREREG.md) (+ amendment 1, commit 54a8a1e trước mọi call).
6/6 completions, 0 transport error, mọi finish_reason=stop, 0 native/PUT execution.
Tokens: 19214 prompt + 1434 completion. Local Qwen2.5-Coder-32B endpoint (metadata root AWQ, ctx 8192), không paid call.

| Context (E4 T2) | Control | Treatment (bỏ `"output": null`) |
|---|---|---|
| concept_adaptive | wrong: withdraw ValueError claim, predict "will return None" ×2 | **wrong**, giống hệt control |
| concept_committed | wrong: như trên | **wrong**, giống hệt control |
| generic_adaptive (negative control) | correct: keep ValueError, predict raise | correct |

- **Determinism:** cả 3 control replies byte-identical với original v40 replies → replay tái hiện đúng.
- **Verdict theo amendment rule 4c:** mọi reproducing concept context vẫn wrong khi bỏ `output: null` → **H_obs not
  supported**. Manual reading khớp automatic score: treatment `why` vẫn viết "contradicts the spec which requires
  returning None".

## Ý nghĩa

- Rival "đọc `output: null` như `return None`" không giải thích lỗi E4. Các OBS variants khác (vd. `output_capture:
  unavailable`, `all_invocations_proven: false`) chưa được test.
- Lỗi chỉ xảy ra ở hai concept arms; GA thấy cùng observations vẫn đúng. Khác biệt context là concept packet, có
  `concept_binding.allowed_outcome = "return None"`. Đây là **observation post-hoc**, không được test: packet có thể
  đẩy normative value vào prediction slot (concept-induced role substitution).
- **Không mở lại Gate A** (PREREG). Nếu xét lại post-hoc, E4 sẽ gần ROLE hơn, nhưng mọi revival của H_role cần plan mới,
  register trước, không dùng probe này để đổi verdict Phase A.

Files: `run.py`, `responses/*.json` (raw text, usage; không có URL), `results.json`.

**Note 2026-10-22:** cụm "concept-induced role substitution" ở trên chỉ là post-hoc hypothesis. Concept-binding ablation
sau đó ([REPORT](../concept_binding_ablation_20261022/REPORT.md)) ra **inconclusive**, nên không dùng cụm này như kết luận.
