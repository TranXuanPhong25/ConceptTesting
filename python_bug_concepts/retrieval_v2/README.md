# Structure-aware Python concept retrieval

Bản cải thiện dùng AST để tìm operation/site trong code rồi rank các card bằng
structural evidence và hai BM25 channels cho spec/API. Corpus gồm 132 card gốc và
30 card semantic bổ sung, tổng **162 card**. Tất cả chạy local bằng standard library.

**Kết quả nội bộ trên 113 PUT HumanEval:** top-3 đúng nhóm bug và vị trí lỗi đầu
tiên ở **74/113 (65,5%)**; nếu chỉ tính đúng nhóm bug thì **88/113 (77,9%)**.
Trên 40 task ranking audit sau freeze: **25/40 (62,5%)** cho tiêu chí chặt hơn.
Xem [RESULTS.md](RESULTS.md) và [toàn bộ 113 task](evaluation/all_tasks.jsonl).

Các nhãn và vị trí lỗi do một người gán; native witness đã kiểm tra official
contract và đối chiếu PUT/reference. Corpus/nhãn đã xem public source của cả 113
task. Audit kiểm tra ranker sau freeze, chưa phải một kết quả generalization trên
corpus mới. Retrieval đúng concept không có nghĩa là hệ thống tự sinh được witness
hoặc test có oracle đúng.

## Dùng

Lệnh chính tự dùng v2 khi có `--code` và search tất cả fields:

```bash
python -m python_bug_concepts search --code path/to/program.py --top-k 3 --json
python -m python_bug_concepts search 'Unicode byte character length' --retriever v2
python -m python_bug_concepts show py.branch-boundary-contract
```

Chỉ định bản cũ để so sánh:

```bash
python -m python_bug_concepts search --code path/to/program.py --retriever original
```

Hoặc gọi trực tiếp:

```python
from python_bug_concepts import search, get_concept

packet = search(code=source, top_k=3)
for hit in packet["results"]:
    print(hit["concept"]["id"], hit["evidence"])
```

Mỗi result trả toàn bộ `where / how / what`, source provenance và tối đa ba source
sites với line, expression, reason. Đó là candidate để kiểm tra theo contract,
không phải bug verdict. Input code chỉ được parse, không được execute. Với code
không parse được, v2 trả warning và dùng lexical fallback. `base.search` vẫn là
API legacy để giữ baseline; public `python_bug_concepts.search` là entry point mới.

Natural-language search mặc định vẫn dùng corpus gốc. Dùng `--retriever v2` để
tìm text trong 162 card. Các option `--field where/how/what` tiếp tục dùng bản gốc;
explicit v2 yêu cầu `field=all`. Source/category filters vẫn hoạt động ở cả hai.

## Dữ liệu và tái lập

- [data/all_concepts.jsonl](data/all_concepts.jsonl): export 162 card với provenance.
- [data/extra_concepts.json](data/extra_concepts.json): 30 semantic cards bổ sung.
- [data/extra_patterns.jsonl](data/extra_patterns.jsonl): 18 CPython documentation
  sections; đây là language/API evidence, không phải 18 bug-fix examples.
- [data/extra_sources.json](data/extra_sources.json): hashes và pinned revision,
  dùng license CPython đã lưu ở corpus gốc.
- [evaluation/inputs.json](evaluation/inputs.json): public PUT/spec, ID và split.
- `evaluation/gold.json`, `mechanism_sites.json`, `fault_cases.json`,
  `witness_grading.json`: grading-only labels/sites/witnesses, không dùng bởi retriever.
- `evaluation/baseline_snapshot/`: corpus và code baseline ban đầu.
- [PREREG.md](PREREG.md), [REVIEW.md](REVIEW.md): protocol, amendments, giới hạn.

```bash
python -m python_bug_concepts.retrieval_v2 build
python -m unittest python_bug_concepts.tests python_bug_concepts.retrieval_v2.tests python_bug_concepts.test_api -v
python -m python_bug_concepts.retrieval_v2.summarize
```

Lệnh summarize chỉ đọc score đã lưu và kiểm tra freeze. Audit đã chạy một lần;
evaluator từ chối overwrite. Grader replay là phần riêng có execute code trong
bounded workers; nó không thuộc retrieval flow. Chưa có LLM/API call hay benchmark
test-generation run trong cải thiện này.
