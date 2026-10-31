Data flow, multi function linking/deps concept  
A.4: fewshot-coT concept Q\&A is worse   
Can thiep vao concept luc inference  
Vì sao thành công (phân tích của tôi)  
1\. Giám sát dày: mỗi hàm có (số câu × 7–8) nhãn thay cho 1 bit, bù cho dữ liệu VD vừa ít vừa nhiễu.  
2\. Nhãn rẻ và chính xác vì do công cụ tính.  
3\. Nút thắt concept làm model ít dựa vào tên biến/API, nên độ bền tăng mạnh nhất.  
4\. Concept khớp lớp lỗi: cải thiện lớn nhất ở bộ concept (+5.8), nhỏ hơn ở general (+3.4) và BP (+1.2).  
5\. Baseline yếu: model nhỏ và SFT cho VD vốn kém, nên còn nhiều chỗ để cải thiện.  
6\. Một phần lớn là hiệu ứng hình thức giám sát (kết quả NVC). Placebo k1 của repo: nhãn bị hoán vị làm model sụp (AUROC .64 so với .86). Câu hỏi "conc

 Thiết kế concept  
   \- VD: 7 concept rút ra từ 4 loại lỗi (memory leak, use-after-free, buffer overflow, null deref): null assignment, null check, pointer deref, memory allocation, buffer access, bounds check, memory free. Nhãn gán bằng phân tích tĩnh; một câu lệnh có thể mang nhiều nhãn.  
   \- Dự đoán nhánh (BP): 12 giá trị trừu tượng lấy từ execution trace (TRACED, CodeNet). Gồm True/False; Zero; Positive/Negative regular (trị tuyệt đối 1..1000); Positive/Negative large; NULL/Not NULL; Alphabetic/Non-alphabetic; Initialized. Model không học được giá trị cụ thể, nhưng học được giá trị đã lượng tử hoá.

- **Giữ quan hệ giữa các statement: hiện tại các statement đang còn rời rạc, LLM chỉ chú ý đến 1 dòng mà không biết các call graph xung quanh ra sao**  
- **Dạy concept nên làm gì khi gặp cái này:** Retrieve ví dụ có cấu trúc tương tự: cách dựng input, đường đi đạt được và test tương ứng. Thử cặp ví dụ đúng/sai, thay vì chỉ ví dụ nhận diện concept. Đây là đề xuất chuyển contrastive prompting sang test generation. (dạng như kite)  
- Harness \+ feedback  
- Khi ghép data dependence với control dependence, ta có **Program Dependence Graph — PDG**. Joern dùng **Code Property Graph — CPG** để chứa nhiều lớp quan hệ: AST, CFG, reference, call và dependency. Specification có cạnh `REACHING_DEF` và `CDG` cho hai loại dependency này. [CPG specification](https://cpg.joern.io/#pdg).  
- Với hướng sinh test của bạn, mình thấy phép dùng hữu ích là **backward slicing**: bắt đầu từ statement muốn kiểm tra, lần ngược các cạnh để lấy những phép gán, điều kiện và lời gọi ảnh hưởng tới nó. Như vậy mình lấy được một cụm code có quan hệ cụ thể để suy ra input cần thiết.  https\://codeql.github.com/docs/writing-codeql-queries/about-data-flow-analysis/  
- Incremental seen-bug: [https\://arxiv.org/pdf/2510.04618](https://arxiv.org/pdf/2510.04618), [https\://arxiv.org/abs/2508.00271](https://arxiv.org/abs/2508.00271), HindSight

|  |  |  |
| ----- | ----- | ----- |
| **Generative concept bottleneck** | Một lớp concept tham gia trực tiếp vào dự đoán token | CB‑LLMs có mô hình cho text generation và can thiệp concept để điều khiển output. Đây là hướng trực tiếp nhất với câu hỏi của bạn. [CB‑LLMs, ICLR 2025](https://arxiv.org/html/2412.07992v2), [code](https://github.com/Trustworthy-ML-Lab/CB-LLMs) |
| **Encoder cho cấu trúc code/concept** | Graph hoặc vector theo statement được mã hoá và kết hợp với representation của code | GraphCodeBERT là tiền lệ đưa data flow vào biểu diễn code. Thiết kế generator sinh test từ concept graph cần huấn luyện và đánh giá mới. [GraphCodeBERT](https://arxiv.org/abs/2009.08366) |

concept chọn phép biến đổi input, strategy của property-based testing, solver hoặc công cụ cần gọi. Hướng này không đưa concept vào hidden state; nó dùng concept để thay đổi quá trình tìm test.

– hướng dẫn bằng concept trong promtp x

\- ép model sinh theo concept 

\- model sinh genẻatỏ 

Điểm t thấy quan trọng nhất: Có thể phân biệt ba loại concept:

* Input concepts: null, empty, boundary, duplicate, overflow...  
* Behavioral concepts: invariant, monotonicity, idempotence, state transition...  
* Fault-revealing concepts: equality sensitivity, order sensitivity, state dependence, precision sensitivity...

Muốn kiểm tra hành vi, tính chất hay loại lỗi nào?

Input generation

Input nào có khả năng bộc lộ hành vi hoặc lỗi đó?

Test oracle

Làm thế nào xác định kết quả đúng?

Reference solution: Đáng tin cậy hơn khi có lời giải đã được xác minh.

Property/Metamorphic oracle: Không cần biết chính xác output, chỉ cần kiểm tra các thuộc tính bắt buộc.

Static Analyzer Rule Corpus → Cross-Language Bug Concepts → Applicable Input Constraints → LLM Test Generation → Execution Validation. [chatgpt](https://chatgpt.com/c/6aca66e0-624c-83ec-91e6-17fee228a8da)

concept: Boundary Violation

applicability:

  \- Collection indexing or traversal

  \- Boundary-dependent condition

triggers:

  \- size \== 0

  \- size \== 1

  \- index \== size \- 1

  \- index \== size

generation:

  \- Infer applicable input parameters

  \- Satisfy reachability constraints

  \- Construct concrete boundary inputs

validation:

  \- Check input preconditions

  \- Validate with specification or differential oracle

Trong đó cần chứng minh được rằng bước applicability matching và trigger instantiation sinh ra những input mà LLM thông thường bỏ sót.

## 2\. Nhưng phải chú ý tính mới

Có hai nghiên cứu khá sát:

* [Mutation-Guided LLM-based Test Generation at Meta](https://arxiv.org/abs/2501.12862): dùng LLM tạo test nhằm kill những mutant mô phỏng lỗi thuộc nhóm quan tâm.  
   ![]()  
  arXiv  
* [MUTGEN (2026)](https://arxiv.org/abs/2506.02954): đưa mutation feedback vào prompt, lặp quá trình test generation để cải thiện mutation score.  
   ![]()  
  University of Limerick

Do đó, chỉ bổ sung concept vào mutation-guided prompt chưa chắc đủ mới.

Hướng có tiềm năng hơn là xây dựng taxonomy của các điều kiện phân biệt hành vi (behavioral divergence conditions), rồi dùng nó làm tầng suy luận trung gian giữa mutant và input generation.

Có thể dựa trên mô hình RIP:

Reach

Chạy tới mutation

Infect

Tạo state khác biệt

Propagate

Khác biệt quan sát được

Một input chỉ đạt Reach hoặc Infect chưa chắc kill được mutant. Khác biệt phải lan tới hành vi có thể kiểm chứng.

Chỗ nào áp dụng seảch/beam search 

Xếp hạng concept \= rẻanking, ML?

1. **Có ý nghĩa vượt khỏi một example.** Nó mô tả một lớp hành vi hoặc quan hệ, không chỉ một mutant diff hay input.  
2. **Có điều kiện áp dụng rõ.** Tại sao relation đúng theo spec? Những trường hợp nào không áp dụng? PUT có biểu hiện như vậy không đủ chứng minh spec yêu cầu như vậy.  
3. **Dẫn đến một test obligation cụ thể.** Đọc concept xong phải biết cần thay đổi gì, giữ nguyên gì, quan sát gì.  
4. **Có thể kiểm tra tác dụng.** Bỏ hoặc thay concept thì test được sinh có thay đổi đúng theo ý nghĩa dự đoán không?

Mình tìm được các benchmark phù hợp với hướng LLM-based Test Generation có đánh giá cả bug detection và test oracle correctness.

Điểm quan trọng là nên ưu tiên benchmark có ba thành phần:

1. Buggy version — chương trình chứa lỗi đã biết.  
2. Fixed/correct version — chương trình được dùng làm tham chiếu hành vi đúng.  
3. Existing tests — bộ test hiện có, để đo coverage và xác định những lỗi chưa được phát hiện.

Có thể chạy test do LLM sinh trên cả hai phiên bản để kiểm tra nó có thực sự phát hiện lỗi, thay vì chỉ tạo ra một assertion thất bại.

## **1\. Các benchmark đáng sử dụng**

| Benchmark | Ngôn ngữ | Loại lỗi | Buggy/fixed | Mức phù hợp |
| ----- | ----- | ----- | ----- | ----- |
| [Defects4J](https://github.com/rjust/defects4j) | Java | Real bugs | Có | Rất cao |
| [BugsInPy](https://github.com/soarsmu/BugsInPy) | Python | Real bugs | Có | Rất cao |
| [QuixBugs](https://github.com/jkoppel/QuixBugs) | Python, Java | Algorithmic bugs | Có | Cao, dễ thử nghiệm |
| [TestGenEval](https://testgeneval.github.io/index.html) | Python | Real-world test generation | Không phải trọng tâm chính | Bổ trợ |

Defects4J nổi bật vì mỗi bug có phiên bản `b` (buggy), `f` (fixed) và triggering test đã được kiểm chứng. Framework cũng cung cấp sẵn công cụ đo coverage, mutation score và real fault detection rate.

![]()  
GitHub  
\+1

BugsInPy là lựa chọn tương đương cho Python, hỗ trợ checkout hai phiên bản, chạy test, coverage, mutation và fuzzing.

![]()  
GitHub  
\+1

QuixBugs có 40 chương trình thuật toán với phiên bản lỗi và phiên bản đúng, đặc biệt thuận tiện để thử nghiệm một pipeline sinh input và oracle ở mức hàm.

![]()  
QuixBugs  
\+1

## **2\. PBT-Bench — phù hợp nhất với hướng concept-guided test generation**

NeurIPS 2026 · Python · Property-Based Testing

[Website](https://pbtbench.com/) · [GitHub](https://github.com/ElliotXinqiWang/PBTbench) · [Paper](https://arxiv.org/abs/2605.15229)

# **365**

Injected bugs

# **100**

Problems

# **40**

Libraries

PBT-Bench được thiết kế để đánh giá khả năng LLM suy ra các semantic invariants từ API documentation, sau đó sinh input bằng Hypothesis để kích hoạt bug.

Đặc biệt:

* Các bug được tiêm vào thư viện Python thực tế.  
* Bug vượt qua existing unit tests.  
* Agent không được cung cấp thông tin về bug.  
* Test được đánh giá bằng tiêu chí Fail-to-Pass (F→P): FAIL trên buggy và PASS trên fixed.  
* Có phân loại độ khó từ boundary bugs đến stateful protocol violations.

Điều này rất gần hướng bạn đang nghiên cứu: hướng dẫn model tìm vùng input chưa được khám phá thông qua các concept.

![]()  
arXiv  
\+2

Khác biệt quan trọng: PBT-Bench dùng semantic properties từ documentation để hướng dẫn tìm bug; còn hướng của bạn có thể dùng coverage gaps, branch conditions, data-flow patterns và test-trigger concepts.

## **3\. Defects4J — phù hợp nhất để chứng minh hiệu quả trên real bugs**

Defects4J không chỉ cung cấp dữ liệu. Nó còn có công cụ chính thức `run_bug_detection`, thực hiện đúng kiểu đánh giá mà bạn đang tìm:

Quy trình kiểm thử hai phiên bản

Generated test suite

Buggy

FAIL

Fixed

PASS

Bug-revealing test

Ứng viên phát hiện đúng lỗi mục tiêu

Tool này kiểm tra test suite trên phiên bản được dùng để sinh test, chạy tiếp trên phiên bản đối diện và xác định các triggering tests.

![]()  
Defects4j  
\+1

Nếu muốn nghiên cứu incremental test generation, bạn có thể lấy existing tests làm đầu vào, tính branch coverage, sinh test bổ sung và đo số real bugs mới được phát hiện.

## **4\. Hai paper đáng đọc thêm về oracle và false positives**

[RTED — Reflective Unit Test Generation for Precise Type Error Detection](https://arxiv.org/abs/2507.02318)

RTED sử dụng type constraints và reflective validation để giảm false positives khi sinh test cho Python. Được đánh giá trên BugsInPy và TypeBugs, với mục tiêu vừa phát hiện lỗi vừa cải thiện precision.

![]()  
arXiv  
ASE 2025

[UTBoost — Rigorous Evaluation of Coding Agents on SWE-Bench](https://aclanthology.org/2025.acl-long.189/)

UTBoost dùng LLM sinh thêm unit tests để phát hiện các patch sai mà existing tests bỏ sót. Paper xác định 36 task có test chưa đầy đủ và phát hiện 345 erroneous patches trước đó bị đánh giá nhầm là pass.

![]()  
ACL Anthology  
ACL 2025

## **5\. Đề xuất bộ benchmark cho nghiên cứu của bạn**

Mình nghiêng về thiết kế ba tầng đánh giá:

| Tầng | Benchmark | Cần đo |
| ----- | ----- | ----- |
| Proof of concept | QuixBugs | Concept có giúp tìm input phân biệt buggy/correct? |
| Main experiment | BugsInPy hoặc Defects4J | Có tăng real bug detection mà không tăng oracle errors? |
| Generalization | PBT-Bench | Concept có giúp suy ra property và trigger input khó? |

Các metric nên tách riêng:

* Branch Coverage Gain: mức tăng coverage so với existing tests.  
* Bug Recall: tỷ lệ lỗi thực tế được phát hiện bởi ít nhất một test hợp lệ.  
* Oracle Validity: tỷ lệ test có assertion hợp lệ, được đánh giá bằng reference hoặc property độc lập.  
* False Alarm Rate: tỷ lệ test báo lỗi trên fixed version đã kiểm chứng, sau khi xử lý flaky tests và các lỗi ngoài phạm vi.  
* Cost per Detected Bug: số token, thời gian hoặc số lần gọi model cho mỗi bug được phát hiện.

Một lưu ý về thiết kế thí nghiệm: Fail-to-Pass đánh giá đồng thời khả năng kích hoạt lỗi và tính đúng đắn của oracle, nhưng không tách riêng được hai yếu tố đó.

Nếu muốn đóng góp nghiên cứu về concept-guided generation, nên đánh giá cả input lẫn assertion:

\\\[ \\begin{aligned} InputEffectiveness &= P(\\text{input reveals behavioral difference})\\\\ OracleCorrectness &= P(\\text{expected output is valid})\\\\ BugDetection &= P(\\text{FAIL buggy, PASS fixed}) \\end{aligned} \\\]

Ở metric đầu, chỉ so sánh đầu ra buggy/fixed có thể bỏ sót khác biệt side effects hoặc exceptions, nên cần định nghĩa quan sát hành vi rõ ràng.

Kết luận: Nếu muốn bắt đầu với Python, mình đề xuất BugsInPy \+ PBT-Bench. BugsInPy là benchmark real bugs để chứng minh kết quả thực tế; PBT-Bench là benchmark synthetic semantic bugs rất sát với ý tưởng concept-guided input generation.

Để tránh data leakage, hãy chỉ cung cấp buggy code và những tài liệu được phép cho model. Fixed code, bug patch và ground-truth tests phải được giữ riêng trong evaluator.

bởi vì

bản chất llm

nó sinh ra không phải để sinh test

không phải để trả lời câu hỏi

nó sinh ra với mục tiêu khác

nên là chính là mình phải trả lời được câu hỏi

điểm giao giữa bài toán và llm là gì

nó phải có điểm giao

RQ: điểm giao, mối liên hệ giữa concept và LLM, testing

bài toán là gì

cơ sở

các thành phần liên quan

có đo lường được không

vì sao dùng cách đo đó

và precision được báo riêng cạnh số bug. Nhờ vậy một arm không thể "thắng" chỉ nhờ sinh thật nhiều test rồi kéo theo nhiều false al  
Program Variant Generation: LLM tạo các phiên bản chương trình khác dựa trên code gốc và specification.  
Generator-Based Input Generation: LLM viết chương trình sinh test input, thay vì trực tiếp sinh từng input.  
Diversity-Driven Differential Testing: Chạy cùng input trên chương trình gốc và các biến thể, tìm output khác biệt để phát hiện bug.

khác với majority voting thông thường, TrickCatcher chỉ bỏ phiếu giữa các output khác output của chương trình gốc. Đây là điểm mới trong cách xây dựng test oracle

### **2\. Thêm specification vào cùng buggy code là chưa đủ**

### Tác giả so sánh bốn cách cung cấp context, trong đó:

* ### Chỉ buggy code.

* ### Chỉ specification được LLM sinh.

* ### Cả buggy code và specification.

* ### Không có cả hai.

### Kết quả là chỉ dùng specification tốt hơn việc để cả specification và buggy implementation trong prompt.

### Điều này gợi ý rằng dù đã có mô tả hành vi đúng, implementation lỗi vẫn có thể ảnh hưởng đến cách LLM suy luận oracle.

### **5\. Chất lượng docstring ảnh hưởng trực tiếp đến chất lượng test**

* Feedback có tác dụng rõ ràng, ngay cả khi chỉ yêu cầu model tạo test khác trước. Điều này tạo cơ sở để thử feedback có cấu trúc từ surviving mutants hoặc uncovered branches.  
* Coverage và mutation score chỉ là proxy. Nếu mục tiêu nghiên cứu là phát hiện real bugs, cần đánh giá thêm bằng buggy/fixed versions với oracle độc lập.  
* ULT có thể phù hợp để đánh giá khả năng khám phá input phức tạp, nhưng không phải benchmark chuyên biệt cho real-bug detection.

Một RQ đáng thử là: Does mutation-guided concept selection improve real-fault detection beyond the gains achieved by iterative feedback alone?

RQ này kiểm tra được liệu concept thực sự mang lại thông tin hữu ích, hay kết quả cải thiện chỉ đến từ việc cho model sinh thêm test và nhận feedback.

việc cung cấp thông tin về những gì test hiện tại đã kiểm tra có tác động rất lớn tới khả năng tìm ra trường hợp bị bỏ sót

### **Prompt của paper có gì đặc biệt?**

Agent1 yêu cầu model thực hiện ba thao tác:

1. Phân tích base tests để xác định blind spots trên các input hợp lệ.  
2. Thiết kế một mutation nhỏ để khai thác blind spot.  
3. Tự mô phỏng mutant trên từng base test, trước khi trả về code.

Agent2 sử dụng cấu trúc chặt hơn: mô tả chức năng, phân tích test coverage, liệt kê 2–3 blind spots, lập mutation plan và trace từng test.

Một phát hiện thú vị là Agent1 với reasoning tự do thường hiệu quả hơn Agent2 với template cố định. Việc bắt LLM phân tích quá nhiều mục chưa chắc giúp sinh mutant tốt hơn.

Thông thường:

* Rule-based: Đổi toán tử theo quy tắc cố định.  
* LLM Test-Blind: Đọc code rồi tự tạo bug.  
* LLM Test-Aware: Đọc code \+ specification \+ existing tests, tìm blind spots rồi tạo bug khai thác đúng những blind spots đó.

Hướng tiếp cận:

1. Constraint Mining: Dùng LLM trích xuất các ràng buộc nghiệp vụ từ OpenAPI Specification.  
2. Observation–Confirmation: Dùng LLM phân tích và xác nhận các ràng buộc để giảm hallucination.  
3. Test Oracle Generation: Chuyển ràng buộc thành code Python kiểm tra response.  
4. Semantic Verification: Kiểm tra oracle bằng các response example hợp lệ để loại bỏ oracle sai.

Điểm mới: Khai thác ràng buộc từ tài liệu API để sinh oracle kiểm tra logic nghiệp vụ, thay vì chỉ kiểm tra status code và schema.

Lưu ý: RBCTest tập trung vào sinh assertion/oracle, không phải tối ưu sinh test input để phát hiện bug.

[FailMapper: Automated Generation of Unit Tests Guided by Failure Scenarios](https://doi.org/10.1109/ASE63991.2025.00197)

Ruiqi Dong et al. · ASE 2025 · Có mã nguồn công khai

Paper này đặt ra một vấn đề gần như trùng với động cơ nghiên cứu của bạn:

Số lượng bug types rất lớn, nên việc hướng dẫn LLM theo từng loại bug khó mở rộng. Thay vào đó, tác giả tổng quát hóa thành 9 failure scenarios và thiết kế các chiến lược sinh test tương ứng.

Phương pháp sử dụng Monte Carlo Tree Search (MCTS) để khám phá những tình huống có khả năng làm chương trình thất bại.

![]()  
Monash University

Kết quả do tác giả báo cáo:

* Phát hiện 40/50 bug trên tập con Defects4J, trong khi baseline tốt nhất phát hiện 12/50.  
* Phát hiện 12/20 bug từ GitBug-Java và Bears.  
* Phát hiện 14 lỗi được xác nhận trong hai dự án Apache.

Đây là các kết quả từ những tập đánh giá cụ thể, không nên suy rộng thành tỷ lệ phát hiện lỗi trên mọi chương trình.

Mã nguồn, gồm bản Java và Python prototype

GitHub

Repository hiện có phân tích AST, các nhóm logical-bug patterns, mô hình failure và vòng lặp sinh–chạy–đánh giá test.

![]()  
GitHub

So với hướng của bạn: FailMapper tổng quát hóa từ biểu hiện thất bại (failure manifestation), còn bạn muốn tổng quát hóa từ nguyên nhân tiềm ẩn (bug mechanism) thành các điều kiện đầu vào.

Đây là khác biệt có ý nghĩa, nhưng bạn cần chứng minh taxonomy của mình tạo ra khả năng phát hiện lỗi tốt hơn failure scenarios sẵn có.

## **KTester (ICSE 2026\) — Testing Knowledge → Test Design**

[Knowledge Matters: Injecting Project and Testing Knowledge into LLM-based Unit Test Generation](https://arxiv.org/html/2511.14224)

KTester phân tách hai bước: thiết kế test scenario và sinh mã kiểm thử.

Nó bổ sung project knowledge từ static analysis, đồng thời hướng dẫn LLM sử dụng các nguyên tắc kiểm thử như boundary analysis, control flow và exception handling. Các scenario được biểu diễn trung gian dưới dạng JSON trước khi chuyển thành test code.

![]()  
arXiv

Điểm khác biệt: KTester dựa vào testing heuristics, không xây dựng một taxonomy từ các quy tắc phát hiện bug của SpotBugs/CodeQL.

[GitHub KTester](https://github.com/SYSUSELab/KTester) — đã công khai source, template, phần trích xuất project knowledge và evaluation scripts.

![]()  
GitHub

Hướng: Lấy hành vi phiên bản hiện tại làm đáp án (regression oracle)  
Paper: DCAware: chỉ ra rằng để LLM tự sửa lặp nhiều vòng thì assert ngày càng dễ pass nhưng kém bắt lỗi ("Self-Repair  
Trap"). Thay vào đó cung cấp ngữ cảnh tĩnh và giá trị lúc chạy.  
Venue: ASE 26  
Ngôn ngữ / dữ liệu: Java, Defects4J  
Có cần train không: Không  
────────────────────────────────────────  
Hướng: Suy ra từ tài liệu hoặc đặc tả, không nhìn code  
Paper: AugmenTest  
Venue: ICST 25  
Ngôn ngữ / dữ liệu: Java, 142 lớp có mutant  
Có cần train không: Không  
────────────────────────────────────────  
Hướng:  
Paper: ChatAssert: dùng thêm tool bên ngoài để sửa assert  
Venue: TSE 25  
Ngôn ngữ / dữ liệu: Java  
Có cần train không: Không  
────────────────────────────────────────  
Hướng:  
Paper: From Business Requirements to Test Assertions  
Venue: arXiv 26  
Ngôn ngữ / dữ liệu: Java, 10 bug Defects4J Lang  
Có cần train không: Không  
────────────────────────────────────────  
Hướng:  
Paper: Doc2OracLL, Tratto  
Venue: FSE 25  
Ngôn ngữ / dữ liệu: Java  
Có cần train không: Có, loại  
────────────────────────────────────────  
Hướng: Nhiều agent đưa ra đáp án rồi chọn  
Paper: AssertMate: dùng sinh code, RAG, CoT, rồi LLM làm giám khảo chọn  
Venue: arXiv 26  
Ngôn ngữ / dữ liệu: Java, Defects4J  
Có cần train không: Không  
────────────────────────────────────────  
Hướng:  
Paper: Nexus: 4 agent tranh luận, chạy thử trên một bản cài đặt ứng viên rồi tự sửa  
Venue: arXiv 25  
Ngôn ngữ / dữ liệu: Python (HumanEval, MBPP, LiveCodeBench, ULT)  
Có cần train không: Không, nhưng chưa có code  
────────────────────────────────────────  
Hướng: Lọc bỏ assert sai  
Paper: DeCon: LLM sinh hậu điều kiện để loại assert sai. Họ đo được hơn 62% assert do LLM sinh trên HumanEval là sai.  
Venue: arXiv 25  
Ngôn ngữ / dữ liệu: Python  
Có cần train không: Không  
────────────────────────────────────────  
Hướng: So nhiều bản cài đặt với nhau  
Paper: TrickCatcher (đã dùng), DiffTrust (đo độ không nhất quán giữa các bản)  
Venue: AAAI 26  
Ngôn ngữ / dữ liệu: Python  
Có cần train không: Không  
────────────────────────────────────────  
Hướng:  
Paper: Auditing Feedback-Driven Evolution: lấy 1 chương trình làm đáp án thì output khớp với nhóm 3 bản đúng chỉ  
27.8–50.1%, và độ cải thiện báo cáo bị thổi phồng 9–15 điểm  
Venue: arXiv 26  
Ngôn ngữ / dữ liệu: Python, CodeContests  
Có cần train không: Không  
────────────────────────────────────────  
Hướng: Assert tính chất thay vì giá trị chính xác  
Paper: PBT-Bench, ContractEval  
Venue: NeurIPS 26, ACL 25  
Ngôn ngữ / dữ liệu: Python  
Có cần train không: Không  
────────────────────────────────────────  
Hướng: Đoán trực tiếp test pass hay fail  
Paper: FOCAL  
Venue: arXiv 26  
Ngôn ngữ / dữ liệu: —  
Có cần train không: Có, loại  
────────────────────────────────────────  
Hướng: Tổng quan  
Paper: LLM-Based Test Oracles: Source-of-Authority Taxonomy, 83 study  
Venue: IEEE Access  
Ngôn ngữ / dữ liệu: —  
Có cần train không: —

## **1\. Các paper sử dụng Python**

| Paper | Venue | Ground truth bug | Bản lỗi vượt qua test sẵn có | Đánh giá FP tự động |
| ----- | ----- | ----- | ----- | ----- |
| PBT-Bench | NeurIPS 2026 | 365 bug tiêm, có bản fix | ✓ | ✓ |
| RTED | ASE 2025 | BugsInPy, TypeBugs | ✓ | ✓ (Precision) |
| UTBoost | ACL 2025 | Patch sai so với gold patch | ✓ | ✓ |
| PatchDiff | ICSE 2026 | Patch của agent so với gold patch | ✓ | Một phần |
| AssertFlip, Issue2Test | ICSE 2026 | SWT-bench: test fail trên bản lỗi, pass trên bản fix | ✓ | Ngầm định |
| TestPrune, iCoRe | FSE 2026 | SWE-bench, SWT-bench | ✓ | Ngầm định |
| PROBE | Findings ACL 2026 | Bug được developer xác nhận \+ mutant | ✓ | Chưa rõ |

## **2\. Các paper peer-reviewed trên ngôn ngữ khác (8 paper)**

| Paper | Venue | Ngôn ngữ |
| ----- | ----- | ----- |
| EvalAndMitigate | ISSTA 2026 | Java |
| Coverage/Mutation-vs-effectiveness | ISSTA 2026 | Java |
| DCAware | ASE 2026 | Java |
| CASCADE | FSE 2026 | Java |
| MR-Coupler | FSE 2026 | Java |
| LLMutantKiller | ISSTA 2026 | JavaScript |
| Cleverest | FSE 2025 | C |
| TC-Bench | ICLR 2026 | C++ |

LLM thường bỏ sót tổ hợp boundary conditions và lựa chọn input range không phù hợp.

## **4\. Metamorphic Testing có thể đóng góp gì?**

Có một chỗ paper này vẫn hữu ích cho bạn: oracle generation.

Concept có thể được dùng cho hai mục đích khác nhau:

1. Input-trigger concept: Giúp tạo test đi vào nhánh chưa được phủ.  
2. Behavioral/metamorphic concept: Giúp xác định quan hệ đầu ra cần được duy trì khi thay đổi input.

## **4\. Liên hệ với hướng Concept-Guided Test Generation**

Đây là phần mình thấy có giá trị nhất đối với nghiên cứu của bạn.

Hiện tại, nếu dùng concept cố định trong prompt, LLM phải tự quyết định cách áp dụng concept, nhưng không có cơ chế học xem concept nào thực sự hữu ích đối với từng loại lỗi.

CASCADE gợi ý một thiết kế khác:

Đề xuất: Concept-Aware Case Retrieval

1. Phân tích hàm và mutant, trích xuất đặc trưng như mutation operator, biểu thức điều kiện, kiểu dữ liệu và control flow.  
2. Truy xuất những case có concept và chiến lược kiểm thử đã thành công trước đó.  
3. LLM sử dụng case để đề xuất input và assertions.  
4. Chạy test trên chương trình gốc và mutant, ghi nhận kết quả.  
5. Cập nhật retriever dựa trên khả năng sinh test hợp lệ và kill mutant.

Ví dụ một case có thể lưu:

{  
  "mutation": "GT\_TO\_GTE",  
  "condition": "x \> 10",  
  "concept": "boundary\_value\_analysis",  
  "input": {"x": 10},  
  "expected": "low",  
  "original\_pass": true,  
  "mutant\_killed": true  
}

Đây là ví dụ giả định, trong đó specification xác định `x = 10` phải trả về `"low"`.

Thay vì chỉ lưu `concept = boundary_value_analysis`, chúng ta lưu điều kiện áp dụng, input, oracle và kết quả thực tế.

Sau một thời gian, retriever có thể học rằng boundary value analysis thường có ích với relational operator mutation, nhưng chưa chắc hữu ích với những mutation liên quan đến trạng thái hay thứ tự thực thi.

Đặc biệt, có thể dùng một reward như:

$r=1[validtest\wedge passoriginal\wedge killmutant]$

Điểm cần lưu ý: với các mutant tương đương, không tồn tại test nào kill được bằng cách quan sát hành vi. Ngoài ra, việc lấy output của chương trình gốc làm oracle chỉ phục vụ differential mutation testing, không chứng minh chương trình gốc đúng specification.

### **Có một liên hệ trực tiếp với software testing**

Tác giả chính của CASCADE, Siyuan Guo, cũng tham gia nghiên cứu trước đó:

[Optimizing Case-Based Reasoning System for Functional Test Script Generation with Large Language Models (KDD 2025\)](https://arxiv.org/abs/2503.20576)

Công trình này ứng dụng CBR để sinh functional test scripts, kết hợp retrieval fine-tuning và fine-tuning LLM.

Trong phần phụ lục C.5 của CASCADE, nhóm tác giả cũng trực tiếp nhắc tới workflow mà kỹ sư kiểm thử sửa các test script do LLM tạo, rồi lưu lại làm case mới. Đây là một dấu hiệu khá rõ cho thấy cơ chế CBR của họ đã được nghiên cứu trong bối cảnh software testing, dù CASCADE không đánh giá trực tiếp trên mutation testing.

![]()  
arXiv  
\+1

## **5\. Những hạn chế cần lưu ý**

CASCADE vẫn tồn tại một số vấn đề quan trọng.

Cold start và sparse rewards. Nếu model không tạo được bất kỳ lời giải đúng nào, case bank không phát triển. Điều này đặc biệt đáng ngại với mutant khó kill.

Phụ thuộc vào tính tương đồng của bài toán. Một case hoạt động tốt trên hàm này không chắc chuyển được sang hàm khác, ngay cả khi code có bề ngoài tương tự. Với testing, có lẽ cần ưu tiên đặc trưng cấu trúc và ngữ nghĩa của mutation thay vì chỉ dùng text embedding.

Chỉ lưu case thành công. Retriver vẫn học từ cả reward 0 và 1, nhưng case bank chỉ giữ nghiệm thành công. Những thử nghiệm thất bại chứa thông tin về input không hiệu quả, vùng đã kiểm tra và điều kiện chưa đạt được; đây có thể là nguồn kiến thức hữu ích.

Đánh giá dài hạn chưa đầy đủ. Tác giả cũng thừa nhận chưa nghiên cứu đủ về memory growth, forgetting và hành vi trên horizon rất dài. Các bảo đảm no-regret phụ thuộc vào nhiều giả định lý thuyết.

![]()  
arXiv  
\+1

## **6\. Đánh giá khả năng áp dụng**

| Hướng áp dụng | Đánh giá |
| ----- | ----- |
| Sinh test trực tiếp | Không phải đóng góp chính |
| Truy xuất test case tương tự | Rất phù hợp |
| Chọn concept phù hợp cho mutant | Tiềm năng cao |
| Học từ feedback mutation testing | Rất phù hợp |
| Giải quyết oracle problem | Chưa giải quyết |
| Phát hiện loại lỗi hoàn toàn mới | Còn hạn chế |

Kết luận: Mình không nghĩ nên bê nguyên CASCADE vào pipeline sinh test ngay. Đóng góp đáng khai thác là cơ chế reward-driven retrieval: học xem kinh nghiệm kiểm thử nào thực sự giúp phát hiện lỗi, thay vì mặc định rằng concept hoặc ví dụ giống nhau về ngữ nghĩa sẽ hữu ích.

Một thí nghiệm hợp lý là so sánh Plain LLM → Concept Prompting → Static CBR → Adaptive CBR, giữ cùng model và ngân sách inference, rồi đánh giá bằng valid test rate, mutation score và số mutant kill được trên các chương trình chưa từng thấy. Nếu Static CBR đã cải thiện đáng kể, khi đó mới có cơ sở đầu tư thêm Contextual Bandit.

Code paper: [GitHub – guosyjlu/CASCADE](https://github.com/guosyjlu/CASCADE). Bộ benchmark: [DTLBench](https://huggingface.co/datasets/guosy/DTLBench).

[https\://arxiv.org/abs/2605.06702](https://arxiv.org/abs/2605.06702)

Finttune deer co tin hieu ve dong loi

**Vậy claim hiện đứng được là:** tool tạo ra những facts có grounding và witness; facts có thể giúp hướng việc sinh test. Nhưng **chưa chứng minh chắc rằng LLM đọc concept sẽ tìm bug tốt hơn plain với điều kiện so sánh công bằng**. Phần đang thiếu chính là nối các facts thành **giả thuyết vi phạm spec**, thay vì đưa từng gap rời rạc rồi yêu cầu sinh input.

Tuy nhiên, **“chỉ ra dòng chưa được exercise” chưa phải “xác định dòng có bug”**. Hiện hệ thống biết:

> Dòng/điều kiện này còn thiếu bằng chứng kiểm thử, và có input chạm được nó.

Nó chưa lập luận rõ:

> Giá trị từ dòng A đi qua nhánh B tới dòng C, khiến business rule R bị vi phạm.

Đó chính là phần **concept \+ relation \+ spec** bạn đề xuất bổ sun

Nếu ý bạn là **LLM suy luận chỉ được thấy concept graph, spec và quan hệ**, thì đó là một thiết kế khác cần làm rõ: tool đọc code → xuất biểu diễn concept → LLM suy luận trên biểu diễn đó. Và phải kiểm soát cả snippet/biểu thức trong fact, vì chúng cũng có thể mang code sang prompt.

2. **Bị implementation dẫn sai hướng tìm input.** Facts mô tả những gì code hiện có làm/chưa được exercise. Nếu code **thiếu hẳn một business rule**, tăng coverage của code đó có thể vẫn không phát hiện thiếu sót.

Vì vậy hướng concept–relation mới nên tách rõ:

* **Spec → nghĩa vụ cần thỏa**, lập độc lập trước khi đọc implementation.  
* **PUT → hành vi thực tế và quan hệ giữa các node.**  
* **Đối chiếu hai phía → giả thuyết lỗi → trigger input.**  
* Expected được xác nhận bằng rule hoặc oracle độc lập.

Nếu chỉ lấy concept từ PUT rồi yêu cầu model giải thích/sinh test theo chúng, **nguy cơ hợp thức hóa bug vẫn còn**, dù biểu diễn có thêm graph hay relation.

| Metric | Ý nghĩa | Trung bình 12 LLM |
| ----- | ----- | ----- |
| ${V}_{I}$ | Sinh input hợp lệ | 86.4% |
| ${V}_{IO}$ | Input hợp lệ, expected output đúng | 78.1% |
| ${D}_{I}$ | Input khiến buggy và silver khác nhau | 63.8% |
| ${D}_{IO}$ | Input phân biệt được và expected output đúng | 61.3% |

Nghĩa là khó nhất không phải đoán expected output, mà là nghĩ ra input khiến chương trình thực sự sai.  
Paper gọi đây là fault hypothesis generation bottleneck: LLM thiếu khả năng xây dựng giả thuyết chính xác về điều kiện gây lỗi. 

RQ1: Điều đó cho thấy xác định lỗi nằm ở đâu là một nút thắt lớn, ngay cả khi mô hình đã có khả năng sửa tương đối tốt nếu được cung cấp vị trí chính xác.

## [**https\://chatgpt.com/c/6ac9a6ac-3428-83ec-a47f-dbab6713089a**](https://chatgpt.com/c/6ac9a6ac-3428-83ec-a47f-dbab6713089a)

## **2\. Các paper khác có thể cải thiện concept-guided test generation**

| Paper | Cơ chế cải thiện | Khả năng áp dụng vào concept |
| ----- | ----- | ----- |
| [TestAgent (2026)](https://arxiv.org/abs/2607.09101) | Multi-agent \+ Code Knowledge Graph \+ execution feedback | Rất cao — chọn concept dựa trên dependency và ngữ cảnh code |
| [MUTGEN (2026)](https://doi.org/10.1109/TSE.2026.3682975) | Mutation-guided feedback, lặp để kill mutants | Rất cao — xác định concept nào chưa được kiểm thử hiệu quả |
| [MetaAgent (2025)](https://arxiv.org/abs/2508.00271) | Reflection \+ persistent knowledge \+ tool learning | Cao — tích lũy chiến lược test theo concept |
| [CoT \+ Coverage Feedback RL (2026)](https://doi.org/10.1145/3745765) | Reinforcement learning dựa trên coverage feedback | Cao — tối ưu sinh test có định hướng |
| [Agent-Testing Agent (2026)](https://aclanthology.org/2026.eacl-long.339/) | Adversarial test generation, điều chỉnh độ khó theo feedback | Trung bình–cao — định hướng sinh test vào điểm yếu của hệ thống |

## **. Hướng nghiên cứu tao đánh giá có triển vọng nhất**

Thay vì thử concept prompting vs few-shot vs CoT một cách độc lập, có thể nghiên cứu:

Adaptive Concept-Guided Test Generation with Execution Feedback

Ý tưởng là cho hệ thống lựa chọn và cập nhật concept dựa trên bằng chứng từ static analysis và execution feedback.

Ví dụ, với đoạn code xử lý số nguyên, hệ thống phát hiện có phép cộng gần giới hạn kiểu dữ liệu, chọn concept `integer_overflow`, tạo test ở các boundary và chạy mutation testing. Nếu mutant liên quan đến điều kiện biên vẫn sống, hệ thống dùng feedback để điều chỉnh cách tạo test, thay vì chỉ yêu cầu LLM sinh thêm test chung chung.

Cần thiết kế thí nghiệm tách biệt:

1. Base LLM \+ few-shot/CoT.  
2. Base LLM \+ static concept prompting.  
3. Base LLM \+ execution feedback, không có concept.  
4. Base LLM \+ adaptive concept \+ execution feedback.

Đánh giá bằng mutation score, bug detection, concept coverage, valid test rate và token cost.

Một lưu ý quan trọng là nghiên cứu năm 2026 về agentic iteration cho thấy one-shot prompting có thể vượt multi-agent trên mutation score khi framework multi-agent thiếu repository context. Vì thế, thêm agent không tự động làm test tốt hơn.

![]()  
IEEE Xplore

Nếu chỉ chọn hai paper để nghiên cứu sâu nhằm cải tiến concept-guided test generation, tao sẽ chọn TestAgent và MUTGEN trước MetaAgent. TestAgent giải quyết concept selection/context grounding, còn MUTGEN giải quyết feedback-driven refinement. Đây là hai điểm có thể tạo ra cải thiện đo lường được, thay vì đơn thuần đổi cấu trúc prompt.

Có. Thậm chí cold-start là một trong những vấn đề quan trọng nhất của Adaptive Concept-Guided Test Generation, vì phương pháp này phụ thuộc vào execution feedback để quyết định concept nào cần ưu tiên.

Vấn đề là: khi chưa có test hoặc chưa có execution history, hệ thống lấy thông tin từ đâu để chọn concept đầu tiên?

## **1\. Cold-start xuất hiện ở đâu?**

Có hai dạng cần phân biệt:

| Trường hợp | Vấn đề |
| ----- | ----- |
| Không có test ban đầu | Không có coverage, execution trace hay surviving mutants để định hướng |
| Có test nhưng chưa có lịch sử concept | Biết nhánh nào chưa được phủ nhưng chưa biết concept nào có khả năng tạo ra test tốt |

Trường hợp thứ hai thú vị hơn vì nó liên quan trực tiếp đến khả năng học và thích nghi của concept selector.

## **2\. Tao đề xuất giải quyết bằng Static Bootstrap \+ Adaptive Feedback**

![][image1]

Ở vòng đầu, concept selector chỉ có static features. Từ vòng thứ hai, nó mới có execution feedback để đưa ra quyết định tốt hơn.

Điều này giúp hệ thống không cần một bộ test ban đầu, nhưng cũng không phụ thuộc hoàn toàn vào phỏng đoán của LLM.

## **3\. Tuy nhiên, cold-start còn tạo ra một research question hay hơn**

Liệu concept selection dựa trên static analysis có thực sự tốt hơn random concept selection hoặc generic test generation khi chưa có feedback?

Tao đề xuất thêm một thí nghiệm so sánh:

| Phương pháp | Cold-start | Sau feedback |
| ----- | ----- | ----- |
| Random concepts | Chọn ngẫu nhiên | Không thích nghi |
| Static concepts | Chọn theo phân tích code | Không thích nghi |
| Generic LLM \+ feedback | Sinh test không có concept | Thích nghi |
| Adaptive concepts | Khởi tạo từ static analysis | Thích nghi dựa trên kết quả |

Đặc biệt, nên vẽ bug detection / mutation score theo số vòng lặp hoặc token budget, không chỉ lấy kết quả cuối cùng.

Một phương pháp có thể đạt mutation score cao sau 20 vòng nhưng hoạt động rất kém trong 5 vòng đầu. Khi đó, chi phí cold-start thực sự rất lớn.

## **4\. Có một rủi ro quan trọng**

Nếu concept selector chỉ học từ việc kill mutants, nó có thể ưu tiên những concept dễ kill mutant thay vì những concept có khả năng phát hiện real bugs.

Ví dụ, concept `boundary_condition` liên tục kill được nhiều mutant nên luôn được chọn, trong khi `state_transition` cần nhiều lần thực thi mới tìm được lỗi.

Đây là bài toán exploration vs exploitation.

Một hướng khả thi là dùng multi-armed bandit hoặc contextual bandit:

* Mỗi concept là một arm.  
* Ngữ cảnh gồm code features, uncovered branches và surviving mutants.  
* Reward dựa trên incremental coverage, mutation score, test validity và chi phí.  
* Dành một phần ngân sách cho exploration để tránh bỏ qua concept chưa được thử.

Nhưng mutation score chỉ nên là tín hiệu trung gian; khả năng phát hiện lỗi thực mới là mục tiêu đánh giá cuối cùng.

Tao nghĩ research question đáng nghiên cứu nhất là:

> Can static program analysis provide an effective cold-start strategy for adaptive concept-guided test generation, and can execution feedback improve concept selection under a fixed testing budget?

Điểm hay là research question này có thể kiểm chứng bằng thực nghiệm, đồng thời tách rõ hai đóng góp: chọn concept tốt trước khi có feedback và cải thiện việc chọn concept sau khi có feedback.

By combining graph-grounded obligations, blinded surrogate execution, and deterministic reconciliation, FEAgent turns model reasoning into concrete, inspectable evidence while keeping uncertainty explicit. The results show that this audit layer can expose substantial blind spots in labels and unit tests while direct execution prevents unsupported relabeling. The next priorities are matched-budget component ablations and execution audits of unflagged cases.

[image1]: <data:image/png;base64,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>