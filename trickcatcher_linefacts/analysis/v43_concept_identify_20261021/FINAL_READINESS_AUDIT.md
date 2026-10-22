# Frozen preparation + metadata-readiness audit

Verdict: **PASS cho metadata readiness**, không có MUSTFIX. Chưa approve task
completion run: cần đọc readiness result và giữ exact source/freeze sau bước này.

Reviewer chỉ đọc source/data/metadata, parse AST và kiểm tra hash/equality.
Không chạy pipeline, test, network, model, PUT hay diagnostic relation/tool.
Pool audit chỉ kiểm tra provenance/compaction từ saved records; không adjudicate
normative binding hoặc tính candidate satisfaction.

Đã kiểm tra độc lập:

- Freeze file SHA256:
  53940eb79fb68e3bc750c045f392c0abf6e78f6abc4f243a20fef15579a95739.
- Tất cả 60 current source hashes khớp freeze và preparation_approval.json;
  passed=true. Core source khớp exact hashes đã approve trong REVIEW2.md.
- Tám prepared file hashes khớp freeze. Pool counts E1…E8 là
  13/7/8/7/9/15/9/10, tổng 78 rows.
- Mỗi pool khớp chính xác public spec/source/parameters của saved parent và
  compact union từ initial observation, injection, mọi arm event feedback có
  native_checked=true/domain_filter=accepted. Dedup/order/O IDs đều khớp; không
  có conflict giữa cùng input. Không có field gold/reference/fixture verdict
  được thêm. Các rows có status ok/exception; output ok có capture=literal.
- Cả bốn parent terminal_inventory hashes khớp frozen identities; toàn bộ exact
  file contents của mỗi parent cũng khớp inventory. Không chỉ kiểm tra manifest
  self-consistency.
- Frozen dependencies khớp ENVIRONMENT.json, executable binary hash thực tế,
  đủ 16 installed distribution METADATA versions trong stable env và quota script
  hash. Reviewer không chạy interpreter của experiment.
- Trước readiness, binding8 chỉ có freeze.json, preparation_approval.json và
  prepared/. Không có task completion attempt.

readiness.py SHA256 đã review:
a98c726548c1417fee4f88f05841f11c6a4dcb55e0f634dcd0f7f8961d9b08ea.

Đường chạy script chỉ tạo một MetadataClient (GET /models) rồi tối đa ba
tokenizations cho mỗi tám frozen episodes. Không gọi Client.complete(); override
request chặn /chat/completions. Không gọi identify_tools.tools()/compare()/contrast;
feedback là synthetic size envelope được đánh dấu readiness-only. Final packet
construction dùng cùng spec/source/rows/proposal/checks cho raw và tool, chỉ thêm
synthetic feedback ở tool arm. Không có gold lookup hoặc candidate repair.

Controller lock và consumed status chặn duplicate readiness; source/pool/dependency
verification chạy trước/sau, quota được kiểm tra, exact model/context/tokenizer
contracts vẫn do ported client enforce. Request/count/metadata được ghi vào riêng
readiness/, model GET body có redacted receipt/hash. Mỗi transport/tokenizer/cap
failure dừng trước task call và không tự retry. Giới hạn là một GET models cộng
tối đa 24 POST tokenize; cached tokenizations có thể giảm physical requests.

Synthetic envelope là estimate, không chứng minh mọi possible model proposal đều
fit. Actual call vẫn phải qua tokenizer guard input6144/output1536/context8192.
Không được cắt observations, tăng cap hoặc sửa treatment nếu readiness fail.

## External launcher review — fix verified

launch.py giữ launch lock xuyên suốt controller/wait/callback, có consumed-state
guard, kiểm tra launcher/readiness script/result hashes, gọi đúng frozen pipeline
và callback về registration thread với đúng binding8 root. Task attempt reuse và
no unknown retry vẫn do frozen client enforce. Callback record nằm ngoài root.

Blocker stale quota status đã được sửa: quota continuation yêu cầu child
returncode=0, status hash thay đổi, state=stopped và exact quota reason. Child fail
trước khi ghi fresh status sẽ không gây automatic relaunch. Reviewer đọc delta;
không chạy launcher. Launcher readiness path/hash sẽ cần kiểm tra lại nếu dùng
readiness namespace mới.

Owner xác nhận detached stdout/stderr nằm ở analysis/controller.log, ngoài binding8;
terminal inventory không hash log còn đang ghi. Phần này chưa cấp final run approval.

## Readiness1 terminal result

Readiness1 **STOP**, không phải context PASS: E1 initial=1017, raw=2755,
synthetic tool=8359 tokens > input6144, reason=readiness_input_cap. Reviewer đọc
status, metadata records và file counts: một models GET cộng ba tokenizer POST
đều received, ba consumed tokenizer attempts/results, zero completion attempts
trong readiness và actual task transport. Status SHA256:
d9d95ec0478aef3871d39df45a3cdbbc801bc3470ebf2116fe711302353b188b.

Readiness2 chưa được approve ở thời điểm addendum này. Mọi engineering amendment
phải nêu rõ nó supersede original readiness stop/no automatic repair rule, giữ
nguyên failed readiness1 records và báo failed gate trong final report. Không có
model completion nào để chọn/tune treatment theo semantic outcome.

## Readiness2 prospective amendment review

Verdict: **PASS cho một metadata readiness2 attempt**, chưa approve task run.
Không có MUSTFIX. Reviewed SHA256:

| External file | SHA256 |
| --- | --- |
| readiness2.py | 6fb2b2033a7f8e5caca9a3d24621369ee4da46456ad85228a16e7b4723ba190e |
| launch.py | 543ce98e39eadd4095e3829f4547dda2e9d9b21ae428e1b6446fd1db55517038 |
| READINESS_AMENDMENT.md | c3cda00dccd5cfeff0eb43b1848141a156deb672f88d11f160588f342700328f |
| EVALUATOR_RUBRIC.md | a0b6b9858822f705115e1fe61e5546084da18b3e5949f3e80d7b4e00753198ae |

Amendment ghi rõ supersede original engineering stop/no automatic repair rule,
trước mọi task completion. Tối đa một namespace readiness2 với thêm một models GET
và 24 tokenizer POST; nếu fail phải stop, không thêm adaptation. Original readiness1
STOP/metadata phải giữ nguyên và báo riêng. Reviewer xác nhận frozen60source,
8pool hashes, freeze SHA và readiness1 status SHA vẫn khớp; zero task attempts.

readiness2.py dùng exact public spec quote, fake 8-digit matrix values, full rows
và ba candidate columns. Nó tính input measurements và partial AST read inventory
từ dữ liệu/source đã public, không chạy PUT, candidate relation, spec oracle hay
gold lookup. Bốn contrast slots chọn theo serialized size, không theo effect hay
satisfaction. Feedback được đánh dấu synthetic readiness-only; quote/measurement/
AST realism chỉ phục vụ context estimate. Đây vẫn không phải universal upper bound.
Metadata-only guard, single consumed namespace, quota checks, source verification,
token cap và no completion path giữ nguyên. Reviewer chỉ đọc/AST/hash; không chạy
readiness2 hay các input-measurement/AST-tool functions.

Launcher trỏ đúng readiness2 script/status/hash và giữ fresh quota-stop checks đã
review. Prospective evaluator rubric không được import vào pipeline/readiness/
launcher hay prompt; nội dung E1…E8 khớp public spec/source, giữ full8 denominator,
candidate coverage failures, separate judgment/binding/interface metrics và
original semantic win/control gate. Không có model outcome nào trước rubric.

Final task run approval vẫn chờ actual readiness2 result, metadata receipts và
exact hashes. Readiness1 failed gate không được đổi tên thành PASS.
