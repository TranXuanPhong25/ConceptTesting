# TELPA

[Full text v2](https://arxiv.org/abs/2404.04966v2), TOSEM 2025; tên mới “Advancing Code Coverage: Incorporating Program Analysis with Large Language Models”. Kiểm program analyses và evaluation. [Zenodo version được paper dẫn](https://zenodo.org/records/15410112) mở được, có code/data ZIP và thông báo newer record; chưa tải/audit.

**Paper facts:** Object construction analysis và branch dependency analysis bổ sung usage/context; ineffective tests làm counterexamples cho feedback loop. Evaluation trên 27 Python projects, nhắm hard-to-cover branches; abstract báo branch coverage improvements 31.39%/22.22% với hai nhóm baselines. [Nguồn: paper v2](https://arxiv.org/abs/2404.04966v2).

**Áp dụng đề xuất:** Base traces có thể làm starting evidence cho target-specific strategy; dependencies hỗ trợ trigger inference.

**Giới hạn:** Không lấy ineffective test ở đây làm spec counterexample. LineFacts đã thử concrete-call feedback v9 và kém hơn Hypothesis; giữ strategy generation. Với function nhỏ, object construction/interprocedural context có thể không đem thêm thông tin.
