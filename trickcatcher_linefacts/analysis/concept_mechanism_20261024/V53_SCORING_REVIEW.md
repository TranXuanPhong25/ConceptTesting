# V53 independent review trước scoring

Ngày 2026-10-24. Reviewer chỉ đọc source, PREREG, prompt/answer files và transcripts gốc; không gọi model/HTTP, không execute generated checks/PUT/reference và không tính efficacy outcomes. Không sửa source, frozen outputs hoặc PREREG cũ.

**Readiness: PASS với điều kiện về unresolved evaluator records.** Với 72 answers hiện tại, không tìm thấy must-fix về syntax, tool provenance hoặc cách scorer thực hiện Amendment 1 làm cần generation lại. Root có thể chạy original CPU scorer sau khi xác nhận lifecycle/ownership và lưu provenance inventory này. Đây không phải verdict promising của experiment.

**Inventory và provenance**

Structured evidence: [V53_PROTOCOL_INVENTORY.json](V53_PROTOCOL_INVENTORY.json). File này chứa hashes của source/PREREG, từng prompt/answer, mapping đến original transcript và transcript hashes; không chứa secrets hoặc endpoint URLs.

| Kiểm tra | Kết quả |
|---|---|
| Registered distinct problems / PUTs | 24 / 33 |
| Expected / present answers | 72 / 72 |
| Fenced, parseable, non-empty answers | 72 |
| Check functions | concept 81; lines 79; open 224; total 384 |
| Duplicate check names trong một answer | 0 |
| Parameter names/kinds/defaults khớp prompt signature | 384/384; annotations không quyết định interface |
| Static imports/global/nonlocal hoặc explicit raise | 0 answers |
| Original answer-agent transcripts tìm được | 72, map đúng 72 answers |
| Read own prompt / Write own answer | Mỗi agent đúng 1 / 1 |
| Current answer bằng last transcript Write content | 72/72, so sánh byte content |
| Substantive tool access ngoài own Read/Write | 0 |

Original transcripts nằm trong session `bff6dd90-c044-4e71-bda0-a5213ecbb610`, dưới local Claude project directory. Search chỉ giới hạn các top-level session JSONL có tên v53 và subagent files của đúng session đó; không recursive-scan toàn bộ out hoặc đọc secrets.

Mỗi transcript còn có một `SubagentHandback` với input `message`: đây là thao tác trả kết quả cho orchestrator, được ghi riêng, không cấp data access hoặc code execution. Review diễn giải restriction Read/Write theo quyền truy cập thông tin/thực thi, không coi return bookkeeping là một external tool violation. Nếu dùng mechanical whitelist literal chỉ gồm hai tên tool thì cả 72 đều bị flag vì handback; cần ghi interpretation này trong final protocol audit, không giấu tool. Không có Bash, Edit, secondary Read hoặc external tool execution trong 72 transcripts.

Static checks không chứng minh mọi function sẽ luôn trả bool, never raise hoặc không mutation trên mọi input. Runtime strict-bool wrapper, public-input rejection rule và universe execution mới đo các điểm đó. Chưa dùng static inventory để loại semantic failures hoặc sửa model answers.

**Đối chiếu scorer với Amendment 1**

- Arms đúng `concept`, `lines`, `open`, cùng `SHARED` caller-only/strict-bool instructions. `lines` tách taxonomy khỏi line-by-line extraction; `open` yêu cầu atomic stated/implied input conditions.
- Syntax/duplicate-name/missing guard được chạy trước scoring. Scorer có raw-text fallback từ inherited `code_block()`, nên chưa enforce no-fence tuyệt đối trong mọi trường hợp; current 72 đều có đúng một fenced block, do đó không ảnh hưởng current run.
- `run_checks()` wrap từng `check_k` riêng, yêu cầu strict Python bool; check trả False/raise trên public input bị drop; conjunction của các check còn lại định nghĩa acceptance. Không có kept check thì accept-all, vẫn hiện số kept=0; đây không phải automatically valid mining success.
- `tool_accept()` dùng **v48 `menu_fixed.constraints_report`**, không dùng v44 parser cũ. Menu-fixed có explicit unsupported và chặn partial power parsing. Counterexamples của v44 không được gán trực tiếp thành lỗi numeric tool trong v53. Numeric tool không hỗ trợ mọi relational constraint; đó là phạm vi baseline, không phải full validity oracle.
- `effect()` dùng confirmed-input set differences trước/sau cap-20 refill, tách lost và gained; task lost/gained dùng boolean task coverage. Aggregation giữ per-oracle losses và primary decision đúng các điều kiện Amendment 1.
- Primary vẫn là concept-vs-open recall margin ≥0.10 kèm safety; concept-vs-lines là report-only. Không có phép so taxonomy mới được nâng thành primary sau outcomes.
- Tool bounds đi qua cùng public-input rejection sanity rule. Public agreement không chứng minh normative soundness; hidden contract chỉ ở evaluator.
- Sonnet rows được `P.sonnet()` tạo theo số valid programs thực tế và quorum trong `O.votes`. V53 truyền hardcoded `3` vào `effect` như valid-program-count; trong effect hiện tại giá trị đó chỉ làm khác eligibility metadata mà effect không trả về, không thay emitted outputs/FA/lost/gained. Nên dùng actual valid count nếu sau này xuất eligibility, nhưng không cần đổi current source để tính current reported metrics.

**Điều kiện phải kiểm tra khi score**

1. `O.score_inputs()` phải return ready, original execution input/program hashes khớp. V53 không guard `ready is None` riêng nên incomplete v49 sẽ fail unpacking thay vì ghi incomplete report; nếu xảy ra, dừng và report incomplete, không sửa data để đi tiếp.
2. Parent phải xác nhận không scorer/controller khác đang ghi cùng output; original `score.json` là immutable. Source/answer inventory ở JSON phải được hash-check lại trước/after run vì v53 chưa có own comprehensive freeze manifest trong scorer.
3. **Unresolved reference records phải được report riêng.** Inherited `reference_truth()` đặt `valid = contract[0]=='ok'`; skipped/timeout contract do đó có valid=False. V53 hiện gom mọi valid=False vào invalid denominator và không serialize `reference_skipped` vào task report. Nếu evaluator có skipped/timeout/unresolved thì không được đọc default primary verdict như một validity conclusion đầy đủ. Cần bổ sung evaluator-integrity audit, tách unknown khỏi contract-invalid và withhold scientific verdict khi sự thiếu này có thể đổi gate. Không sửa threshold hoặc lựa chọn inputs theo outcome. Đây là điều kiện readiness, chưa kiểm tra runtime outcomes trong review này.
4. `P.sonnet(..., excluded=set())` không load v52 excluded file. Local v52 không có `excluded.json`; do đó không có known excluded program bị khôi phục trong snapshot này. Nếu file đó xuất hiện trong lifecycle audit hoặc nguồn programs thay đổi, phải reconcile trước scoring.
5. Scorer chạy generated checks và có thể chạy/reuse reference/oracle CPU caches; nó không gọi model. Run cần dùng `E.CONFIG['V4_PYTHON']` và worker sandbox hiện có. Ghi process/time/resource failures, không xem worker failures là concept semantics.

**Resource accounting từ transcripts**

72 logical generation agents, 216 assistant messages có usage, model label `claude-sonnet-5-5`. Deduplicate usage theo `(transcript, assistant message id)`, lấy bản usage cuối của mỗi message: input tokens 432, cache-creation input tokens 1,505,521, cache-read input tokens 6,583,608, output tokens 59,077. Đây là transcript token accounting, không phải 72 provider requests hoặc dollar estimate. Giá/cache billing và khả năng transcript usage thiếu cần audit riêng trước cost claim.

**Giới hạn diễn giải**

Một validity improvement trên existing universe chưa chứng minh concept-guided input generation hoặc transfer. More atomic checks trong open (224 so với 81/79) là treatment output, không tự là budget violation; cần report actual tokens/runtime. Current protocol có thể quyết định package promising mà chưa chứng minh taxonomy effect. V53 là dev experiment và không có quyền đổi thành held-out claim chỉ nhờ PREREG.

**Wrapper review trước launch**

Đã đọc `run_v53_score.py` mà không execute. Nó gọi original scorer, giữ nguyên gates/caps, ghi journal và chặn `reference_skipped` hoặc valid-reference-unresolved trước khi các records được dùng. `finally` khôi phục monkey-patched functions. Chưa thấy thay đổi semantic scoring ngoài fail-closed integrity guard.

Hai must-fixes nhỏ cho wrapper trước launch: pin cả `problems.json`, PREREG, presence/content của `excluded_problems.json` và bảy reviewed source hashes trong `V53_PROTOCOL_INVENTORY.json`; kiểm tra lại cùng manifest sau score trước khi ghi complete. Bản review đầu của wrapper mới pin validity.py và prompt/answer files lúc bắt đầu, nên chưa ngăn denominator/dependency change hoặc mutation trong một CPU run dài. Nếu hash mismatch sau khi immutable score đã ghi, phải mark invalid/withhold verdict; không overwrite để che discrepancy.

Wrapper guard dùng inherited `reference_skipped` flag, không tự chứng minh mọi raw contract failure type đã được phân loại. Parent runtime evaluator-integrity audit vẫn cần phân biệt contract exception (known invalid) với load/crash/unresolved status nếu chúng xuất hiện. Không cần thay registered threshold để làm việc này.

Rereview trước launch: **hai must-fixes đã được sửa, READY cho CPU scoring**. `verify_inputs()` pin bảy source hashes, problems mapping, PREREG và full prompt/answer inventories; v53/v52 exclusion files absent tại snapshot phải tiếp tục absent. Verification chạy trước và sau `v.score()`; failure ghi scientific verdict withheld. Chưa execute wrapper trong review. Raw-status audit vẫn cần flag `['exception', 'load:...']` và resource failures khi phù hợp: ft_worker encode load error dưới exception nên inherited skipped flag không bắt trường hợp đó. Contract assertion exception bình thường vẫn là known invalid.

**Independent review của saved-reference integrity audit**

Đã đọc `audit_references.py` và đối chiếu mapping với `E.reference_truth()`, `mutoracle.load_ref()` và `iorel.run_batch()`. Independent check chỉ parse cached JSON và Python literals; không execute reference/PUT/checks hoặc đọc v53 efficacy score.

- Với cả 33 tasks, input order của v41 PUT job và reference job giống nhau. V49 `generated/job.json` chứa đúng decisive inputs trừ v41 pool, theo original SHA256 ordering; reference sources và entry giống frozen v41 reference job. Không có source/input mapping mismatch.
- `REFERENCE_INTEGRITY.json` covers 32,311 decisive input rows, đủ cached, không missing/conflict/unresolved contract/unresolved valid reference. Đã rehash tất cả files trong manifest: 0 mismatch ở snapshot review.
- Contract statuses: 19,469 `ok`, 12,842 `exception`; mọi contract exception đều `AssertionError`. Không load/resource/timeout/skipped exceptions bị nhầm thành invalid.
- Cả 19,469 valid-reference outputs có status `ok` và parseable bằng literal parser; không có truncated/unparseable reference value ẩn dưới status `ok`.

**Điều kiện evaluator integrity đã đạt trên snapshot này.** Audit script đọc union của v41 và generated caches; current generated cache mapping đã được đối chiếu đúng source và order, nên không thấy stale-cache gap. Vẫn cần post-run hash verification và wrapper guard để phát hiện thay đổi/failure phát sinh sau snapshot. Đây là reference-readiness evidence, chưa là efficacy verdict của v53.
