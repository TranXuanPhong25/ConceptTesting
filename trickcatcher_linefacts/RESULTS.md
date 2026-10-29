# trickcatcher_linefacts: phương pháp, cấu hình, kết quả, ablation, threats, tiến độ

Cập nhật 2026-10-11. Bối cảnh: setting của TrickCatcher (Liu et al., ACL 2025), tập EvalPlus. Mỗi bài là một PUT do LLM viết,
**qua hết base test của HumanEval nhưng vẫn có bug**; nhãn lấy từ HumanEval+ (khoảng 700–1000 input/bài) cộng lời giải chuẩn.
Mục tiêu là sinh test **bắt được bug**, có hướng dẫn bằng **concept** (fact người đọc hiểu được, phát biểu bằng thuật ngữ học phần kiểm thử).
Chi tiết từng quyết định và sửa đổi có trong `PREREG.md` (đăng ký trước, kèm amendment).

---

## 1. Phương pháp

### 1.1 Pipeline (4 lane; sơ đồ: https://claude.ai/artifact/7a6yvf5bhiVmZVyt9UvTC8)

| Lane | Việc | Thành phần |
|---|---|---|
| A · Tool tính concept (mỗi bài, 1 lần) | tìm chỗ base test còn sót | đào precondition `valid()` từ spec → miền input → fuzz chỉ lấy input hợp lệ → chỗ sót của base test → xếp hạng top-3 fact |
| B · Sinh input (các arm khác nhau ở đây) | chọn input để test | LLM, generator, hoặc witness của tool |
| C · Oracle (hậu kiểm, không thấy code PUT) | tính expected | 10 bản ref viết từ spec → đồng thuận → judge → lọc postcondition |
| D · Chấm (chỉ ở đây dùng nhãn) | đo | HumanEval+ canonical + contract EvalPlus |

### 1.2 Concept (fact)
Fact có dạng "trong mọi test hiện có, tại điểm k, P luôn đúng" (giống likely invariant của Daikon, nhưng áp lên bộ test). Fact được fuzz xác nhận là chạm được.
Các loại fact theo học phần:
- C1/C2/C3 coverage; giá trị biên; lớp tương đương; def-use (DU);
- mutant còn sống: ROR/AOR/COR/UOI/CRP, cộng MUTANT-X (SDL, call-removal, SIR, BCR, ZIL/OIL/RIL) ở v3.

Xếp hạng v3: round-robin theo slot, mỗi biến chỉ một fact DU, K = 3. Cổng trên dev giữ lại MUTANT-X và DU.
Placebo dùng cùng văn phong nhưng nói về hành vi đã được test.

### 1.3 Các phiên bản tính fact
| Phiên bản | Điểm khác |
|---|---|
| v3f | fuzz tự viết, không lọc input theo spec (bộ đã chốt) |
| v3c | chỉ giữ fact có input thỏa **contract EvalPlus**; dùng làm mốc trần (contract là nhãn của benchmark) |
| v3m | precondition do Qwen đào inline từ chữ ký + docstring (ý tưởng từ RBCTest: observation → confirmation → predicate → verifier trên base test) |
| v3m2 | sửa bước confirmation: nhận cả điều kiện **suy ra tất yếu** (ví dụ "lengths" nên > 0); **kết quả chính hiện tại** |
| v4 | Hypothesis (strategy do LLM viết) + mutmut 3.8 + coverage.py; tracer chỉ giữ cho C3/biên/DU/vòng lặp; B5 bỏ kiểm trích nguyên văn |

### 1.4 Các arm (lane B)
| Arm | Input | Fact |
|---|---|---|
| plain | LLM tự viết ≤10 assert (thấy code + spec + base test) | — |
| concept | như plain + top-3 fact | có |
| gen-plain | LLM viết generator `sample_one()` bằng **prompt gốc của TrickCatcher** → 100 lần gọi → lọc hợp lệ → chọn 3 | — |
| gen-concept | như gen-plain + fact; tool `fact_hit` kiểm, sửa 1 lần, ưu tiên input chạm fact | có |
| gen-placebo | như gen-concept với fact placebo | placebo |
| toolinput | witness của fuzz cho top-3 fact | witness |
| v4: concept-hybrid / placebo-hybrid / plain-hybrid | vòng 1 viết trực tiếp; vòng 2 **chỉ cho fact chưa chạm**: LLM viết strategy Hypothesis nhắm fact đó. plain-hybrid có cùng số lượt vòng 2 nhưng không có fact (đối chứng "sinh nhiều hơn") | có / placebo / — |
| tc-full | TrickCatcher đầy đủ, chỉ thay model (mục 8) | — |

### 1.5 Oracle (lane C và các đối chứng), đều chấm trên **cùng input**
"full" là oracle hoàn chỉnh của lane C; không liên quan tới contract. Contract EvalPlus chỉ dùng khi chấm (lane D), áp cho mọi oracle.

| Oracle | Expected lấy từ |
|---|---|
| o0 | assert do arm tự viết (LLM thấy code) |
| o0+post | o0, bỏ assert vi phạm postcondition |
| b1one / b1 | LLM chỉ đọc chữ ký + docstring (không thấy code): 1 mẫu / 3 mẫu phải khớp nhau (ý của AugmenTest) |
| **ref (B2)** | 10 bản ref do Qwen viết bằng **prompt DPP gốc của TrickCatcher**, giữ bản qua base test; phát expected chỉ khi ≥3 bản sống **và đồng thuận tuyệt đối** |
| ref+judge (B4) | khi ref bỏ phiếu trắng mà input phân biệt PUT với mutant của một fact MUTANT: judge chỉ đọc spec, chọn giữa PUT(x) và mutant(x) (ý của AssertMate) |
| **full** | ref+judge, rồi lọc postcondition (B3, ý của DeCon; postcondition do Qwen viết, giữ cái đúng trên mọi cặp (input, output) của base test) |
| dpp / tc (B0) | variant GPT-3.5 mà TrickCatcher công bố: chỉ từ spec + đồng thuận / có xem PUT + luật Thuật toán 1 của họ |

### 1.6 Chỉ số
- **Detection:** một mẫu bắt được bug nếu có assert qua lời giải chuẩn và fail trên PUT, với input **thỏa contract**. Báo theo mẫu/K và theo bài (≥1 trong K mẫu).
- **Báo nhầm (FA):** assert fail trên lời giải chuẩn **hoặc dùng input trái contract EvalPlus** (quy tắc áp dụng từ 2026-10-11).
- **% mẫu báo bug cho chương trình đúng:** mẫu có ít nhất một assert báo nhầm. Bản gần đúng của RQ2 trong TrickCatcher.
- **Offline:** PF = tỉ lệ input HumanEval+ chạm fact mà làm PUT fail; strong@3 = số bài có ít nhất một fact với PF ≥ 0.5 trong top-3.
- **Thống kê:** sign test theo từng bài (số mẫu bắt được bug, từ 0 đến K). Primary là tập dev, pilot báo riêng.

---

## 2. Cấu hình

| Mục | Giá trị |
|---|---|
| Model | Qwen2.5-Coder-7B-Instruct, fp16, vLLM 0.7.3, transformers 4.48.2, tensor parallel 2 trên Kaggle 2×T4; endpoint OpenAI-compatible qua ngrok |
| Tập bài | 133 bài không thuộc nhóm thiết kế = **113 dev + 20 pilot**; loại nhóm thiết kế {22, 33, 111, 122, 123, 139} |
| K | 3 mẫu cho mỗi (bài, arm) |
| Arm (sinh assert) | temperature 0.7, top_p 0.95, max_tokens 1024; seed cố định theo (bài, arm, mẫu, stage, retry) |
| Đào precondition / strategy | temperature 0, top_p 1, max_tokens 4096 |
| B1 | t 0.7, 3 mẫu, mỗi request ≤10 lời gọi (≤1500 ký tự) |
| B2 ref | prompt `genprog_dfp_sys/usr` (sha256 `bdf6e9c7…`, `ba4085d3…`), t 0.8, 10 mẫu |
| B3 postcondition | t 0.8, 5 mẫu |
| B4 judge | t 0, max_tokens 512, thứ tự A/B ngẫu nhiên theo seed |
| Fuzz (v3) | 400 input hợp lệ, tối đa 2000 lần thử; biến đổi input base test + nhắm quan hệ |
| Generator (gen-*) | 100 lần `sample_one()`; cắt input >1000 ký tự; timeout 1 s/lần gọi và 120 s/tổng |
| Sandbox | mọi code của PUT và của LLM chạy dưới `unshare -rn python -I` |
| Prompt TrickCatcher | `geninput_generator_sys/usr`, `genprog_dfp_*`, nguyên văn từ artifact commit a0d285a, có kiểm sha256 |
| v4 | Hypothesis 6.169.0, mutmut 3.8.0 (libcst 1.9.0), coverage.py 7.16.2 |

---

## 3. Kết quả

### 3.1 Offline (dev, 112 bài có nhãn)
| Phiên bản | strong@3 | random@3 (cùng pool) | trần | Ghi chú |
|---|---|---|---|---|
| v3f | 45 | 43.8 | 53 | 29% witness hiển thị vi phạm contract |
| v3c (contract) | 46 | 46.4 | 53 | 0 witness trái spec; 8 bài mất hết fact |
| v3m (Qwen đào) | 44 | 44.9 | 53 | precondition: precision 0.85, recall 0.999 |
| v3m2 | 44 | 45.0 | 53 | precision 0.86, recall 0.998; 55/133 bài không còn ràng buộc nào |

PF trung bình của fact hiển thị khoảng 0.47, nền khoảng 0.17 (thắng/thua khoảng 51/21, p ≈ .0005). Pilot offline (v3f, chỉ chạy một lần): strong@3 5/20, random 8.2.
→ Fact trỏ đúng chỗ bug (PF gấp khoảng 3 lần nền), nhưng **xếp hạng chưa hơn chọn ngẫu nhiên** trong cùng pool.

### 3.2 Arm v3m2 với oracle o0 (dev, chưa áp quy tắc contract)
| Arm | Bug bắt được/mẫu | Bài bắt ≥1/3 | Báo nhầm |
|---|---|---|---|
| plain | 42.7 | 66 | 26.5% |
| concept | 47.0 | 65 | 30.4% |
| toolinput | 51.3 | 66 | 29.8% |
| gen-plain | 33.0 | 53 | 31.0% |
| gen-concept | 41.3 | 61 | 28.9% |
| gen-placebo | 36.3 | 61 | 29.2% |

- **gen-concept vs gen-plain: 35/18, p = .027.** Khi cắt về cùng số assert vẫn là 36/17, p = .013.
- Pilot: 8/0.

### 3.3 Re-oracle input của v3m2 (dev; báo nhầm tính cả input trái contract)
Mỗi ô: bug bắt được/mẫu · báo nhầm · % mẫu báo bug cho chương trình đúng.

| Arm | o0 | b1 | ref (B2) | full (ref+judge+post) | dpp (B0) |
|---|---|---|---|---|---|
| plain | 41.0 · 28% · 69% | 40.0 · 20% · 58% | 47.3 · 3.0% · 11% | 45.7 · 2.8% · 11% | 40.7 · 1.5% · 6% |
| concept | 44.7 · 33% · 73% | 47.0 · 21% · 60% | 53.0 · 4.8% · 14% | 52.0 · 4.1% · 13% | 46.0 · 2.3% · 8% |
| gen-plain | 31.7 · 32% · 79% | 29.3 · 21% · 51% | 39.3 · 2.5% · 7% | 39.0 · 2.5% · 7% | 34.3 · 1.1% · 3% |
| gen-concept | 39.0 · 31% · 75% | 36.7 · 20% · 54% | 47.0 · 3.8% · 10% | 45.7 · 3.3% · 9% | 39.7 · 2.3% · 7% |
| gen-placebo | 35.0 · 31% · 75% | 34.7 · 20% · 55% | 43.7 · 3.5% · 10% | 42.3 · 3.5% · 11% | 37.0 · 2.6% · 8% |
| toolinput | 48.0 · 32% · 74% | 49.3 · 23% · 61% | 60.0 · 4.3% · 17% | 60.0 · 3.5% · 14% | 52.7 · 2.4% · 10% |

So sánh theo từng bài (thắng/thua, p):

| So sánh | o0 | b1 | ref | full | dpp |
|---|---|---|---|---|---|
| concept vs plain | 29/19, .19 | 30/13, .014 | 28/14, .044 | **28/12, .017** | 25/12, .047 |
| gen-concept vs gen-plain | **33/18, .049** | 30/17, .079 | 28/15, .066 | 27/16, .13 | 23/16, .34 |
| gen-concept vs gen-placebo | 26/20, .46 | 23/21 | 22/22 | 21/22 | 18/19 |
| concept vs toolinput | 19/21 | 23/19 | 12/21 | 11/21, .11 | 10/20 |
| gen-concept vs toolinput | 18/32, .065 | 16/35, .011 | 11/34, .0008 | 11/36, .0003 | 8/32, .0002 |
| gen-plain vs plain | 16/37, .005 | 10/33, .0006 | 16/31, .04 | 17/29, .10 | 14/28, .044 |

Pilot (20 bài): gen-concept vs gen-plain là 9/1 (ref và full), 10/1 (o0). concept vs plain không khác biệt.

Thống kê phụ:
- B2: 1.172/1.330 ref qua base test; bỏ phiếu trắng vì không đủ 3 bản sống 972 lần, vì bất đồng 260 lần.
- B3: giữ được 423/647 postcondition, trên 116 bài.
- B4: chỉ 47 input cần judge; judge chọn PUT 33, mutant 9, bỏ trống 5; giá trị chọn đúng (theo canonical) 35/42.

### 3.4 Báo nhầm của o0 do đâu (v3m, dev, assert fail trên canonical)
| Nguyên nhân | concept | plain | toolinput |
|---|---|---|---|
| LLM tính sai expected (khoảng ½ tính hoặc đếm sai, khoảng ⅖ hiểu sai spec) | 74% | 79% | 67% |
| input trái contract | 11% | 6% | 17% |
| chép hành vi PUT (expected = output có bug) | 10% | 8% | 11% |
| đúng phần tử, sai thứ tự spec yêu cầu | 2% | 3% | 3% |
| còn lại (docstring sai, sai số float, dạng `is None`) | ~3% | ~3% | ~2% |

---

## 4. Ablation

1. **Nguồn oracle (cố định input):** o0 → o0+post → b1one → b1 → b1+post → ref → ref+judge → full (bảng 3.3).
   - Không cho LLM xem code (b1one) **không** giảm báo nhầm.
   - Bắt 3 mẫu khớp nhau (b1) giảm còn khoảng 20%.
   - Thêm postcondition giảm còn khoảng 10%.
   - **Để chương trình tính (ref) giảm còn 3–5% và tăng detection 6–12 bug/mẫu.**
   - Judge và postcondition chỉ thêm rất ít.
2. **Ai viết chương trình tham chiếu:** variant GPT-3.5 của TrickCatcher (dpp) báo nhầm thấp hơn nữa (1–2.6%) nhưng ít ref sống hơn (974/1.330) nên detection thấp hơn ref của Qwen. Luật tc (variant thấy PUT) có báo nhầm khoảng 20% khi tính cả input trái contract.
3. **Concept hay placebo:** ở các arm generator, gen-concept vs gen-placebo hòa với mọi oracle. Chưa tách được hiệu ứng **nội dung** fact.
4. **Sinh nhiều hơn hay sinh tốt hơn** (v3m, cắt về cùng số assert): gen-concept vs gen-plain 38/17, p = .006. Lợi thế không đến từ số assert. Chưa cân bằng được số lần gọi LLM (gen-concept có vòng sửa); plain-hybrid trong v4 kiểm soát yếu tố này.
5. **Viết chương trình sinh input hay viết thẳng:** gen-plain kém plain (16/37). Ép mọi fact đi qua generator là thiệt, nên v4 chỉ dùng chương trình cho fact khó (hybrid).
6. **Lọc input theo spec khi tính fact (v3f → v3c → v3m → v3m2):** offline gần như không đổi (45/46/44/44), nhưng không còn fact giả do input trái spec.
7. **Quy tắc contract khi chấm:** detection của o0 giảm, ví dụ concept 47.0 → 44.7. Phần chênh lệch này từng bị tính là "bắt bug" nhờ input trái spec.

---

## 5. Threats to validity

**Nội tại**
- **Model có thể đã nhớ HumanEval.** Qwen2.5-Coder và GPT-3.5 có thể đã thấy lời giải chuẩn của HumanEval, nên các bản ref/variant chính xác hơn thực tế. Oracle bằng chương trình có thể được lợi.
- **Chỉ có một nguồn đáp án.** Nhãn chỉ đến từ lời giải chuẩn HumanEval+ (Auditing: một nguồn đáp án duy nhất có thể làm phồng kết quả). HumanEval+ đã được kiểm tra kỹ, nhưng 5 bài có ví dụ docstring sai (doc_fail: 69, 152; pilot 108, 116, 131) được báo cáo riêng.
- **Nhãn không tất định.** PUT bài 34 và 58 trả `list(set(...))`, thứ tự phụ thuộc hash, nên số input fail thay đổi giữa các lần chạy. Mỗi phiên bản giữ nhãn của chính nó và có ghi cảnh báo.
- **Quyết định sau khi đã xem dữ liệu.** Tất cả được ghi trong PREREG:
  - thiết kế arm gen-* nảy ra sau khi xem pilot LLM;
  - v3m2 sửa prompt sau khi xem chất lượng đào precondition;
  - các sửa harness (bằng chứng lấy từ chữ ký hàm, predicate nhận tập con tham số, cắt input >1000 ký tự, timeout ở v4);
  - quy tắc contract khi chấm được thêm sau khi đã có kết quả o0.
- **Cổng chọn loại fact dùng chính tập dev**, nên dev nghiêng có lợi cho các arm có fact. Placebo chỉ kiểm soát được một phần.
- **Chi phí không cân bằng:** gen-concept gọi LLM nhiều hơn (retry). Đối chứng cân bằng là plain-hybrid (v4).
- **Hạ tầng:** ngrok từng gián đoạn. Đã có retry và cache theo khóa (messages + params), nên chạy lại không làm đổi output.

**Cấu trúc (construct)**
- Detection và báo nhầm tính theo assert/mẫu, khác precision/recall theo PUT của TrickCatcher. tc-full sẽ báo cả hai.
- "% mẫu báo bug cho chương trình đúng" là bản gần đúng: input được sinh khi LLM nhìn PUT có bug, không phải chương trình đúng.
- Judge (B4) được dùng quá ít (47 input) nên chưa đánh giá được.
- v4 mất các toán tử mà mutmut không có (SDL, SIR, ZIL/OIL/RIL, break↔continue đầy đủ); 6 bài timeout không có fact.

**Bên ngoài**
- Bài cỡ HumanEval: hàm nhỏ, Python, đặc tả bằng docstring.
- Chỉ một model 7B. Chưa thử TrickyBugs (bài thi lập trình, C++/Python).

**Kết luận thống kê**
- Có nhiều so sánh, chưa hiệu chỉnh p (multiple comparisons). Primary đã đăng ký trước là gen-concept vs gen-plain trên dev.
- Pilot chỉ 20 bài nên lực thống kê thấp.

---

## 6. Tiến độ (2026-10-11, khoảng 19:00)

| Hạng mục | Trạng thái | Đường dẫn |
|---|---|---|
| Fact v3f / v3c / v3m / v3m2 + offline | xong | `out/facts_v3*`, `out/offline_v3*` |
| Arm v3m2 (6 arm × 3 mẫu × 133 bài) | xong | `out/gen2_qwen7b_v3m2/` |
| Phân tích (a) cắt cùng số assert, (b) nguyên nhân báo nhầm | xong (v3m) | scratchpad `analysis/` |
| B0, B1, B2, B3, B4 trên input v3m2 | xong | `out/oracle_b01/report.txt`, `oracle_b01.py` |
| Quy tắc contract + % báo bug cho chương trình đúng | xong (trong `oracle_b01.py`) | |
| B5 + v4 tools + 7 arm | v4 xong offline (âm, mục 7); v4c (sửa arity) fact xong 127 + 6 timeout, đang chạy offline và arm | `run_v4.py`, `out/facts_v4c`, `out/gen2_qwen7b_v4c` |
| Oracle B1–B4 trên input v4 | chờ arm v4 | |
| tc-full (TrickCatcher đầy đủ, Qwen) + RQ2 trên chương trình đúng | xong (mục 8) | `tc_full.py`, `out/tcfull_qwen7b*` |
| Chưa commit | cần người dùng yêu cầu | |

## 7. Cập nhật 2026-10-11 khoảng 20:15: offline v4 (dev), kết quả âm

| Phiên bản | Bài có fact | strong@3 | random@3 | trần |
|---|---|---|---|---|
| v3m2 | 77/112 | 44 | 45.0 | 53 |
| **v4** | **47/112** | **22** | 22.2 | **23** |

- Nguyên nhân chính: **90/133 strategy Hypothesis do Qwen viết không qua kiểm tra**, nên phải dùng fallback `st.from_type`, tức sinh input ngẫu nhiên theo kiểu dữ liệu.
  - 65 bài lỗi "wrong_arity": số tham số mà strategy trả về không khớp hàm (ví dụ trả tuple sai số phần tử, hoặc trả thẳng một giá trị thay vì tuple tham số); 459 lần rút đều sai.
  - 9 + 3 bài có câu trả lời thừa code ngoài `def strategy()`.
  - Hệ quả: fuzz v4 chạm được ít chỗ sót hơn hẳn fuzz v3 (biến đổi từ input base test). Số fact chạm được: OUTCOME 19 so với 48, BOUND 24 so với 94, MUTANT 88 so với 199.
- Hướng sửa (chưa làm):
  - (a) harness tự bọc strategy trả một tham số thành tuple 1 phần tử, và nới quy tắc "chỉ có def strategy()";
  - (b) gộp miền input của LLM **với** fuzz v3 thay vì thay hẳn;
  - (c) cho LLM thêm một lần sửa có kèm ví dụ input của base test.
- v4 arm đang chạy lại (`out/gen2_qwen7b_v4b`); tc-full đang chạy (`out/tcfull_qwen7b`, RQ2).

## 8. Cập nhật 2026-10-11 khoảng 21:30: TrickCatcher đầy đủ với Qwen (tc-full), dev

Chỉ đổi model (GPT-3.5 → Qwen2.5-Coder-7B), giữ prompt và quy trình gốc (sinh input bằng generator, 10 variant, bỏ phiếu đa số), chạy trên đúng 133 bài này, K = 3 mẫu. Chấm cùng luật với các arm: input trái contract EvalPlus tính là báo nhầm.
Đầu ra: `out/tcfull_qwen7b/` (report.json, paper_metrics.json); RQ2: `out/tcfull_qwen7b_rq2/`.

| Phương pháp | bug bắt được/mẫu | bài bắt được ≥1/3 | báo nhầm | % mẫu báo bug cho chương trình đúng | so với tc-full theo bài (thắng/thua, p) |
|---|---|---|---|---|---|
| **tc-full (Qwen)** | **44.0** | 46 | 5.2% | 6% (ước lượng); RQ2 thật: 8/113 = 7.1% | |
| toolinput + ref | 60.0 | | 4.3% | 17% | **28/14, p = .044** |
| concept + ref | 53.0 | | 4.8% | 14% | 29/21, p = .32 |
| concept + full | 52.0 | | 4.1% | 13% | 29/21, p = .32 |
| plain + ref | 47.3 | | 3.0% | 11% | 31/24, p = .42 |
| gen-concept + ref | 47.0 | | 3.8% | 10% | 25/27, p = .89 |
| gen-placebo + ref | 43.7 | | 3.5% | 10% | 22/26 |
| gen-plain + ref | 39.3 | | 2.5% | 7% | 20/31, p = .16 |

- Chỉ số theo paper TrickCatcher (k = 5, dev): recall 0.378, precision 0.911, F1 0.534.
- RQ2 (thay PUT bằng chương trình đúng, chạy lại toàn bộ): 177 assertion trên 113 bài; 157 trong số đó là input trái contract, 20 là giá trị sai; 8 bài bị báo bug.
- Đọc kết quả:
  - Các arm của ta (cùng Qwen, oracle ref) bắt nhiều bug hơn tc-full về tổng số. Theo từng bài thì chỉ toolinput thắng có ý nghĩa; concept hơn nhưng chưa có ý nghĩa (29/21).
  - tc-full báo nhầm trên chương trình đúng ít hơn (6–7% so với 10–17%). Lý do: nó chỉ phát assertion khi PUT khác đa số variant, còn arm của ta phát mọi assertion mà oracle không bỏ phiếu trắng.
  - Các arm gen-* (cùng prompt sinh generator của TrickCatcher) không hơn tc-full. Phần thắng của concept/toolinput nằm ở chỗ chọn input trực tiếp, không ở generator.
- Script so sánh: scratchpad `analysis/tc_vs_arms.py`.

## 9. Nguồn tham khảo cho từng hướng

Cột "Mức dùng" ghi rõ mức độ: **nguyên văn** (dùng lại prompt/code/quy trình gốc), **chuyển thể** (lấy ý tưởng, cài lại cho setting này), **số liệu** (chỉ trích số để biện minh hoặc làm threat). Những paper đánh dấu * đã được agent đọc bản gốc (2026-10-11), nhưng mã arXiv/venue chưa được ghi lại ở đây; cần bổ sung trích dẫn đầy đủ trước khi viết luận văn.

### 9.1 Setting, dữ liệu, baseline

| Thành phần ở đây | Nguồn | Mức dùng |
|---|---|---|
| Setting "PUT qua base test nhưng vẫn có bug", 133 bài, PUT, base test | TrickCatcher: Liu et al., *LLM-Powered Test Case Generation for Detecting Bugs in Plausible Programs*, ACL 2025, tr. 430–440; artifact commit `a0d285a` | nguyên văn (dữ liệu) |
| Nhãn đúng/sai (canonical + input HumanEval+), contract dùng để chấm | EvalPlus: Liu et al., *Is Your Code Generated by ChatGPT Really Correct?*, NeurIPS 2023 (HumanEvalPlus v0.1.10) | nguyên văn (chỉ để chấm) |
| Bài gốc, docstring, base test | HumanEval: Chen et al. 2021, arXiv:2107.03374 | nguyên văn |
| Arm gen-plain (prompt sinh generator) | TrickCatcher, prompt `geninput_generator` trong artifact | nguyên văn |
| Arm gen-concept / gen-placebo | prompt generator của TrickCatcher + fact/placebo nối thêm | chuyển thể |
| tc-full (mục 8) | TrickCatcher, Sec. 4, Algorithm 1, App. A/B; chỉ thay GPT-3.5 bằng Qwen | nguyên văn (cài lại, được duyệt rule 2) |
| Oracle dpp (B0): variant chỉ từ spec + đồng thuận tuyệt đối | Differential Prompting: Li et al., *Nuances are the Key*, ASE 2023; bản DPP do TrickCatcher sửa và chạy sẵn bằng GPT-3.5 | nguyên văn (dùng output có sẵn) |
| Oracle tc (B0): variant có xem PUT | TrickCatcher, artifact | nguyên văn (dùng output có sẵn) |
| Precision/recall/F1 theo k, RQ2 chạy trên chương trình đúng | TrickCatcher Sec. 5 | nguyên văn (cách đo) |

### 9.2 Phía concept / input (lane A, B)

| Thành phần | Nguồn | Mức dùng |
|---|---|---|
| Từ vựng concept (statement/branch, biên, phân lớp tương đương, def-use, mutant) | slide môn kiểm thử (`test_slides/`, `VOCAB.md`) | đóng góp riêng của luận văn |
| Fact, xếp hạng, placebo, toolinput | thiết kế riêng (PREREG v1–v3) | đóng góp riêng |
| Đào precondition: observation → confirmation → code → verifier ngữ nghĩa (v3m, v3m2, B5) | RBCTest: Huynh et al., ICSE'26, arXiv:2504.17287 (gốc đào ràng buộc output của REST API; ở đây đào precondition input của hàm Python) | chuyển thể |
| B5: bỏ lọc trích nguyên văn, để verifier loại điều kiện bịa | RBCTest (verifier là lớp lọc chính) | chuyển thể |
| B5: ép precondition cứng thay vì nhắc trong prompt | ContractEval* (model chỉ tuân contract trong prompt 23–53%) | số liệu |
| v4: sinh input theo miền bằng Hypothesis, LLM viết strategy | Hypothesis: MacIver et al., JOSS 2019 (thư viện 6.169.0) | dùng thư viện |
| v4: mutant | mutmut 3.8.0 (thư viện) | dùng thư viện |
| v4: độ phủ | coverage.py 7.16.2 (thư viện) | dùng thư viện |

### 9.3 Oracle (lane C, B0–B4)

| Bước | Nguồn | Mức dùng |
|---|---|---|
| B1: oracle chỉ từ spec, không cho LLM thấy PUT; giữ khi các mẫu thống nhất | AugmenTest: Khandaker et al., arXiv:2501.17461 (bản Extended có FP 15.5% so với 27.3%); Doc2OracLL* | chuyển thể |
| B2: 10 chương trình tham chiếu chỉ từ spec, qua base test, đồng thuận tuyệt đối, ≥3 bản sống | DPP trong TrickCatcher (prompt `genprog_dfp` nguyên văn); Auditing: Liang et al., arXiv:2608.19626 (expected do LLM tự viết chỉ khớp 27.8–50.1% nhóm chương trình đúng) | chuyển thể (prompt nguyên văn, được duyệt rule 2) |
| B2: ref không được thấy PUT | TrickCatcher artifact: 263/1.229 variant có xem PUT giống hệt PUT | số liệu |
| B2 threat: đồng thuận vẫn có thể sai | DiffTrust: Valentin et al., *Incoherence as Oracle-less Measure of Error in LLM-Based Code Generation*, AAAI-26, arXiv:2507.00057 | số liệu |
| B3: lọc assert bằng postcondition, postcondition phải qua cặp base test | DeCon: Yu et al., *Detecting Incorrect Assertions via Postconditions Generated by a Large Language Model*, arXiv:2501.02901; Tratto* (cảnh báo FP khi không có verifier) | chuyển thể (được duyệt rule 2) |
| B4: judge chỉ thấy spec, chọn giữa PUT(x) và mutant(x) thay vì tự tính | AssertMate: Wang et al., *Agent-Based Test Assertion Generation via Diverse Perspective Aggregation*, IEEE TSE, arXiv:2608.05822 | chuyển thể |
| B4 (chưa làm): property thay cho expected | PBT-Bench* | ý tưởng |
| Đếm input trái contract là báo nhầm; đo trên chương trình đúng | Auditing (arXiv:2608.19626); TrickCatcher RQ2 | nguyên văn (cách đo) |

### 9.4 Đã đọc nhưng chủ động không dùng

| Paper | Lý do không dùng |
|---|---|
| DCAware: Li et al., *Escaping the Self-Repair Trap*, ASE 2026, arXiv:2608.05917; ChatAssert* | Sửa assert theo kết quả chạy trên PUT. Ở đây PUT có bug, nên sửa theo nó sẽ biến bug thành đáp án. Regression oracle cũng chứa bug. |
| Nexus: Huang et al., *Execution-Grounded Multi-Agent Test Oracle Synthesis*, arXiv:2510.26423 | Có vòng sửa theo PUT (cùng vấn đề trên); không có code. |
| FOCAL*, Tratto*, Doc2OracLL* | Cần train, và nhắm Java. |
| Ma, *From Business Requirements to Test Assertions*, arXiv:2607.10277 | Java, chỉ 10 bug, đầu vào là yêu cầu nghiệp vụ; không hợp setting. |

### 9.5 Thống kê
- Sign test hai phía (binomial chính xác), ghép cặp theo bài, bỏ bài hòa: `oracle_b01.sign_p`. Chưa hiệu chỉnh nhiều phép so sánh (xem mục 5).

## 10. Đo riêng phần tool (fuzzer + tracer + mutant), v3m2, dev

Tool chỉ tìm **input** chạm fact (witness), không biết expected: PUT(x) có bug nên không dùng làm đáp án được. Với fact MUTANT, tool có hai ứng viên PUT(x) và mutant(x) nhưng không biết cái nào đúng (chỗ này B4 dùng judge để chọn). Script: scratchpad `analysis/tool_witness.py` (bundle `tasks_v3m2_all.json`, đúng bundle của lượt chạy v3m2; bản đầu dùng nhầm `tasks_v3m_all.json`, đã sửa).

| Cấu hình | Kết quả |
|---|---|
| Bài có ít nhất 1 witness | 77/113 (138 witness, 24 trái contract EvalPlus) |
| Tool một mình + oracle hoàn hảo (canonical) | witness lộ bug ở **41 bài** (cận trên của riêng tool) |
| Tool một mình + oracle ref (không có LLM viết test) | **34 bài** |
| Arm toolinput (LLM thấy code + witness, viết assert, được thêm input) + ref | 60.0 bug/mẫu |
| Arm plain + ref | 47.3 bug/mẫu |

Nguồn bug bắt được trong arm toolinput (ref, 339 mẫu): chỉ nhờ witness 68, chỉ nhờ input LLM tự thêm 79, cả hai 33, không bắt được 159. Witness chiếm 396/3.018 assertion nhưng góp mặt trong 101/180 mẫu bắt được bug.

## 11. Cập nhật 2026-10-12 sáng: các phiên bản mới

### 11.1 Arm concept-toolinput (bước 3 kế hoạch v5; trên gợi ý v3m2, dev 113 bài, K = 3)
Một prompt: 3 câu gợi ý, mỗi câu kèm đầu vào mẫu chạm tới nó. Chấm lại bằng `oracle_b01.py --run out/gen2_qwen7b_v3m2_ct --out out/oracle_ct`; so theo bài bằng scratchpad `analysis/ct_paired.py`.

| Cách lấy kết quả đúng | concept-toolinput | toolinput | concept | plain | vs toolinput (chính) | vs plain |
|---|---|---|---|---|---|---|
| o0 (luật contract) | 45.3 · 33% | 48.0 | 44.7 | 41.0 | 17/22, p = .52 | 26/24 |
| ref | 57.0 · 5.0% | 60.0 | 53.0 | 47.3 | **11/16, p = .44** | 32/18, p = .065 |
| full | 56.3 · 4.6% | 60.0 | 52.0 | 45.7 | 10/16, p = .33 | 33/18, p = .049 |

Kết luận: gộp câu gợi ý vào cạnh đầu vào mẫu **không hơn** toolinput (phép so sánh chính đã đăng ký); hơn plain gần ngưỡng.
% báo lỗi chương trình đúng: ref 17%, full 14% (toolinput: 17%, 14%).

### 11.2 v5: Hypothesis chỉ khi bí (bước 2 kế hoạch v5)
- Hypothesis do LLM viết tìm được đầu vào cho **10/276** chỗ bỏ sót mà fuzz cũ không chạm (3.6%).
- Gợi ý chỉ đổi ở 4 bài (dev 20, 23; pilot 70, 151); bài dev có gợi ý 77 → 78. Offline: gợi ý tốt @3 = 44/112, tốt nhất 53, ngẫu nhiên 45.0, placebo 13, **giống hệt v3m2**.
- Bước 1 trước đó (v3mm, bản đột biến mutmut thay bản tự viết): 43/112, tốt nhất 49 → giữ bản tự viết.
- Kết luận: với dữ liệu này, cả mutmut lẫn Hypothesis "khi bí" đều không thêm được gợi ý có ích. Arm trên v5 chỉ chạy lại 4 bài đổi (PREREG "v5 step 2 result").

### 11.3 Lọc đầu vào trái đề (F1, F1b, F2, F4; chấm lại trên đầu vào của 6 arm v3m2, dev)
Mỗi bộ lọc bỏ test có đầu vào bị coi là trái đề **trước khi chấm**; contract EvalPlus chỉ dùng để đo bộ lọc. Script `validity_filters.py`, báo cáo `out/validity_filters/gen2_qwen7b_v3m2/report.txt`. Audit độ phủ nhóm ràng buộc: scratchpad `constraint_concepts/`.

| Bộ lọc | Cách | Bắt đầu vào trái đề (/591) | Gạt nhầm đầu vào hợp lệ (/11.907) | trong đó đang lộ bug | Held-out bài lẻ: bắt / gạt nhầm |
|---|---|---|---|---|---|
| F1 | điều kiện v3m2 (bắt trích nguyên văn) | 71 | 8 | 0 | 30 / 7 |
| **F1b** | điều kiện B5 (cùng prompt, tắt lọc trích dẫn) | **283** | 48 | 3 | **146 / 25** |
| F4 | đào có concept dẫn đường (đi qua 15 nhóm ràng buộc) | 211 | 113 | 30 | 65 / 30 |
| F2 | ≥ một nửa bản code ref crash | 102 | 7 | 2 | |
| F4b | F4 + 3 quy tắc chống tự đặt ràng buộc (rút từ bài chẵn/pilot) | 217 | 74 | 15 | 94 / 30 |
| F3 | Qwen chỉ đọc đề, hỏi "đầu vào có hợp lệ không", đa số 3 lần | 330 | **1.707** | 126 | |

Với cách lấy kết quả đúng ref (bug/lần chạy · báo nhầm · % lần chạy báo lỗi chương trình đúng):

| Arm | không lọc | F1b | F4 |
|---|---|---|---|
| concept | 53.0 · 4.8% · 14% | 52.7 · **2.6%** · **7%** | 52.0 · 3.1% · 8% |
| plain | 47.3 · 3.0% · 11% | 46.7 · 1.6% · 5% | 46.7 · 2.1% · 6% |
| toolinput | 60.0 · 4.3% · 17% | 59.7 · 2.3% · 9% | 59.0 · 3.2% · 12% |
| concept vs plain (theo bài) | 28/14, p = .044 | 29/14, p = .032 | 27/14, p = .060 |

- **F1b gần như giảm một nửa báo nhầm và % báo lỗi chương trình đúng, gần như không mất bug.** Gốc vấn đề cũ là bộ lọc "trích nguyên văn" trong bước đào (loại 126 điều kiện đúng).
- **F4 (concept dẫn đường) kém F1b**: khi đi qua từng nhóm, Qwen biến điều hàm *kiểm tra/trả về* thành điều kiện đầu vào (ví dụ "sắp xếp các số từ 1 đến 9" → đầu vào chỉ được 1..9; chính điều kiện tam giác vuông thành điều kiện đầu vào) nên gạt nhầm 113 đầu vào hợp lệ, 30 cái đang lộ bug. Trên bài lẻ (held-out) chỉ bắt 65 so với 146.
- 24% lời gọi trái đề vi phạm điều kiện mà đề không hề nói (ví dụ gcd đòi a, b > 0): không lọc hợp lệ được.
- F4b sửa được một phần (gạt nhầm 113 → 74) nhưng vẫn kém F1b cả trên bài lẻ held-out (bắt 94 so với 146, gạt nhầm 30 so với 25). Với Qwen 7B, prompt đào điều kiện mở ("liệt kê mọi điều kiện") + bỏ lọc trích dẫn đang tốt hơn prompt đi qua từng nhóm concept.
- F3 bắt nhiều đầu vào trái đề nhất (330) nhưng gạt nhầm 1.707 đầu vào hợp lệ (126 đang lộ bug): với ref, concept tụt 53.0 → 44.3 bug/lần chạy. Không dùng được.
- F5 (đưa điều kiện vào prompt sinh test): không có tác dụng, xem 11.5.

### 11.4 v4c chấm lại bằng ref/full (dev 112 bài có kết quả chấm, K = 3; `out/oracle_v4c/report.txt`)
Mỗi ô: bug/lần chạy · báo nhầm · % lần chạy báo lỗi chương trình đúng.

| Arm | o0 | ref | full |
|---|---|---|---|
| concept-hybrid | 46.7 · 29.9% · 77% | **56.3 · 3.6% · 14%** | 55.3 · 3.2% · 12% |
| toolinput | 42.3 · 29.6% · 76% | 55.0 · 3.9% · 12% | 54.3 · 3.7% · 12% |
| plain-hybrid | 45.0 · 29.7% · 77% | 50.7 · 2.1% · 9% | 50.7 · 2.3% · 10% |
| placebo-hybrid | 38.3 · 29.0% · 74% | 48.0 · 2.5% · 9% | 47.7 · 2.9% · 10% |
| plain | 40.7 · 29.0% · 74% | 44.7 · 2.0% · 8% | 44.3 · 2.2% · 9% |
| concept | 33.7 · 29.0% · 71% | 43.0 · 3.3% · 13% | 41.3 · 2.7% · 11% |
| gen-plain | 32.7 · 34.5% · 80% | 41.0 · 2.2% · 7% | 41.0 · 2.2% · 8% |

So theo bài (ref / full): concept-hybrid vs plain-hybrid 26/14 (p = .081) / 24/14 (p = .14); vs placebo-hybrid 27/20 / 27/21; vs toolinput 22/21 / 21/21; concept vs plain 18/23 / 16/24.
- Với kết quả đúng đáng tin, concept-hybrid đứng đầu và ngang toolinput, hơn plain-hybrid gần ngưỡng; nhưng gợi ý v4c yếu nên concept (một vòng) vẫn thua plain. Vòng 2 (Hypothesis cho gợi ý chưa chạm) giúp rõ: concept-hybrid vs concept 22/0, plain-hybrid vs plain 14/0 — một phần do thêm test.

### 11.5 F5: viết điều kiện đầu vào (đào bởi B5) vào prompt sinh test (dev 113 bài, K = 3; `out/oracle_req/report.txt`)
Cùng gợi ý v3m2, cùng 3 arm; chỉ thêm một đoạn "đầu vào phải thỏa: ..." vào prompt (121/133 bài có điều kiện). So với v3m2 (không có đoạn đó):

| Arm | đầu vào trái đề (v3m2 → F5) | bug/lần chạy, ref (v3m2 → F5) | F5 thắng/thua theo bài (ref) |
|---|---|---|---|
| concept | 5.3% → 5.0% | 53.0 → 52.0 | 14/16, p = .86 |
| plain | 2.8% → 3.5% | 47.3 → 46.0 | 12/15, p = .70 |
| toolinput | 5.5% → 6.1% | 60.0 → 60.7 | 11/8, p = .65 |

- **Kết quả âm:** Qwen 7B gần như phớt lờ đoạn điều kiện trong prompt; tỉ lệ đầu vào trái đề không giảm. Lọc sau khi sinh (F1b, 11.3) vẫn là cách hiệu quả.
- Trong F5, concept vs plain vẫn giữ: ref 29/16 (p = .073), full 30/15 (p = .036).
- Ghi chú: toolinput đưa nguyên đầu vào do tool tìm ra (có thể trái đề) vào prompt nên càng không bị đoạn điều kiện ảnh hưởng.

### 11.6 Property concept, bước A: tính chất kết quả làm cách chấm (dev; `property_oracle.py`, `out/property_oracle/report.txt`)
Dùng các điều kiện kết quả B3 (LLM viết từ đề, chỉ giữ điều đúng trên mọi test cũ) làm cách chấm trên cùng đầu vào của 6 arm v3m2: test bắt lỗi khi kết quả của hàm có lỗi vi phạm tính chất mà đáp án chuẩn thỏa. Chỉ xét đầu vào hợp lệ theo EvalPlus.
- 98/113 bài có ít nhất một tính chất; tổng 361 tính chất, 25 tính chất bị đáp án chuẩn vi phạm trên đầu vào hợp lệ nào đó.
- Tính chất bắt được 50 bài; ref bắt 82 trên cùng đầu vào. Chỉ 4 bài tính chất bắt mà ref không; 36 bài ngược lại.
- 13 bài có tính chất báo lỗi cả chương trình đúng.
- Kết luận: tính chất yếu hơn hẳn kết quả đúng cụ thể; chỉ đáng dùng bổ sung khi ref bỏ trống. Bước B (concept property dẫn sinh test) để sau, ưu tiên hướng giảm đầu vào trái đề.

### 11.7 RBCTest: mỗi bước giúp bao nhiêu (bỏ từng bước của F1b; dev, đầu vào của 6 arm v3m2)
Bộ đào điều kiện F1b (B5) có 4 bước lấy từ RBCTest: (1) liệt kê điều kiện, (2) xác nhận từng điều kiện có trong đề, (3) viết code kiểm tra, (4) chạy code đó trên đầu vào của test cũ và docstring, điều kiện nào làm đầu vào hợp lệ bị từ chối thì loại. Mỗi bản dưới bỏ một bước, dùng lại đúng câu trả lời đã lưu của B5; chỉ bản bỏ bước (2) cần một lần gọi viết code mới mỗi bài (cùng prompt, seed). Script `rbc_ablation.py`; báo cáo `out/validity_filters/gen2_qwen7b_v3m2_rbc/report.txt`.

| Bản | Điều kiện giữ lại | Bắt đầu vào trái đề (/591) | Gạt nhầm đầu vào hợp lệ (/11.907) | …đang lộ bug | concept với ref (bug · báo nhầm · báo lỗi chương trình đúng) | concept vs plain (ref) |
|---|---|---|---|---|---|---|
| không lọc | – | 0 | 0 | 0 | 53.0 · 4.8% · 14% | 28/14, p = .044 |
| **F1b (đủ bước)** | 286 | 283 | **48** | 3 | **52.7 · 2.6% · 7%** | 29/14, p = .032 |
| bỏ (4) chạy trên test cũ | 365 | 335 | 2.319 | 103 | 46.0 · 2.9% · 6% | 25/13 |
| bỏ (2) xác nhận | 305 | 287 | 89 | 21 | 50.7 · 2.6% · 7% | 27/14 |
| bỏ cả (2) và (4) | 398 | 338 | 2.734 | 231 | 39.7 · 3.2% · 6% | 24/12 |
| F1: thêm bắt trích nguyên văn (không có trong RBCTest) | 151 | 71 | 8 | 0 | 53.0 · 4.0% · 11% | 28/14 |

- **Bước (4) là bước quan trọng nhất.** Bỏ nó, bộ lọc gạt nhầm gấp khoảng 48 lần (48 → 2.319 đầu vào hợp lệ, 103 cái đang lộ bug) và concept mất 6.7 bug/lần chạy. Nó loại 79/365 điều kiện sai, ví dụ bài 52 "mọi phần tử của l phải nhỏ hơn t" (đó là điều hàm kiểm tra rồi trả True/False, không phải điều kiện đầu vào), bài 62 "xs có ít nhất 2 phần tử", bài 68 "độ dài arr từ 1 đến 10000" (test cũ có list rỗng).
- **Bước (2) giúp vừa phải.** Trực tiếp nó chỉ loại 15/421 điều kiện, nhưng khi bỏ nó thì code viết cho cả danh sách khác đi và gạt nhầm tăng 48 → 89 (21 cái lộ bug), concept mất 2 bug/lần chạy.
- **Bước bắt trích nguyên văn mình thêm vào (F1) có hại:** loại 201 điều kiện, phần lớn là đúng, nên chỉ bắt 71 thay vì 283.
- Mọi bản đều giữ concept hơn plain theo bài (p từ .03 đến .07).

### 11.8 hybrid trên gợi ý v3m2 (dev 113 bài, K = 3; `out/oracle_v3m2hyb/report.txt`)
Cùng 7 cách của v4c, chỉ đổi sang gợi ý v3m2. "-hybrid": vòng 1 LLM viết test như cách gốc; vòng 2, gợi ý nào chưa test nào chạm thì LLM viết mô tả Hypothesis cho riêng gợi ý đó, máy sinh đầu vào, LLM viết kết quả đúng. Mỗi ô: bug/lần chạy · báo nhầm · % lần chạy báo lỗi chương trình đúng · test/lần chạy.

| Cách | o0 | ref | full |
|---|---|---|---|
| **concept-hybrid** | 49.7 · 31% | **62.0 · 3.9% · 15% · 10.9** | 60.7 · 3.4% · 12% |
| toolinput | 47.3 · 31% | 60.7 · 3.3% · 14% · 7.7 | 60.7 · 2.6% · 12% |
| plain-hybrid | 46.0 · 32% | 53.0 · 2.7% · 10% · 11.0 | 52.0 · 2.5% · 9% |
| concept | 37.0 · 32% | 47.3 · 4.4% · 14% · 8.1 | 45.7 · 3.6% · 11% |
| placebo-hybrid | 37.0 · 30% | 47.0 · 3.0% · 9% · 8.7 | 45.3 · 2.9% · 9% |
| plain | 40.3 · 29% | 45.0 · 2.4% · 9% · 8.2 | 43.3 · 2.5% · 9% |
| gen-plain | 33.0 · 35% | 41.3 · 2.3% · 7% · 7.1 | 40.3 · 2.3% · 8% |

So theo bài (ref; trong ngoặc: cắt về cùng số test, giữ N test đầu nên chủ yếu cắt test vòng 2):
- **concept-hybrid vs plain-hybrid: 32/14, p = .011** (29/15, p = .049); full 31/14, p = .016. Hai cách có cùng số test (10.9 so với 11.0), nên đây là so sánh công bằng nhất: cùng quy trình, chỉ khác có gợi ý concept hay không.
- concept-hybrid vs placebo-hybrid: 33/11, p = .001, nhưng cắt về cùng số test còn 21/19. Gợi ý giả (chỗ đã kiểm) ít khi "chưa được chạm" nên placebo-hybrid ít được vòng 2; phần thắng chủ yếu đến từ vòng 2.
- concept-hybrid vs toolinput: 19/17 (hòa); cắt về số test của toolinput (7.7) thì toolinput thắng 33/16.
- Vòng 2 giúp mạnh: concept-hybrid vs concept 25/0, plain-hybrid vs plain 18/0.
- concept một vòng vs plain ở prompt v4: 22/17 (không có ý nghĩa), yếu hơn ở prompt gen2 (28/14).
- Kết luận: trên gợi ý tốt, concept + vòng 2 Hypothesis là cách mạnh nhất cùng với toolinput, và hơn rõ bản cùng quy trình không có concept. Nó tốn nhiều test hơn toolinput (10.9 so với 7.7) cho cùng số bug.

### 11.9 Đính chính: concept một vòng vs plain khi chạy lại với seed khác
Lượt hybrid (§11.8) tạo test vòng 1 của concept và plain bằng **đúng** prompt gen2 (`prompts.build`), cùng gợi ý v3m2, cùng temperature 0.7; chỉ khác seed. Vậy nó là một lần chạy lặp lại độc lập (trước đây mình gọi nhầm là "prompt v4").

| | concept | plain | theo bài (ref) | theo bài (full) |
|---|---|---|---|---|
| gen2 (seed cũ) | 53.0 | 47.3 | 28/14, p = .044 | 28/12, p = .017 |
| seed mới | 47.3 | 45.0 | 22/17, p = .52 | 21/16, p = .51 |
| gộp 6 lần chạy | 50.2 | 46.2 | 34/26, p = .37 | 33/24, p = .29 |
| F5 (thêm đoạn điều kiện vào prompt) | 52.0 | 46.0 | 29/16, p = .073 | 30/15, p = .036 |

Kết luận: concept một vòng hơn plain khoảng 4 bug/lần chạy, cùng chiều trong cả 3 lượt chạy, nhưng gộp lại không có ý nghĩa thống kê theo bài. Kết quả p = .044 của gen2 một phần do may. Bằng chứng mạnh cho concept hiện là concept-hybrid vs plain-hybrid (32/14, p = .011, cùng số test).

### 11.10 Phân tích điểm yếu của lượt tốt nhất (concept-hybrid trên v3m2, chấm ref, dev 113 bài)
Chia bài theo chất lượng gợi ý (offline, gợi ý tốt @3 của v3m2): không có gợi ý (36 bài), có gợi ý nhưng không cái nào tốt (33), có gợi ý tốt (44). "Bắt" = ít nhất 1 trong 3 lần chạy.

| Nhóm bài | Bắt: concept-hybrid / plain-hybrid / toolinput | concept-hybrid vs plain-hybrid (theo bài) | vs toolinput |
|---|---|---|---|
| có gợi ý tốt (44) | 35 / 30 / 35 | **20/3** | 5/7 |
| gợi ý không tốt (33) | 19 / 21 / 16 | 7/8 | 7/4 |
| không có gợi ý (36) | 20 / 19 / 19 | 5/3 (prompt giống plain, chỉ khác seed) | 7/6 |

- Toàn bộ lợi thế của concept nằm ở 44 bài có gợi ý tốt. 69/113 bài (61%) không có gợi ý tốt nào để đưa.
- 39 bài bỏ sót: 29 bài không có test nào dùng đầu vào hợp lệ làm lộ bug; 10 bài có đầu vào lộ bug nhưng ref bỏ trống hoặc sai.
- Vòng 1 LLM chỉ chạm tới 33–54% gợi ý tốt (OUTCOME 33%, BOUND 42%, MUTANT 54%; NUM 86%); sau vòng 2 lên 69–89%.
- Gợi ý NUM/BOUND ("n chưa bao giờ bằng 0", "chưa bao giờ âm") đẩy LLM thử giá trị đề không cho phép: tỉ lệ đầu vào trái đề concept 3.8% so với plain 2.4% ở bài có gợi ý loại này (gộp 2 lượt chạy). Ví dụ bài 36, 41: "n chưa bao giờ bằng 0" → test n = 0, trái điều kiện EvalPlus.
- Trên bài có gợi ý tốt, toolinput (đầu vào mẫu chạm gợi ý) ngang hoặc hơn concept-hybrid (7/5) với ít test hơn.

### 11.11 Vòng 2 so với gọi LLM thêm một lần (ref, dev)
-hybrid giữ nguyên test vòng 1 rồi thêm test, nên không bao giờ thua bản một vòng (plain-hybrid vs plain 18/0 là đương nhiên). Đối chứng công bằng hơn: gộp test của 2 lần gọi độc lập cùng prompt (seed gen2 + seed lượt hybrid), ký hiệu ×2.

| | 1 lần gọi | -hybrid (test/lần chạy) | ×2 (test/lần chạy) | -hybrid vs ×2 theo bài |
|---|---|---|---|---|
| plain | 45.0 | 53.0 (12.3) | **57.0** (18.5) | 8/20, p = .036 |
| concept | 47.3 | **62.0** (12.4) | 59.0 (18.3) | 11/16, p = .44 |

Vòng 2 không có concept (plain-hybrid) kém việc hỏi LLM thêm một lần; vòng 2 có concept thì bằng hoặc hơn, với ít test hơn (12 so với 18). (Số test ở đây đếm lời gọi khác nhau, gồm cả đầu vào trái đề.)

### 11.12 Phân tích chi tiết điểm yếu (trang: https://claude.ai/artifact/8v4jfJxo9Sjc9z9foNW6G1; dữ liệu `out/analysis_weak/`)
- 36 bài không có gợi ý: Codex (đọc code + docstring + test cũ, chạy được code, không xem HumanEval+) bắt 33/36, chỉ 1/61 assert sai (`out/codex_nofacts/`). concept-hybrid bắt 20/36. 14 bài chỉ Codex bắt gần như đều là edge case về lớp input: input rất lớn (đệ quy tràn, 5 bài), ký tự ngoài ASCII (3), phần tử lặp (3), khoảng trắng (1), rỗng (1), lồng ngoặc (1).
- 33 bài gợi ý sai chỗ: 9 bài kho có gợi ý tốt cùng loại nhưng luật chọn bỏ sót; 10 bài gợi ý tốt chỉ thuộc loại bị loại khỏi prompt (SHAPE/OUTPUT/LOOP…); 10 bài kho chỉ có gợi ý chạm vùng lỗi yếu; 4 bài không gợi ý nào chạm.
- LLM không làm theo gợi ý tốt (vòng 1): 87/195 lượt bỏ lỡ, 42 cặp (bài, gợi ý). 19 cặp: không thử dạng input đơn giản mà gợi ý cần (list 1 phần tử, rỗng, a > b, toàn số âm, chữ hoa); 17: cần tính tổ hợp cụ thể; 4: thử đúng hướng nhưng lệch; 2: chỉ chạm được bằng input trái đề.
- Input trái đề do gợi ý: 16 bài concept sinh input trái đề mà plain không (4 bài khác không có gợi ý, chỉ là nhiễu). Nhóm A (9 bài): gợi ý về 0/âm/dưới cận. Nhóm B (3): gợi ý trỏ vào code tự kiểm tra input sai. Nhóm C (4): điều kiện ngầm khó (số nguyên tố, không trùng, quan hệ độ dài).
- toolinput = witness (input fuzz đầu tiên chạm gợi ý) của chính 3 gợi ý concept; không dùng nhãn (`facts.py:95,150,514,953`, `run_gen.py:341`).
- v6 (gợi ý fuzz dưới validator F1b): gợi ý đã đưa có witness trái đề giảm 29/165 → 16/156; 12 bài dev đổi gợi ý; 75/113 bài còn gợi ý.
- v6 offline (`out/offline_v6_report/REPORT.md`): gợi ý tốt @3 44/112 (v3m2: 44), tốt nhất 52 (53), ngẫu nhiên 44.6 (45.0), placebo 13 (13). Bỏ gợi ý trái đề không làm mất gợi ý tốt. Chưa chạy LLM (GPU tắt).

### 11.13 v7: concept từ đề cho bài không có gợi ý (offline, dev; `out/offline_v7/report.txt`)
`spec_facts.py`: với bài không còn gợi ý từ code (v6), công cụ không dùng LLM kiểm tra test cũ đã có input thuộc 4 lớp chưa: rất lớn (≥ 1000 phần tử/giá trị), phần tử lặp, ký tự ngoài ASCII, khoảng trắng đầu/cuối/lặp. Lớp nào điều kiện F1b cho phép mà test cũ chưa có → gợi ý, kèm input mẫu (biến đổi từ input test cũ). Bốn lớp rút từ các bài chẵn trong 14 bài chỉ Codex bắt.
- 36 bài dev có gợi ý v7 (64 gợi ý: LARGE 38, NONASCII 16, SPACE 6, DUP 4); dev có gợi ý 75 → 111/113.
- Gợi ý tốt (PF ≥ .5 trên HumanEval+) ở 11/36 bài; bài chẵn (dùng để rút lớp) 6/20, bài lẻ (held-out) 5/16. Trước đó các bài này có 0 gợi ý.
- Hạn chế đo: HumanEval+ ít khi có input ≥ 1000 hoặc ký tự ngoài ASCII (nhiều gợi ý PF 0/0, tức không có input nào để chấm), nên số "gợi ý tốt" là cận dưới. Kết quả viết test: đang chạy.

### 11.14 v6: viết test trên gợi ý dựng lại dưới F1b (dev 113 bài, K = 3; `out/oracle_v6hyb/report.txt`)
- Chỉ 12 bài dev đổi gợi ý (17, 20, 36, 56, 59, 67, 71, 109, 127, 135, 148, 160); các bài khác có prompt giống hệt v3m2-hybrid nên kết quả lặp lại (dùng lại cache).
- Trên 12 bài đổi gợi ý, input trái đề của concept: 51/335 (15.2%) → 37/335 (11.0%); concept-hybrid 71/565 → 61/515; plain không đổi 41/346 (11.8%). Concept gần về mức của plain.
- Toàn bộ dev, chấm ref: concept 47.3 → 47.3 bug/lần chạy, báo nhầm 4.4% → 3.9%, % báo lỗi chương trình đúng 14% → 13%; concept-hybrid 62.0 → 61.3, 3.9% → 3.7%. Bug không mất.
- concept-hybrid vs plain-hybrid vẫn giữ: ref 30/13 (p = .014), full 29/13 (p = .020). concept-hybrid vs toolinput 19/18.
- Còn sót: bài 13 (gcd, "a chưa bao giờ âm") và 49 (modp) vẫn giữ gợi ý trái đề vì F1b không đào được "a, b > 0" / "n ≥ 0" từ đề.

### 11.15 v7: viết test trên 36 bài có gợi ý từ đề (tạm: thiếu 4 lượt plain-hybrid; ref từ cache, không b1/judge)
`out/gen2_qwen7b_v7hyb_v4_partial`, `out/oracle_v7hyb_partial`. So với v6 (cùng 36 bài, khi đó không có gợi ý). Ô: bug/lần chạy với ref.

| Cách | v6 → v7 | bài bắt được (≥1/3) | báo nhầm ref | input trái đề |
|---|---|---|---|---|
| concept | 14.7 → 15.3 | 19 | 1.8% → 2.2% | 1.6% → 2.5% |
| concept-hybrid | 14.7 → **20.3** | 24 | 1.8% → 1.5% | 1.6% → 1.6% |
| plain | 14.0 → 14.0 | 18 | 0.6% | 0.5% |
| plain-hybrid (bỏ 46, 63, 160) | 14.0 → 18.7 | 22 | 0.6% | 0.5% → 1.8% |
| placebo-hybrid | 14.3 → 13.3 | 15 | 0.9% | 1.0% |
| toolinput | 14.3 → 17.7 | 22 | 1.0% → 2.0% | 0.9% → 2.1% |

- concept-hybrid bắt thêm 6 bài, đều đúng các lớp Codex tìm ra: ký tự ngoài ASCII (16, 141, 161), input rất lớn (46, 63, 66); không mất bài nào (v7 vs v6 theo bài 11/4, p = .12).
- Nhưng plain-hybrid cũng tăng (14.0 → 18.7): ở v6 các bài này không có gợi ý nên plain-hybrid không có vòng 2; ở v7 nó được cùng số lượt vòng 2 như concept-hybrid. concept-hybrid vs plain-hybrid 6/6, concept vs plain 7/7: **chưa thấy nội dung gợi ý từ đề hơn vòng 2 chung chung**.
- concept-hybrid vs placebo-hybrid 12/3 (p = .035; chẵn 7/0, lẻ 5/3).
- Kết quả cuối cần 4 lượt plain-hybrid còn thiếu và b1/judge (cần GPU).
- Tỉ lệ lượt (gợi ý × lần chạy) có input thuộc đúng lớp gợi ý (`eval_hits.jsonl`, sau khi sửa bộ chấm): rất lớn — plain 0/114, concept 26/114, concept-hybrid 27/114 (vòng 2 không sinh được input > 1000 ký tự); ngoài ASCII — 4/48, 7/48, **41/48**; khoảng trắng — 6/18, 4/18, 7/18; lặp — 6/12, 6/12, 11/12. Ở vòng 1, LLM hiếm khi làm theo gợi ý "ký tự ngoài ASCII" (7/48); vòng 2 bù được.

### 11.16 Baseline EvalAndMitigate (Zhao et al., ISSTA'26): onlydoc, advdoc (dev 113 bài, K = 3; `out/oracle_evalmitigate/report.txt`)
Code: `evalmitigate/` (Codex port, prompt giữ cấu trúc của `EvalAndMitigate/Prompt_example`, không cho thấy test cũ như paper). onlydoc: test chỉ từ chữ ký + docstring gốc. advdoc: Qwen soi lỗi → sửa code → viết docstring mới (T = 0, 1 lần/bài), rồi viết test chỉ từ docstring mới.

| Cách | o0 | ref | full |
|---|---|---|---|
| advdoc | 38.7 · 25.1% · 72% | 42.7 · 3.9% · 16% | 41.0 · 3.5% · 15% |
| onlydoc | 37.3 · 22.2% · 63% | 40.3 · 2.9% · 12% | 39.7 · 2.7% · 12% |
| (so sánh) concept-hybrid / plain / concept, lượt v3m2-hybrid | | 62.0 / 45.0 / 47.3 | 60.7 / 43.3 / 45.7 |

Theo bài (ref): concept-hybrid vs advdoc **38/7 (p = 3e-6)**, vs onlydoc **45/8 (p = 2e-7)**; toolinput vs advdoc 36/9; plain-hybrid vs advdoc 34/17 (p = .024); concept vs advdoc 26/18 (p = .29); plain vs advdoc 28/22 (p = .48); advdoc vs onlydoc 19/17.
- Trên HumanEval với Qwen 7B, hai baseline của paper không hơn plain (cách có thấy code + test cũ). Bỏ code đi làm giảm báo nhầm ở o0 (onlydoc 22% so với plain 29%) nhưng cũng bỏ mất thông tin để chọn input, nên bắt ít bug hơn.
- concept-hybrid hơn rõ cả hai baseline.
- Khác với setting của paper: HumanEval có docstring gốc tốt (paper giả định không có), các cách của mình thấy test cũ còn baseline thì không.
- advdoc: 128/133 bài đọc được docstring mới; 5 bài dùng lại docstring gốc (fallback).

### 11.17 Ghép: input của concept-hybrid + kết quả đúng kiểu onlydoc (không GPU; dev)
b1one = Qwen chỉ đọc chữ ký + docstring (không thấy code) viết kết quả đúng 1 lần, đúng kiểu onlydoc; b1 = 3 lần phải khớp. Mỗi ô: bug/lần chạy · M · E · báo nhầm (M = test qua trên hàm lỗi nhưng fail trên bản đúng, E = ngược lại; % trên số test có kết quả).

| Input của | o0 (thấy code) | b1one (kiểu onlydoc) | b1 | ref |
|---|---|---|---|---|
| onlydoc (paper) | 37.3 · 0.7% · 6.3% · 22% | 38.7 · 0.7% · 6.6% · 22% | 36.7 · 0.4% · 7.2% · 14% | 40.3 · 0.3% · 7.8% · 3% |
| advdoc (paper) | 38.7 · 0.9% · 6.3% · 25% | 41.3 · 0.7% · 6.4% · 26% | 38.7 · 0.5% · 7.0% · 17% | 42.7 · 0.2% · 8.5% · 4% |
| plain | 40.3 · 2.3% · 7.9% · 29% | 41.0 · 1.5% · 7.8% · 33% | 39.3 · 1.3% · 9.1% · 20% | 45.0 · 0.3% · 11.6% · 2% |
| concept-hybrid | 49.7 · 2.9% · 8.0% · 31% | **55.0** · 2.0% · 9.4% · 32% | 51.0 · 1.8% · 10.1% · 21% | **62.0** · 0.5% · 14.5% · 4% |
| toolinput | 47.3 · 3.0% · 8.8% · 31% | 53.0 · 1.8% · 10.5% · 32% | 50.3 · 1.4% · 12.0% · 20% | 60.7 · 0.3% · 15.5% · 3% |

- Ghép concept-hybrid (chọn input) + kết quả kiểu onlydoc: 55.0 bug/lần chạy, hơn onlydoc của paper 43/11 (p = 1e-5), hơn advdoc 41/16 (p = .001); với b1: 41/15 và 37/19. Đổi cách lấy kết quả đúng trên cùng input của concept-hybrid: o0 49.7 → b1one 55.0 (18/7, p = .043) → ref 62.0. Hai hướng cộng được với nhau.
- Nhưng M của concept-hybrid với b1one vẫn 2.0%, cao hơn onlydoc (0.7%) dù cả hai không thấy code: input sát vùng lỗi là chỗ đọc đề dễ hiểu sai theo đúng cách hàm lỗi đã hiểu sai. M thấp của onlydoc một phần vì input của nó ít khi chạm vùng lỗi (E cũng thấp). ref cho M thấp nhất (0.2–0.6%) và E cao nhất.

### 11.18 Ước lượng (không GPU): test advdoc + test vòng 2 của concept-hybrid (dev, ref)
Ghép test của advdoc với các test vòng 2 (Hypothesis nhắm gợi ý) mà concept-hybrid / plain-hybrid đã sinh ở lượt v3m2-hybrid, cùng mẫu (task, sample); chấm bằng ref.
- advdoc 42.7 bug/lần chạy (9.8 test) → advdoc + vòng 2 concept **55.0** (13.1 test), theo bài 23/0 (p = 2e-7); advdoc + vòng 2 plain (cùng số lượt gọi) 51.3 (13.0 test); concept vs plain 13/5 (p = .096).
- Hạn chế: vòng 2 ở đây nhắm các gợi ý mà vòng 1 của concept bỏ lỡ, không phải của advdoc; chạy đúng cần GPU (cách "advdoc-hybrid").

### 11.19 Lưu ý về dev/pilot (đọc trước khi trích dẫn các kết quả trên)
- Mọi lựa chọn phiên bản (v3f → v7, các arm, oracle, bộ lọc) đều được làm và so trên 113 bài dev; dev đóng vai tập validation, không phải tập kiểm tra. Một số quyết định dùng nhãn HumanEval+ trên dev (cổng chọn loại gợi ý; lớp input của v7 rút từ các bài Codex bắt được, đã chấm bằng đáp án). Chưa hiệu chỉnh p cho việc so nhiều cặp.
- Pilot (20 bài) dự định làm tập kiểm tra nhưng đã dùng một phần khi dựng taxonomy F4, và quá nhỏ. Trên pilot, lượt tốt nhất (v3m2-hybrid, ref): placebo-hybrid 11.0, toolinput 11.0, concept-hybrid 10.7, plain-hybrid 10.3, plain 9.7, concept 9.7 (trên 20 bài): **không thấy** lợi thế của concept.
- Kết luận chắc chắn cần chốt cấu hình rồi chạy một lần trên tập mới (ví dụ PUT EvalPlus chưa dùng / PUT của model khác, hoặc TrickyBugs).

### 11.20 Property làm cách chấm dự phòng khi ref bỏ trống (lượt v3m2-hybrid, dev; `out/property_oracle_v3m2hyb/`)
Khi ref không đưa ra kết quả (quá ít bản code hoặc bất đồng), dùng các tính chất kết quả B3 (LLM viết từ đề, giữ cái đúng trên mọi test cũ): test bắt bug nếu kết quả của hàm lỗi vi phạm tính chất mà đáp án chuẩn thỏa; báo nhầm nếu đáp án chuẩn cũng vi phạm.
- Mọi cách tăng khoảng 3 bug/lần chạy (thêm 3–4 bài), ví dụ concept-hybrid 62.0 → 65.0, toolinput 60.7 → 64.7, plain 45.0 → 48.0.
- Đổi lại % lần chạy báo lỗi chương trình đúng tăng 3–5 điểm (concept-hybrid 15% → 20%).
- concept-hybrid vs plain-hybrid giữ nguyên: 33/15 (p = .013).
- Kết luận: property là phần bù nhỏ, có giá; không đổi kết luận chính. Bước B (concept tính chất dẫn sinh test) chưa làm.

### 11.21 v7 kết quả cuối (đủ 2793 lượt, chấm đủ b1/judge; `out/gen2_qwen7b_v7hyb_v4_r2`, `out/oracle_v7hyb/report.txt`)
Toàn dev (ref): concept-hybrid **67.0** (v6 61.3), toolinput 64.7, plain-hybrid 57.3, concept 48.0, placebo-hybrid 45.7, plain 45.0; báo nhầm concept-hybrid 3.3%, % báo lỗi chương trình đúng 15%.
- Toàn dev theo bài (ref): concept-hybrid vs plain-hybrid 33/16 (p = .021), vs placebo-hybrid 38/8, vs toolinput 23/20; concept vs plain 23/20.
- Riêng 36 bài có gợi ý từ spec: concept-hybrid 14.7 → 20.3, plain-hybrid 14.0 → 18.7; concept-hybrid vs plain-hybrid 8/6 (p = .79), concept vs plain 7/7; vs placebo-hybrid 12/3 (p = .035; chẵn 7/0, lẻ 5/3). Kết luận như bản tạm (§11.15): lợi chủ yếu nhờ có vòng 2, chưa thấy nội dung gợi ý spec hơn vòng 2 không gợi ý.

### 11.22 Held-out MBPP+ (đang dựng; `out/heldout_mbpp/`)
PUT: lời giải blind của Codex (lượt 1, model mặc định: 42 PUT) và gpt-5.6-luna (lượt 2; lần thử đầu sinh template lỗi cú pháp, đã loại; lần sau 46 PUT), gộp 53. Đọc tay (`labels_manual.json`, gắn trước mọi kết quả): chỉ **9/53 là bug thật** (logic 3, robustness 2, performance 4); 44 là spec MBPP mơ hồ hoặc canonical MBPP+ lạ (ví dụ `removezero_ip('0.0.0.0') == '0...'`, `check_integer('') is None`). 35 bài là PUT ở cả hai model. MBPP+ vì vậy là held-out yếu; cần cân nhắc nguồn khác trước khi chạy.
- Lượt 3 (Claude Haiku, blind, trên 322 bài lượt 1 làm đúng; `blind_haiku/`, `filter_haiku/summary.json`): 322/322 file
  parse, không file nào trùng; 10 PUT, 5 bài mới (93, 223, 264, 453, 792). Đọc tay: bug thật 93 (mũ âm trả 1), 264
  (`int()` cắt 10.5 thành 10), 453 (số chính phương cộng căn hai lần); mơ hồ 223 (cả 58 input fail đều có n ≠ len(arr),
  trái "its length (n)"), 792. Tổng held-out **58 PUT, 12 bug thật**. Chốt cấu hình (PREREG held-out amendment 3):
  công thức v7, chính trên 58 bài, phụ trên 12 bài bug thật. Đang port pipeline sang MBPP+ (`heldout/`, Codex).

### 11.23 advdoc-hybrid: test advdoc + vòng 2 nhắm gợi ý (tạm: 797/798 lượt, endpoint chết 23:05; `out/oracle_advhyb_partial/report.txt`)
Vòng 1 = test của advdoc (EvalAndMitigate); gợi ý v3m2 nào chưa test nào chạm thì vòng 2 viết mô tả Hypothesis cho nó, kết quả đúng của input mới do Qwen viết chỉ từ docstring mới. Đối chứng advdoc-plainhybrid: cùng số lượt vòng 2, không có gợi ý. ref/post lấy từ cache, không b1/judge; so theo bài bỏ bài 160 (thiếu 1 lượt). Dev, bug/lần chạy · báo nhầm · % báo lỗi chương trình đúng:
- ref: advdoc-hybrid **56.0** · 3.8% · 17%, advdoc-plainhybrid 51.3 · 3.7% · 16%, advdoc 42.7; full: 54.0 / 50.3 / 41.0.
- Theo bài (ref): advdoc-hybrid vs advdoc **21/0 (p = 1e-6)**, advdoc-plainhybrid vs advdoc 15/0; advdoc-hybrid vs advdoc-plainhybrid **13/6 (p = .17)**; vs onlydoc 35/11.
- So với các cách của mình (lượt v3m2-hybrid, cùng gợi ý): vs concept-hybrid 9/20 (p = .061; full 9/21, p = .043), vs plain-hybrid 30/24, vs toolinput 13/21.
- Khớp ước lượng §11.18 (55.0 vs 51.3). Vòng 2 cộng thêm được vào baseline của paper; gợi ý concept hơn vòng 2 không gợi ý theo hướng đúng nhưng chưa có ý nghĩa thống kê. advdoc-hybrid vẫn kém concept-hybrid: vòng 1 thấy code + test cũ (concept) tốt hơn vòng 1 chỉ từ docstring.
- Pilot (20 bài, ref): advdoc-hybrid 8.0, advdoc-plainhybrid 6.7 (bài 160 thuộc dev).

### 11.24 Vì sao concept-hybrid hơn advdoc-hybrid (dev, bỏ bài 160; script `analysis/`)
Chạy PUT và đáp án chuẩn trên mọi input đã sinh để tách "chọn input" (có input làm PUT ≠ đáp án, tức một oracle hoàn hảo sẽ bắt) khỏi "lấy kết quả đúng" (ref). Bug/lần chạy:

| Cách | input lộ bug vòng 1 | ref vòng 1 | + vòng 2 (lộ bug) | input lộ bug tổng | ref tổng | ref/lộ bug | input vòng 1 trùng test cũ | input trái spec vòng 1 | % input lộ bug |
|---|---|---|---|---|---|---|---|---|---|
| concept-hybrid | 53.3 | 47.3 | +15.7 | 69.0 | 62.0 | 0.90 | 2.6% | 4.5% | 13.5% |
| advdoc-hybrid | 49.3 | 42.7 | +13.7 | 63.0 | 56.0 | 0.89 | 15.7% | 7.5% | 8.7% |
| plain-hybrid | 51.7 | 45.0 | +9.3 | 61.0 | 53.0 | 0.87 | 1.8% | 3.0% | 12.3% |

- Không phải do oracle: ref biến input lộ bug thành phát hiện với tỉ lệ như nhau (0.90 / 0.89). Khoảng cách nằm ở input.
- Khoảng 3/4 khoảng cách (4.6 trên 6.0) đến từ vòng 1 (vòng 1 của concept-hybrid chính là arm concept, của advdoc-hybrid là arm advdoc); vòng 2 thêm gần như nhau (+14.7 vs +13.3 với ref), dù advdoc-hybrid có nhiều gợi ý bị bỏ lỡ hơn (1.35 vs 1.15 yêu cầu/lần chạy).
- advdoc viết test chỉ từ docstring, không thấy code và test cũ: 15.7% input vòng 1 là chép lại đúng input của test cũ (ví dụ trong docstring), mà PUT đã qua mọi test cũ nên các input này không thể lộ bug; nhiều input trái spec hơn (`strlen(None)`, `string_to_md5(None)`); input chọn kiểu "điển hình" (1, 2, 3, rỗng). concept thấy code nên nhắm chỗ code yếu: số thực cho `incr_list` (42), ký tự ngoài ASCII cho `strlen` (23), `string_sequence(1000)` (15, chậm), `'Aba'` cho `is_palindrome` (48), chuỗi rỗng cho `find_max` (158).
- Trên 20 bài concept-hybrid thắng: cả 20 bài advdoc-hybrid có ít lần chạy có input lộ bug hơn; 9 bài khác biệt chỉ ở vòng 1, 9 bài cả hai vòng, 2 bài chỉ ở vòng 2.
- Tách phần vòng 1 (ref): advdoc 42.7 → plain 45.0 (thấy code + test cũ) → concept 47.3 (thêm gợi ý). Phần "thêm gợi ý" ở vòng 1 không chắc khi chạy lại seed khác (§11.9).

### 11.25 v7: concept-hybrid có thắng toolinput không (dev, ref; `analysis/v7_vs_toolinput.py`)
- Thô: concept-hybrid 67.0 vs toolinput 64.7, theo task 23/20 (p = .76); full 65.7 vs 65.0, 22/22. **Chưa thắng.**
- concept-hybrid dùng nhiều test hơn: 14.2 vs 8.7 call/sample. Cắt concept-hybrid về đúng số test của toolinput: 46.7, toolinput thắng **37/15 (p = .003)**. Concept một vòng vs toolinput: 18/37 (p = .015). Pilot: toolinput 11.0, concept-hybrid 10.0.
- Gộp test của concept-hybrid + toolinput: 76.7 (21.0 call/sample), nhưng gộp 2 sample concept-hybrid cũng được 75.0 (25.5 call/sample; 8/9), plain-hybrid + toolinput 75.3 (13/8): lợi chỉ do nhiều test hơn, không do kết hợp.
- toolinput cũng dùng concept: input của nó là witness input của chính các hint (fact → input), chỉ không có câu chữ. Theo số test, đưa thẳng input hiệu quả hơn đưa câu hint rồi để LLM tự chọn input.

### 11.26 Round 2 thật ra thêm gì (v7 dev, ref; `analysis/round2_split.py`)
Round 2 chọn tối đa 2 Hypothesis input mỗi hint bị bỏ lỡ, rồi gọi Qwen bằng prompt toolinput (thấy code + base test + các input đó, "write an assertion for each of these inputs; you may add others", tối đa 10). Khi không chọn được input nào, prompt này thành prompt plain, tức một lần gọi plain mới.
- concept-hybrid: 1.88 request/sample nhưng chỉ giữ được 0.9 Hypothesis input/sample; 103/238 sample có round 2 không chọn được input nào. Qwen tự thêm 4.5 test/sample (call mới, khác round 1).
- Bug/run tăng ở round 2: concept-hybrid +19.0 = chỉ nhờ Hypothesis input 8.0, chỉ nhờ test Qwen tự thêm 6.0, cả hai 5.0. plain-hybrid +12.3 = 7.0 / 3.0 / 2.3 (2.3 Hypothesis input và 2.8 test tự thêm mỗi sample).
- Hypothesis input rất hiệu quả (0.9 test/sample cho 13 bug/run). Nhưng khoảng 1/3 phần tăng của concept-hybrid là "gọi Qwen thêm một lần", và concept-hybrid được lần gọi plain miễn phí này nhiều hơn plain-hybrid (103 vs 71 sample không có input), nên một phần khoảng cách concept-hybrid vs plain-hybrid không đến từ hint.

### 11.27 v8-strict: round 2 chỉ giữ Hypothesis input đã chọn (CPU, exact cho ref/full; `out/oracle_v8strict_est/report.txt`, `analysis/v8_compare.py`)
Dựng từ run v7: concept-hybrid / plain-hybrid / placebo-hybrid = test round 1 + đúng các input round 2 đã chọn (bỏ 4.0 / 2.3 / 0.5 test Qwen tự thêm mỗi sample); arm khác giữ nguyên. Chấm ref/post từ cache, không judge (mọi arm chấm cùng thư mục). Dev, ref (call/sample):
- toolinput 64.7 (8.7), **concept-hybrid 61.0** (9.9; v7 67.0), plain-hybrid 55.7 (11.9; v7 57.3), concept 48.0, placebo-hybrid 45.3, plain 45.0.
- concept-hybrid vs plain-hybrid: **29/20 (p = .25)** (v7 33/16, p = .021). Cùng số test (cắt arm nhiều test hơn): 58.3 vs 48.0, **34/17 (p = .024)**. vs placebo-hybrid 33/13 (p = .005). vs toolinput 22/23; cùng số test 16/36 (p = .008).
- 36 task có hint từ spec: concept-hybrid vs plain-hybrid 18.3 vs 18.3 (8/7); vs toolinput 9/7.
- Kết luận: phần thắng plain-hybrid của v7 có phần nhờ lần gọi Qwen thêm; bỏ đi thì không còn significant khi để nguyên số test, nhưng vẫn significant khi so cùng số test (plain-hybrid giữ nhiều input round 2 hơn vì chỉ cần input hợp lệ). Hint từ spec (v7) không hơn round 2 không hint.

### 11.28 Metric kiểu VibePass (V_I / D_I / D_IO; dev, per sample = task/run; `analysis/vibepass_metrics.py`, `analysis/vibepass_metrics_report.md`)
V_I = có input hợp lệ; D_I = có input làm PUT ≠ canonical (lộ bug, không cần oracle); D_IO = có input lộ bug kèm expected value đúng theo oracle. FH = V_I − D_I (khoảng hụt do tìm input sai), OV = D_I − D_IO (khoảng hụt do expected output sai).

| run / arm | V_I | D_I | D_IO o0 | D_IO ref | FH | OV o0 | OV ref |
|---|---|---|---|---|---|---|---|
| v7 toolinput | 110.3 | 75.7 | 47.0 | 64.7 | 34.7 | 28.7 | 11.0 |
| v7 concept-hybrid | 112.0 | 75.0 | 51.7 | 66.7 | 37.0 | 23.3 | 8.3 |
| v7 plain-hybrid | 113.0 | 67.0 | 50.7 | 57.3 | 46.0 | 16.3 | 9.7 |
| v8-strict concept-hybrid | 110.7 | 69.3 | – | 61.0 | 41.3 | – | 8.3 |
| v8-strict plain-hybrid | 112.7 | 64.3 | – | 55.7 | 48.3 | – | 8.7 |
| v8-strict placebo-hybrid | 113.0 | 52.0 | – | 45.3 | 61.0 | – | 6.7 |
| advdoc / onlydoc | 112.3 / 112.7 | 50.0 / 47.7 | 38.7 / 37.7 | 42.7 / 40.3 | 62.3 / 65.0 | 11.3 / 10.0 | 7.3 / 7.3 |
| advdoc-hybrid / -plainhybrid (tạm) | 111.3 | 63.0 / 58.7 | 46.7 / 44.3 | 56.0 / 51.3 | 48.3 / 52.7 | – | 7.0 / 7.3 |

- Giống VibePass: khoảng hụt lớn nhất là tìm input (FH 35–65 task/run); input hợp lệ không phải vấn đề. OV phụ thuộc oracle: với o0 là 10–29, với ref chỉ 6–11.
- Theo task trên D_I: v7 concept-hybrid vs plain-hybrid 36/21 (p = .063); v8-strict 32/22 (p = .22); vs toolinput 24/26 (v7), 23/29 (v8); vs placebo-hybrid 44/10 (v7), 39/15 (v8). Phần hơn của concept nằm ở phía input nhưng so với plain-hybrid chưa significant; chỉ chắc khi so với placebo.

### 11.29 Hạng 2: chọn hint theo giả thuyết lỗi (offline; fit trên 58 task chẵn, kiểm trên 54 task lẻ; `analysis/hint_rank.py`, `analysis/hint_rank_report.md`)
Kho hint = mọi fact code của v6 (mọi kind, không loại) + fact spec của v7, khoảng 13 hint/task; luật chấm điểm rồi lấy top 3. good@3 (chẵn / lẻ):
- pick() hiện tại: v6 24 / 20, v7 29 / 25. Random trên toàn kho: 25.7 / 29.4. Ceiling toàn kho: 42 / 44.
- LR không dùng ref: 35 / 32 (vs random p = .20). Luật tay: 35 / 33 (p = .10). **Không có luật nào không dùng ref thắng rõ random trên task lẻ.**
- **LR + tín hiệu mutref** (trên input PUT và mutant khác nhau, mutant khớp đa số ref program còn PUT thì không): 37 / **35**, vs random p = .018, vs pick_v7 trên task lẻ 10/0 (p = .002). Tỉ lệ hint tốt của MUTANT khi mutref bật .56, khi không bật khoảng .25, như nhau trên chẵn và lẻ. Tín hiệu này gần ý TrickCatcher (dùng ref program viết từ spec), phải ghi rõ.
- LR + mutref + refdis (PUT khác đa số ref trên input chạm hint): 38 / 40, nhưng refdis gần như chính là oracle ref, là cận trên, không đưa vào method.
- Phần lớn mức tăng đến từ **bỏ luật loại theo kind** (random trên toàn kho đã 29.4 so với pick 25), và từ việc luôn đưa đủ 3 hint (pick hay đưa ít hơn 3). good@3 không đo việc Qwen có làm theo được hint không (luật mới chọn nhiều OUTPUT, SHAPE, LOOP-MAX trước bị loại), nên phải chạy LLM mới biết số bug có tăng không.
- Tỉ lệ hint tốt theo kind: MUTANT .44, OUTCOME .44, STMT .43, DU .42, MUTANT-X .38, BOUND .35, DECISION .30, NUM .22, LOOP-MAX .21, OUTPUT .19, REL .18, SHAPE .13, LOOP .12, SPEC .10. Site đã được base test chạy hay chưa không phân biệt được hint tốt/xấu (.23 vs .22).

### 11.30 Hạng 3: trigger inference, viết hint thành điều kiện trên input (offline; `analysis/trigger_conditions.py`, `analysis/trigger_conditions_report.md`)
Thư viện feature cố định (độ dài, rỗng, dấu, 0, độ lớn, sắp xếp, lặp, lớp ký tự, quan hệ giữa tham số…), chốt trước khi xem kết quả. Điều kiện gồm 1–2 feature, phải đúng với witness và sai với mọi base input, và trên fuzz input phải dự đoán được việc chạm hint (P(hit|C) ≥ .5 và ≥ 3 lần P(hit|không C)). Fuzz được chạy lại khớp hoàn toàn với out/facts_v3m2.
- Trên 87 lượt Qwen bỏ lỡ hint tốt (lượt v3m2): dựng được điều kiện và điều kiện đó giải thích được lần bỏ lỡ (không input hợp lệ nào của Qwen thỏa) ở **53/87**. Theo nguyên nhân: "không thử dạng input đơn giản" **34/38**, "đúng hướng nhưng lệch" 3/8, "chỉ invalid input mới chạm" 3/6, "cần tính giá trị cụ thể" 13/35 (8 không có ứng viên).
- Kiểm trên chính input hợp lệ của Qwen: input thỏa điều kiện chạm hint 105/110 (95%), không thỏa thì chỉ 13/852 (1.5%). Điều kiện đúng là trigger thật; nhưng chưa chạy LLM nên chưa chứng minh được đưa điều kiện vào prompt sẽ sửa được lần bỏ lỡ.
- Độ phủ: 45/65 hint tốt đã đưa, 114/165 hint đã đưa (dev); 117/139 điều kiện chỉ 1 feature (độ dài = 1 hoặc 2, giá trị 0, số âm, rỗng…).
- Lưu ý: câu hint mẫu kèm "e.g. <witness>" thì gần như thành toolinput; thử công bằng phải dùng câu điều kiện không kèm witness, hoặc dùng làm feedback round 2 (hạng 1). Với task 94, điều kiện mô tả input mà spec đã đào cấm, nên đưa vào sẽ sinh thêm invalid input.

### 11.31 VibePass làm held-out thứ hai: khả thi (CPU, không LLM; `analysis/vibepass_feasibility.py`, `analysis/vibepass_feasibility_report.md`)
- 173 dòng / 76 câu hỏi. 83 buggy solution qua hết public test của LiveCodeBench; 73 trong đó fail ít nhất 1 private test (72 sai output, 1 chỉ timeout) và khác silver trên input mà `test_checker` chấp nhận: **73 PUT dùng được / 30 câu hỏi**. Bản strict (sai output hoặc crash, silver qua hết test chính thức): 71 / 28 câu hỏi; riêng LeetCode **66 PUT / 24 câu hỏi**.
- Bug khó: buggy solution trung vị chỉ fail 23% private test, dài trung vị 77 dòng; 45/66 là hard, 21 medium, không có easy. Nhiều PUT cùng câu hỏi (có câu 7 bản) nên phải thống kê theo câu hỏi.
- Silver qua hết public, 170/173 qua hết private (3 dòng chỉ timeout). `test_checker` chấp nhận mọi input chính thức và loại 52% input tự sinh, dùng được làm contract (do GPT-5-mini viết, chưa audit tay).
- 10 dòng AtCoder bị gắn nhãn "buggy" chỉ vì cách harness LiveCodeBench đọc stdin / thread; đề xuất bỏ AtCoder (chỉ 5 dòng strict, cần thêm 1–2 ngày dựng runner).
- Đề xuất: dùng 66 PUT LeetCode strict làm held-out phụ (bài khó, báo riêng, không gộp với MBPP+), map public test → base check(), silver → đáp án, test_checker → contract, private test + input sinh hợp lệ → chấm. Dựng format khoảng 0.5–1 ngày; cần kiểm công cụ fact/mutant chạy được với method trong class. Đăng ký PREREG riêng trước khi chạy.

### 11.32 Held-out MBPP+ 12 bug thật, cấu hình v7 đã đăng ký (`out/heldout_mbpp_real12/oracle_v7hyb/report.txt`)
12 task, K = 3, 7 arm, chấm ref/full (không có dpp/tc). Bug/run (trên 12 task), số task bắt được ≥ 1/3 lần, false alarm, test/sample, ref:
- plain 2.67 · 3 · 1.0% · 8.8; plain-hybrid 2.67 · 3 · 2.6% · 10.7; toolinput 2.67 · 3 · 5.3% · 7.9; concept 2.33 · 3 · 11.8% · 7.3; **concept-hybrid 2.33 · 3 · 9.3% · 9.2**; placebo-hybrid 2.33 · 3 · 1.3% · 8.9; gen-plain 1.33 · 2.
- Theo task (ref): concept-hybrid vs plain-hybrid 1/1, vs toolinput 0/1, vs placebo-hybrid 1/1, concept vs plain 1/1. Mọi arm chỉ bắt được khoảng 3/12 bug; **không thấy lợi thế của concept** trên held-out, và mẫu quá nhỏ để kết luận gì thêm.
- Concept sinh nhiều invalid input hơn hẳn: 31 assertion trái contract ở concept và concept-hybrid, false alarm 9–12% so với 1–3% của plain/plain-hybrid. Precondition đào cho MBPP+ (spec ngắn) không chặn được các hint trỏ ra ngoài miền hợp lệ — đúng điểm yếu A3.
- ref abstain vì bất đồng 119 lần (ref program 100/120 sống); judge được hỏi 13 lần, chọn đúng 10.

### 11.33 CrossHair trên 276 gap bí của v5 (CPU, không LLM; `analysis/crosshair_gaps.py`, `analysis/crosshair_gaps_report.md`)
Cài đặt chốt trước: crosshair-tool 0.0.111 (z3 5.1), 60 s CPU mỗi gap, precondition = validator B5, kiểu tham số lấy từ base input; witness chỉ tính khi `tracer.fact_hit` chạm và validator v4 chấp nhận. 276 gap = 238 dev + 38 pilot; không có gap MUTANT (BOUND 133, SHAPE 51, OUTCOME 35, NUM 30, STMT 14, REL 13).
- STMT/OUTCOME/BOUND (182 gap): CrossHair kiểm được **10/276** (dev 6/238), bằng Hypothesis do LLM viết (10/276; 9 nếu dùng validator v4). Chỉ trùng 5; gộp cả hai được 15/276. 161/182 gap hết 60 s; 10 gap được chứng minh không tới được (dưới precondition và kiểu đã thấy).
- Mở rộng sang SHAPE/REL/NUM: 24/276 (gộp với Hypothesis 27/276), nhưng 10/14 witness mở rộng trái contract EvalPlus (`'\x00'`, trộn kiểu).
- **Không witness nào của CrossHair làm lộ bug** (PUT = canonical trên cả 9 witness hợp lệ), trong khi 6/9 witness của Hypothesis lộ bug. Kiểm đối chứng: CrossHair tìm lại được 16/19 fact mà fuzz đã chạm.
- Kết luận: CrossHair không tốt hơn Hypothesis trên các gap bí và không thêm bug nào; không đưa vào pipeline. Phần lớn gap bí là vùng khó tới bằng cả symbolic lẫn ngẫu nhiên, và tới được cũng hiếm khi là chỗ có bug.

### 11.34 advdoc-hybrid kết quả cuối (đủ 798/798 lượt, có b1/judge; `out/gen2_qwen7b_advhyb_v4_r2`, `out/oracle_advhyb_r2/report.txt`)
Trùng với số tạm ở §11.23: ref advdoc-hybrid **56.0**, advdoc-plainhybrid 51.3 (full 54.0 / 50.3); b1one 50.7 / 46.0. Theo task (ref, đủ 113 task): vs advdoc-plainhybrid 13/6 (p = .17), vs advdoc 21/0, vs concept-hybrid 9/20 (p = .061), vs toolinput 13/21. Kết luận của §11.23–11.24 giữ nguyên.

### 11.35 Hạng 5: concept về hành vi theo spec (BEHAV, v10_spechint, offline; `out/pipelines/v10_spechint/humaneval/offline_behav/report.md`)
Qwen chỉ đọc spec, liệt kê yêu cầu hành vi (trích nguyên văn) kèm điều kiện D "input mà yêu cầu này có ý nghĩa"; hint BEHAV chỉ sinh khi không base input nào thỏa D mà có fuzz input hợp lệ thỏa. Sau 2 lần sửa lỗi ở bước lọc (PREREG_PENDING amendment 1, 1b), lần 3:
- 157 yêu cầu sống sót, nhưng **146/157 đã được base test thỏa D**, nên chỉ ra 7 hint BEHAV ở 5 task.
- good@3: v7 54/112 → v10 55/112; task chẵn 29 → 30 (task 34, "output chỉ gồm phần tử không trùng", PF .86), **task lẻ 25 → 25**. Theo luật đã đăng ký (chỉ chạy LLM nếu BEHAV thêm hint tốt trên task lẻ): **không chạy LLM**.
- Nguyên nhân: yêu cầu Qwen 7B đào ra ở mức thô ("output đã sắp xếp", "output là string", "đếm a, e, i, o, u"), nên điều kiện D cũng thô và base test nào cũng thỏa. Bug nằm ở mức mịn hơn (ví dụ "đã sắp xếp" chỉ lộ bug với input chưa sắp xếp có phần tử trùng hoặc số âm), là thứ yêu cầu mức spec không mô tả.
- Kết luận: miền concept "hành vi theo spec" ở dạng này không bù được tầng 1 (khoảng 38 task bug ngữ nghĩa). Hướng còn lại cho tầng 1 là giả thuyết lỗi mịn hơn (mutref của hạng 2 trên chỗ đã cover).

### 11.36 v9_callfb: round 2 = Qwen viết call cụ thể + feedback 3 mức (dev, ref; `out/pipelines/v9_callfb/humaneval/oracle/report.txt`)
- Bug/run: toolinput 64.0, **concept-hybrid 51.3** (v8-strict 61.0), concept 48.0, plain 45.0, **plain-hybrid 45.0** (v8-strict 55.7), placebo-hybrid 44.7.
- Theo task: v9 vs v8-strict concept-hybrid **3/19 (p = .001)**, plain-hybrid 0/21. concept-hybrid vs plain-hybrid 26/19 (p = .37), vs toolinput 18/33 (p = .049), vs placebo-hybrid 26/18. Round 2 chỉ thêm 6/0 task so với concept một round; plain-hybrid không thêm task nào so với plain (0/0).
- Vì sao kém: concept-hybrid đề xuất 5.506 call, 5.441 hợp lệ nhưng chỉ **132 chạm hint (2.4%)**, giữ được 0.19 input/sample (Hypothesis ở v7/v8: 0.9). Theo kind: hint SPEC (input rất lớn, non-ASCII) 21/2.295 — Qwen không viết được literal 1.000 phần tử, trong khi strategy Hypothesis sinh dễ; MUTANT 616 call tới site và làm khác cục bộ nhưng chỉ 12 làm output khác (khó truyền ra output); BOUND 728 tới site nhưng chỉ 28 chạm đúng biên. plain-hybrid giữ 2.0 input/sample nhưng không lộ thêm bug nào: input Qwen tự nghĩ nằm sát input round 1, kém đa dạng hơn draw ngẫu nhiên của Hypothesis.
- Kết luận: với Qwen 7B, để LLM viết **strategy** rồi để thư viện sinh input (Hypothesis) tốt hơn hẳn để LLM viết **input cụ thể** có feedback. Feedback 3 mức không bù được. Giữ round 2 kiểu Hypothesis (v8-strict) làm bản chính; v9 không dùng.

### 11.37 Witness-only: phần đóng góp của fuzzing khi không có LLM (dev v7, CPU; `analysis/witness_only.py`, `analysis/witness_only.txt`)
- witness-only = các input witness của hint đã chọn (chính là input toolinput đưa cho LLM), expected value lấy từ oracle. Không gọi LLM. Trung bình 1.4 call/task.
- Bug/run (ref): **witness-only 43.0** (1.4 call/sample, false alarm 0.09), toolinput 64.7 (8.7 call), concept-hybrid 66.7 (14.2 call, v7 chưa strict), plain-hybrid 57.3 (14.3 call). Kết quả với full gần như giống.
- Tách detection của toolinput: chỉ trên các call trùng witness được 39.0, chỉ trên các call LLM tự thêm được 39.3. Tức là LLM bỏ hoặc viết sai một phần witness (39.0 < 43.0), nhưng các test nó tự thêm cũng bắt được khoảng chừng ấy bug.
- Theo task: toolinput hơn witness-only 31/3; concept-hybrid hơn witness-only 38/11; plain-hybrid hơn witness-only 39/24 (p = .08); concept-hybrid vs toolinput 23/20 (n.s.).
- Ý nghĩa:
  - Khoảng 2/3 bug mà toolinput bắt được đã có sẵn ở witness của fuzz, chỉ cần một oracle. Đây là phần của tool, không phải của LLM.
  - LLM thêm được khoảng +22 bug/run so với witness-only. Vì vậy mọi so sánh concept phải kèm cả witness-only và toolinput.
  - Kế hoạch: báo witness-only làm baseline bắt buộc trong giao thức cuối. Với B3 (ablation), phải đo "concept giúp LLM" theo phần vượt witness-only, không theo tổng.

### 11.38 Cùng số test bằng random subset thay prefix (v8-strict construction, dev; `analysis/matched_subsets.py`, `analysis/matched_subsets.txt`)
- Arm nào nhiều call hơn thì cắt xuống bằng arm kia bằng random subset (seed 20261013, 100 lần, lấy trung bình), thay cho lấy prefix (prefix thiên về thứ tự LLM viết). Đây là sửa 4 của giao thức, phần phân tích phụ. Theo task, so bằng tổng phân số qua 3 sample, nên số task "khác" nhiều hơn so với prefix.
- Bug/run (ref), random so với prefix:
  - concept-hybrid vs plain-hybrid: 59.3/51.5, 43/26 (p = .053); prefix 58.3/48.0, 34/17 (p = .024).
  - concept-hybrid vs placebo-hybrid: 58.5/43.7, 42/23 (p = .025); prefix 50.7/42.7, 28/16.
  - **concept-hybrid vs toolinput: 54.2/62.5, 26/40 (p = .11)**; prefix 46.0/62.0, 16/36 (p = .008).
  - plain-hybrid vs toolinput: 48.1/63.6, 23/50 (p = .002).
  - concept vs plain (round 1): 46.5/42.7, 30/26 (n.s.).
  - Với full: hướng giống ref; concept-hybrid hơn plain-hybrid 45/24 (p = .015), hơn placebo 43/21 (p = .008).
- Ý nghĩa: prefix làm concept-hybrid **trông kém toolinput hơn thực tế**, vì input round 2 (phần có hint) nằm cuối danh sách. Với random subset, khoảng cách tới toolinput giảm từ 16 xuống 8 bug/run và không còn có ý nghĩa; toolinput vẫn nhỉnh hơn. Lợi thế của concept-hybrid so với không hint và so với placebo vẫn còn, nhưng với ref thì sát ngưỡng (.053). Từ giờ phân tích cùng số test dùng random subset.

### 11.39 Hạng 2 chạy LLM: chọn hint theo giả thuyết lỗi (v7_mutref; phân tích đã đăng ký trên 54 task lẻ của dev; `analysis/mutref_compare.py`, `analysis/mutref_compare.txt`)
- Bản strict (round 2 chỉ có input Hypothesis đã chọn), ref, bug/run: concept-hybrid **30.0** (10.0 call), toolinput 28.3, plain-hybrid 25.3, concept 24.7, placebo-hybrid 23.3, plain 21.0.
- **So sánh chính (đã đăng ký)**:
  - concept-hybrid vs plain-hybrid: **17/9 (p = .17)**; cùng số test (random subset) 29.7 vs 24.1, 23/11 (p = .058).
  - concept-hybrid vs toolinput: 11/8 (p = .65); cùng số test 26.7 vs 28.1, 14/18.
  - Phụ: concept-hybrid vs placebo-hybrid 18/5 (p = .011); cùng số test 21/9 (p = .043).
  - Với full: hướng giống ref (vs plain-hybrid 17/11, vs toolinput 11/9, vs placebo 18/6).
- So với luật chọn hint cũ trên cùng 54 task: concept-hybrid strict 30.0 vs v8-strict 29.7, 13/10 (p = .68); bản raw 32.0 vs 30.7, 13/8. toolinput 28.3 vs 29.0 (8/8).
- Lưu ý:
  - Bản strict được chấm bằng oracle của run raw; 961/33.748 lần tra (2.8%) không có record oracle (input Hypothesis Qwen không viết thành assertion) và bị tính là không phát hiện, nên các arm hybrid strict có thể bị tính thấp đi một chút.
  - Dev có 112 task (v7: 113).
- Kết luận:
  - Luật mới tăng good@3 offline (25 → 35) nhưng **không tăng rõ số bug** khi chạy LLM.
  - Hint vẫn hơn placebo rõ. Nhưng so với không hint và với toolinput thì vẫn chưa có ý nghĩa thống kê.
  - Đúng như dự đoán ở CONCEPT_WEAKNESS: điểm nghẽn là Qwen làm theo hint và round 2, không phải chọn hint.
  - Giữ luật v7 làm cấu hình chính theo giao thức (luật mutref không thắng trên task lẻ).

### 11.40 TrickCatcher-full adapter sửa serialisation (baselines/tc_full_v2, CPU rerun trên generation đã cache)
- Bỏ JSON round-trip, input chỉ đi qua repr/ast.literal_eval. Task 127 từ 0 lên 400 input. Task 157 đổi 300 → 307 (một generator bị timeout). Các task khác không đổi.
- 4 task vẫn rỗng (50, 66, 119, 161). Nguyên nhân là code generator do Qwen viết bị lỗi (dùng sai API cyaron, NameError, sai số tham số). Đây là hành vi đúng của TrickCatcher, không phải lỗi adapter.
- Paper metrics trên 133 task: detecting samples 151 → 154, any-of-K 53 → 54, FA rate 9.3% → 10.5%.
- Chưa chấm lại ref/full trên dev. Việc này làm cùng với v11_fair, theo giao thức cuối.

### 11.41 Dev sanity run của giao thức cuối: v11_fair (dev 113 task, K = 3, oracle ref; `analysis/final_protocol_v11_dev.md`)
- Chạy thật trên GPU, bật cả 4 cờ: strict sinh thật, placebo cùng số request round 2, giới hạn 8 call / 20 assertion, scorer chung.
- **Bug/run (ref)**: toolinput 64.3, **concept-hybrid 61.0**, **placebo-hybrid 57.7**, plain-hybrid 55.7, concept 48.0, plain 45.0, witness-only 43.0, gen-plain 41.3.
  - concept-hybrid và plain-hybrid ra đúng số của bản dựng bằng CPU v8-strict (61.0 / 55.7), nên phần dựng CPU trước đây là đúng.
- **So sánh chính** (theo task):
  - concept-hybrid vs plain-hybrid: 29/20 (p = .25); random subset 43/26 (p = .053).
  - concept-hybrid vs toolinput: 22/23 (p = 1); random subset 26/42 (p = .068).
  - concept-hybrid vs witness-only: 35/14 (p = .004).
- **Phát hiện mới: placebo cùng ngân sách gần bằng concept.**
  - Trước đây placebo-hybrid chỉ có 1.27 call/sample và được 45.7. Khi cho cùng số request round 2 (3.46 call), placebo-hybrid lên 57.7.
  - concept-hybrid vs placebo-hybrid còn **26/22 (p = .67)**; random subset 38/27 (p = .21). D_I: 35/25.
  - Vậy phần lớn lợi thế "hơn placebo" trước đây đến từ **số lần round 2**, không phải từ nội dung hint. Hint thật chỉ hơn hint giả khoảng 3 bug/run, chưa có ý nghĩa thống kê.
- **Precision** (assertion đúng / assertion fail trên PUT): plain .965, gen-plain .942, concept-hybrid .929, placebo-hybrid .930, plain-hybrid .928, toolinput .910, witness-only .902. Tỉ lệ sample báo lỗi chương trình đúng: concept-hybrid 14.2%, toolinput 14.2%, plain-hybrid 10.0%, placebo-hybrid 9.7%, plain 8.6%.
- **Chi phí trên mỗi sample** (sinh test): concept-hybrid 3.27 call / khoảng 2.8k token vào; toolinput 1 call / khoảng 0.6k; witness-only không gọi LLM.
- **Kết luận dev:**
  - Trong cùng ngân sách, fact nằm trong hint (concept) chưa hơn rõ không hint (plain-hybrid), chưa hơn hint giả cùng ngân sách (placebo), và vẫn kém toolinput một chút.
  - Thứ giúp nhiều là **round 2 với Hypothesis** (tool) và **witness** (fuzz).
  - Đây là động lực của B3 (concept có quan hệ) và B4 (giả thuyết vi phạm spec). Baseline paper đang chạy, sẽ báo ở mục sau.

### 11.42 Baseline paper trong giao thức cuối (dev 113 task, K = 3, ref chung; `analysis/final_protocol_v11_dev.md`)
- Bug/run: MuTAP 43.7 (precision .86), TrickCatcher-full (tc_full_v2) 43.0 (.99), SymPrompt 17.7 (.72), ACH 3.3 (1.00, chỉ giữ test giết mutant, 0.23 assertion/sample), CoverUp 3.0 (dừng sớm vì base test đã phủ code, 0.8 call/sample).
- concept-hybrid (61.0) thắng mọi baseline: vs MuTAP 37/15 (p = .003), vs TC-full 35/16 (p = .011), vs SymPrompt 61/5, vs ACH 73/0, vs CoverUp 73/1.
- Nhưng toolinput 64.3 và witness-only 43.0 cho thấy phần lớn lợi thế đến từ tool (witness + Hypothesis), không từ nội dung hint (§11.41). Amendments 3/4 (client baseline retry, over-context) trong PREREG.

### 11.43 Hai hướng concept mới: v14_obgraph / v15_mrconcept (2026-10-14, CPU only)
- Người dùng yêu cầu thử grounded obligation graph và conditional metamorphic concepts trước, trong folder mới.
  Hai copy riêng từ v13_hyp: [v14_obgraph](pipelines/v14_obgraph/README.md), [v15_mrconcept](pipelines/v15_mrconcept/README.md).
- Registration mới trong PREREG; exploratory cohort = 20 dev task IDs chọn bằng seed 20261014, K=1. Chưa dùng held-out.
- CPU preparation trên 20/20 PUT pass base: 193 code nodes, 395 AST/linefact concept labels, 70 spec clauses,
  424 typed edges (226 observed DATA, 198 enclosing CONTROL). 19/20 task có edge tới RETURN. Cả hai copy cho cùng counts.
  Đây là structural availability; chưa phải số obligation/MR có ích hoặc số bug phát hiện.
- 28 tests pass (14/copy), gồm path/purity/schema adversaries, runtime trigger/path checks, giữ MR fail trên input
  chưa base-tested của buggy PUT, paired-input budget/resume, và tách canonical confirmation khỏi false alarms.
- Shared-ref adapter CPU smoke trên frozen witnesses HumanEval/27: 2 calls, 10 cached spec-only ref responses,
  2 calls được execute/score trong mỗi copy. Đây là compatibility check; không đánh giá các arm mới.
- 222 direct source/config/doc files của v7/v11/v12/v13 giữ nguyên hash sau checks. Source vendor không sửa.
- **Chưa có model-effectiveness result:** người dùng báo hết quota, không có Qwen endpoint. Chưa gọi model để
  propose obligations/MRs hoặc generate strategies, không dùng paid fallback. Runbook của mỗi copy đã sẵn;
  trần dự kiến 440 + 380 = 820 logical model requests cho hai smoke runs, reuse refs, báo actual tokens khi chạy.
- Chi tiết/validation: `pipelines/<variant>/CPU_VALIDATION.{md,json}`; local version tree:
  [EXPERIMENTS-2026-10-14.md](pipelines/EXPERIMENTS-2026-10-14.md).

### 11.44 v14_obgraph / v15_mrconcept GPU smoke: proposal-format failure (2026-10-14)
- Chạy thật trên Qwen2.5-Coder-7B-Instruct, frozen 20 dev tasks/K=1, shared saved v11 spec-only refs.
  Full cohorts: v14 180 rows, v15 160 rows; ref execution/scoring hoàn tất. Không chạy held-out.
- **Cả hai có 0 accepted/shown semantic cards trên 20 tasks**, không có new card witnesses. Các concept arms
  dùng generic fallback đã đăng ký, nên đây **chưa là phép thử có treatment** cho graph hoặc conditional MR.
- V14 rejection census: invalid/missing Python T 47; invalid typed path 48; unknown clause ID 13; Python syntax 6;
  parse failure 1. Model hay đưa concrete input lists vào T, node IDs vào edge path, và JavaScript/expression vào O.
- V15: 89 rows không có function source đúng schema, 18 dùng calls ngoài whitelist, 13 syntax/string errors.
- Descriptive D_IO tasks/20: v14 graph/cards/noconcept **6/6/6**, plain 7, toolinput strategy-adapter 7, original
  witness-only 6, new-witness-only 0. V15 MR 6, blind 7, flatfacts 6, toolinput adapter 7, original witness-only 6.
  Primary sign contrasts: v14 0/0; v15 1/2; nominal p=1 ở cả hai. Không dùng chúng để kết luận idea không có ích.
- Physical successful requests: 311 mỗi run, total 622; cache hits v14 129 / v15 69; transport failures 0.
  New reference calls 0. Actual uncached tokens: v14 231.027 input + 39.734 output; v15 178.235 + 29.321.
- Finding: **proposal format/code-source compliance là gate đang hỏng**. Cần một copy mới với Python/schema
  guidance rõ và proposal-stage gate trước khi đánh giá utility; không sửa source hay diễn giải lại run frozen này.
- Tracked report/data/script: [v14_v15_gpu_smoke.md](analysis/v14_v15_gpu_smoke.md),
  [v14_v15_gpu_smoke.json](analysis/v14_v15_gpu_smoke.json), [summary script](analysis/v14_v15_gpu_smoke.py).
- User corrected order: resume B3 → B4 trước, rồi mới quay lại v14/v15. B3 dùng exact frozen relation replay
  adapter (PREREG clarification) để giữ manifest; completed baselines không rerun, held-out chưa bắt đầu.

### 11.45 B3 v12_rel hoàn tất: relation chưa hơn flat concept rõ ràng (2026-10-14)
- Frozen seven-arm/K=3: 2.793 evaluated rows, 133/133 task execution records; dev 113 và pilot 20 tách riêng.
  Task 44 chạy lại thành công với nguyên worker/job/timers; nguyên nhân thiếu result lần đầu chưa xác định.
- Dev D_IO tasks/run (mean over K): rel-hybrid **63,33**, flat-hybrid **62,33**, review-hybrid **60,67**,
  rel-nospec **61,33**, plain **56,33**, placebo **57,67**, toolinput **62,33**.
- Primary relation vs flat: raw wins/losses **16/15, p=1**; random equal-count **25/33, p=.358**.
  Relation vs no-spec-links cũng chưa có khác biệt rõ (raw 15/10, p=.424; matched 26/25, p=1).
- Relation vs plain: raw **32/22, p=.220**; matched **49/25, nominal p=.0071**. Matched vs placebo
  41/27, p=.114; vs toolinput 27/36, p=.314. Các p-value chưa điều chỉnh multiple comparisons.
- Pilot rel 11,0 vs flat 9,67 tasks/run; primary raw 2/0, p=.5; matched 5/4, p=1.
- B3 manifest gốc không export witness-only; B4 có cả original và hypothesis witness controls.
  Hint budget dùng whitespace proxy/punctuation padding, không bảo đảm bằng actual tokenizer tokens.
- Chưa đạt registered relation-vs-flat promotion gate; không chạy held-out. B4 đã bắt đầu generation;
  v14_obgraph_py/v15_mrconcept_py tiếp tục chờ B4 score theo thứ tự người dùng.
- Tracked report + full comparison/provenance: [b3_v12_rel_results.md](analysis/b3_v12_rel_results.md),
  [b3_v12_rel_results.json](analysis/b3_v12_rel_results.json).

### 11.46 v14/v15 Python-format repair hoàn tất (2026-10-14)
- Frozen 20 dev tasks/K=1, cùng saved v11 ref; v14 180 rows, v15 160 rows. Generation/ref scoring đã xong.
  Chạy chồng CPU-heavy B4 với 2 workers; v14 từng bị HTTP 404 rồi resume cache khi người dùng bật GPU lại.
- v14_obgraph_py: **5 accepted/shown cards trên 3/20 tasks**, không có discovery witness cho các cards.
  Graph/card/noconcept D_IO đều **6/20**, plain 7, placebo 6, toolinput adapter 7, original witness-only 6,
  new-witness-only 0. Primary graph vs card raw và equal-count đều wins/losses **0/0, p=1**.
  Chỉ 1 property-evaluation record mỗi graph/card/noconcept arm; 0 confirmed obligation violations.
  Graph treatment rất thưa, chưa cho thấy lợi ích. Remaining rejection chủ yếu path/grounding/purity.
- v15_mrconcept_py: **41 accepted/shown cards trên 16/20 tasks**, 8 cards có discovery witnesses.
  MR/blind D_IO **5/5**, flatfacts 4, placebo 4, toolinput adapter 4, new-toolinput 6, original witness-only 6,
  new-witness-only 0. Primary raw wins/losses **2/2, p=1**; matched **2/1, p=1** (means 4,30/3,64).
- MR property-oracle checks khác với endpoint shared-ref D_IO: không có confirmed property reports trên
  selected inputs; MR-guided arm có 3 candidate reports, cả 3 false alarms với canonical. Accepted schema/base
  consistency chưa bảo đảm relation đúng. Các arm cũng có abstentions, ghi đầy đủ trong report.
- Actual uncached successful requests: v14 35 (90.071 input / 16.662 output tokens), v15 117 (90.012 / 12.620).
  Cache hits 405/263; failed request-ledger entries 6/0. Không có paid fallback hoặc held-out run.
- Đây là exploratory smoke, không đủ cơ sở promote hay kết luận toàn bộ hướng graph/MR không có ích.
  Phân tích extraction limits nằm ở METHOD_V14_V15.md; source/config/budgets của run không được sửa sau kết quả.
- Report, provenance và script: [v14_v15_format_repair.md](analysis/v14_v15_format_repair.md),
  [JSON](analysis/v14_v15_format_repair.json), [script](analysis/v14_v15_format_repair.py).

### 11.47 B4 v13_hyp hoàn tất: hypothesis pipeline kém flat/toolinput trên dev (2026-10-14)
- Đủ 2.793 generation/evaluation rows, 133/133 ref execution records, dev 113 + pilot 20, K=3.
  Score trước đó thiếu task 44; exact saved-worker retry thành công sau 446,43 s, source/job/timers không đổi.
  Native score hoàn tất 23:56:47 local; không có model call mới trong scoring retry. Nguyên nhân lần thiếu đầu chưa xác định.
- Dev D_IO tasks/run: **hyp-hybrid 46,33**, flat-hybrid **62,67**, rel-hybrid **63,33**, toolinput **63,00**,
  plain-hybrid **54,67**, witness-only **41,67**, hyp-witness-only **15,00**.
- Primary hyp vs flat: raw wins/losses **14/43, nominal p=.000154**; equal-input subsets **21/51, p=.000535**.
  Hyp vs toolinput: raw **14/35, p=.003802**; matched **20/41, p=.009853**. Không đạt promotion gate.
- Hyp vs plain chưa rõ: raw 19/31, p=.119; matched 36/32, p=.716. Các p-values chưa điều chỉnh multiplicity.
- Mechanism dev: 133 shown hypotheses trên 58/113 tasks; 66 có witnesses, 15 có surviving-mutant differences.
  Proposal toàn 133 tasks: 133 logical calls, 687 parsed candidates, 197 kept; top-3 shown total 160 trên 70 tasks.
- Generation budget thực dùng khác nhau: hyp-hybrid 1,83 calls/sample, flat 3,27; shared hypothesis proposal
  tính riêng một lần/task. Equal-input matching không match LLM requests; kết quả là hiệu quả full methods,
  chưa isolate riêng hypothesis wording. B4 manifest có witness controls nhưng không export placebo.
- Pilot: hyp 9,0, flat 10,33, toolinput/plain 10,67 tasks/run; primary differences chưa rõ ở cohort nhỏ này.
- Kết quả B3/B4 và repaired v14/v15 đã hoàn tất. Không promote hoặc chạy held-out từ các kết quả này.
  Hướng FSM/spec/model mutation mới chỉ là plan/research, chưa có experiment result.
- Tracked report, native attribution, costs và provenance:
  [b4_v13_hyp_results.md](analysis/b4_v13_hyp_results.md), [JSON](analysis/b4_v13_hyp_results.json),
  [script](analysis/b4_v13_hyp_results.py).


### 11.48 v16 behavioral abstraction — CPU foundation, 2026-10-15

User authorized starting immediately; benchmark-wait timer stopped. New v11_fair-based source
v16_behavior, then separate v16_behavior_compact storage repair after task 94 exceeded worker IPC cap.
Earlier sources/vendor unchanged; no paper reproduction or paid calls.

- Representation gate **17/20**, required >=16/20: passed. 136 replay attempts, 135 completed/matching,
  1 unresolved timeout, 0 observed mismatches. Opaque: 63 recursion, 76 recursion/float division, 144 eval.
- **26 CPU tests pass** (8 behavior/DSL tests, 18 inherited fairness tests). Real frozen task-152 strategy
  adapter: 10 draws, all 10 accepted by the common domain filter; no model call.
- 409 observed finite projected states, 442 witnessed transitions. This is an under-approximation,
  not symbolic execution, a complete FSM or a proof that merged paths are feasible.
- Task 152 return observes result version 7 after six appends. Change-based versions preserve observed
  collection changes/aliases; repeated no-op writes need not create a new version.
- 119 first-order implementation mutants; 104 distinguishable on bounded common inputs, 55 have
  at least one non-base discriminator (counts include opaque tasks). These are mutant disagreements,
  **not** detected PUT bugs or validated specification mutations. Fixed source-prefix cap omits later
  operations for some tasks; 78/152 have no compatible mutation in the initial grammar.
- Explicit operation requirements, source/control/state IDs, typed JSON predicates and two-stage
  spec-only extraction/binding runner implemented. Generation uses a common domain-only filter;
  activation is measured after selection. Proposal/generation/scoring code has not run with the model.
- Qwen endpoint check returned HTTP 404; new endpoint requested. **0 model calls**, concept gate and
  D_IO unmeasured. No concept-advantage/promotion claim. MOVE CHECK, full spec-model mutation,
  complete symbolic transitions/refinement and MCTS remain later extensions.
- [CPU report](pipelines/v16_behavior_compact/CPU_VALIDATION.md),
  [machine-readable counts/hashes](pipelines/v16_behavior_compact/CPU_VALIDATION.json),
  [runbook](pipelines/v16_behavior_compact/README.md).

- Final pre-model hardening copy: [v16_behavior_ready](pipelines/v16_behavior_ready/README.md),
  rejects malformed JSON containers, quotes, IDs and reasoning as counted proposal failures.
  Fresh CPU gate again **17/20** with the same replay/mutation counts, **29 tests pass**, and
  task-152 real adapter smoke 10/10. No model outputs influenced these changes; protocol/source
  hashes verified. Use this copy for continuation. [Ready CPU report](pipelines/v16_behavior_ready/CPU_VALIDATION.md).


### 11.49 v16_behavior_ready — GPU proposal gate failed, 2026-10-15

GPU metadata ready 10:13:41 +0700. First attempt stopped during binding prompt construction:
tracer lazily imported in a thread tried to register SIGALRM. Three spec responses cached.
External main-thread preload adapter resumed the exact source/config/task protocol and requests;
no pipeline edits, model repair, validators/seeds/budget changes or new tasks.

- Full **20/20 task proposal cohort**, 2 calls/task. **Concept gate 0/20**, required >=10/20: failed.
  Six candidate obligations passed quotation/schema (5 task 51, 1 task 152); **0 accepted/shown cards**.
  Representation CPU gate remains 17/20; that did not establish usable semantic concepts.
- **40 logical / 40 successful new completion requests**, 40 unique cache keys, 3 cache hits on resume,
  zero failed completion transport attempts. Actual **35,582 input / 23,251 output tokens**.
  Request-duration sum 881.41 s is concurrent-request time, not wall time. No paid fallback.
- Rejections: 9 spec JSON parse failures; 13 quotation mismatches; 18 relations missing structural
  input/output dependency; 10 DSL operator/arity failures; 1 DSL depth/type failure; 2 references to
  output in input predicates; 47 missing R0 references, 1 missing M1 reference. These count rejected
  items/stages, not independent tasks. Missing IDs often propagate earlier spec rejection.
- DSL expressiveness is a concrete bottleneck: raw outputs request unsupported mod/filter/map,
  string operations and whole-function operators. Task 27 invents flip_case; task 51 binding uses
  a mutation name string as discriminator. Task 152 has a schema-valid obligation but no compatible
  mutation under the fixed grammar. Parse/grounding/expressiveness failures prevent this treatment
  from reaching generation. They do not establish semantic-concept detection gain or failure.
- **Generation rows 0; scorer not run; D_IO unmeasured (not zero).** Gate stops as preregistered.
  Do not relax gate or rerun with changed content in this frozen version. Future work needs a
  separately registered copy, ideally typed semantic templates and explicit unsupported cases.
- [Report](analysis/v16_behavior_gate_results.md), [JSON](analysis/v16_behavior_gate_results.json),
  [analysis script](analysis/v16_behavior_gate_report.py),
  [frozen resume adapter](analysis/resume_v16_frozen.py). All frozen hashes verified.


### 11.50 v17_templates — compiled spec-model alternatives, gate 2/20 (2026-10-15)

New copy of v16_behavior_ready. Nine reusable typed semantic templates replace generated expression
trees. Tool-owned spec spans, full public base verification (all 20 below cap 200), first-order
spec-model alternatives and computed discrimination. No dependency on implementation mutant IDs.
Main-thread tracer preload built into this runner. No source/validator edits after outputs.

- **44 CPU tests pass**, representation **17/20**. Manual compiler-only task-152 positive control
  passed four base cases; explicitly excluded from proposal/gate results.
- Full 20-task model proposal cohort: 12 schema proposals, 4 base-consistent compiled templates,
  **2 checked/shown cards on 2/20 tasks (27,78)**. Gate requires 10/20: failed.
- Rejections: 18 spec-unit-reference failures (including omitted evidence), 13 unknown proposal IDs
  cascading from earlier rejection, 6 base/type unknowns, 2 base contradictions, 1 candidate with no
  replayed source-anchored discriminator. JSON parse/operator-tree failures no longer dominate.
- **40 logical/new requests**, zero completion transport failures/cache hits; **38,891 input / 4,116
  output tokens**. No generation or canonical scoring. D_IO unmeasured, not zero.
- Qualitative audit: task 27's MAP swapcase candidate has a Unicode discrepancy/anchor, but rationale
  copies the three prompt placeholders. Task 78's membership count matches source behavior on its
  witness; its prose incorrectly calls that a semantic misunderstanding. These are technically accepted
  by the frozen checks, not evidence of successful explicit fault reasoning. Keep primary gate 2/20;
  do not silently redefine or relax it. Candidate discrepancies are not canonical-confirmed bugs.
- Final state: concept_gate_failed_generation_stopped. Future design must change the LLM role/interface
  and tool-produced evidence, not simply enlarge token limits or accept generic rationale.
- [Report](analysis/v17_template_results.md), [JSON](analysis/v17_template_results.json),
  [analysis script](analysis/v17_template_results.py), [runbook](pipelines/v17_templates/README.md).

### 11.51 Separate synthetic interface capability probe — selection 6/6 (2026-10-15)

Conditional probe preregistered before its calls and run only after v17 gate failure. Six hand-authored
requirements: character filtering, bidirectional order, indexed sum, pairwise absolute difference,
filtered multiplicity, empty-safe minimum. Declared configurations/examples and randomized candidate
positions verified on CPU before responses. No benchmark code/gold or modification of v17.

- Parameter synthesis: 5/6 compile; **4/6 match the declared finite examples**; 2/6 evidence/schema-valid;
  **1/6 both example-correct and evidence/schema-valid**. Separate syntax from semantic/interface failures.
- Selection among 2–4 supplied compiled candidates: valid choice and correct **6/6**.
  Uniform-choice expected count 1.83/6; always-C0 baseline 3/6. Small convenience synthetic probe,
  not a generalization/significance claim. Different interface prompts intentionally differ, so output
  format alone is not isolated as a cause. Example agreement is not a universal semantic proof.
- **12 new requests**, **9,364 input / 370 output tokens**, no completion transport failure/cache hit.
  Separate budget from v17; combined this round 52 new requests, 48,255 input / 4,486 output tokens.
- This supports investigating tool-built/base-filtered candidate models and LLM selection/ranking,
  instead of LLM constructing parameters/IDs/rationale from scratch. No v18 benchmark run or D_IO claim.
  Frozen generation remains stopped. Probe source/data design:
  [probe.py](analysis/template_capability_probe/probe.py); results in the shared v17 report above.


### 11.52 v18_modelselect — tool candidates work; LLM selection not better than rule (2026-10-15)

User authorizes model-ID selection and explicitly excludes MCTS. Selection-only pilot, new copy
v17_templates -> v18_modelselect. No parameter/evidence/rationale generation by LLM; no task-ID
or function-name candidate dispatch. Tool uses typed template enumeration, disclosed lexical prior
and public-base filtering. Uniform and rule-first controls use the exact same shuffled menus.
All choices, candidates, pools and pre-gold execution records freeze before canonical/contract audit.
No strategy generation, held-out evaluation or end-to-end D_IO comparison in this pilot.

- **52 CPU tests pass**, representation17/20. Nonempty base-consistent retained pool/menu on
  **13/20 tasks**, including7 menus with distinct sampled behaviors within an output scope.
- Canonical audit: **703 valid frozen input calls**, zero invalid/unresolved. On this finite pool,
  **12/20** tasks have a sampled-consistent model in the retained pool and displayed menu.
  No consistent candidate lost by display trimming. This is sampled requirement consistency,
  not universal model correctness. One selected requirement targets a tuple component only.
- **LLM11**, **rule-first12**, **uniform expected9.17** sampled-consistent task selections.
  Conditional on menu containing a consistent model: LLM11/12. Paired LLM vs rule:0 wins/1 loss.
  On7 ambiguous menus: LLM5, rule6, uniform expected3.17. No incremental LLM selection gain shown.
- Failure separation:7 tasks have no candidates; task91 has candidates but none fully matches the
  reference on the frozen pool; task56 has the consistent empty=True BALANCE model available but
  LLM chooses empty=False. Task78's mixed str/empty-list base representation is conservatively
  unsupported by type inference, despite the generic registry being capable of that behavior.
- Selected candidate properties produce **119 input-level discrepancy reports across12 tasks**;
  canonical confirms all119, zero observed candidate-property false alarms. These are not119 bugs,
  not D_IO, and do not prove global property correctness: task91's candidate can yield confirmed
  reports on some inputs while differing from the reference elsewhere. Keep that distinction.
- Tool evidence now contains actual source/state observations, relation classes, predicted value,
  PUT effect and non-unique fault matches, rather than prose accepted by minimum string length.
  Task152 ([0],[1]): model predicts[1], PUT[-1]; signed-subtraction alternative matches59/59 frozen
  native calls. Task149 ['aa','aa']: model preserves2 occurrences, PUT1; duplicate-removal alternative
  matches16/16 frozen calls, even-index alternative9/16. This is bounded hypothesis discrimination,
  not unique causal proof. Task136 exception matches alone do not localize an aggregate/guard.
- **20 logical/new requests**, **6,410 input /165 output tokens**, zero transport failures/cache hits;
  all20 choice responses valid (13 model IDs,7 NONE). Two independent synthetic audit-kernel checks
  confirm control scoring and confirmed-vs-false requirement classification. Frozen hashes verified.
- [Report](analysis/v18_modelselect_results.md), [JSON](analysis/v18_modelselect_results.json),
  [analysis script](analysis/v18_modelselect_results.py), [runbook](pipelines/v18_modelselect/README.md).
  Pilot complete. Future generation comparison needs a fresh preregistration; do not regenerate
  this run's candidates/choices from canonical feedback or call these metrics D_IO.


## 11.53 v19_rulegen — rule-first generation comparison (2026-10-15)

Complete20 design dev tasks/K=1,120 samples. Frozen protocol/generation and pre-gold parent provenance/guidance verified; all20 native scores and raw/equal-input comparisons independently recomputed. Saved spec-only references unchanged. No missing work to resume.

| Arm | D_IO detected tasks /20 | D_IO input events | Selected inputs |
|---|---:|---:|---:|
| plain |3|4|28|
| behavior |3|4|18|
| behavior+concept |3|6|24|
| placebo |3|4|22|
| toolinput |4|8|30|
| witness-only |13|40|62|

- Representation17/20, frozen rule-first concept/fault coverage13/20. No canonical-driven replacement; full20-task denominator.
- Concept and behavior detect the same tasks27/85/149. Primary comparison0 wins/0 losses, raw and equal-input, nominal sign p=1. More failing inputs do not increase detected tasks.
- Equal-input concept vs behavior3.00/3.00; plain2.41/2.65; placebo2.61/3.00; toolinput3.00/3.00; witness-only2.76/6.72. These are mean task counts over100 random subsets, not integer new detections. Witness comparison0 wins/5 losses, nominal p=.0625; zero-yield tasks are matched to zero and therefore discarded from this diagnostic.
- Main bottleneck:203 SyntaxError and9 ValueError rejections among300 logical strategy responses;11 further worker RuntimeErrors.198 rejected responses contain leading prose plus fenced code.141 rejected first code blocks pass the same static checker if extracted (read-only diagnosis, no repaired generation/scoring). Reliable generation interface is required before interpreting this as an isolated test of concept reasoning.
- Shared-reference false alarms0 in every arm. Separate property/card audit: concept8 confirmed events vs behavior5, plain4, placebo6, toolinput12, witness-only51;0 observed property false alarms, placebo4 abstentions. Card events can repeat an input and are not D_IO.
-300 logical requests,269 physical requests,31 exact-cache hits; physical182,256 input /69,369 output tokens (logical210,367/77,150).0 new oracle requests. Parent discovery/preprocessing costs excluded from incremental totals; witness-only reuses those candidate/old-tool witnesses and does not represent13 new LLM discoveries.
- No concept generation improvement demonstrated; direct witness reuse is strongest in this exploratory run. Do not repair frozen outputs; any interface change needs a separate pipeline/preregistration.
- [Report](analysis/v19_rulegen_results.md), [JSON](analysis/v19_rulegen_results.json), [audit script](analysis/v19_rulegen_results.py).


## 11.54 v19 code-flow scope audit (2026-10-15)

User requested actual implementation validation rather than detection metrics. CPU/source audit confirms v19 is AST pseudocode + typed model/fault prompt augmentation, not connected FSM/semantic behavioral reasoning. All29 concept-bearing slots have empty source bindings; FSM/replay evidence is not used in guidance, no catalog definitions are supplied, activation is logged only after random input selection. Task149's relevant deduplication mutation is omitted by fixed first3 truncation. Two independent CPU counterexamples reveal missing AugAssign old-value reads and an unsupported match/case branch incorrectly marked structurally supported (latter not claimed to occur in the20-task cohort). Gates/tests/hashes do not prove end-to-end semantic validity. Output extraction alone would not repair these methodological gaps. Frozen treatment/results unchanged, no GPU work added.

[Audit](analysis/v19_flow_audit.md), [CPU checks](analysis/v19_flow_audit.py), [evidence](analysis/v19_flow_audit.json). Detection results in §11.53 remain implementation-specific exploratory results; they cannot settle the proposed connected behavioral-reasoning approach.

## 11.55 v20 audited CPU multiplicity mechanism (2026-10-15)

User required plan → independent subagent audit → implementation. Two read-only reviewers audited semantics and experimental validity before code; all blockers/resolutions recorded. Later independent code audits overruled passing fixtures, exposing lexical scope, builtin shadowing, argument provenance/eligible loss, bounded analyzer and validator-adapter bugs. Every frozen correction uses a new copy/preregistration; earlier failed artifacts retained separately.

Final `v20_groundedflow_domainfix`:14 static/helper checks,35/35 known authored fixture expectations pass. Operation/occurrence before/committed events, exact original-argument identity, same eligible-value count loss and transparent return transport link a partial candidate requirement to native effects/output. No MCTS, complete FSM/symbolic execution, automatic spec entailment or unique-cause claim.

Full20 known-dev CPU inventory retained:1/20 supported (task149, known design),12 native-checked attempts,3 complete candidate evidence instances,0 reviewed-grounded real-task instances; confirmed_bug null.19 unsupported tasks remain denominator.0 model requests, no canonical/reference execution/GPU/D_IO. Final inventory PUT bound24; final fixture native executions38, separate from predicate checks and preserved prior copies. Per-task inventory wall time recorded; full engineering CPU time not measured.

Both reviewers accept only this narrow CPU increment; not broad mechanism/GPU readiness. Reviewed real-task obligations, derived collection provenance and guard/loop semantics remain open. [Plan](PLAN_GROUNDED_FLOW_V20.md), [review history](analysis/v20_plan_review.md), [CPU report](analysis/v20_cpu_results.md), [JSON](analysis/v20_cpu_results.json).

## 11.56 v21 Qwen-chain P1 offline interfaces (2026-10-16)

Scheduled user authorization covers offline interfaces/checks only. New best-v7 source copy `v21_qwenchain`; parent hashes/provenance recorded, online/historical experiment entrypoints disabled. Implements isolated S1/S2 views, five-stage schemas/reference/version lineage, bounded literal/feedback interfaces, cumulative attempt ledger/context/dependency caches and pinned raw execution reuse. Qwen owns semantic interpretation/alignment; tools do not use a semantic matcher.

Final **48 offline checks pass**. Initial44-pass invocation preserved; independent audits found Unicode mapping, opaque-output comparison, feedback/S5 completeness and cache-budget counterexamples; fixes and regressions precede final freeze. Both reviewers accept the scoped P1 interface deliverable. Final source/config/prereg hashes verified and saved in P1_FROZEN.json.

**0 model requests/GPU/canonical/ref/D_IO; semantic accuracy unmeasured.** Hand-authored response/native fixtures are interface checks, not Qwen behavior. Generic operation_value observations remain unknown, line hits do not prove expression activation. Real tokenizer/context binding, online transport and independent16-fixture semantic pilot remain later work. [Report](analysis/v21_offline_interfaces.md), [JSON](analysis/v21_offline_interfaces.json), [snapshot](pipelines/v21_qwenchain/P1_FROZEN.json).

## 11.57 Qwen chain controlled16 first live pilot (2026-10-16)

User authorized real endpoint calls. Fresh registered v21_qwenchain_pilot,74 preflight checks and two independent transport/fixture/alias reviews. Live model/context confirmed; raw-tokenizer counts with pinned official chat template match every completion's prompt usage. Frozen source/generation verified.

Actual32 completions (80 scheduled slots),35169 input/11946 output tokens, no failed transport/unknown usage;32 tokenization metadata calls. S1 valid0/16, S2 valid0/16; S3/S4/S5 each blocked16. No generated test inputs, no real20/ref/canonical/D_IO. Human semantic gate unadjudicated.

Failure diagnosis:12 S1 replies are bare items without envelope,4 S1 and all16 S2 replies copy the contract/meta-schema. Current prompt supplies competing envelope/fields/exact_shape structures, and Qwen mirrors those instructions. This is a prompt/interface failure; no conclusion about downstream alignment accuracy. Raw substantive statements are preserved, not silently wrapped/repaired. [Report](analysis/v21_qwenchain_pilot_results.md), [JSON](analysis/v21_qwenchain_pilot_results.json). Any follow-up must use a separate preregistered copy; first run remains final.

## 11.58 Qwen chain single-output-shape adaptation (2026-10-16)

Separate preregistered prompt-only copy v21_qwenchain_singlejson, same16 fixtures/validators/budgets/gates;74 offline checks and two read-only reviews before completions. Source/generation frozen and verified. First pilot remains unchanged and is not pooled.

35/35 completions,33,290 input /6,412 output tokens;35 tokenizer metadata calls,0 errors/unknown usage. S1 valid13/16 (3 quote_mismatch); S2 valid3/16 (13 empty guard rejects); S3 valid3,blocked13, all3 abstain; S4/S5 blocked13 +not-applicable3. Mechanical gate19/62=30.65%, required applicable probes0/7. No generated inputs, experimental native executions or D_IO.

Audit found our prompt/validator inconsistency: prompt allows empty strings but S2 requires nonempty guard even for unconditional behavior; preflight checks missed this choice. Raw f02 dedup and f04 boundary descriptions are plausible, but remain rejected artifacts. Separately f12 shows a semantic alignment miss: S2 recognizes len(xs)>2 early False while the spec permits any length, yet S3 abstains as consistent. f13 overclaims consistency despite undefined suitable. Schema passing therefore does not certify understanding. Whole-spec quote/span supplied by prompt is provenance only, not clause-extraction accuracy.

Stop at failed gate; no third adaptation, automatic real20 or human-gate bypass. Human semantic accuracy remains unadjudicated. [Report](analysis/v21_qwenchain_singlejson_results.md), [raw diagnostic](analysis/v21_qwenchain_singlejson_results.json).

## 11.59 v22 contract/alignment fixes and diagnostic rerun (2026-10-16)

User requested fixing empty-guard implementation and missed S3 mismatch. New v22_qwenchain_audit registered/frozen;89 offline checks. S2 guard/effect conventions fixed, S3 now Qwen-authored per-obligation comparisons with mechanical coverage/reference/internal-consistency checks; unknown upstream cannot prove consistency. S3 cap increased1024→2048, other budgets unchanged; same16 seen fixtures, exploratory multi-component adaptation. Experiment review before freeze; flow review after launch, recorded without retrodating.

39/39 completions,46,603 input/10,909 output tokens;39 tokenizer calls,0 errors. S1 valid16/16; S2 valid5,failed11 (9 local_id,2 items_cap); S3 valid1,failed4,blocked11; S4/S5 valid1,blocked15. Gate24/62=38.71%, applicable probes1/7; failed. Six admissible unique inputs on f06,3 native prediction matches/3 contradictions. S5 unknown,0 final inputs. No D_IO/automatic real20 or semantic accuracy claim.

Guard and quote failures absent, but format shifts remain. f06 identifies subset-vs-equality mismatch and generates extra-container input whose native output is False. f12 never reaches S3 due behavior ID error. [Full diagnostic](analysis/v22_qwenchain_audit_results.md), [review chronology](analysis/v22_qwenchain_audit_review.md).

Separate registered v22_qwenchain_s3replay imports the exact accepted old Qwen S1/S2 parents for f11/f12/f13 (source/task/artifact/parent hashes verified), then runs only3 new S3 calls:5,352 input/1,029 output tokens;3 tokenizer calls,0 errors. All3 rejected (empty_ok/status), no downstream work. Raw f12 now notices extra length guard, but condition precision remains incomplete; f13 still overclaims mismatch from undefined suitable. This isolates a qualitative change in model claims, not accepted pipeline success or unseen validation. [Replay report](analysis/v22_qwenchain_s3replay_results.md).


## 11.60 v23_concepthyp — audited mechanism diagnostic and small-model probe (2026-10-17)

User authorized best-version copy, code-first work and clean-context audit; later authorized Qwen diagnostic16 on a supplied endpoint. New v23_concepthyp copies best v7 with parent hashes; v7 unchanged. jsonschema/httpx/Jinja2/existing isolated workers used.26 CPU checks and16-case source-bound preflight pass; source frozen after independent audit fixes. Three-arm design separates concept-guided/direct hypotheses and explicit concept presentation with the exact same hypothesis. [CPU/audit report](analysis/v23_cpu_audit.md).

Separate preregistered supplied-concept probe: two clean-context gpt-6-luna/low agents, same5 seen fixtures (3buggy,1correct masked effect,1ambiguous). Both5/5 mechanically valid, both catch3/3 buggy cases with correct assertions,0 observed false alarms. Independent review confirms all19 submitted input expectations/PUT predictions and the same4 bug-revealing inputs across arms. **No incremental concept benefit observed.** Concept arm only adds passing contrasts. Authored concepts, seen/easy subset, per-arm batch context and no token parity; does not establish Qwen extraction reliability or benchmark gain. [Probe report](analysis/v23_luna_probe/report.json), [protocol](analysis/v23_luna_probe/protocol.json).

Qwen diagnostic16 launched detached with source/fixture freeze, max160 logical calls, no content repair or automatic benchmark expansion. Online result pending; do not count CPU fixtures or Luna outputs as Qwen. Status under out/pipelines/v23_concepthyp/humaneval/concept_hypothesis_diagnostic/.


## 11.61 v23 Qwen diagnostic16 complete — schema passes, semantic mechanism fails (2026-10-17)

Normal exit0, exact source/source-bound CPU/generation/parent-v7 hashes verified. All160 logical requests received160 Qwen completions, all160 stage artifacts mechanically valid;0 transport retries/unknown usage.175,022 input/28,221 output tokens,153 tokenizer metadata calls/0 errors;53m31s. No new Qwen/oracle calls in analysis, no source/prompt/schema/output repair.

Full16 seen authored cases retained:7buggy,8correct,1ambiguous. concept_chain/direct_chain/hyp_only: fixture-oracle input-discrepancy cases4/5/5, correctly specified failing-assertion cases**2/2/2**, unique correct assertions2/4/2. Correct assertion sets C/H=f12,f16; D=f06,f16. False assertions that fail on PUT occur on2/5/4 cases (including buggy PUTs); false alarms on actually correct PUTs2/8,2/8,3/8. Admitted candidate slots52/69/66 of96 per arm; invalid literal/arity/prediction slots41/25/27; domain-filtered3/2/3. All48 input and48 revision artifacts provide candidates; no valid abstention, even on ambiguous f13.

Independent clean-context semantic review confirms: both miss returned dedup f02 and equality-vs-inclusion f06; both invent faults on correct unused/unreachable operations f14/f15 and fail ambiguity f13. f04/f10 identify a real relation mismatch but supply passing/nondiscriminating triggers. f12 has the right bug label for the wrong empty/out-of-domain mechanism. Correct fault mechanism plus admissible sufficient trigger appears only C=f08, D=f08/f16 (qualitative model-assisted review, not human gold). Generated genuine assertions can occur despite wrong hypothesis and PUT prediction, so detection is not proof of the proposed reasoning mechanism.

Expected-output drift toward PUT is a major loss: f02 expects deduplicated lists, f04 strict counts, f08 direct/H exceptions instead of spec None. Incorrect expected output equals PUT on10/8/14 admitted slots for C/D/H, suppressing true assertions. No procedural spec/code leakage found in the32 preparation requests; no hidden evaluator feedback was supplied. S2 fabricated limitations also feed false hypotheses. **No demonstrated incremental concept benefit; no promotion/benchmark expansion.** Separate Luna probe remains null and is not pooled.

[All16 cases, costs, failures and interpretation](analysis/v23_qwen_diagnostic_results.md), [verified analysis JSON](analysis/v23_qwen_diagnostic_results.json), [recompute script](analysis/v23_qwen_diagnostic_results.py). Callback handled; no work to resume or duplicate.


## 11.62 v24 executable obligations — audited code/CPU increment (2026-10-17)

User approved executable-obligation repair: new best-v7 copy v24_obligations, original v7/v23 untouched. Clean-context plan and code audits resolved typed calibration, execution resume/staging/cost uncertainty, reach feedback and report coverage issues.29 CPU checks and full9 preflight pass with authored controls; not model efficacy. Spec-only Qwen predicate/quote/domain/uncertainty, pure isolated trigger+predicate, calibrated observed witness/reach gating and named JSON binding. [Plan](PLAN_EXECUTABLE_OBLIGATIONS_V24.md), [audit report](analysis/v24_cpu_audit.md).

Narrow seen cohort9:3buggy,5correct,1ambiguous. Diagnostic-gold finite semantic bank explicitly qualifies predicates; not a reference-free semantic verifier or universal proof. Fixed24 type-only Hypothesis inputs plus public bases; identical concrete witnesses/native traces for verified_hyp/text_hyp/toolinput.2 generation calls/arm; same independent fixture scoring after generation freeze, input-only track (no model expected-output claim). Report raw and gated-selected input yields, false flags, duplicates/unknowns, all novel inputs and novel detections beyond ENTIRE pool; witness_only pool detections not recredited to LLM. Pool may saturate3 bugs; never modified for headroom. Online max90 logical calls, no benchmark expansion/content repair/paid fallback; results pending separately.

Qwen diagnostic9 launched detached after74-file source/prepared-packet/dependency freeze and unchanged v7/v23 hash verification. Model/context reachable; first actual artifact received. Completion watcher active; no duplicate launch or frozen edits. Status: out/pipelines/v24_obligations/humaneval/obligation_diagnostic/status.json.


## 11.63 v24 diagnostic9 complete — interface failed before executable-concept evaluation (2026-10-17)

Normal exit0; source/dependency/prepared-packet/preflight/preparation/generation hashes and parent-v7 hashes verified.90/90 Qwen completions, finish_reason=stop,0 retries/unknown completion usage;149,348 input/15,882 output tokens,86 tokenizer calls;31m04s. No additional Qwen/oracle call, PUT/predicate execution or repairs during analysis. All9 cases retained (3buggy,5correct,1ambiguous).

Contract accepted0/9: all9 place code in relation and prose in predicate_source, producing predicate_syntax before calibration. All9 decision=proposed, no ambiguity abstention;7 domain=Python. No Qwen obligation reaches semantic bank. Behavior9/9 mechanically valid; initial hypothesis8/9, final1/9 (missing reason on1initial/8final). All54 generation artifacts contain Markdown fences and fail strict invalid_JSON:0 executed/selected/new LLM inputs in every arm,18 failed stages/arm. All initial/final support unverified;224 contract checks unknown due absent qualified contract, not native failure.

Important control limitation: value() forwards accepted parsed artifacts only. Actual text_hyp concept=null9/9 and hypothesis=null8/9; verified contract/hypothesis=null9/9. Intended raw-text versus executable comparison is not realized. All9×2rounds preserve identical6 common native-evidence rows across3arms. Independent review of raw outputs additionally finds incomplete count predicates, inclusion ignoring observation, fabricated ambiguous/default semantics, missed returned dedup/equality and false masked-code hypotheses. None of these rejected sketches is repaired, executed or credited.

Witness-only catches3/3 bugs with36 distinct bug-revealing inputs (f02=14,f04=14,f06=8) in full224 shared24+base records; correct5 have none, ambiguous1 unscored. Baseline saturates tiny cohort.0 false flags with0 calibrated/accepted content is not a precision claim. Recorded common native workers448 PUT calls, online trigger workers5/124 evaluations (0 obligation evals); separate CPU controls6 PUT calls and25 workers/2779 predicate evaluations. No worker failure, interrupted uncertainty or rerun. Input-generation-only, common post-freeze fixture scoring; no model-authored assertion result.

**Disposition: output-interface infeasibility, not a valid concept-effectiveness null or superiority test.** No promotion, repair, relaunch, benchmark or paid fallback. Separate Luna null remains unpooled. [All9 outcomes/costs/limitations](analysis/v24_obligations_results.md), [raw Qwen/verification JSON](analysis/v24_obligations_results.json), [read-only recompute](analysis/v24_obligations_results.py). Callback handled, nothing to resume/duplicate.


## 11.64 v25 prospective split-output feasibility5 — audited code, bounded GPU pilot (2026-10-17)

User authorized continuation and reuse of old endpoint. New best-v7 copy v25_interface_gate, explicit v24 runtime ports; v7 parent and frozen v23/v24 source/generation verified unchanged. Separate spec-only metadata JSON/code-only obligation and hypothesis metadata/code-only trigger. Prospective bare-or-one-whole-fence envelope, no swaps/fills/semantic repairs or v24 output recovery. All rejected raw responses retain origin/hash plus decoded envelope when available; exported three controls share concrete native rows even on failure. Standard jsonschema/Hypothesis/inspect/ast/Counter/httpx/Jinja2 with inherited isolated worker policy.

Clean-context plan/code/follow-up audits resolved unknown evidence passing correct f14, interrupted context export, rejected decoded evidence loss, empty failure controls and completed-run metadata drift. **19 final CPU checks pass**, full package compileall pass, all5 authored preflight controls pass (4 calibrated +1 unknown-spec; native checks verified).74 source files/dependencies/prepared bank+pool hashes frozen before any capability/task completion. CPU scripted responses are authored controls only, never Qwen success.

Seen f02/f04/f06 bugs, f14 correct masked operation, f13 ambiguous. A requires4 calibrated obligations +f13 unknown; B requires3 observed-supported hypotheses, f14 consistent with all pool checks evaluated/true+native, f13 unknown; C requires supported discriminators, normal true contrast, ambiguity abstention. Failure stops dependent phases and retains all5 denominator. Finite authored semantic calibration is diagnostic gold, not a deployable semantic verifier. Novel inputs/tasks subtract ENTIRE frozen24+base pool; witness-only may saturate3 bugs. Input-only generation, independent fixture scoring after output freeze, no model-authored expected-output claim.

Detached controller + completion watcher launched12:36UTC on user-authorized old endpoint, environment-only. At most30 task slots/30,720 output tokens plus optional1 adversarial bare-JSON capability echo/64 tokens; cumulative93 physical attempt ceiling, no content retry/paid fallback/benchmark/full comparison. Backend mode fixed before tasks. Actual Qwen/worker costs and all-case semantic review pending terminal report, separately from CPU checks. [Plan](PLAN_INTERFACE_GATE_V25.md), [audit and verification](analysis/v25_cpu_audit.md). Owned status: out/pipelines/v25_interface_gate/humaneval/feasibility5/status.json; do not duplicate launch or edit frozen source.


## 11.65 v25 feasibility5 stopped — transport failure, no task output (2026-10-17)

Callback handled. Controller normal exit0 after14m32s, **A=false; B/C blocked**. No task completion body received: f02/f04 each3ReadTimeout, f06 completion HTTP503→non-retryable404, f14/f13 each3tokenizer HTTPStatusError before completion. Tokenizer status codes/bodies absent. No evidence of task schema/code semantic failure, protocol mismatch or counterexample; server/tunnel/backend root cause cannot be distinguished from persisted artifacts. No reset/retry/relaunch or frozen edits.

Five metadata slots/8physical task completion attempts, all task usage unknown. Only capability echo completed: actual bare {schema_gate:true}, origin=qwen_endpoint,42input/10output tokens,1attempt; mode fixed guided_json before tasks. Tiny echo does not validate task schema performance. Metadata13calls (2models+1OpenAPI+10tokenizer:4success/6error), prelaunch11model probes separate. Runtime task token0 counters are absent recorded usage, not actual zero consumption. OpenAPI advertisement preserved as digest/decision only.

All5 metadata failed at transport; predicates/calibration/behavior/hypotheses/triggers/inputs blocked. Calibration reached0/4 defined predicates; f13 ambiguity abstention unobserved, not a reasoning failure. No Qwen code/task envelopes, generated inputs/assertions or arm comparison to judge. Raw controls preserve request hash/failure reason and null text/origin because no response; subsequent records not_requested. All5×3contexts share identical6 native rows. Runtime semantic_review=pending is hardcoded; actual task review unavailable. Generation zeros are blocked defaults, not efficacy; no precision/false-alarm claim from absent qualified content.

Independent cached-result scoring: full124pool inputs, witness-only3/3bugs/36bug inputs (f02=14,f04=14,f06=8), correct masked f14=0/25 discrepancies, ambiguous f13 unscored.248native workers/PUT calls,0Qwen predicate workers, no failure/unknown/rerun. Separate authored CPU preflight10PUT calls +22predicate workers/2776evaluations. No new PUT/predicate/model calls during analysis. No LLM yield or novelty result beyond ENTIRE pool; witness baseline already saturates3bugs.

Read-only root recomputation and clean-context subagent review verified74source files, regenerated prepared data/dependencies/preflight,770frozen artifacts, parent-v7/v24 origin hashes and all raw-control/transport consistency. Transport/status/report ledgers are outside original freeze; analysis stores separate audit-time hashes. **Transport-incomplete diagnostic; neither v25 feasibility nor concept contribution measured.** No promotion/comparison/benchmark/real20/held-out/paid fallback. Previous Luna null separate/unpooled. [All5/costs/limitations](analysis/v25_interface_gate_results.md), [verification JSON](analysis/v25_interface_gate_results.json), [read-only verifier](analysis/v25_interface_gate_results.py). No work to resume/duplicate.


## 11.66 delayed v25 transport probe scheduled — user-authorized (2026-10-17)

After proposing a tiny transport diagnostic, user says "10 nữa thử lại". One new probe scheduled2026-10-17T14:08:06UTC/21:08:06Vietnam, separate out/transport_probes/v25_20261017_140806. Frozen v25 source/old run untouched. Same original f02 metadata prompt/payload, plain first then guided_json; max2completion requests/1attempt each, max2metadata requests once, no retries/polls/extra echo. Metadata or plain transport/protocol failure blocks remaining calls. No automatic diagnostic5/comparison/benchmark/real20/held-out/paid calls.

Clean-context code audit resolved deadline race and encoded/nested secret redaction.5authored httpx CPU checks pass; script/old source+snapshot/payload/time protocol frozen before network. Detached controller1277567 waiting; same-thread terminal callback configured. Records HTTP status/latency/sanitized body/original SHA, raw response origin and known/unknown usage. Fixed sequential order and absent server logs prevent a causal backend/root-cause claim. No new model call at schedule verification; actual results pending. [Utility](analysis/v25_transport_probe.py), [audit](analysis/v25_transport_probe_audit.md), status under owned probe output. Do not duplicate/restart after started.


## 11.67 delayed transport probe terminal — ngrok endpoint offline (2026-10-17)

Probe chạy đúng14:08:06UTC/21:08:06Vietnam (delay0.051909s), dừng preflight sau0.219525s. Chỉ1GET /v1/models: HTTP404/ERR_NGROK_3200, latency0.217735796s, error body báo endpoint offline.0tokenizer requests,0plain/guided completion attempts/responses,0PUT/predicate workers. Không diễn ra plain-vs-guided/schema/semantic comparison. Metadata generic usage_unknown state không phải unknown model completion usage; không có generation request trong probe này.8unknown-usage attempts của diagnostic5 cũ giữ riêng.

Script SHA/frozen protocol,74v25 source files, prepared data,770old frozen artifacts và old transport/status/report analysis hashes đều verified unchanged. Exact planned request pair chỉ khác guided flag; cap2single-attempt completions không sử dụng. Root+clean-context independent audit xác nhận evidence. Không đủ server logs kết luận GPU/upstream/guided-decoder root cause; fixed sequential design cũng không xác lập causal comparison.

Privacy caveat: ngrok error body có bare hostname vượt frozen redactor; không copy body/hostname vào analysis/tracked files, originals giữ nguyên, chưa repair source. Callback handled; không retry/reset/diagnostic5/comparison/benchmark/paid/new calls. Cần endpoint online hoặc endpoint mới trước fresh authorized run. [Sanitized report](analysis/v25_transport_probe_results.md), [data](analysis/v25_transport_probe_results.json), [read-only verifier](analysis/v25_transport_probe_results.py).


## 11.68 explicit fresh transport retry — still endpoint offline (2026-10-18)

User says "tử lại đi". New run v25_20261018_040624 at04:08:10UTC/11:08Vietnam; same frozen f02 payload pair, max2single-attempt completions, no automatic further run-id. Reuses frozen utility read-only via small new wrapper with bare/encoded-host privacy adapter;7local HTTP/privacy controls pass and clean-context code audit no blocker. Original v25 source/prompts/attempts untouched.

Actual1models GET →HTTP404/ERR_NGROK_3200, endpoint offline; latency0.194394049s, wall0.197042s.0tokenizer/plain/guided completion attempts,0unknown completion usage,0PUT/predicate workers. No model output, schema/concept or paired-backend result. Generic metadata usage_unknown label does not mean a generation call was sent; old8unknown attempts remain separate. No server logs to identify upstream cause.

Wrapper/frozen script hashes, original74sources/prepared-data/770frozen artifacts, old diagnostic+probe transport/status/report analysis hashes all verified unchanged. New error artifact has bare hostname masked; no body/endpoint copied to tracked analysis. No retry/reset/diagnostic5/comparison/benchmark/paid expansion. Callback handled. [Report](analysis/v25_transport_retry_results.md), [verification JSON](analysis/v25_transport_retry_results.json), [read-only verifier](analysis/v25_transport_retry_results.py).

## 11.69 Luna subagent chain diagnostic (2026-10-18)

User asked whether model is the bottleneck. Six preregistered failure-targeted probes:3 S2 extraction cases +3 S3 replay cases, fresh gpt-6-luna subagent per exact saved Qwen system/user packet, no parent history/answers/labels or content retries. Same frozen v22 validators/aliases; all parent source/generation and packet-message equality verified.

Luna6/6 valid vs prior Qwen0/6. S3: correct sum→abstain; length-guard bug→mismatch with sufficient len>2 AND sum<=limit divergence; undefined suitable→unknown. S2 describes any-even, sorted distinct values and early exit using valid IDs/caps. This supports model capability as a material contributor; prompt/interface design still matters.

Not a causal equal-budget benchmark: agent harness/tool/default reasoning differs, no comparable token accounting, one response on6 seen targeted failures. No full-chain/S4/S5/generation/D_IO/human gate or concept-gain claim. No new GPU/paid calls. [Prereg+report](analysis/luna_chain_probe_20261018/REPORT.md), [raw/validation](analysis/luna_chain_probe_20261018/results.json).


## 11.70 user-authorized native v23/v24/v25 Luna rerun — launch and early-stop checkpoint (2026-10-18)

User requests exact gpt-5.6-luna/low subagents, tools optionally disabled. Native v23diagnostic16/v24diagnostic9/v25feasibility5 run(client,root) engines unchanged at fresh out/model_probes/luna_versions_20261018. Independent plan/code audits;16local mock controls and native CPU preflights passed. Parent CPU verification retained, no Qwen endpoint or held-out/benchmark calls. Max280single-attempt task CLI invocations plus1actual canary turn; no content retry/model fallback. Requested identity/local catalog only unless server events supply ID. Role flattening/base instructions/sampling-token caps differ from Qwen, so this is an unmatched harness diagnostic, not causal model isolation.

Two config-only pre-start rejections preserved. Actual canary13,565input/199output (cached12,288) FAILED schema-exposure gate; execution host denied a requested tool. Before task outputs, independently audited epoch4 permits only two exact pre-turn startup warnings, openly records schemas exposed/host disabled, rejects any task tool/router attempt before caching/scoring and aborts that version. No canary retry. Active protocol_v4/readiness_v4, exact pre-canary source archive retained.

Runs detached16:36UTC, original cohorts16/9/5. v25 finished9/9received task responses, A=false/B-C blocked:5metadata valid, f13 correct unknown, f06 calibrated2028/2028; f02/f04/f14 rejected predicate_binding_mutation. Independent static review finds their normative relations correct in valid domain: validator globally treats repeated comprehension variable x in separate Python3 scopes as mutation. Rejected code never repaired/executed/rescored, native gate unchanged. No v25 downstream/hypothesis/input benefit/false-alarm conclusion. v23/v24 still running at checkpoint. [Registered protocol](analysis/luna_versions_20261018/PREREG.md), [audit](analysis/luna_versions_20261018/AUDIT.md), [independent v25 review](analysis/luna_versions_20261018/V25_REVIEW.md). Full terminal within-version controls/usage/semantics pending; no promotion/expansion.


## 11.71 explicit Luna continuation after quota interruption (2026-10-19)

Epoch1v23/v24 stopped at73/65received responses plus one usage-limit turn.failed/error each, no task tool attempt. v25 complete9calls/Afalse remains unchanged. Full partial-suite snapshot analysis/luna_versions_20261018/results.json records149taskCLIinvocations/147received, known1,166,055input/33,168outputtokens and2unknown-usage quota attempts; canary separate13,565/199. Partial v23/v24 are not final efficacy results.

User says "thử tiếp đi m". Fresh luna_versions_continue_20261019 imports original native inputs/artifacts/caches byte-identically, entire original inventories/source hashes frozen, no oldwrites. Missingstages only through original unchangedLuna/low host-disabledClient, newcontinuation_transport namespace, max87/25new single attempts; previousquota slots cumulativeatmost2 underfreshauthorization. Independent clean-context audit confirms copy/integrity/caps and cacheidentity acrossroots. v23started15:42:59UTC; freshresponses confirm access, then v24launched. No model/provider/prompt/source/validator changes, newcanary, Qwen/paid/heldout/benchmark expansion. Full16/9controls/scoring pending; v25notrerun. Externalcostmustsum importedold+newledgers once, not read stale nativeimported-onlycosts. Across-daytrajectory/harnesslimits retained. [Continuation prereg](analysis/luna_versions_continue_20261019/PREREG.md).


## 11.72 native v23/v24/v25 Luna retest complete — no task gain, concrete interface/gating losses (2026-10-19)

Full original16/9/5denominators completed with requestedgpt-5.6-luna/low, unchanged nativecode/prompts/parser. Quota continuation reused73/65accepted responses byte-identically and added79/25missing stages; no acceptedstage regenerated, both oldquota attempts retained.251successful target contexts distinct,0recorded tasktool/router attempts; executionhostdisabled butschemasexposed, failedcanaryexposure preserved. Requestedmodelidentity only; CLIrole/base/sampling budgets differ from Qwen, no causal equal-budget model isolation.

v23: concept_chain5/7correct-assertion bugtasks vsdirect7/7,hyp_only5/7; FA1/0/0, blocked2/0/2. All16concepts/behavior faithful in independentqualitativereview. f04/f16concept hypotheses have correct rawmismatch reasoning but malformedJSON, blockingC/H withoutrepair; f12C revisionexpectedTrue for([1,2,3],5) is wrong (sum6>5), genuinefalsealarm. f13C/H preserveundefinedsuitability/abstain, directinventsfirst-elementsemantics and4expectedvalues unscored; FA0doesn'tcoverambiguity. All236candidate slotsobserved, expectedcorrectC73/74,H74/74,D84/84scorable+4undefined. No explicitconceptgain atgeneration overhyp_only; ambiguityhandling benefit qualitativeonly.

v24:90responsesJSON-shaped, nativevaliditycontract6/9 (5calibrated+unknown),behavior9/9,initial8/9,final9/9,generation54/54. f02contractcorrectrelationusesexplicitlyforbidden.get; f03/f14contracts andf04initialtrigger falselyrejected forcomprehensionxreuse. All9actualnormative/behavior/fault diagnoses faithful. Finalsupportonlyf04. Verifiedraw30inputs/10buginputs/2bugtasks→selected4/4/1, text48/12/3, tool48/14/3, witness36buginputs/3tasks. Novelbuginputs outsideENTIREpool verifiedraw10/selected4,text11,tool14;0newdetectedtasksbeyondwitness. f06generates6novelbuginputs, includingexacttrigger withcachedobligationFalse/triggerTrue/reachTrue, butfrozenpreparation supportunverified preventsacceptance.0falsecontractflags oncalibratedcases/0falseverifiedflags on4acceptedinputs,99/224poolcontractrowsunknown; f13oracleunknown/toolround1abstentionviolation andloosepurposelabels retained. Controlsidentical6rows/case, rawtextcontractnull3rejectedcases; notallarmsreceivefullguidance.

v25:9responses,metadata5/5faithful;f13unknown,f06calibrated2028rows. f02/f04/f14normativecodeappearscorrectin-domain butglobalknown-Storevalidatorrejectslegalxreuse acrossseparatePython3comprehensions. No rejectedcodeexecuted/renamed/rescored; Afalse/B-Cblocked unchanged. No hypothesis/input/novelty/falsealarmperformance conclusion. This is validator scope defect, notobservedwrongrelation orsuccessfulfullchain.

Cumulative target253CLIinvocations/251responses/2unknownquotausage, known2,010,148input/54,531outputtokens (cached1,291,136/reasoning21,660subsetsoftotals). Canary separate13,565/199;2config-only prestartCLIrejections0modelturns. Knowninclcanary2,023,713/54,730; unknownquotausage stillunknown. Native resumedcostobjects imported-only, externalold+newaggregate authoritative; internalCLIHTTPrequests/dollars unobserved. v24recordedmain682PUTcalls/47predicateworkers3281evals, CPU25workers2779evals+6evaluatorPUTcalls;v25main248PUT/17predicateworkers2053evals,CPU10PUT+22workers2776evals. v23legacy378workerresults (366ok/12exception), exactlaunch/PUTcounters unavailable. No workerfailures/unresolveddurablereservations.

Original/fullimport/generation/rawCLIhashes verified; independentclean-context reviewers read all16/9/5outputs and cumulativecost/integrity. No raw/frozenrepair or widercomparison/heldout/benchmark/modelfallback/paidAPI. **No demonstrated concept task-detection gain; useful mechanisms limited by serialization, lexical-scope validation and rigid support gating.** Futurefixrequiresseparatefrozenvariant/protocol; currenttaskcomplete. [Full report](analysis/luna_versions_continue_20261019/REPORT.md), [raw/provenance/cumulative data](analysis/luna_versions_continue_20261019/results.json), [read-only finalizer](analysis/luna_versions_continue_20261019/finalize.py), [all16](analysis/luna_versions_continue_20261019/V23_REVIEW.md), [all9](analysis/luna_versions_continue_20261019/V24_REVIEW.md), [all5](analysis/luna_versions_20261018/V25_REVIEW.md).


## 11.73 v32_scope_support — lexical fix exercised, support CPU-tested, fresh Luna blocked at trigger interface (2026-10-19)

User accepted fixing comprehension scopes and support promotion after new witnesses. New best-v7 copy plus explicit v25 ports, stdlib AST lexical bindings, separate unverified candidate admission, cumulative ENTIRE24+base-prefix plus every proposal ledger. No old source/output repair, execution or rescore. Clean-context plan/code audit and stable-source48/48CPU tests passed. Fresh requested gpt-5.6-luna/low seen5 frozen run completed16:23:13–16:25:39UTC: **A=true/B=false/C=not run**.

All5: f02 sorted-multiset contract238/238 calibrated, correct dedup fault/duplicate trigger,target3,14/25witnesses, Badmitted; f04 >=count contract510/510, correct >fault/equality trigger,target3,14/25witnesses,Badmitted; f06 membership-subset contract2028/2028 and set-equality fault/condition correct but trigger(container,required) violates trigger(arguments), rejected predicate_signature,Bnotadmitted; f14 sorted-copy contract238/238, unused-set masking recognized,25/25True,consistent Badmitted; f13 undefined suitability metadata/hypothesis unknown,24native/24unknowncontract+undefinedoracle,triggerNA,Badmitted. f06 also falsely claims supplied cases lack its discriminator: actual common6 all discriminate (five empty-required and one nonempty strictsubset). Preserve raw rejected trigger, never execute/wrap/rename it. Global B stop blocks C for all5; these are not5generation failures.

Fresh f04/f14 sibling comprehension x reuse accepted unchanged/calibrated, f02 nested capture valid: actual lexical fix exercised. Support promotion only authored CPU evidence: provisional absent-trigger candidate can gain a new witness, but old counterexamples/unknown/failed proposals block. No model provisional admission/promotion or C inputs observed; no generation/contrast/final-input-abstention, comparison, novel-input or task-gain result. Four finite banks3014logicalprobes are not universal/reference-free proof. Full pool124 observations:100known normative checks,36true flags(14+14+8),0false flags among64correct/0missedbugs among36bug observations;24f13unknown separate. Trigger coverage50/75bug-poolrows, f06unavailable25, controlsNA. Witness-only already3/3bugtasks. Raw/gated input0/0 because uncalled; rateNA, no improved model-authored assertion claim.

Actual22single-attemptCLI/22received/22freshthreads, known163666input/4463outputtokens,0unknownusage,0recordedtool/router attempts. Cached109440/reasoning2605 subsets. Median5.658s/call, range4.329–7.689s, elapsed145.731s. RequestedCLI model identity only, rolesflattened/Codexinstructions/unmatchedsampling,schemasexposedhostdisabled, internalHTTP/dollarsunobserved. Main248PUTcalls +30predicateworkers3164eval; CPUpreflight10PUT+22workers2776eval,0failed/unresolved. Regression workers separate in report/accounting (two development/full suites3548PUT+468predicateworkers41936eval; initial45pass/3fail corrected then48pass). Original18040fileinventory/source/prepared/run902/raw177hashes independently verified. No retry, fullcomparison/benchmark/real20/held-out/paid/endpoint calls or active job. Own derived analysis labeling correction preserves results_initial; latest f13 observed24,oracleNA; frozen runtime unchanged.

[Full report](analysis/v32_scope_support_20261019/REPORT.md), [machine evidence](analysis/v32_scope_support_20261019/results.json), [all5 semantic review](analysis/v32_scope_support_20261019/SEMANTIC_REVIEW.md), [terminal audit](analysis/v32_scope_support_20261019/TERMINAL_AUDIT.md), [new source/protocol](pipelines/v32_scope_support/PREREG.md). Remaining observed blockers: trigger interface compliance and evidence grounding. No concept task-gain conclusion.

## 11.74 Qwen3.5 OpenRouter30dev chain feasibility (2026-10-19)

User explicitly authorized ~30tasks with qwen/qwen3.5-35b-a3b; real scripts/openrouter_env.sh was only sourced silently, never inspected/printed. New v32_qwenchain_or30 copy of v22, unchanged semantic prompts/validators;30dev tasks randomly selected from frozen113dev pool, seed20261019.97 offline checks pass. Larger visible caps(2048/2048/4096/2048/2048),reasoning requested off,2workers,≤150single-attempt stages,cap=min(env,1USD),provider price ceilings/durable reservations. No model fallback/content repairs/retries.

COMPLETE:93/93 completions,276850input/44330outputtokens,0reasoning/unknownusage,$0.05124275. Source/generation/all completed transport/native/scoring evidence hashes verified. S1valid29/30,S2valid28/30,S3valid7 (3selectedhypothesis tasks +4terminal),20S3rejects/3blocked. S4valid3→18uniqueinputs (17nativechecked,1filtered);S5valid0,3ID/aliasrejects,0finalproposals. S3 rejects chiefly11empty_ok,5status,2coverage,1uniqueJSON,1terminalstatus.

After generation freeze, native canonical comparison finds conditional any-stage IO differences in3/30 tasks:58sortedintersection vssetiteration,79added0..255guard,137numeric vslexicographic comparison.17decisive/1unresolvedinputs; final-S5 IO0/30. Example task58([10,2,5],[5,2,10]) PUT[2,10,5] vscanonical[2,5,10]; task137('10','2') PUT'2' vscanonical'10'. Candidate predictions:7native matches/10contradictions/1unverified, not a trusted spec oracle. Canonical differences remain conditional on spec-domain/minedfilter admissibility; no human semantic accuracy or baseline concept-gain claim.

Verdict: promising selected reasoning and concrete inputs with a small paid model, but full chain still blocked chiefly by serialization/status/reference contract. Not sufficient to promote to a large benchmark; stabilize interface and recheck scope/semantic grounding before wider comparison. No added model work/spend authorized by this finding. [Report](analysis/v32_qwenchain_or30_results.md), [machine evidence](analysis/v32_qwenchain_or30_results.json), [frozen prereg](pipelines/v32_qwenchain_or30/PREREG.md). All jobs finished; callback handled.

## 11.75 GPT-5.6 Luna low chain vs direct30 — direct dominates current hard-gated chain (2026-10-20)

User authorized the proposed last comparison with exact requested gpt-5.6-luna/low. New v33_lunachain30, same30prepared tasks as v32. Compiler assigns row IDs and derives status mechanically from model-authored comparisons; model remains responsible for semantics.99 offline checks and1separate successful canary. Fresh ephemeral empty read-only CLI, execution host disabled/schemas exposed, no model tools or paid endpoint/env access. Source/generation/completed evidence and canary/source/prepared hashes verified.

Same maximum5calls/12uniqueinputs per arm/task, randomized task/arm order. Direct uses3/3/2/2/2input slots; chain S1/S2/S3 then≤6S4/≤6S5. Actual compute differs due chain stopping.253/253 task CLI receipts (chain103,direct150),0unknown/forbidden/tool attempts; knowninput2,225,985/output96,074tokens (chain1,005,737/61,666 vsdirect1,220,248/34,408),canary6,690/9separate. InternalHTTP retries/dollars and independently reported server model ID unavailable; CLI model/effort pinned as requested.

Primary strict typed canonical IO: chain8/30 vsdirect26/30; final-retained8vs21; chain-only0,direct-only18. Post-hoc Python-value equality audit identifies task130's10strict differences as2vs2.0type-only; conservatively excluding these yields8vs25(any),8vs21(final),chain-only0/direct-only17. Do not call type-only observations semantic bugs. Registered equal-input200randomsubset means8vs8.37 over30,sharednonemptycohort9; coverage conditioning prevents a new full-pipeline claim. No concept advantage observed.

Coverage:chain selected/inputtasks9/30,27uniqueinputs;direct30/30,324inputs. Chain S1valid30,S2valid25,S3valid23,S4/S5valid9.14tasks stop atS3terminal,7blocked by grounded-interface errors. Remaining implementation/documentation gap:6rejects are >12validsource references (legacy cap not clearly stated in simplified prompt);1omits uncertainty fields. These are not evidence of wrong semantics. Even rescuing all7blocked cases could add at most7taskdetections(8+7=15),stillbelowdirect25 without changing the14terminal decisions. Of17value-unequal direct-only tasks,10chainunknown,1chainabstain,5blocked,1inputsearchfailure. Case58 has a correct sortedness hypothesis but picks a case whose set order happens already sorted plus unhashable out-of-reference-domain input; direct finds a concrete ordering difference.

Verdict: do not promote this hard-gated5stage workflow as main method; stronger model/fixedIDs do not yield task gain here. This is not proof concepts generally fail. Canonical comparisons conditional on spec-domain/minedfilter admissibility, no held-out/general semantic accuracy/mechanism-only causal claim, maxima matched but actualtokens/calls not. No auto further model calls/retries/expansion. [Full report](analysis/v33_lunachain30_results.md), [machine evidence](analysis/v33_lunachain30_results.json), [prereg](pipelines/v33_lunachain30/PREREG.md). Completed callback handled.


## 11.76 retrospective recent-run attribution — concept-to-input training not yet supported as the main remedy (2026-10-20)

User asks whether correct concepts fail to yield inputs or failures occur elsewhere. Read existing v23/v24/v32/v33/v27/v28/v34/v35 reports and v33 saved JSON; no new model/API/worker calls, source/raw repair or scoring changes. Cohorts/models differ: no pooled rate or cross-version causal estimate. v33 Python-value sensitivity direct-only17 losses =10 S3unknown+1abstain,3S2source_refs+1behavior_fields+1S3comparison_refs,1input-search miss:11 upstream terminal/5 mechanical/1search. Semantic accuracy is null, so schema validity is not correct-concept gold. Chain generates on9/30 and exposes8 vs direct25; no chain-only. Fixing all7mechanical blocks holds upper bound15<25 if terminal choices fixed; input-quality matched subset8vs8.37 shows no gain.

Luna v24 f06 generates6 novel revealing inputs accepted0 due frozen support gate; unsupported f06 hypothesis was hidden from verified guidance, so this shows synthesis capability/gating loss, not causal concept use. v32 has calibrated concepts and correct diagnoses but C unattempted after invalid trigger; no failed-input-synthesis claim. v23 concepts/behavior faithful, two correct raw hypotheses blockedJSON and one wrong expected causesFA. v27/v28 oracle model capability largely fixes Qwen failures but stronger-model arms includingplain all16–17/20; no added concept utility. v34 five of8wins lack exposing concept inputs, all16confirmed win-tests newly model-written; v35 fixedpool17/33exposes vsplain19/33, conditionalconceptceiling14fails17threshold (not unrestrictedmodelcapacitybound).

Assessment: prior suggestion to prioritize concept→input training is premature. Evidence favors separating upstream semantic selection/abstention, interface/gating, oracle soundness, fixed-pool limits and lack of incremental information. Independently correct-concept + actual generation-opportunity + failed-translation cases have not been systematically labeled. This neither disproves concepts/training nor supports another run. [Synthesis and limits](analysis/recent_concept_failure_attribution_20261020.md).


## 11.77 Astra concept design / Qwen32B authorization — quota checkpoint, no efficacy run (2026-10-20)

User requests Astra improved catalog/tests, then authorizes small diagnostic on exact qwen2.5-coder-32b-instruct and stop/schedule if Codex5h remaining<20%. Astra drafted7relation concepts,8seen episodes/3arms/72single-attemptturns; not finished/approved/implemented/frozen. Parent found/fixed public catalog projection witness leak in draft and highlighted proactive-vs-feedback revision. Read-only v28 frozen-ledger audit69actions:58replay,35accepted/33nativechecked across13cases,27errors,59hypothesislinks,3identical-query-list repeats; active replay is prior art, no newefficacyclaim. Endpoint metadata only verified exactmodel/context8192,1modelsGET,0completions/unknownattempts/newPUTcalls. Live quota27→19%; interrupted Astra and stopped research work, checkpointed for original-task continuation. Verified active systemd-user timer at17:46:32UTC20Oct /00:46:32Vietnam21Oct (reset+120s), guarded by freshquota check. No duplicate launch, paid fallback, benchmark, training or other-session edits. [Draft and handoff](analysis/astra_concept_design_20261020/README.md).


### Astra D1 quota amendment — user resume at15%, actual remaining10% (2026-10-20)

User explicitly lowers stop threshold20→15%. Cancelled old waiting timer, checked live quota at16:40UTC:10%remaining, therefore stopped/interrupted Astra again without research/model launch. Replacement verified active at same17:46:32UTC/00:46:32Vietnam, unit suffix-15; quota guard and continuation instructions now remaining<=15%. Existing0Qwencompletion/0unknownattempt checkpoint unchanged. No findings or efficacy result from this brief conditional resume.


## 11.78 v40_concept_agent — Astra design implemented/frozen, endpoint404 blocks model run (2026-10-21)

User sayscontinue; quota100% at01:05UTC, stop<=15%. Previous scheduledCLI wakefailed activewriterconflict (no modelrun); manuallycontinued. Astra completed7relationcatalog and8episode3arm72slotD1 design withpriorart/selfaudit. Freshbest-v7copy+v30tool/v23fixtureports v40_concept_agent implements predictions beforeexecution, native-onlyfeedback, selectiveclaimstates, adaptive/committedquerycontrols and finalinputs withoutsemanticadmissiongate. Initialauditwithheldapproval for droppedtooldata, malformedactions, lostrawresponse andresumeusage/limits; allfixed beforecalls. StableCPU12/12pass4.02s including72scriptedresponses/resume(no actualmodelturns); independentclean-context codeauditapproved frozenpreparation89fb756eda3d472dc12afd1cb924c7581e6a0da897ae64b67802cacc248e4af0 conditional onliveexactmodel/tokenizer/quota. Mainpreparation16nativeobservations/32durableworkerlaunches,allcompleted; PUTentrycountnotexplicitlyrecorded, notzero. No originalsource/outputrepair,vendor/Kaggle edits orautoexpansion.

PrelaunchGET /v1/models returns404; one metadataattempt today,0taskattempts/responses/tokenizerrequests/unknowntaskusage. All72slots not_attempted across24episode-armrows; generation, semanticrevision, adaptation, discovery, falseclaims andnovelty unmeasured. Yesterdayexactmodel/context8192 metadata doesnotcertifytodayavailability. No hiddenwitness/expectedoracle inpublicmessages, E3/E6sharedexposurefloorseparate, no supplied-semantics/extraction/generic-equality overclaim. Source/prepared/dependency/guardverified frozen; approval/statusreadywaitingendpoint. Asyncquestion requests liveendpoint; no retry/fallback/scheduledGPUlaunch. [Implementation/readiness report](analysis/v40_concept_agent_20261021/REPORT.md), [all slots/status](analysis/v40_concept_agent_20261021/prepared_status.json), [codeaudit](analysis/v40_concept_agent_20261021/CODE_REVIEW.md), [Astra design](analysis/astra_concept_design_20261020/DESIGN.md), [protocol](pipelines/v40_concept_agent/PREREG.md).


### v40 user-authorized delayed launch scheduled —2026-10-21, no task outputs yet

User asks10minthenrun. Detachedcontroller verifiedalive waits until05:23:50UTC/12:23:50Vietnam before anytaskcall. Recheckquota>15%, frozen source/prepareddata andliveexactmodel/context/tokenizer; noQwencompletionbeforedeadline. Sourceunchanged, onlyexternalorchestration; no transportretry/fallback/unknownattemptreset. Safequotapause maywaitreset/resumeexactdurableslots. CallbackCodexqueueexistingthread replacesfailedCLIwriterresume. Actualexecution/callbacknotyetobserved,0taskattemptsatscheduling. [Schedule](analysis/v40_concept_agent_20261021/SCHEDULE.md).


## 11.79 v40 delayed Qwen32B terminal — first completion transport failure, semantic diagnostic unmeasured (2026-10-21)

Owned callback handled without relaunch/repair/retry/reset. Deadline05:23:50UTC, actualcontrollerlaunch05:23:51.190827UTC(12:23:51Vietnam); quota54%>15%, freshparentcheck53%. Live models/tokenize received exactqwen2.5-coder-32b-instruct/context8192; earlier404 historical. First slot E3__concept_adaptive__1 reserved/failed after180.10103203100152s, reasonTransportStop transport_or_JSON_failure. No raw_response/acceptedresponse/artifact/event; no completedbody persisted. Frozenclient coarsensHTTPX/JSONerrors; configuredtimeout180s+elapsedconsistentwithtimeout but underlyingReadTimeout/reset/HTTPstatus/serverreceipt/queue/progress unknown withoutserverlogs. Do not callthisschema/semantic/counterexamplefailure.

All8episodes×3arms×3turns:1failedtransport+71not_attempted,0receivedoutputs/parsedclaims/modelqueries/replays/finalinputs. E3CAturn1fails, its2laterturnsnotattempted; GA/CC all3notattempted; everyother7episode all9notattempted. No post-turn toolfeedback/modeloutput delivered; only E3initialpacket(B0included) was placed inattemptedrequest, serverreceiptunknown. E3/E6preparedinjectedexposingrows were notdelivered inturn2. No modelabstention orcorrectness/falsealarm/novelty/utility/adaptivity metric; noconceptgain ornegative semanticconclusion. Knownusageattempts0+unknownusageattempt1, actualtokens/dollarsunobserved. Tokenizer2359 is requestsize, NOT received/billedinput; output1536 onlycap. Delayedrunmetadata2received(models/tokenize),prelaunchmetadata1failed404separate. Modelnativeworkers0; sharedCPU32launchesallcompleted/ok,16nativeagreements; explicitPUTcounterabsent,32singleentrycallsinferrednotrecorded.

Independentclean-contextterminalauditPASS:89source+8prepared+approval/dependency/Pythonbinary/guard/schedulerscript hashesmatch; separate terminalinventory162/162 filesexact(SHA7046515ee6c05cc2ad8f2c355e44bc5a554f92b4a27466898d5e74016f32bcad),no generation_frozen becauseincomplete. Analysis-onlyscorerlabels distinguish1failed/71unattempted and no-received-outputmetricsNA; no raw/treatmentchanges. Schedulercallbackcodexqueue0 andthiscallbackreceived; diagnosticprocessreturncode0isnotcompletion(statusstopped). Noactivecontroller/automaticfurthercall. [Terminal/all8×3](analysis/v40_concept_agent_20261021/TERMINAL.md), [machine status](analysis/v40_concept_agent_20261021/incomplete_status.json), [independent audit](analysis/v40_concept_agent_20261021/TERMINAL_AUDIT.md).


## 11.80 v40 explicit retry — model/context preflight stops before completions (2026-10-21)

User explicitly requests retry; clean-context launcher audit PASS, fresh namespace
d1_retry_20261021 with byte-identical source/prepared/approval/shared evidence.
At12:22:33–34UTC, quota93%>15%, models metadata received, then frozen exactalias/
context8192 check fails: requested_model_or_context_unavailable. Response body
not retained; cannot distinguish alias absent versus missing/mismatched context
metadata, identify served model, or infer another timeout.0tokenizer/0completions/
0new workers, all72slots not_attempted across8episodes3arms. No Qwen output,
abstention, predictions/revision, false alarm/yield/novelty/capability or concept-gain
measurement. New model-token usage0 with0completion calls; cumulative original
1failed completion remains unknown usage, never relabeled zero or reset. New1+
old2received metadata=3; historicalprelaunch404 separate. Copied16CPUobservations/
32workers historical once, not new attempts; explicitPUTcounter absent. Old162file
inventory and89source/8prepared unchanged; new151terminalinventory matched. No
repair, timeout/prompt change, retry, fallback, benchmark, heldout/training or paid
call; no active controller. [Report/all24rows](analysis/v40_retry_20261021/REPORT.md),
[machine status](analysis/v40_retry_20261021/incomplete_status.json).


Explicit retry callback received12:25UTC, after foreground reporting. Read-only
reverification passed old162/new151 inventory,89source/8prepared/approval/deps;
all72notattempted unchanged. Quota91%>15%. No duplicate launch/scoring/Qwen/worker
calls. Callbackreceipt now observed; see analysis/v40_retry_20261021/callback_reverification.json.


## 11.81 v40 second explicit retry — current server advertises7B, required32B alias absent (2026-10-21)

User says “thế thử đi”. Prospective singlemetadataGET at12:30:12UTC returnsHTTP200
in0.6727s; saved secret-safe body/hash advertises qwen2.5-coder-7b-instruct with
max_model_len16384, requiredexact32B alias absent. This establishes currentgate
failure, not historicalmissingmetadata reconstruction or weights verification.
No32Bdiagnostic launch/tokenizer/completion/newworkers, all72conditionalslots
not_attempted, no semantic/capability/conceptgain result. No7Bsubstitution, frozen
source/contextchange, automaticretry/reset orpaid/benchmark/heldout/training. New
1metadatareceived; cumulative4receivedmetadata, historical404separate; cumulative
1taskattempt remainsunknown actualusage,0responses. Historical16sharedobservations/
32workers countedonce,0newworkers. Quota90%; old162/151inventory/source/prepared
verified unchanged. [Actualmetadata/report/all8×3](analysis/v40_retry2_20261021/REPORT.md),
[machine status](analysis/v40_retry2_20261021/status.json).


## 11.82 v40 retry3 complete — useful inputs, semantic revision and incremental concept gates fail (2026-10-21)

Exactrequested/returned Qwen2.5-Coder32B, metadata root32B-AWQ/context8192;
13:20:19–14:07:31UTC.72/72received actualresponses, allrawJSONparseable,71schema-
valid/65controlleraccepted.24/23/18acceptedturns CA/GA/CC; all24finalturns valid.
No unattempted slots, no newtransportfailure/retry/repair. FiveCC T2replacement-
commitment failures +oneCC prematurefinal +oneGA E1queryclaim schemafailure, all
raw preserved;13thirdreplaycap refusals. No domain/native disagreement. Frozen
89source/8prepared/approval/deps/guard andallold/newinventories exact.

All3arms independently expose6/6buggy episodes throughreplay/final, including4/4
no-supplied-exposure E1/E2/E4/E5. Supplied16rows aloneexposeE3/E6; no CA-only task
win(0/0vsGA). Finalinputs accepted16/16each, revealing11/12,10/12,11/12 across6buggy
cases;2correctE7matches+2ambiguousE8unknown perarm. Input-only fixture-oracletrack,
no model-authored assertiongain. Uniqueexposing task-inputpairs outside ENTIRE
v40same-tasksharedpool25/19/15; stricterall-tasksharedliteral23/18/14. These are
not historicalwhole24+base/benchmarknovelty claims.

Independentclean-context semantic audits E1–E4 andE5–E8 plusparent rawreview: E1/E5
proactively narrowfalseH, E7allfinals nofalsebug, E8allsemanticabstention. But CA
correctHretention E2/E4=0/2: observes strictcounts/exceptions thenwithdraws true
implementationclaims, substitutes desiredspec inE2. E6CA/CCwithdraw dedup despite
cleanreplays, GAfinalclaims withoutdedup againstevidence. E3CA/CCwrong-direction
inclusionexplanation andinvertedwhy; GAfinalextracontainermismatch correct. CA24/24
validturns means semanticfailurecannotbeexplainedonlybyinterface. E7CArepeats
disprovedqueryT2,withdrawsT3; GAchangespredictionT2. OnlyE7clearunresolvedinitial
falseHfeedbackopportunity(<2registeredminimum); CC7/8emptylaterbatch +6invalidT2
limitsadaptivitycontrol. Capabilityfail+incrementalconceptfail =>combinedpackage
NO-GO perprereg; no n/Kexpansion/training/benchmark torescue. Inputsfounddoesnot
proveclaimsorconceptutility, andsmallsupplied-conceptseenfixtures do notestablish
real-task/abstractconceptuniversalfailure.

Newactualknown tokens220592prompt+21197completion=241789. Cumulativefourroot
completionattempts73/responses72/known72/oldunknown1; actualtotalusage unknown,
knownsubtotalplusoriginalunknown. New146HTTPoperations incl2modelGET/72tokenize/
72completion; scopedcumulative152 incloriginal404; earlier20Octreadiness excluded.
Newnative126completedworkers (116ok/10PUTexceptions),117logicalexecutionrequests/
108inferredcachehits; historical32sharedworkers reusedonce, notrerun. Explicit
PUTcounterabsent,126new+32historicalentrycalls inferredfromsource/status. Quota66%
atcallback/45%14:14UTC, above15. Callbackhandled, noactivecontroller/automaticcalls.
[Full8×3report](analysis/v40_retry3_20261021/REPORT.md),
[semanticA](analysis/v40_retry3_20261021/SEMANTIC_A.md),
[semanticB](analysis/v40_retry3_20261021/SEMANTIC_B.md),
[cost/integrity](analysis/v40_retry3_20261021/INTEGRITY_COST_AUDIT.md).


## 11.83 v43 implementation/readiness — paired binding diagnostic launched, efficacy pending (2026-10-22)

User-authorized best-v7copy+v40ports,3finitepooltools and Qwenbindingproposal/
pairedraw-toolfinals. Same78savedobservations,globalrelationmenu, no per-taskAstra
binding/newPUTcalls. CPU19/19PASS,independentreviewPASS,60source/8pools/deps/
4parentinventories frozenbeforecalls. Stableenv replaced vanishedtempvenv before
prepare; parents untouched. Readiness1synthetictool8359>6144STOP,4metadata preserved.
Prospectivelycommitted/audited pre-inferenceengineeringamendment only changed
syntheticreadiness envelope innewnamespace; source/treatment/gates/caps unchanged.
Readiness2READY25metadata/max4748,notuniversalbound. Actualeach-calltokenizer
guards6144/1536/8192. Max24singleattempts;8initial+16pairedfinalslots, no retries/
unknownreset or thirdreadinessadaptation. Detachedrunstarted17:37:27UTC
(00:37Vietnam22Oct),quota53%>15,firstactualcompletionreserved. No efficacy/semantic
result yet. [Runningreport](analysis/v43_concept_identify_20261021/REPORT.md),
[failedreadiness/amendment](analysis/v43_concept_identify_20261021/READINESS_AMENDMENT.md),
[finalreview](analysis/v43_concept_identify_20261021/RUN_APPROVAL_REVIEW.md).


## 11.84 v43 terminal — one complete binding-selection win, registered no-go (2026-10-22)

Complete18/18received,6dependentfinalsblocked across24plannedslots:5valid/3invalid
initials,raw4valid/1invalid/3blocked,tool5valid/3blocked. AllrawJSONparseable/finish
stop;0transport/unknownv43usage. E1/E3/E6conceptunknown violatesconceptenum (relation
unknown allowed); E2raw9evidenceIDs exceeds8. E3RAWcontainscorrectsubsetbinding
butwholestageblocked, no repair/execution/retry. All8cases retained.

Independentcleancontextsemanticreview+parentRAWreview: strictcompleteexecutable
binding+truthfuljudgment successraw1/8(E4),tool2/8(E4/E5),1tool-onlysemanticwin/0
oppositelosses (<2needed),toolvalid5/8not8/8. NO-GOoriginalscientificgate. E2both
correctmismatchreason butcount_ge missing/selectedempty; formatdifference notwin.
E5rawalreadyidentifieslengthbug butdropscorrectsum_le_limitbinding;toolretainsit,
solefullselectionwin. E7rawfalsebug→toolunknown, butunsupportedoutputroles/wrong
equal_setsmeaningremain, notcorrectcontrol. E8bothmistakefirstitemforundefined
firstsuitable, failambiguity. E1missingoccurrencebinding/E6wrongpositiveboundary.
Initialrequiredfacetcoverage3/8RAW(E3/E4/E5),2/8admitted;4/14concreteproposalsare
justifiedexecutableinclE1companionascending,10unknownproposalsseparate.

All8requested3tools;only5initialsadmitted =>15components,126cells53computed/73
unknown,44holdtrue/9false,20contrasts,0componenterrors. Observedrelationagreement
isnotnormativevalidity. Actualraw/toolpacketparityexactexcepttool_feedback;
same78reusedbiasedpriorQwen/sharedrows,0newPUTworkers/no inputdiscovery/assertion
claim. Noper-taskAstrabinding, global17operatorvocabengineeredonseenfixtures;
notopen-vocabularydiscovery/transfer. No automaticmorecalls/schemafix/fill/benchmark.

ActualQwenusage30,639input+2,569output=33,208known tokens,0v43unknown; original
v40unknown remainsseparateuntouched. Scoped66HTTP:18completions+actualmetadata19
+readiness1FAILED4+readiness2READY25. Originalsynthetic8359capfailure preserved;
prospectivelycommitted/auditedpre-inferenceengineeringamendment/readiness2max4748
withoutsource/prompt/schema/cap/gatechanges, no thirdadaptation. Actualmaxinput3111,
run17:37:27–18:03:20UTC21Oct/00:37–01:03Vietnam22Oct,allfinishstop. Dollar/GPUcost
unmeasured. Independentintegrity102checksPASS:60source/8pools/deps/approval/4v40
parentinventories/generation189/terminal290exact. Callbackhandled, noactivejob.
[All8report](analysis/v43_concept_identify_20261021/REPORT.md),
[independentsemantics](analysis/v43_concept_identify_20261021/SEMANTIC_REVIEW.md),
[integrity/costs](analysis/v43_concept_identify_20261021/INTEGRITY_COST_AUDIT.md).

## 11.85 Round novelty trên saved v11_fair dev — NO SIGNAL (2026-10-23, CPU, ref)

Lấy ý từ blog code review của Anthropic (59% chỗ bị flag lặp đã có từ round đầu). Tách mỗi hybrid sample thành
round 1 / round 2. Gate replay khớp final_protocol_v11_dev.json. Redundancy share (R2 tìm lại bug R1 đã thấy):
concept 29%, placebo 44%, plain 48%. r2_new concept vs placebo 39 vs 39 (15/15). Cùng số input R2 (co-primary
quyết định): 35.5 vs 20.5, 16/8, p = .15 → **NO SIGNAL**. Cùng số request nhưng concept chỉ ra 354 verified input R2,
placebo 926. 28/39 r2_new của concept nằm trên task witness-only đã detect; phần vượt tool concept 11 vs placebo 23
(3/10). Tức là concept round 2 chủ yếu tìm lại vùng mà fuzz witness đã có. False alarm R2/call .006/.017/.029.
[Report](analysis/round_novelty_20261023/RESULTS.md), [PREREG + amendment 1](analysis/round_novelty_20261023/PREREG.md).

## 11.86 v51 latent concept oracle (Qwen2.5-Coder-1.5B frozen probes) — NO-GO (2026-10-23, CPU, $0)

Probe hidden state (layer 28, last token) trên (spec, call, observed output). Train trên MBPP+ mutant (mutmut), nhãn
do tool tính. Concept bottleneck dùng 7 discrepancy concept. Eval trên pool v41 VibePass (22 PUT, 17 problem).
MBPP+ validation: direct .626, CBM .627, placebo type-matched .631, nên concept không thêm gì ngay trong phân phối.
VibePass macro AUC: direct .476, CBM .495, placebo .385, verbal .441, surface .496, **intrinsic NLL .650** (direct thua
intrinsic 3/14, p = .013) → **NO-GO**. Cơ chế: wrong output VibePass có 52% NUM_NEAR (số lệch nhỏ) và 0
TYPE/BOOL/SIZE. Probe đọc tốt concept dạng output (≥ .92) nhưng NUM_NEAR chỉ .78; concept top-1 đúng 19%. B − C = .11
chỉ vì placebo rơi dưới chance. Top-3 của mọi arm ≤ chọn ngẫu nhiên (11.7/22); con số surface 16/22 là artifact do
hòa score. Không chạy 7B. [Report](analysis/v51_latent_concept/RESULTS.md),
[PREREG + amendment 1](analysis/v51_latent_concept/PREREG.md).

## 2026-10-24 Sol6.1 native concept probe (separate from v50)

User-requested12clean-context gpt-6.1-sol/low agents,6seen cases×generic/concept.
Same full saved evidence; generic checklist versus global concept cards. Independent
review:6/6versus6/6,0concept-only wins,0false alarms,1justified ambiguous abstention
each. Concept advantage NOT SHOWN; stronger-model capability on this diagnostic,
not controlled Qwen comparison.0Qwen/PUT calls. Read
[full report](analysis/sol61_concept_probe_20261024/REPORT.md).


## 2026-10-26 v78 learned concept selection — NO-GO (CPU, $0 API)

Frozen v47 menus, supervised logistic selector with spec/code context versus context-removed logistic and
training-only kind/subtype priors. Initial pre-label integrity stop revealed33 PUTs but24 specification groups;
prospective amendment and fresh independent review enforce whole-problem holdout/group-balanced training/bootstrap.
Primary context18 vs random18.25, context-removed19, kind prior19.05, subtype prior20.5, perfect23. Secondary
spec-only21 equals context-removed21/subtype21 on every PUT's reach. Primary also uses~10% more distinct inputs
than random; its cost-conditioned random reaches17.57. All primary promotion gates fail. Stop this package;
no tuning/data expansion.11 synthetic tests pass, all historical v47 metrics replay,1743 parent hashes unchanged;
0 API/new program execution,no GPU. Input-exposure reach only,not assertion correctness or CASCADE online efficacy.
[Report](analysis/v78_learned_select/RESULTS.md), [saved data](analysis/v78_learned_select/RESULTS.json),
[prospective protocol/amendments](analysis/v78_learned_select/PREREG.md).

## 2026-10-29 vr8 semantic gate — CPU ready, endpoint blocked

41 CPU tests pass, including native strategy/classification/final scoring with ten
saved reference programs. Selection frozen: 137,148 (ordering),51,98 (membership),
101,54 (normalization). CPU replay of saved round1: old gate covered6/6 tasks;
semantic predicate observed5/6, with task51 the sole uncovered target. Selection
was not changed after this observation. This is a coverage diagnostic, not a bug
score or evidence that vr8 improves generated tests.

The first controller stopped at endpoint preflight; `/models` returned HTTP404.
No new completion attempts, no generated vr8 tests, no efficacy result. The
empty completion ledger permits an explicit retry with the same frozen sources
once the endpoint is restored. No controller remains active.

[Protocol and commands](pipelines/vr8_semanticgate/README.md).

## 2026-10-29 vr8 semantic gate — COMPLETE, no improvement shown

Supersedes preflight404. Six tasks/three arms:ref6/6confirmed,FA0allarms;
round1already6/6. Secondaryo0:5/6allarms,FAold/generic3,semantic2 because fewer
inputs retained. New semantic inputs7each;novelvalidold/generic23vssemantic19.
Onlytask51changes target:correct vowel table makes membership-disagreement
predicate impossible.200valid candidate occurrences rejected,including saved
bug-exposing input confirmed by post-hoc native replay. Applicability/hardfilter
failure,not transport failure or ConceptCoder reproduction.20newphysicalcalls,
53logical,18,108tokens,0unknown;41CPUtests+terminalhash/receipt auditpass.
Noactivejob/automaticexpansion. [Report](pipelines/vr8_semanticgate/completed/REPORT.md).

## 2026-10-29 vr9 applicability/retention — CPU ready, endpoint404

User-authorized repair aftervr8:separate false from statically refuted class
hypothesis;retain novel valid nonhits within existing4input budget. Frozen6tasks,
exact saved strategies/pools/R1/tenrefs.48CPUchecks+12exact control replays pass.
CPUpreviewtask51strict0→retain4/applicable4selected validinputs;total19→24,
generic23. No efficacy claim/newfinalscore.0newcompletions/tokens;controller64941
exitedpreflight404. Resume only authorized diagnostic when endpoint restored.
[Report](pipelines/vr9_applicability/readiness/REPORT.md).
