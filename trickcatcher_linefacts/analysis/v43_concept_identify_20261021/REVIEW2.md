# Independent implementation re-review — before outcomes

Verdict: **PASS for preparation**, không có MUSTFIX trong implementation đã đọc.
Đây chưa phải final run approval: cần kiểm tra frozen pool/source/dependencies,
parent inventory identity và context feasibility trước khi chạy model.

Reviewer đọc AGENTS/shared memory, CHECKPOINT/CODE_REVIEW, PREREG và source mới
trong clean-context review task. Không chạy test, prepare, diagnostic tools,
network, model hay PUT. Chỉ đọc source, parse AST và tính source hash. Reviewer
chỉ viết file review này; không sửa implementation, parent hay output.

Source SHA256 đã review:

| File trong pipelines/v43_concept_identify | SHA256 |
| --- | --- |
| identify.py | 295fff34255880eb49f6ef4d3165d3b674e4fdfb84bd20a02cd2e2830983225c |
| identify_tools.py | 6248bf787a2d9ff3e2e7575cff309a5d40ad702fdaaa11c94d75da4be320c019 |
| PREREG.md | 0d6cd76129b56cdce82373f36f4f771777ede79b2fd7ee6c7189ebd98208a8bf |
| test_identify.py | 679e3827d845a3f6e42fdeb7538ed898b07dfe8ed94d4fdfc06d46a97b00129e |
| config.json | 281294ad141b49197d5c8a9ae10310dbfb172db736a5d573d59875dcaeca1182 |

Các port d1_client.py, flow_common.py, chat_template.jinja và catalog.json khớp
PORTS.json. AST của source chính parse được; reviewer không import/chạy module.

Các blocker cũ đã được xử lý:

- identify.py:121–125,161–171 kiểm tra selected/evidence IDs trước khi ghi valid.
  JSON/schema/finish failure không được repair; initial invalid block cả hai finals.
- identify.py:53–55,81–92 pin cả bốn parent inventory hashes trong freeze và xác
  minh exact contents. Final independent audit vẫn phải kiểm tra frozen identities.
- identify_tools.py:49–56 và identify.py:135–141 đưa cùng mechanical checks vào
  cả hai arms, luôn giữ spec entailment là unverified. Unsupported roles/arity,
  bad quote và concept mismatch không được tự sửa thành normative binding.
- identify_tools.py:67–125 phân biệt type, None và exception; unknown binding,
  bad arguments và unsupported literal trả unknown. Global relation menu và
  finite seen-fixture scope được khai báo rõ trong PREREG.
- identify_tools.py:143–165 chọn contrast theo satisfaction vector; thay đổi
  predicted value đơn thuần không được gọi là thay đổi satisfaction. Controlled
  pair chỉ có nghĩa một argument thay đổi, không phải một semantic dimension.
- identify_tools.py:168–183 chỉ quảng bá partial read inventory, không có claim
  sound slice/causality. identify_tools.py:186–211 giữ sibling tool results khi
  một component lỗi; chỉ ghi sanitized error type.
- identify.py:58–60 yêu cầu independent source approval trước preparation;
  identify.py:176–179 yêu cầu thêm frozen digest approval trước run.
- identify.py:151–173,176–222 và d1_client.py:73–139 có immutable requests,
  controller lock, quota-only continuation, cache reuse, fixed24 completion cap,
  no retry cho consumed unknown attempts, exact model/context/tokenizer/usage
  checks và input/output caps. Không có new PUT execution trên đường chạy này.

Paired final packets khác nhau ở tool_feedback; spec/source/raw observations,
proposal, vocabulary, checks và schema giống nhau. Preparation chỉ chọn public
source/spec và compact native observations, không đưa gold expected output hay
fixture verdict vào packet. Thí nghiệm vẫn là reused-pool selection diagnostic;
review này không xác nhận novelty, held-out transfer hay normative correctness.

test_identify.py có artificial regressions có ý nghĩa cho occurrence/order,
subset direction, eligibility/multiplicity, None/exception, bool/int, unknown,
arity/names, mechanical-vs-semantic checks, pair isolation, partial read inventory,
sibling tool error, raw/tool parity, final IDs, JSON/finish, frozen parent identity,
preparation approval và consumed transport attempt. Reviewer đọc test source và
owner log CPU_TESTS.log: **19/19 PASS, 0.032s** trong stable env. Không tự chạy
test. Delta cuối có thêm unusable-observation control và compact-table unknown
reason reconstruction. Compact table giữ mỗi observation×binding cùng tất cả
status/value/exception/holds/reason; internal contrast matrix không đổi. Guard
execution_status/output_capture mới trả unknown cho unresolved hoặc opaque output.

Giới hạn cần kiểm tra ở bước final readiness, không phải MUSTFIX hiện tại:

1. Full matrix cùng raw pool có thể vượt input6144 khi pool lớn. Cần ghi context
   feasibility trước model calls; không tự cắt evidence hoặc tăng cap. Tokenizer
   guard hiện tại fail closed nhưng có thể chặn một paired final sau initial call.

PREREG amendment mới cho phép tối đa 25 readiness metadata requests: một models
GET và 24 synthetic-envelope tokenizations, không có completion, diagnostic
binding/tool computation hay gold. Phải ghi riêng và stop nếu readiness thất bại.
Envelope chỉ là size estimate; actual tokenizer guard vẫn quyết định mỗi call.
Reviewer đã đọc amendment này trước preparation; không thực hiện metadata calls.

Environment delta trước preparation cũng PASS: temporary env biến mất nên config
v43 chuyển sang /home/phong/.cache/concepttester/v43-venv/bin/python. ENVIRONMENT.json
ghi Python3.12.2, executable SHA256
d36bd958d0a5b25ac89f20d2b29221920c08d38f88e273f0553d29979d49a068 và đủ 16
installed distributions; direct libraries vẫn là httpx0.27.2, jsonschema4.23.0,
Jinja2 3.1.4. deps() giờ pin toàn bộ installed distribution versions. Reviewer
đọc environment record, amendment và rerun log; không tự chạy env hay test.
Không có preparation hoặc model call trước delta theo owner checkpoint.
