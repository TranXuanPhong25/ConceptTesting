# Python bug patterns → concept base

Base local để retrieve bug concept Python theo **where / how / what**. Đã review đủ **279 pattern records** từ source công khai: **248 records** được liên kết vào **132 concept cards**, thuộc **15 nhóm**; **31 records** được loại có lý do cụ thể. **Không còn record chưa xử lý.** Mọi card đều liên kết về file gốc, revision, line span và SHA-256.

Retrieval dùng **SQLite FTS5/BM25**, chạy bằng Python standard library, không cần API key hay embedding service. Có thể tìm bằng natural language, rule code hoặc file Python. Code đầu vào chỉ được parse AST để bổ sung search hints.

**Cập nhật retrieval v2:** search từ code mặc định dùng [structure-aware retriever](retrieval_v2/README.md), với 30 semantic cards bổ sung ở folder riêng (tổng 162). Kết quả nội bộ: **74/113 PUT HumanEval (65,5%)** có concept trong top-3 đúng nhóm bug và vị trí lỗi đầu tiên; ranking audit **25/40 (62,5%)**. Nhãn do một người gán và có native witness; corpus/nhãn đã xem public task source, nên chưa phải kết quả generalization độc lập. [Report đầy đủ](retrieval_v2/RESULTS.md).

## Dùng ngay

Chạy từ repo root, Python 3.11+ có SQLite FTS5:

```bash
python -m python_bug_concepts build
python -m python_bug_concepts search 'mutable default list shared between calls' --top-k 3
python -m python_bug_concepts search 'tham số mặc định' --top-k 3
python -m python_bug_concepts search B023 --json
python -m python_bug_concepts search 'os.path.commonprefix path component' --top-k 3
python -m python_bug_concepts search --code python_bug_concepts/examples/finally_cleanup.py --top-k 3
python -m python_bug_concepts search 'Unicode encoded character length' --retriever v2 --top-k 3
```

Lọc theo nơi áp dụng, cơ chế, hậu quả, category hoặc source:

```bash
python -m python_bug_concepts search finally --field where
python -m python_bug_concepts search 'character set' --field how
python -m python_bug_concepts search 'unmatched suffix' --field what
python -m python_bug_concepts search 'shared state' --category state --source cpython
python -m python_bug_concepts show py.mutable-default
```

`search` tự build index nếu thiếu và tự rebuild khi dữ liệu corpus thay đổi. Kết quả `--json` chứa toàn bộ card, templates và provenance. `--db /tmp/custom.sqlite3` đặt **trước** subcommand nếu cần index riêng.

`--code` với `field=all` tự dùng v2 và kèm source sites. `--retriever original` dùng lại BM25 ban đầu; `--retriever v2` dùng corpus mở rộng cho cả query text. Build ở root vẫn kiểm tra/index 132 card gốc; build v2 bằng `python -m python_bug_concepts.retrieval_v2 build`.

## Template where / how / what

| Field | Ý nghĩa | Ví dụ: mutable default |
| --- | --- | --- |
| `where` | Context, AST node, precondition và location template để gắn vào code cụ thể | Parameter default là list; function mutate list; contract yêu cầu các call độc lập |
| `how` | Cơ chế lỗi và trigger template | Default được tạo một lần; gọi function hai lần và đều bỏ qua parameter đó |
| `what` | Failure quan sát được và oracle template | Call thứ hai có state từ call thứ nhất; đối chiếu với call dùng fresh default theo contract |

`required_bindings` liệt kê các slot cần điền, ví dụ `target`, `location`, `function`, `parameter`, `first_input`, `second_input`, `contract`. Render template thành một packet cụ thể:

```bash
python -m python_bug_concepts render py.mutable-default \
  --bindings python_bug_concepts/examples/mutable_default_bindings.json
```

Phần `what` phải lấy expected behavior từ **contract/spec của target**. Source rule hỗ trợ cơ chế và điều kiện nghi ngờ; nó không tự chứng minh target có bug. Mỗi card có `applicability_notes` cho trường hợp hành vi đó được dùng có chủ đích.

## Dữ liệu và nguồn

| File/folder | Nội dung |
| --- | --- |
| [data/concepts.json](data/concepts.json) | 132 cards đã tổng hợp, là bản canonical để chỉnh sửa |
| [data/concepts.jsonl](data/concepts.jsonl) | Bản export cho RAG/pipeline, mỗi dòng có thêm resolved sources |
| [CATALOG.md](CATALOG.md) | Catalog đọc trực tiếp với đầy đủ where/how/what |
| [data/concept.schema.json](data/concept.schema.json) | JSON Schema cho concept card |
| [data/patterns.jsonl](data/patterns.jsonl) | 279 pattern records và upstream documentation |
| [data/sources.json](data/sources.json) | Revision, license và hash inventory của 172 file source |
| [data/coverage.json](data/coverage.json) | Quyết định cho từng raw record: mapped/excluded, concept IDs và lý do |
| [data/exclusions.json](data/exclusions.json) | 31 exclusions đã review, mỗi record có loại và lý do cụ thể |
| [COVERAGE.md](COVERAGE.md) | Bảng đọc trực tiếp cho toàn bộ 279 record decisions |
| [data/verification.json](data/verification.json) | Kết quả engineering checks và ví dụ retrieval ngày 2026-10-26 |
| [sources/](sources/) | Các file upstream giữ nguyên byte, kèm license |
| `index.sqlite3` | Index sinh local, đã nằm trong `.gitignore` |

Các nguồn đều pin theo commit, không phụ thuộc nội dung của branch hiện tại:

| Source | Phần lấy về | Revision | License |
| --- | --- | --- | --- |
| [Ruff](https://github.com/astral-sh/ruff/tree/bfa2407e98ee1343caeefd02b4b69043509baa8c) | 193 rule records từ 8 rule families; chọn rule có category `Correctness`/`Suspicious`, giữ cả removed/preview với nhãn tương ứng | `bfa2407e98ee1343caeefd02b4b69043509baa8c` | MIT |
| [flake8-bugbear](https://github.com/PyCQA/flake8-bugbear/tree/22d0af7812d2d65ae5440cbf2bebfd01e67fd0bb) | 62 warning records từ README gốc | `22d0af7812d2d65ae5440cbf2bebfd01e67fd0bb` | MIT |
| [CPython 3.13 documentation](https://github.com/python/cpython/tree/d8f88eca61df69eb550d03738905a6a071f8d0e7/Doc) | 24 sections về language semantics từ FAQ, built-in types và expressions | `d8f88eca61df69eb550d03738905a6a071f8d0e7` | PSF-2.0; xem LICENSE gốc |

Ruff kế thừa nhiều rule từ flake8-bugbear/Pyflakes/Pylint; **279 records không có nghĩa là 279 bug mechanisms độc lập**. 132 cards gộp các record tương ứng với cùng cơ chế. Có 248 raw records được liên kết vào cards; 31 records được loại khỏi index concept và giữ nguyên trong raw corpus, kèm lý do tại `data/exclusions.json` và `COVERAGE.md`. Search hiện index các **concept cards**.

Các exclusions gồm 11 rule về style, 6 về redundancy, 2 về typing convention, 5 khuyến nghị cách viết ký tự raw bằng escape tương đương và 7 về cấu hình linter/formatter/packaging. Đây là quyết định về scope của base, không phải khẳng định các rule đó vô ích. Exclusions không bị xóa khỏi source corpus.

Mỗi raw record phải có đúng một disposition: **mapped** vào ít nhất một concept, hoặc **excluded** với lý do. Validation/build sẽ fail nếu xuất hiện record chưa được review, một record vừa mapped vừa excluded, hoặc exclusion thiếu lý do. `coverage.json` schema version 2 lưu `pattern_decisions`, `excluded_pattern_count` và `unresolved_pattern_count`; bản hiện tại có **0 unresolved**.

Ngoài lỗi runtime, có 6 card thuộc category `syntax` để mô tả failure ở compile-time và 2 card `source-integrity` về sự khác nhau giữa source hiển thị và cấu trúc được parse. Mỗi card ghi rõ điều kiện và layer cần kiểm tra; rule về cấu hình tool được giữ trong exclusions.

Các card có `evidence_status=curated_hypothesis`. Nguồn gồm lint rules và language documentation, chưa phải dataset bug-fix thực tế. Các file trong `examples/` là ví dụ tự viết để kiểm tra retrieval, có ghi rõ contract; không phải benchmark hay test lấy từ paper.

## Dùng từ Python

```python
from python_bug_concepts import search, get_concept
from python_bug_concepts.base import render

packet = search("lambda loop closure", top_k=3)
for hit in packet["results"]:
    card = hit["concept"]
    print(card["id"], card["where"], card["how"], card["what"])

card = get_concept("py.mutable-default")
# render(card, bindings) yêu cầu đủ slot trong card["required_bindings"].
```

BM25 score chỉ xếp hạng mức khớp từ, không phải xác suất có bug. Có Vietnamese aliases và normalization dấu để tìm có/không dấu; cơ chế và template được viết bằng English. Bản gốc là lexical retrieval. V2 thêm structural eligibility/ranking và phân giải một số module alias/shadowing, chưa có semantic embedding, learned ranking hay type/data-flow analysis đầy đủ. Với code fragment không parse được, hệ thống tiếp tục lexical search và trả warning.

## Kiểm tra và tái tạo

```bash
python -m python_bug_concepts validate
python -m unittest python_bug_concepts.tests -v
```

22 tests kiểm tra source integrity, ingestion reproducibility, template binding, natural-language/rule-code/code retrieval, query tiếng Việt, field/source filters, query syntax, code không bị execute và stale-index rebuild. Có checks cho các cơ chế mới, đủ disposition cho 279 records, chặn unresolved/overlap/exclusion thiếu lý do, và invalidate index khi quyết định exclusion thay đổi. Đây là engineering smoke checks; không đo khả năng phát hiện bug hay lợi ích với test generation.

Re-download đúng các snapshot đã pin vào **thư mục mới**, đối chiếu toàn bộ hash trước khi ghi:

```bash
python -m python_bug_concepts.fetch --destination /tmp/python-bug-sources-verified
```

Rebuild raw records từ source đã lưu, hoàn toàn offline:

```bash
python -m python_bug_concepts validate
python -m python_bug_concepts.ingest
python -m python_bug_concepts build
```

`ingest` tái tạo pattern records và source manifest; hãy validate trước để phát hiện source bị sửa. Để thêm card, chỉnh `data/concepts.json`, dùng pattern IDs có thật và điền đủ applicability, templates, bindings; nếu record đang bị loại, bỏ exclusion tương ứng trong `data/exclusions.json`. Source record mới cần được map hoặc loại với lý do trước khi validate/build/tests pass. Không sửa source upstream để làm khớp card.

## Liên hệ với các thử nghiệm trước

v17 đã dùng template; v31/v34/v35 đã thử fault-type concept/template và không thiết lập được concept gain vững chắc (template pool v35 phơi bày 17/33 task, thấp hơn plain 19/33). Base này chuẩn hóa **external Python patterns → concepts → retrieval**, có provenance và template binding để dùng lại. Đã bổ sung [đánh giá chất lượng retrieval](retrieval_v3/RESULTS.md) trên 113 PUT và [API hybrid v4](retrieval_v4/README.md). Báo cáo tách frozen-label coverage, manual/native review, same-model judge và test-generation utility; chỉ phần utility hoàn tất mới cho phép nhận xét lợi ích sinh test.

## Đánh giá chất lượng và hybrid retrieval

Xem [RESULTS](retrieval_v3/RESULTS.md): original Qwen v3 có 67/113 family+site hits;
hybrid v4 có 78/113, so với structural v2 74/113. V4 là kết quả post-hoc trên dữ
liệu đã xem, chưa được chứng minh generalization hay utility riêng. Manual sample
20 row v3 cho 13 actual-bug concepts và 9 row đúng cả where/how/what.

[API v4](retrieval_v4/README.md) là opt-in, dùng response cache được mà không gọi
model. Public default vẫn là v2. Các returned cards là unverified hypotheses;
judge cùng Qwen đã có false positive được native replay bác bỏ.

## Scoped facts v5

[V5](retrieval_v5/README.md) được copy từ v2 sau khi commit baseline163b58a.
Có LibCST scope/source metadata, local value provenance và applicability records.
Dùng riêng với `--retriever v5` trong environment cài requirements của v5.
[Đánh giá](retrieval_v5/RESULTS.md):118tests pass, nhưng family/site hit vẫn88/74
trên113task, bằng v2; chưa có retrieval gain hay utility riêng. Default vẫn v2.
[Version tree](VERSIONS.md) ghi rõ representation, kết quả và giới hạn từng bản.

## Semantic retrieval v6

[V6](retrieval_v6/README.md) sửa eligibility, operation roles và source-site ranking
trong copy của v5. Dùng `--retriever v6 --policy balanced` trong environment có
LibCST1.9.0. [Kết quả development](retrieval_v6/RESULTS.md): family91/113,
first-site90/113,126cards; v2/v5 là88/74 với275cards. Precise có abstention mạnh hơn
nhưng giảm coverage. Label-match không phải actual precision độc lập; chưa đo
test-generation utility của v6. Public auto vẫn v2 để giữ compatibility.
