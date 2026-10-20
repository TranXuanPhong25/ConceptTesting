---
name: linefacts-relational-research
description: Research 2026-10-14: obligation graph trước, conditional metamorphic concepts tiếp theo; 9 paper cards và fair ablations
metadata:
  type: reference
---

(2026-10-14) Research theo yêu cầu người dùng sau HANDOFF-2026-10-14:
[report](../trickcatcher_linefacts/research/relations_2026-10-14/REPORT.md), mỗi paper có folder riêng.

**Decision đề xuất, chưa được thực nghiệm xác nhận:** ưu tiên grounded obligation graph nối spec + concepts +
typed dependency paths + execution evidence, phát triển tiếp B3/B4. Nhánh tiếp theo là conditional metamorphic
concepts; abstract object protocols chỉ khi dataset thật sự stateful. Không coi graph topology hay prompting
là đã có gain. Đọc PromeFuzz, MR-Coupler, MemoRIA, MetaFOE, HITS, TELPA, DBcover, Think-on-Graph và PDG.

**How to apply:** report phân biệt paper facts và adaptation; có source/artifact status, contrasts giữ same
evidence để kiểm topology/concepts, và same-oracle track cho MR. Research không sửa pipeline, PREREG hay chạy
LLM. B4 amendment 1 đã giải quyết truncation; chain parser hiện chỉ kiểm candidate line IDs, chưa kiểm từng edge.
Related: [[research-state]], [[conceptcoder-paper-facts]], [[ckgfuzzer-paper-facts]].
