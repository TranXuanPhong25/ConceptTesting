"""Project local C annotations onto ConceptCoder Table 1's seven VD labels.

This is a taxonomy adapter, NOT the authors' released static analyzer. The
local eighth ``if_statement`` label is deliberately excluded. Patch-derived
metadata (fault condition, fix hint, CWE, gold family) is never read.
"""

from __future__ import annotations

from typing import Any


PAPER_LABELS = (
    "Null assignment",
    "Null check",
    "Pointer dereference",
    "Memory allocation",
    "Buffer access",
    "Bounds check",
    "Memory free",
)


def project_item(item: dict[str, Any]) -> dict[str, Any]:
    """Return a seven-label, statement-level view using only source-local fields."""
    source = item["func_vuln"]
    lines = source.splitlines()
    raw = item["lines_concept"]
    statements = []
    for key in sorted(raw, key=lambda value: int(value)):
        index = int(key)
        vector = raw[key]
        if index < 0 or index >= len(lines):
            raise ValueError(f"concept line {index} outside source")
        if len(vector) != 8 or any(value not in (0, 1) for value in vector):
            raise ValueError(f"unexpected local concept vector at line {index}")
        labels = [label for i, label in enumerate(PAPER_LABELS) if vector[i]]
        if labels:
            statements.append({"line_index": index, "source": lines[index].strip(), "labels": labels})
    return {
        "id": item["id"],
        "taxonomy_source": "ConceptCoder Table 1, seven VD concepts",
        "labeler_source": "local tree-sitter reimplementation; not official ConceptCoder analyzer",
        "statements": statements,
    }
