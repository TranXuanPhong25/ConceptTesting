# Concept còn yếu ở đâu, vì sao, và kế hoạch sửa

Cập nhật 2026-10-13. Mọi số liệu trên 113 task dev (112 task có plus input làm lộ bug), K = 3, Qwen2.5-Coder-7B,
chấm bằng oracle ref, trừ khi ghi khác. Nguồn chi tiết: RESULTS.md §11.10–11.27; trang phân tích
https://claude.ai/artifact/8v4jfJxo9Sjc9z9foNW6G1 (lượt v3m2-hybrid); sơ đồ phiên bản
https://claude.ai/artifact/7a6yvf5bhiVmZVyt9UvTC8.

## 1. Tóm tắt

Concept (hint) bị mất giá trị ở 3 tầng. Tầng "miền concept chưa đủ" không phải tầng mất nhiều nhất.

| Tầng | Còn lại bao nhiêu task có hint tốt (PF ≥ .5) | Mất ở đâu |
|---|---|---|
| 1. Miền concept: trong toàn bộ kho có ít nhất 1 hint tốt (tính cả kind bị loại và hint spec v7) | khoảng 74/112 (66%) | khoảng 38 task: kho không có hint tốt, miền concept không mô tả được bug |
| 2. Chọn hint: 3 hint đưa vào prompt có ít nhất 1 hint tốt | 44 + 11 (v7) = 55 | 10 task mất vì luật loại theo kind, 9 task mất vì luật chọn top 3 |
| 3. Qwen làm theo: input thật sự chạm hint tốt | khoảng 55% số lượt | Qwen bỏ lỡ 87/195 lượt (hint × run) |

Những gì đã chắc chắn:
- concept-hybrid thắng placebo-hybrid: 38/8 ở v7, 33/13 ở v8-strict.
- concept-hybrid thắng các baseline của paper: advdoc 38/7, onlydoc 45/8, TrickCatcher full.
- concept-hybrid thắng plain-hybrid **khi so cùng số test** (v8-strict 34/17, p = .024).

Những gì chưa đạt:
- Chưa thắng plain-hybrid khi để nguyên số test (v8-strict 29/20, p = .25).
- Chưa thắng toolinput: cùng số test thì thua 16/36.
- Hint từ spec (v7) chưa hơn round 2 không có hint (8/7).

## 2. Điểm yếu và nguyên nhân

### A. Bước sinh hint (facts)
1. **Nhiều task không có hint từ code.** Ở v3m2 có 36/113 task không có hint nào, trong khi Codex tìm được bug ở 33 task trong số đó.
   - Nguyên nhân: hint từ code (branch/line chưa chạy, mutant, boundary, def-use) chỉ nói về cấu trúc code. Bug ở các task này nằm ở lớp input: input rất lớn (RecursionError), non-ASCII, phần tử lặp, whitespace thừa. Những bug đó không hiện ra thành chỗ chưa chạy trong code.
   - v7 thêm hint từ spec cho các task này, nên 111/113 task có hint. Nhưng trên 36 task đó, concept-hybrid vs plain-hybrid chỉ 8/6 (v8-strict 8/7): phần tăng đến từ việc có round 2, không phải nội dung hint.
2. **Hint chỉ sai chỗ.** Có 33 task có hint nhưng không hint nào tốt:
   - 10 task: hint tốt thuộc kind bị loại khỏi prompt (SHAPE, OUTPUT, LOOP, LOOP-MAX, REL, DECISION). Luật loại theo kind được chốt trên dev và loại mất cả các trường hợp tốt.
   - 10 task: kho chỉ có hint yếu (PF < .5). Hint cấu trúc không khớp với bug ngữ nghĩa, tức code hiểu sai spec ngay trên những dòng đã chạy (ví dụ `move_one_ball`, `match_parens`, `pluck`).
   - 9 task: kho có hint tốt cùng loại nhưng luật chọn top 3 bỏ sót. Luật chọn không hơn chọn ngẫu nhiên (good@3: 44 so với 45.0).
   - 4 task: không hint nào chạm được input làm lộ bug.
3. **Hint gây invalid input.** concept sinh 146 invalid input, plain sinh 94.
   - Nguyên nhân: base test "chưa bao giờ dùng X" thường là vì spec cấm X, ví dụ hint "n chưa bao giờ bằng 0" trong khi spec đòi n > 0.
   - v6 dùng F1b nên giảm hint có witness invalid từ 29 xuống 16. Các điều kiện ngữ nghĩa khó (số nguyên tố, không trùng) vẫn đào kém.

### B. Round 1: Qwen làm theo hint kém
4. Với các hint tốt đưa cho concept, Qwen bỏ lỡ 87/195 lượt:
   - 38 lượt: không thử dạng input đơn giản mà hint cần (list 1 phần tử, số âm đứng đầu, chữ hoa);
   - 35 lượt: cần tính ra một giá trị hoặc tổ hợp cụ thể;
   - 8 lượt: đúng hướng nhưng lệch;
   - 6 lượt: chỉ invalid input mới chạm được.

   Nguyên nhân: hint nói về bên trong code (line, biến, branch), còn model 7B khó đổi câu đó thành input. Hint từ spec ở mức input cũng chỉ giúp một phần: round 1 chạm non-ASCII 7/48 (plain 4/48), input rất lớn 26/114 (plain 0/114), whitespace 4/18 (plain 6/18).
5. **toolinput thắng khi tính trên mỗi test.** toolinput chính là witness input của các hint đó, đưa thẳng cho Qwen.
   - Mọi hint hiện tại đều được sinh ra từ một fuzz input đã chạm chỗ đó, nên toolinput luôn có sẵn input đúng.
   - Cắt concept-hybrid về cùng số test với toolinput: toolinput thắng 37/15 ở v7, 36/16 ở v8-strict. concept một round vs toolinput: 18/37.

### C. Round 2
6. **Hypothesis ít khi tìm được input chạm hint.** Mỗi sample có 1.88 request nhưng chỉ giữ được 0.9 input; 103/238 sample không giữ được input nào.
   - Nguyên nhân: Qwen 7B viết strategy chung chung, trong khi điều kiện cần chạm rất hẹp. v5 cũng chỉ giải được 10/276 chỗ fuzz không chạm tới.
   - Mặt khác, input Hypothesis đã giữ được thì rất hiệu quả: 0.9 test mỗi sample góp khoảng 13 bug/run.
7. **So với plain-hybrid từng chưa công bằng (đã sửa ở v8-strict).**
   - Lần gọi Qwen cuối của round 2 dùng prompt toolinput có câu "you may add others"; nếu không có input nào thì thành một lần gọi plain.
   - concept-hybrid được gọi thêm kiểu này nhiều hơn (103 so với 71 sample), nên khoảng 6 bug/run trong 67.0 của v7 đến từ test Qwen tự thêm.
   - Sau khi sửa: concept-hybrid 61.0 vs plain-hybrid 55.7, 29/20; cùng số test 34/17.

### D. Oracle
8. Kể cả với ref, vẫn có 15% run báo lỗi cả chương trình đúng, false alarm 3.3%. ref abstain 920–1.053 lần vì quá ít bản code và khoảng 240–270 lần vì các bản không khớp.
   - Nguyên nhân: 10 bản ref do chính Qwen 7B viết và phải khớp hoàn toàn; invalid input vẫn lọt qua.
   - Nếu oracle đúng hoàn toàn thì chỉ thêm được tối đa khoảng 7 bug/run (69.0 input lộ bug vs 62.0 ref, lượt v3m2-hybrid).
9. Input càng sát bug thì đọc spec càng dễ sai: với b1one, M của concept-hybrid là 2.0%, của onlydoc là 0.7%.

### E. Độ tin cậy của kết quả
10. Mọi lựa chọn đều làm trên 113 task dev. Pilot (20 task) không thấy concept có lợi thế: concept-hybrid 10.0, plain-hybrid 9.7, toolinput 11.0.
11. Held-out MBPP+ chỉ có 12 bug thật (58 PUT); sign test phải đạt từ 10/2 mới significant. p-value chưa được hiệu chỉnh cho việc so nhiều cặp.
12. Mốc trên của Codex (33/36) không so ngang được: Codex được chạy code và có thể đã thấy HumanEval khi train.

## 3. Kế hoạch (xếp theo độ ưu tiên, 2026-10-13)

Luật chung cho mọi bước:
- Mỗi version là một folder mới, copy từ `pipelines/<bản tốt nhất>`; ghi PREREG trước khi chạy.
- Round 2 kiểu strict: chỉ giữ input đã kiểm bằng tool, không có test Qwen tự thêm.
- So theo cùng số test, luôn so cả với toolinput; control plain-hybrid được cùng số lần gọi và cùng vòng feedback, chỉ khác là không có hint.
- Chọn trên dev; pilot báo riêng.
- Commit sau mỗi phát hiện; cập nhật sơ đồ.

"Cách 1/2/3" là ba đề xuất trước đó: cách 1 = viết hint thành điều kiện trên input, cách 2 = Qwen viết call cụ thể + tool feedback, cách 3 = biến thể witness.

Tiêu chí xếp hạng: hint còn có lợi rõ ở đâu (bằng chứng v8-strict), sửa được bao nhiêu task, chi phí, và có dùng lại cho bước sau không.

| Hạng | Việc | Sửa tầng | Vì sao ở hạng này | Cách làm | Chi phí | Tiêu chí đạt |
|---|---|---|---|---|---|---|
| 0 (hạ tầng, đang chạy) | Đóng gói `pipelines/v7`; held-out MBPP+ 12 task; sample cuối của advdoc-hybrid | – | Cần cho mọi bước sau | Codex đóng gói và kiểm tra bản copy cho kết quả giống v7; script GPU đã sẵn | GPU cho phần chạy | bản copy cho ra đúng v7 (bundle, cache, report) |
| **1** | **Round 2: Qwen viết call cụ thể, tool trace trả feedback** (cách 2, v9) | C, B | Round 2 là chỗ duy nhất hint còn có lợi rõ (cùng số test 34/17). Đòn bẩy là số input chạm hint: Hypothesis chỉ giữ được 0.9 input mỗi sample. Bước này cũng là máy dùng lại cho hạng 4 | Với mỗi hint bị bỏ lỡ, Qwen viết 5 lời gọi cụ thể. Tool chạy PUT có trace và trả feedback (ví dụ "len = 2; the branch needs len < 2"), thử lại tối đa 2 lần, giữ tối đa 2 input chạm hint. Control plain-hybrid: cùng số lần gọi, feedback chỉ nói hợp lệ hay không | GPU | Số input chạm hint mỗi sample cao hơn hẳn 0.9; cùng số test thắng plain-hybrid và không thua toolinput |
| 2 | Chọn hint tốt hơn (offline) | A2 | 19 task mất ở tầng chọn dù kho đã có hint tốt; chỉ cần CPU, làm ngay được khi chưa có GPU. Chưa chắc tăng số bug vì Qwen vẫn làm theo kém, nên xếp sau hạng 1 | Bỏ luật loại theo kind, cho mọi kind cạnh tranh; dựng luật xếp hạng trên task chẵn, kiểm trên task lẻ | CPU | good@3 trên task lẻ tăng rõ so với luật hiện tại và so với chọn ngẫu nhiên |
| 3 | Viết hint thành điều kiện trên input (cách 1, offline) | B | Bị hạ hạng: hint từ spec của v7 vốn đã ở mức input mà round 1 vẫn làm theo kém (non-ASCII 7/48 so với plain 4/48; whitespace 4/18 so với 6/18), chỉ hint input rất lớn là giúp rõ (26/114 so với 0/114). Giá trị chính bây giờ là làm nội dung feedback cho hạng 1 | Tool so witness với input của base test (độ dài, dấu, 0, rỗng, hoa/thường, lặp, thứ tự, độ lớn, lớp ký tự) rồi viết điều kiện ở mức input. Đo trên 38 lượt "không thử dạng input đơn giản" | CPU | Phủ phần lớn 38 lượt đó; nếu đạt thì cắm vào feedback của hạng 1 |
| 4 | Input discovery cho các gap fuzz không chạm tới | A1 | Mọi hint hiện tại đã có witness của fuzz, nên LLM chỉ thêm giá trị ở chỗ fuzz không chạm được. Dùng lại máy của hạng 1 | Chạy vòng của hạng 1 trên 276 gap bí của v5; chỉ đo khả năng tìm input, không cần oracle | GPU | Giải được nhiều hơn hẳn 10/276 của Hypothesis; gap giải được thành hint mới có witness |
| 5 | Concept mức spec về hành vi | A1 | Nhắm khoảng 38 task tầng 1 (bug ngữ nghĩa), nhưng tốn công dựng, và hint spec của v7 chưa hơn round 2 không hint, nên rủi ro cao | Hint kiểu "spec yêu cầu output đã sắp xếp / không phân biệt hoa thường / hòa thì chọn phần tử đầu, nhưng base test chưa thử input phân biệt được", kèm witness | CPU dựng, GPU chạy | Có hint tốt ở các task bug ngữ nghĩa |
| 6 | Biến thể witness (cách 3) | B | Thực chất là "toolinput có thêm input", dễ chỉ tăng nhờ nhiều test hơn; cần control mới | Đưa hint kèm witness, yêu cầu k input khác witness mà vẫn chạm cùng chỗ; tool kiểm. Control: toolinput + fuzz variant ngẫu nhiên cùng số input | GPU | Thắng control đó khi so cùng số test |

Thứ tự thực hiện:
1. Ngay bây giờ (chưa có GPU): hạng 2 và hạng 3.
2. Khi có GPU: hạng 1, dùng kết quả hạng 3 làm feedback; sau đó hạng 4.
3. Hạng 5 và 6 tùy kết quả hạng 1.

Nếu có version mới thành bản tốt nhất trên dev, held-out vẫn giữ run v7 đã đăng ký làm kết quả chính; version mới chỉ báo phụ.

### Cập nhật sau khi xét ý kiến SAVIOR (2026-10-13)
SAVIOR tách hai bước: chọn nơi có nguy cơ lỗi (bug-driven prioritization), rồi tìm input thỏa điều kiện kích hoạt lỗi (bug-guided verification). Đối chiếu với linefacts:
- **Đã có:** MUTANT, BOUND và REL đã nhắm cả những chỗ đã được chạy. `fact_hit` của MUTANT đòi PUT và mutant ra output khác nhau (tracer.py:678). Vì vậy chỉ thêm "nhắm mutant" thì không phải cải tiến mới.
- **Gộp vào hạng 1:** feedback của tool chia 3 mức: (a) đã tới site, (b) hành vi cục bộ đã khác, (c) khác biệt đã truyền ra output. Đây là mô hình reach–infect–propagate, giúp Qwen biết input của nó hỏng ở bước nào.
- **Hạng 2 đổi thành chọn hint theo giả thuyết lỗi.** Xếp hint theo khả năng có lỗi, tính cả site đã được chạy, thay vì theo category, tier và độ đa dạng block như `pick()` hiện tại (facts.py:609). Có thể thêm một tín hiệu chỉ dùng spec: mutant nào ra cùng kết quả với đa số ref program (viết từ spec), trong khi PUT ra khác, thì là giả thuyết lỗi mạnh. Rủi ro: tín hiệu này gần với ý tưởng của TrickCatcher, phải ghi rõ khi so.
- **Hạng 3 mở rộng thành trigger inference.** Suy ra điều kiện trên input từ guard/path condition dẫn tới site, cộng với so witness với base input. Kết quả dùng làm nội dung feedback cho hạng 1.
- Thứ tự giữ nguyên: 1 > 2 > 3 > 4 > 5 > 6. Tiêu chí cuối vẫn là số bug bắt được với ref khi so cùng số test. Chỉ tăng coverage hay số mutant bị kill thì chưa tính là đạt.

### Thêm vào kế hoạch (2026-10-13, sau khi đọc VibePass)
- **VibePass metrics** (CPU, đêm nay): báo cáo lại các run trên dev theo V_I / V_IO / D_I / D_IO, để tách concept cải thiện bước tìm input (D_I) hay bước oracle (D_IO − D_I).
- **VibePass dataset làm held-out thứ hai** (CPU, đêm nay): kiểm tra buggy solution có qua public test của LiveCodeBench không (đúng setting TrickCatcher), đếm số PUT dùng được và đổi format (class method của LeetCode, stdin của AtCoder). Chỉ chạy method sau khi đăng ký riêng.

## 4. Kế hoạch sửa (2026-10-13 tối): giao thức công bằng + hướng giả thuyết lỗi

Luật (người dùng, 2026-10-13):
- Mọi bản sửa trong pipeline đều làm trong **folder mới** copy từ `pipelines/<bản tốt nhất>`, không sửa folder cũ.
- Mỗi folder mới phải có **`CHANGELOG.md`**: sửa gì so với bản gốc, file nào, commit nào, trạng thái (đang làm / đạt / bị loại).
  Các folder hiện có đã được thêm CHANGELOG.
- Thử xong việc nào thì **commit ngay** (kể cả khi kết quả âm tính).
- Việc **nhỏ** (CPU, script phân tích, sửa vài dòng): mình làm luôn. Việc **to** (sửa nhiều module của pipeline, baseline mới): đợi Codex.

### Việc nhỏ (mình làm, CPU)
| # | Việc | Nguồn | Ở đâu | Ra cái gì |
|---|---|---|---|---|
| S1 | Chấm **witness-only**: chỉ các input witness của fuzz (3 input mỗi sample, như toolinput nhưng bỏ phần LLM), oracle ref; so với toolinput (witness + test LLM thêm) và concept-hybrid | ghi chú của người dùng | `analysis/witness_only.py` (không đụng pipeline) | Tách phần đóng góp của fuzzing khỏi phần của LLM |
| S2 | Phân tích cùng số test bằng **random subset** (seed cố định, 100 lần, lấy trung bình), thay prefix truncation | sửa 4 (phần phụ) | `analysis/matched_subsets.py` | Số liệu cùng số test cho v8-strict, toolinput, placebo |
| S3 | Sửa adapter **TrickCatcher-full**: repr/`ast.literal_eval` thay JSON round-trip | sửa 5 | adapter baseline (chỉ phần serialise) | Kiểm offline: task 127 không mất input; rerun 7 task cần GPU |
| S4 | Hoàn tất `pipelines/v7_vp` (tracer cho class method): chạy test_equivalence (phải bằng v7) và vp_check trên 66 PUT | việc dở | `pipelines/v7_vp/` | Commit khi qua kiểm tra |
| S5 | Chép PREREG_PENDING.md vào PREREG.md khi mutref chạy xong | thủ tục | PREREG.md | – |

### Việc to (đợi Codex)
| # | Việc | Nguồn | Folder mới | Ghi chú |
|---|---|---|---|---|
| B1 | **v11_fair**: (a) strict sinh thật trong round 2; (b) placebo-hybrid cùng số request round 2; (c) giới hạn lúc sinh ≤ 8 lần gọi LLM, ≤ 20 assertion mỗi sample; (d) một scorer chung có tolerance cho oracle, evaluation và analysis; báo D_I, D_IO, precision | sửa 2, 3, 4, 6 | `pipelines/v11_fair/` (copy bản tốt nhất sau mutref) | Kiểm offline: khi tắt (a)–(c), scorer mới phải cho cùng kết quả với v7 ở mọi assertion không dính float |
| B2 | Hoàn tất baseline **CoverUp** và **MuTAP** (đã có một phần trong `baselines/`), dry run với fake client | PLAN_BASELINES bước 2 | `baselines/coverup/`, `baselines/mutap/` | Dùng chung ngân sách và scorer của B1 |
| B3 | **Thang ablation concept**: generic code review → flat concept (fact rời) → concept có quan hệ (typed relations: data/control dependence, spec-clause ↔ code-site); thêm bản bỏ liên kết spec–code. Cùng spec, code, tool, số lần gọi, token và ngân sách input; luôn kèm witness-only và toolinput | ghi chú của người dùng | `pipelines/v12_rel/` (copy từ v11_fair) | Đây là phép thử chính cho claim "concept giúp LLM" |
| B4 | **Giả thuyết vi phạm spec**: nối fact thành chuỗi "giá trị từ dòng A qua nhánh B tới dòng C vi phạm luật R"; cho phép giả thuyết chưa có witness, LLM sinh input, tool xác nhận reach/infect/propagate | ghi chú của người dùng; hạng 1 + 4 | `pipelines/v13_hyp/` (copy từ v12_rel) | Xếp hạng giả thuyết tính cả site đã cover (khoảng 1/3 bug nằm trên đường mọi base test đều chạy qua) |
| B5 | Chạy held-out **một lần** (VibePass 66, MBPP+ 12) với cấu hình chốt và mọi baseline | sửa 1 | – (GPU) | Chỉ sau B1–B2; B3/B4 chỉ lên held-out nếu thắng trên dev |

### Thứ tự
1. Ngay khi có GPU: chạy nốt v7_mutref (`out/runlogs_mutref/chain_from_score.sh`), phân tích theo PREREG, commit.
2. Mình làm S1 → S2 → S3 → S4 (CPU), mỗi việc xong commit một lần.
3. Khi Codex có quota: B1, rồi B2; tiếp theo B3, rồi B4. Mỗi bước: đăng ký PREREG trước, folder mới có CHANGELOG, commit sau khi thử.
4. B5 cuối cùng.
