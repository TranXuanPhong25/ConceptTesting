# V53 independent postscore review

Ngày 2026-10-24. Review sau khi root báo CPU scoring complete. Không model/HTTP call, không execute validator/PUT/reference. Chỉ parse final score và cached jobs/results.

**Kết luận: verified NO-GO cho registered validity-concept comparison.** Concept, lines và open có **acceptance masks giống hệt nhau trên toàn bộ 32,311 inputs**, không chỉ cùng aggregate counts. Cả ba masks bằng hidden contract trên universe hiện có. Vì vậy taxonomy không tạo thêm validity discrimination ở experiment này.

Independent verifier: [verify_v53_postscore.py](verify_v53_postscore.py). Output: [V53_POSTSCORE_VERIFICATION.json](V53_POSTSCORE_VERIFICATION.json). Verifier không import runner hoặc execute generated code; nó independently cộng per-task metrics, tính lại original gates, và reconstruct acceptance bằng cached checker outcomes.

**Metric/gate verification**

| Arm | Invalid caught / invalid | Valid rejected / valid | Exposing inputs rejected |
|---|---:|---:|---:|
| concept | 12,842 / 12,842 | 0 / 19,469 | 0 / 4,084 |
| lines | 12,842 / 12,842 | 0 / 19,469 | 0 / 4,084 |
| open | 12,842 / 12,842 | 0 / 19,469 | 0 / 4,084 |
| numeric tool | 1,854 / 12,842 | 0 / 19,469 | 0 / 4,084 |

Từng scalar aggregate trong `score.totals` bằng tổng từ 33 per-task records, gồm oracle losses/gains. Recomputed primary: recall margin concept−open = 0; required margin ≥0.10 fail; tất cả registered safety conditions pass. Verdict chính xác là `not promising`. Taxonomy contrast concept−lines = 0, safety pass, vẫn report-only theo PREREG. Không thay threshold hoặc denominator.

**Full acceptance-mask verification**

Với mỗi case×arm×check, verifier đọc cached public và universe outcomes theo đúng input ordering/chunk size, kiểm tra `job.inputs`, result lengths, program name và code source consistency. Code trong cache phải chứa current answer code và đúng wrapped `check_k`. Public rejection xác định check bị drop; conjunction của các kept checks reconstruct acceptance từng input. Không có fallback subchunk hoặc missing-cache case trong verification run này; nếu có, verifier sẽ dừng chứ không impute outputs.

Kết quả: tất cả 33 tasks có concept=lines=open masks; từng mask bằng raw hidden contract validity từ v41/reference + v49/generated caches đã independent integrity-review trước đó. Mỗi accepted/rejected input được xác minh, thay vì suy equivalence từ cùng recall/false-rejection rates. Per-task invalid-caught và valid-rejected từ masks bằng score.

**Per-check behavior**

| Arm | Unique checks trên 24 problems | Check instances trên 33 PUT tasks | Kept instances | Public drops | Raised public / universe | Instances reject 0 universe inputs |
|---|---:|---:|---:|---:|---:|---:|
| concept | 81 | 103 | 103 | 0 | 0 / 0 | 61 |
| lines | 79 | 101 | 101 | 0 | 0 / 0 | 58 |
| open | 224 | 283 | 283 | 0 | 0 / 0 | 220 |

Count instances lặp cùng checker khi một problem có nhiều PUTs, nên không diễn giải thành 487 independent learned rules. Unique-answer first-record stats cũng không có drops/raises. Không có model arm bị mất checks vì public-input guard; mask equivalence không phải artifact của mọi check bị drop thành accept-all.

Open tạo nhiều atomic checks hơn nhưng không đổi acceptance mask; thêm checks không tạo thêm coverage ở universe này. Zero-rejection check không tự là sai hoặc vô dụng tổng quát: nó có thể enforce một constraint mà universe chưa vi phạm, hoặc trùng với check khác. Ví dụ concept của task89 có hai checks cùng kiểm tra equal lengths của nums1/nums2 khi dịch một alias statement về n; số comments/checks không phải số independent semantic obligations.

**Oracle-filter effects: verifier xác nhận aggregate và interpretation**

| Oracle | FA trước → sau với mỗi model validator | Confirmed tests lost / gained | Confirmed task lost / gained |
|---|---:|---:|---:|
| Qwen defn | 145 → 108 | 0 / 9 | 0 / 0 |
| Sonnet defn | 56 → 0 | 0 / 36 | 0 / 0 |

Qwen tests: 352→324; Sonnet tests: 118→98. Các confirmed-test gains do cap-20 refill sau khi invalid candidates bị bỏ, không phải thêm generated input hoặc thêm confirmed bug task. Conjunction của validators giống nhau nên downstream filtering result giống nhau. Numeric tool chỉ giảm FA Qwen145→125 và Sonnet56→36, không có confirmed tests/tasks gained hoặc lost.

Postscore verifier independently kiểm tra sums và registered decision từ per-task oracle records. Nó **không chạy lại** oracle/official reach hoặc independently relabel từng emitted assertion; original oracle labels vẫn dựa trên verified scoring pipeline và cached reference integrity. Acceptance-mask equality và source/input mapping là independent evidence bổ sung.

**Blind spots và giới hạn kết luận**

- 21/33 PUT tasks có invalid inputs; 12/33 không có invalid input để đo invalid recall riêng. Các PUT cùng problem chia sẻ specification/validator, nên problem-level analysis cần giữ grouping.
- Universe giữ đúng một top-level argument-type pattern trên mỗi task. Quan sát toàn cohort chỉ có int, str và list ở top level; maximum top-level sequence/string length là 30. Vì vậy wrong outer types, nhiều upper length bounds lớn trong statement, và hành vi ngoài domain sampling chưa được kiểm tra đầy đủ. Không suy universal soundness/completeness từ 100% ở đây.
- Universe có nested-list/ragged structures, nên không phải mọi structural constraint đều không được thử; tuy nhiên structural coverage là hữu hạn và phụ thuộc sampler. Không được nói mọi structural edge case đã covered.
- Finite validation trên public inputs và saved universe không chứng minh spec entailment. Source-level correctness hoặc constraints chưa có counterexample trong universe vẫn cần semantic review khi dùng sang task/domain mới.
- V53 đo constraint extraction/organization và executable validity filtering. Nó chưa đo concept-guided generation theo measured testing gap. Gains của validity extraction so với numeric-only tool là thật trong universe này, nhưng `open` đạt cùng result; không attribution cho taxonomy hoặc explicit concept labels.
- No exclusions, no checker drops/raises, full per-input equivalence khiến current negative result không cần viện đến sample size hoặc interface loss để giải thích. Không promote taxonomy này bằng cách tăng K hoặc thêm cohort nhằm cứu margin.

**Hệ quả cho plan**

Đóng registered validity-concept hypothesis của line này theo NO-GO. Có thể reuse một validity miner đã kiểm chứng như infrastructure cho các hướng khác; việc reuse không biến validator thành thesis contribution về concept. Small-scope generation vẫn là stage khác, chỉ được tiến hành nếu có independent mechanism hypothesis, feasibility và PREREG đúng phần việc đó; v53 không cung cấp positive concept signal để tự động mở model run mới.
