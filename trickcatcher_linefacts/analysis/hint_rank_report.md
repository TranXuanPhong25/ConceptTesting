# Chọn hint theo giả thuyết lỗi (plan hạng 2, CONCEPT_WEAKNESS.md A2) — offline

2026-10-13. CPU only, không gọi LLM. Script: `analysis/hint_rank.py`; số liệu: `out/hint_rank/results.json`,
bảng tự sinh: `out/hint_rank/tables.md`.

## 1. Làm gì

- **Pool (kho hint) mỗi task dev** = mọi code fact v6 mà fuzz chạm được (`out/facts_v6`, **mọi kind**, không loại kind nào)
  + mọi spec fact v7 (`out/spec_facts_v7`, cả ở task đã có code fact). Trung bình ~13 hint/task.
- **Feature (chỉ thông tin method thấy được)**, worker `feat` chạy sandbox (`unshare -rn python3 -I -B`, step budget của tracer):
  - kind, tier (g_demote), block, line, boundary, mutant family, extended;
  - `covered_site`: dòng của hint đã được base test chạy chưa; `on_compare_line`: hint nằm trên dòng có phép so sánh;
  - `hit_frac`: tỉ lệ fuzz input chạm hint. Fuzz input được **dựng lại đúng như facts.py** (cùng seed, cùng validator B5
    `out/precond_qwen7b_v4`); kiểm tra: 0 witness lệch trên 112 task;
  - `out_change`: output của PUT trên witness khác output trên base input gần nhất (theo repr);
  - `crash`: PUT ném exception / timeout trên input chạm hint (implicit oracle, không cần spec);
  - **`mutref` (giả thuyết lỗi, chỉ MUTANT)**: trên các fuzz input mà PUT và mutant khác nhau, mutant ra **cùng** kết quả với
    đa số (> 1/2) các ref program, còn PUT thì không. Ref program = các bản B2 Qwen viết từ spec
    (`out/oracle_v7hyb/ref_responses.json`, lấy code block như `oracle_b01.code_block`, chỉ giữ bản pass base test, cần ≥ 3 bản
    như oracle_b01; số bản giữ được khớp 100% với `out/oracle_v7hyb/exec`). 101/112 task có ≥ 3 ref.
  - **`refdis` (thêm, ngoài yêu cầu)**: trên input chạm hint (mọi kind), PUT khác đa số ref.
  - **Lưu ý: `mutref` rất gần ý tưởng TrickCatcher** (dùng các chương trình sinh từ spec để quyết định PUT có sai không);
    `refdis` thực chất **là** differential testing kiểu TrickCatcher/ref oracle. Xem mục 4.
- **Nhãn (chỉ để chấm)**: PF = P(PUT fail | HumanEval+ input chạm hint) theo assertion chính thức của HumanEval+. Code fact: lấy từ
  `out/offline_v6_report` (worker offline.py). Spec fact: tính lại bằng cùng cách capture của offline.py (worker `label`).
  Good = PF ≥ .5. n_fail khớp offline_v6_report trừ task 34, 58 (PUT dùng `list(set(...))`, đã biết là phụ thuộc hash order).
- **Luật**: fit trên task **chẵn** (58 task), chấm trên task **lẻ** (54 task). Logistic regression nhỏ (L2, trọng số mỗi task bằng
  nhau hay mỗi fact bằng nhau, cách chọn top 3 có/không đa dạng kind — cả hai đều chọn trên task chẵn), và một luật tay dễ giải thích:
  `điểm = good rate của kind trên task chẵn + 1[crash] (+ 1[mutref] − .5[chỉ mutant sai]) (+ 1[refdis] − .5[ref đồng ý PUT])`,
  tối đa 1 hint mỗi kind.

## 2. Kết quả good@3 (số task có ≥ 1 hint tốt trong 3 hint chọn)

Chẵn n = 58, lẻ n = 54. p(rand) = P(random@3 trên pool đầy đủ ≥ số quan sát), tính chính xác (Poisson-binomial).
"vs v7" = số task lẻ thắng/thua so với pick_v7 (sign test).

| Luật | chẵn | **lẻ** | p(rand) lẻ | lẻ vs pick_v7 |
|---|---:|---:|---:|---|
| pick_v6 (`facts.pick`, chỉ kind được phép) | 24 | 20 | 1.0 | 0/5 |
| pick_v7 (pick_v6, task không có code fact thì 3 spec fact đầu) — luật đang dùng | 29 | 25 | .98 | – |
| random@3, pool kind được phép (kỳ vọng) | 25.4 | 19.2 | | |
| random@3, pool code mọi kind | 24.7 | 27.6 | | |
| **random@3, pool đầy đủ (code mọi kind + spec)** | 25.7 | **29.4** | | |
| ceiling@3 kind được phép / code mọi kind / đầy đủ | 30 / 39 / 42 | 22 / 40 / **44** | | |
| LR[kind] (chỉ kind) | 37 | 27 | .88 | 5/3 |
| **LR[noref]** (kind + cấu trúc + crash) | 35 | **32** | .20 | 9/2 (p = .065) |
| hand (kind rate + crash) | 35 | 33 | .10 | 10/2 (p = .039) |
| **LR[noref + mutref]** | 37 | **35** | **.018** | **10/0 (p = .002)** |
| hand + mutref | 38 | 33 | .10 | 10/2 |
| LR[noref + mutref + refdis] | 38 | **40** | 9e-6 | 15/0 |
| hand + mutref + refdis | 38 | 35 | .018 | 12/2 |

Đổi seed tie-break (20 seed khác): LR[noref] lẻ 32 [32–32], LR[+mutref] 35 [35–35], LR[+refdis] 40 [40–40],
hand 32.6 [30–35], LR[kind] 27.9 [26–29]. Luật logistic ổn định; luật tay dao động ±2–3.

Hệ số LR[noref + mutref] (fit trên task chẵn, logit): MUTANT +.50, OUTCOME +.43, STMT +.35, MUTANT-X +.35, DU +.28, BOUND +.20,
SHAPE −.90, SPEC −.41, LOOP-MAX −.31; log10(hit_frac) +.55, out_change +.48, crash_frac +.53, boundary +.20,
covered_site −.26; **mutref +.58**, chỉ mutant sai −.21. Hệ số đầy đủ: `out/hint_rank/tables.md`.

## 3. Good rate theo kind và theo tín hiệu (mức fact, pool đầy đủ)

| Kind | số fact | rate chẵn | rate lẻ | task có hint tốt kind này |
|---|---:|---:|---:|---:|
| MUTANT | 202 | .465 | .409 | 32/48 |
| OUTCOME | 48 | .409 | .462 | 17/32 |
| STMT | 37 | .412 | .450 | 14/27 |
| DU | 94 | .444 | .408 | 14/24 |
| MUTANT-X | 34 | .588 | .176 | 11/21 |
| BOUND | 98 | .327 | .370 | 20/39 |
| DECISION | 37 | .333 | .280 | 5/14 |
| NUM | 46 | .238 | .200 | 6/19 |
| LOOP-MAX | 84 | .136 | .300 | 16/66 |
| OUTPUT | 180 | .207 | .184 | 22/60 |
| REL | 44 | .211 | .160 | 6/24 |
| SHAPE | 326 | .090 | .198 | 30/82 |
| LOOP | 102 | .143 | .094 | 11/50 |
| SPEC | 174 | .065 | .146 | 16/96 |

Rate thấp nhưng nhiều task chỉ có hint tốt thuộc kind đó (SHAPE 30 task, OUTPUT 22, LOOP-MAX 16) — đây là lý do loại kind
a priori làm mất task.

| Tín hiệu | rate chẵn (n) | rate lẻ (n) |
|---|---|---|
| crash > 0 / = 0 | .34 (93) / .21 (666) | .40 (76) / .25 (671) |
| out_change / không | .28 / .11 | .29 / .14 |
| covered_site / chưa chạy | .23 / .22 | .26 / .27 |
| MUTANT: mutref > 0 | .56 (73) | .56 (32) |
| MUTANT: có đa số ref, mutref = 0 | .24 (45) | .26 (49) |
| MUTANT: chỉ mutant khác ref | .19 (42) | .17 (42) |
| refdis > 0 / có đa số mà PUT luôn khớp | .36 / .05 | .44 / .14 |

`covered_site` gần như không phân biệt (ý SAVIOR "nhắm cả chỗ đã chạy" không cho thêm tín hiệu ở đây). `mutref` ổn định giữa
chẵn và lẻ (.56 vs ~.25).

## 4. Đọc kết quả (thẳng thắn)

1. **Phần lớn lợi ích đến từ việc bỏ luật loại kind, không phải từ luật xếp hạng.** Chỉ cần random@3 trên pool đầy đủ đã được
   29.4 trên task lẻ, hơn pick_v6 (20) và pick_v7 (25). Một phần nữa vì pick thường đưa < 3 hint (218 hint cho 112 task),
   còn các luật mới luôn đưa đủ 3 (324 hint).
2. **Không dùng ref: chưa thắng random rõ ràng trên task lẻ.** LR[noref] 32 và hand 33 so với random 29.4 (p = .20 và .10).
   Thắng pick_v6 rõ (14/2) và gần rõ pick_v7 (9/2, p = .065). LR[kind] (27) còn thua random trên task lẻ — luật chỉ theo kind
   overfit task chẵn (37 trên chẵn).
3. **Thêm `mutref` (giả thuyết lỗi từ mutant + ref): thắng random trên task lẻ** — 35 vs 29.4, p = .018; thắng pick_v7 10/0
   (p = .002), không mất task nào so với pick_v6. Đây là luật tốt nhất **không** dùng ref làm oracle trực tiếp cho PUT, nhưng nó
   vẫn dùng ref program — gần với TrickCatcher, phải ghi rõ khi so với TrickCatcher/advdoc.
4. **`refdis` cho 40/44 (ceiling) trên task lẻ nhưng gần như vòng tròn**: hint được chọn vì PUT đã khác ref trên chính input chạm
   hint, tức tool đã có sẵn một input mà ref oracle coi là lộ bug. Bước chấm cuối của pipeline cũng dùng ref oracle, nên tín hiệu
   này về bản chất là differential testing của TrickCatcher, không phải công lao của concept. Chỉ nên dùng làm mốc trên,
   hoặc nếu dùng thì so với baseline "toolinput + ref" cùng tín hiệu.
5. good@3 chỉ đo "có hint tốt trong 3", không đo Qwen có làm theo được không. Các kind trước đây bị loại (OUTPUT, LOOP-MAX,
   SHAPE) bị loại một phần vì dễ sinh invalid input / khó làm theo; luật mới chọn chúng nhiều (OUTPUT 43, SHAPE 28, LOOP-MAX 22
   trong 324 hint của LR[noref]). Cần đo trên GPU trước khi kết luận về số bug.
6. Task lẻ dễ hơn task chẵn ở pool đầy đủ (random 29.4/54 vs 25.7/58); vì vậy luôn so với random cùng cohort, không so
   chẵn với lẻ.

## 5. Phục hồi các task yếu (CONCEPT_WEAKNESS.md A2), chỉ task lẻ

Danh sách nguyên nhân lấy từ `out/analysis_weak/weak_table.json` (làm trên lượt v3m2-hybrid, pool hơi khác v6 nên vài nhãn lệch:
ví dụ task 127 "chọn sót" nhưng pick_v6 đã đúng; task 13 "không hint nào chạm" nhưng pool đầy đủ có spec fact tốt).

| Luật | 10 task mất vì loại kind (lẻ: 8) | 9 task mất vì chọn top 3 (lẻ: 3) | 10 task chỉ có hint yếu (lẻ: 6) | 4 task không chạm (lẻ: 2) |
|---|---|---|---|---|
| pick_v6 / pick_v7 | 0/8 | 1/3 [127] | 0/6 | 0/2 |
| LR[noref] | 4/8 [41, 49, 89, 109] | 1/3 [127] | 1/6 [25] | 0/2 |
| hand | 4/8 [41, 49, 89, 159] | 0/3 | 1/6 [25] | 1/2 [13] |
| LR[noref + mutref] | 4/8 [41, 49, 89, 109] | 2/3 [59, 127] | 1/6 [25] | 0/2 |
| LR[+ mutref + refdis] | 7/8 | 3/3 | 1/6 | 0/2 |

(Task 25 "chỉ có hint yếu" có hint tốt là spec fact v7, thứ không có lúc phân tích đó.)

## 6. Đề xuất

- Nếu muốn một luật không dùng ref: LR[noref] (hoặc luật tay) — thắng luật hiện tại nhưng **chưa chứng minh hơn random** trên task lẻ.
- Luật đề xuất: **LR[noref + mutref]** — thắng random trên task lẻ (p = .018) và pick_v7 10/0. Khi báo cáo phải ghi là dùng
  ref program kiểu TrickCatcher để xếp hạng hint, và control plain-hybrid / toolinput nên được dùng cùng ref program đó
  (ví dụ toolinput chọn witness theo cùng điểm) để so công bằng.
- Không dùng `refdis` trong method chính (vòng tròn với ref oracle).
- Bước tiếp: chạy GPU với 3 hint của LR[noref + mutref] vs pick_v7, cùng số test, theo luật chung ở CONCEPT_WEAKNESS.md §3.

## 7. Chạy lại

```
python3 -B trickcatcher_linefacts/analysis/hint_rank.py all       # feat + label (sandbox, ~10 phút, 12 job) + analyze
python3 -B trickcatcher_linefacts/analysis/hint_rank.py analyze   # chỉ tính lại bảng từ out/hint_rank/{feat,label}
```
Worker bỏ qua task đã có file output; xóa `out/hint_rank/feat` hoặc `label` để tính lại.
