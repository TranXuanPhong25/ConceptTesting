# Kế hoạch: so sánh với SymPrompt, MuTAP, ACH (Meta), CoverUp và thêm held-out VibePass

Cập nhật 2026-10-13. Theo yêu cầu của người dùng ("so sánh với SymPrompt, MuTAP, mutation-guided test generation ở Meta, CoverUp; thêm tập test VibePass… lên kế hoạch làm luôn").

## 1. Nguyên tắc so sánh công bằng
- **Cùng setting TrickCatcher:** input của mọi cách là spec (docstring), code PUT và base test. Output là assertion. Mọi cách chạy trên cùng các task, cùng model (Qwen2.5-Coder-7B, cùng endpoint) và cùng K = 3.
- **Cùng oracle:** bỏ expected output do từng cách tự viết, chấm mọi input bằng ref (10 chương trình viết từ spec, prompt DPP) và full. Như vậy chỉ so phần **chọn input**, đúng chỗ nghẽn mà VibePass chỉ ra. Báo thêm o0 (expected output của chính cách đó) làm số phụ.
- **Cùng ngân sách:** giới hạn số lần gọi LLM mỗi sample và số test mỗi sample bằng nhau. Báo cả kết quả thô lẫn kết quả **so cùng số test**.
- **Metric:**
  - Chính: bug/run (ref) và so từng task bằng sign test.
  - Phụ: D_I (input lộ bug), false alarm, % run báo lỗi chương trình đúng, số lần gọi LLM và token.
- **Method của mình:** cấu hình concept tốt nhất đã chốt trên dev, round 2 kiểu Hypothesis, strict (không có test LLM tự thêm). Kèm hai control: không concept (cùng số lần gọi) và concept giả.
- **Thứ tự tập:** dev (113 task HumanEval) trước để dựng và kiểm baseline. Sau đó chạy **một lần** trên held-out: VibePass (66 PUT LeetCode) và MBPP+ (12 bug thật), không chỉnh gì thêm.

## 2. Baseline
Mỗi paper một folder riêng (`baselines/<tên>/`, AGENTS rule 4). Code gốc của tác giả giữ nguyên trong `vendor/` (rule 3). Hai baseline chưa có code công khai phải **cài lại từ mô tả trong paper**; việc này người dùng đã yêu cầu (rule 2), và sẽ ghi rõ là "reimplementation, adapted".

| Baseline | Ý chính | Code gốc | Cách đưa vào setting TrickCatcher |
|---|---|---|---|
| **CoverUp** (Pizzorno & Berger, FSE 2025) | Lặp lại: đưa đoạn code chưa cover cho LLM, LLM viết test, đo coverage lại | Có (đã dùng trong `CoverUp_concept/`) | Dùng prompt và vòng lặp gốc, chạy với Qwen qua endpoint; coverage bắt đầu từ base test. Lưu ý: base test thường đã cover gần hết code, nên CoverUp có thể dừng sớm. Đây là kết quả cần báo, đúng điểm yếu của "coverage". |
| **MuTAP** (Dakhel et al., IST 2024) | Đưa mutant còn sống (test hiện có không phát hiện được) vào prompt, bắt LLM viết test giết nó; lặp qua từng mutant | Có (ExpertiseModel/MuTAP, cần xác nhận khi tải) | Dùng prompt gốc. Mutant lấy bằng mutmut, như paper. Test hiện có = base test. Ngân sách: tối đa N mutant mỗi task. |
| **SymPrompt** (Ryan et al., FSE 2024) | Gom path constraint (điều kiện nhánh trên từng path) từ AST, mỗi path một prompt | Chưa thấy artifact → **cài lại** | Cài lại phần thu path và tỉa path theo mô tả trong paper; prompt theo mẫu trong paper. Mỗi task tối đa P path. |
| **ACH** (Foster, Harman et al., FSE 2025 industry) | Mô tả "concern" → LLM sinh mutant theo concern → bỏ mutant tương đương → LLM viết test giết mutant | Không có (hệ thống nội bộ Meta, Kotlin) → **cài lại** | Concern = spec của hàm ("lỗi làm hàm sai spec"). LLM sinh k mutant, lọc tương đương bằng LLM như paper, rồi viết test giết mutant. |

Ngoài ra vẫn giữ các baseline đã có: TrickCatcher (đầy đủ), EvalAndMitigate (onlydoc, advdoc), plain, toolinput.

## 3. Held-out VibePass
- **Nguồn:** VibePass (CC-BY-4.0) + LiveCodeBench, chỉ bài LeetCode, 66 PUT strict trên 24 câu hỏi (RESULTS §11.31).
- **Ghép vào setting:** public test → base `check()`, silver → đáp án, `test_checker` → contract, private test + input sinh hợp lệ → chấm.
- **Dựng format:** entry là method của `class Solution`, bọc thành hàm `f(*a) = Solution().method(*deepcopy(a))`, spec là `question_content`.
- **Cần kiểm:**
  - tracer, fact, mutant chạy được trên method trong class;
  - từng PUT qua base `check()`;
  - silver qua `check()`;
  - mỗi PUT có ít nhất 1 input private làm khác silver.
- **Thống kê:** gom theo câu hỏi (nhiều PUT trên cùng một câu hỏi), báo riêng, không gộp với MBPP+.

## 4. Các bước và thứ tự

| # | Việc | Ai làm | Cần GPU | Ra cái gì |
|---|---|---|---|---|
| 1 | Dựng dataset VibePass theo format held-out, kiểm từng PUT | Codex | Không | `heldout/` thêm nguồn VibePass, `out/heldout_vibepass/he/` |
| 2 | CoverUp và MuTAP từ code gốc, đổi sang Qwen và setting này | Codex | Không (dry run với fake client) | `baselines/coverup/`, `baselines/mutap/` |
| 3 | SymPrompt và ACH cài lại theo paper | Subagent | Không (dry run) | `baselines/symprompt/`, `baselines/ach/` |
| 4 | Đăng ký PREREG: cấu hình chốt, ngân sách, metric, so sánh chính | Mình | – | Mục "Baselines + VibePass" trong PREREG |
| 5 | Chạy 4 baseline trên dev, chấm ref/full chung | Mình | Có | RESULTS: bảng so với concept |
| 6 | Chạy một lần trên held-out VibePass + MBPP+ 12: concept, không concept, toolinput, 4 baseline | Mình | Có | RESULTS: kết quả held-out |

So sánh chính trên held-out (đăng ký trước):
- concept-hybrid vs từng baseline, và vs không concept (cùng số lần gọi): bug/run (ref) và so từng task, gom theo câu hỏi với VibePass.
- Phụ: so cùng số test, D_I.
