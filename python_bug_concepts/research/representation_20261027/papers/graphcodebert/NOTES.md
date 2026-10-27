# GraphCodeBERT: Pre-training Code Representations with Data Flow

Reviewed 2026-10-27; research only.

[Primary paper](https://arxiv.org/abs/2009.08366). [Author artifact](https://github.com/microsoft/CodeBERT/tree/master/GraphCodeBERT).

Data-flow edges encode value origins and guide attention. Published tasks include code search. Useful motivation for preserving value transformations in retrieval; not evidence that a pretrained encoder recognizes actual Python specification violations. Official code-search workflow includes fine-tuning; do not assume the base checkpoint has those retrieval scores.
