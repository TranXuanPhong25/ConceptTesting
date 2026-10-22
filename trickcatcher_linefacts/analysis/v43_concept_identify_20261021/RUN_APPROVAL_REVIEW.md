# Independent final run approval

Verdict: **PASS** cho original v43 eight-episode, paired raw/tool diagnostic,
tối đa 24 single-attempt completions, zero new PUT workers. Không có MUSTFIX.
Approval áp dụng cho exact source/freeze/helpers dưới đây; launcher vẫn phải kiểm
tra quota>15 và model/context/tokenizer trước actual calls.

Reviewer chỉ đọc source, persisted metadata và dữ liệu; kiểm tra AST/hash/equality.
Không gọi network, model, PUT, pipeline/test hay diagnostic relation/tool.

Required approval identities:

| Artifact | SHA256 / digest |
| --- | --- |
| freeze.json file SHA256 | 53940eb79fb68e3bc750c045f392c0abf6e78f6abc4f243a20fef15579a95739 |
| freeze_hash = flow_common.digest(parsed freeze.json) | 2d75578df59e8abc52a6c631c52b72f0c3669bdf2034bcdaf2c58f73d34e3b5d |
| readiness2.py | 6fb2b2033a7f8e5caca9a3d24621369ee4da46456ad85228a16e7b4723ba190e |
| readiness2/status.json | d8aa016dd7cd3143ee970659cc617316d59f7b23344a856c2f08b6fe8ae74ca2 |
| launch.py | 543ce98e39eadd4095e3829f4547dda2e9d9b21ae428e1b6446fd1db55517038 |
| READINESS_AMENDMENT.md | c3cda00dccd5cfeff0eb43b1848141a156deb672f88d11f160588f342700328f |
| EVALUATOR_RUBRIC.md | a0b6b9858822f705115e1fe61e5546084da18b3e5949f3e80d7b4e00753198ae |

approval.json.sources phải bằng toàn bộ 60 entries của freeze.sources, không chỉ
core subset. Core identities đã kiểm tra lại:

| Source | SHA256 |
| --- | --- |
| identify.py | 295fff34255880eb49f6ef4d3165d3b674e4fdfb84bd20a02cd2e2830983225c |
| identify_tools.py | 6248bf787a2d9ff3e2e7575cff309a5d40ad702fdaaa11c94d75da4be320c019 |
| PREREG.md | 0d6cd76129b56cdce82373f36f4f771777ede79b2fd7ee6c7189ebd98208a8bf |
| config.json | 281294ad141b49197d5c8a9ae10310dbfb172db736a5d573d59875dcaeca1182 |
| test_identify.py | 679e3827d845a3f6e42fdeb7538ed898b07dfe8ed94d4fdfc06d46a97b00129e |

Final checks đã PASS:

- Current 60 source hashes khớp freeze và preparation approval; tất cả tám pool
  hashes khớp. Provenance/78 rows đã audit độc lập ở FINAL_READINESS_AUDIT.md.
- Đủ 16 installed distribution METADATA versions, executable binary SHA và quota
  script SHA khớp frozen dependencies. Bốn parent inventory identities và exact
  contents vẫn khớp; không có parent drift.
- Readiness2 state=ready, đúng script/freeze hashes; đủ 24 episode×phase sizes và
  24 consumed tokenizer attempts/results. Metadata có đúng một models GET và 24
  tokenize POST, tất cả received. Counts trong saved results khớp status sizes.
- Models response receipt HTTP200 được giữ với redacted body/raw hash; body quảng
  bá exact qwen2.5-coder-32b-instruct/context8192. Max synthetic input là 4748 tokens
  ở E6 tool, dưới cap6144. Envelope vẫn là estimate; actual tokenizer là authority.
- Tất cả tám persisted readiness raw/tool packets có identical system, spec,
  source, rows, proposal/checks/vocabulary/schema khi bỏ tool_feedback. Rows khớp
  frozen pools; tool feedback được đánh dấu READINESS ONLY. Evaluator rubric không
  được import/render vào frozen pipeline hoặc helper requests.
- Launcher giữ consumed launch lock, exact helper/readiness hashes, fresh-status
  quota-only continuation, correct binding8 path và original-thread callback.
  Unknown completion attempts không được retry/reset. Log ở analysis/ nằm ngoài
  binding8 terminal inventory. Detailed source audit ở REVIEW2/FINAL_READINESS_AUDIT.
- Actual task status.json chưa tồn tại; không có completion attempt trong actual
  transport hoặc readiness transports. Không có diagnostic model/PUT outcome.

Readiness1 vẫn **STOP**: E1 synthetic tool8359>6144, một models GET+ba tokenize POST.
Status SHA vẫn là d9d95ec0478aef3871d39df45a3cdbbc801bc3470ebf2116fe711302353b188b.
Prospective readiness amendment giữ failure này và chỉ cho thêm readiness2 trước
inference. Final report phải tách 4 readiness1 metadata requests, 25 readiness2
metadata requests và actual run calls/usage. Đây không phải recovered task result.

Approval không cho phép extra cases/arms, repair model output, cap increase, paid
fallback, benchmark/training hoặc fresh PUT execution. Post-generation freeze rồi
independent manual review toàn bộ 8 initials/16 final slots, kể cả invalid/blocked/
unknown; áp dụng prospective rubric và original GO/control gate. Không suy ra
semantic success từ readiness hoặc implementation PASS.
