# Round novelty — kết quả (2026-10-23, CPU, saved v11_fair dev, ref oracle)

Registration: [PREREG.md](PREREG.md) (+ Amendment 1 sau independent review, trước khi tính outcome). Số liệu:
[results.json](results.json). Script: [round_novelty.py](round_novelty.py).

Động lực: blog "Solving code review at Anthropic": khoảng 59% chỗ reviewer flag lặp lại ở các round sau là code đã có
từ lần review đầu, tức là round thêm chủ yếu tìm lại vấn đề cũ. Câu hỏi ở đây: round 2 của các hybrid arm tìm được
bug mà round 1 bỏ sót không, và hint thật (concept) có làm round 2 "mới" hơn placebo không.

**Gate PASS:** replay khớp `final_protocol_v11_dev.json` ở mọi arm (detecting samples, failing, correct failing,
false alarms, D_I, D_I samples). Tổng round split của mỗi hybrid arm khớp số detecting samples đã lưu.

## Bảng chính (339 sample mỗi arm = 113 task × K 3)

| | concept-hybrid | placebo-hybrid | plain-hybrid |
|---|---:|---:|---:|
| R2 calls (input round 2) | **354** | 926 | 890 |
| Sample có R2 | 135 | 198 | 163 |
| Detect cả sample | 183 | 173 | 167 |
| det1 (round 1 đã detect) | 144 | 134 | 135 |
| det2 (round 2 detect) | 55 | 69 | 61 |
| r2_new (R2 detect, R1 không) | 39 | 39 | 32 |
| r2_redundant (R2 tìm lại bug R1 đã thấy) | 16 | 30 | 29 |
| **Redundancy share** (analog 59%) | **29%** | 44% | 48% |
| r2_new trên task witness-only đã detect | 28 | 16 | 18 |
| r2_new vượt tool (witness-only không detect) | **11** | **23** | 14 |
| Conditional novelty (r2_new / R1 miss) | .20 | .19 | .16 |
| r2_new matched (cùng số input R2 với placebo) | 35.5 | 20.5 | – |
| D_I mới ở round 2 | 46 | 43 | 38 |
| False alarm R2 / R2 call | .006 | .017 | .029 |
| Sample mà R2 thêm flag sai đầu tiên | 4 | 3 | 5 |

Witness-only detect 43/113 task.

## So sánh (sign test theo task, 113 task)

- Primary đã đăng ký (raw r2_new, sau amendment chỉ để mô tả): concept vs placebo **39 vs 39, 15/15, p = 1**.
- **Co-primary quyết định (matched input):** concept vs placebo **35.5 vs 20.5, 16/8, p = .15**.
- r2_new vượt tool: concept vs placebo **11 vs 23, 3/10, p = .09** (ngược chiều điều kiện thứ hai).
- det2: 55 vs 69, 14/20, p = .39. concept vs plain-hybrid r2_new: 39 vs 32, 15/11, p = .56.
- Exploratory placebo vs plain-hybrid r2_new: 39 vs 32, 11/9.
- Task có r2_new: concept 20, placebo 18, plain 21. Concept và placebo chung 7 task; 13 chỉ concept, 11 chỉ placebo.

## Quyết định: **NO SIGNAL** (theo luật đã đăng ký)

Khi cùng số input round 2, hint thật không làm round 2 tìm thêm nhiều bug mà round 1 bỏ sót hơn placebo một cách có
ý nghĩa (p = .15). Điều kiện thứ hai cũng fail: phần mới của concept phần lớn nằm trên task mà fuzz witness đã bắt
được (28/39), còn placebo có nhiều phần mới vượt tool hơn (23 vs 11).

## Cơ chế (mô tả, không phải gate)

1. **Input yield:** cùng số request, concept hint chỉ cho ra 354 verified input ở round 2, so với 926 của placebo
   (khoảng 2.6 lần ít hơn). Strict round 2 chỉ giữ input mà tool xác nhận đã chạm hint; concept hint khó chạm hơn
   placebo hint.
2. **Mỗi input của concept hiệu quả hơn nhưng n.s.:** matched 35.5 vs 20.5 (16/8). Concept cũng ít redundant hơn (29%
   so với 44–48%) và ít false alarm hơn ở round 2 (.006 so với .017/.029 mỗi call).
3. **Phần mới của concept phần lớn là bug mà tool đã chạm tới:** 28/39 r2_new của concept nằm trên task mà
   witness-only đã detect. Hint của concept dẫn Hypothesis về đúng vùng mà fuzz witness của chính hint đó đã có.
   Hiện tượng này giống phát hiện 59% của blog: round thêm tìm lại cái đã tìm được, chỉ khác là ở đây cái cũ nằm ở
   tool witness chứ không ở round 1. Placebo hint chỉ sang chỗ khác nên phần mới vượt tool nhiều hơn.
4. **Round 2 gây ít harm:** chỉ 3–5/339 sample có flag sai đầu tiên đến từ round 2.

Hàm ý: trong pipeline đã có witness-only, concept round 2 chủ yếu nhân đôi phần của tool. Kết quả này khớp với
§11.37/§11.41 (tool mang phần lớn lợi ích). Theo luật đã đăng ký, không đề xuất run mới từ phân tích này.

Giới hạn: R1 khác nhau giữa các arm (concept R1 = concept arm, placebo R1 = placebo hint mới, plain R1 = plain arm),
nên raw r2_new phụ thuộc số sample R1 bỏ sót; conditional novelty (.20/.19/.16) được báo kèm. "Vượt tool" dùng
witness-only ở mức task (deterministic, 43 task). D_I split chỉ có một phần (reach).
