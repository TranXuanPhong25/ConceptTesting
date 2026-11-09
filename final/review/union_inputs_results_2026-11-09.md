# Union inputs: Plain + EP+BVA + Decision Table

Union phát hiện **109/1454 eligible PUTs**, trên 38/157 eligible tasks, bằng 6344 unique novel-valid inputs. Đây là gộp input đã sinh, không phải một generator mới. Union có budget lớn hơn từng arm; không suy ra gain ở cùng budget.

| Arm | Novel valid inputs | Detected PUTs | Task có detection |
|---|---:|---:|---:|
| plain | 2906 | 68 | 25 |
| ep_bva | 2402 | 89 | 30 |
| decision_table | 2608 | 74 | 25 |
| union | 6344 | 109 | 38 |

Union kinds: {'wrong_value': 65, 'resource': 39, 'crash': 5}; mỗi PUT lấy strongest kind wrong-value→exception→resource. Loại 1572 duplicate memberships giữa các arms.

Source đã chạy reference và PUT trên đúng union pool, nên evaluation này replay lại toàn bộ shared reference/scorer từ checkpoint read-only. Thiếu checkpoint hoặc mismatched freeze/evidence sẽ fail; không chạy lại cùng native workload. Đã kiểm các first-failure confirmations trên từng PUT và pool identity. 0 model calls mới, 0 native calls mới; giữ nguyên mọi source outputs/checkpoints.

Config thực tế: 164 task records/157 eligible tasks;timeout 8.0 giây/input;input cap union60/task so với20/task/arm;corrected reference/scorer/seeds giữ nguồn.

Chi phí upstream generation không phải miễn phí: ```{"invocations": 472, "received": 471, "unknown": 1, "known_usage": {"prompt_tokens": 985123, "completion_tokens": 613376, "total_tokens": 1598499}}```

Matched-valid-budget (post-hoc descriptive, seeded random subsets; không lấy prefix):
- plain vs union:macro detected PUT fraction 0.046444 vs 0.058758;p=0.15078;zero-budget tasks3/157.
- ep_bva vs union:macro detected PUT fraction 0.060368 vs 0.048195;p=0.18258;zero-budget tasks7/157.
- decision_table vs union:macro detected PUT fraction 0.049770 vs 0.060032;p=0.016998;zero-budget tasks6/157.

Source checks, source inventory trước/sau và materialized union replay PASS. Catalogue semantics của các generator nguồn chưa được xác nhận chỉ từ union detection.
