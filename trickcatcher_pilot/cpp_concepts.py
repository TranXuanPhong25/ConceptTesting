"""Export source-only C++ concept cards from the released ConceptCoder annotator.

The upstream VD annotator has an IndexError on C++ subscript nodes with fewer
than three children. This adapter replaces only that index collector with the
same logic plus a child-count guard; the upstream files remain unchanged.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import sys
from pathlib import Path
from typing import Any


VD_LABELS = (
    "null_assignment", "null_check", "ptr_deref", "buffer_allocation",
    "buffer_access", "bound_check", "free",
)


def _safe_get_indices(root: Any, _code: str) -> list[str]:
    indices = []
    queue = [root]
    while queue:
        node = queue.pop()
        if node.type == "comment" or "string" in node.type or "char" in node.type:
            continue
        if node.type == "subscript_expression" and len(node.children) > 2:
            child = node.children[2]
            if child.type not in ("number_literal", "binary_expression"):
                indices.append(child.text.decode())
        queue.extend(reversed(node.children))
    return list(set(indices))


def load_upstream_annotator(artifact: Path) -> Any:
    module_dir = artifact / "code" / "design_concept"
    sys.path.insert(0, str(module_dir))
    module = importlib.import_module("design_and_annotate_VD_concepts")
    module.get_indices = _safe_get_indices
    return module


def annotate(source: str, upstream: Any, max_statements: int = 12) -> list[dict[str, Any]]:
    properties = upstream.bfs(source, upstream.parser)
    lines = source.splitlines()
    by_line: dict[int, list[str]] = {}
    for label in VD_LABELS:
        for occurrence in properties[label]:
            for line in occurrence["lines"]:
                if 0 <= line < len(lines) and lines[line].strip():
                    labels = by_line.setdefault(line, [])
                    if label not in labels:
                        labels.append(label)
    # Preserve one representative of each concept before filling the remaining
    # cap by source order. This prevents repeated array accesses from hiding a
    # later bounds check in the prompt.
    selected: set[int] = set()
    for label in VD_LABELS:
        first = next((line for line in sorted(by_line) if label in by_line[line]), None)
        if first is not None:
            selected.add(first)
    for line in sorted(by_line):
        if len(selected) >= max_statements:
            break
        selected.add(line)
    return [
        {"line": line + 1, "labels": by_line[line], "source": lines[line].strip()[:180]}
        for line in sorted(selected)[:max_statements]
    ]


def export(puts: Path, artifact: Path, out: Path, limit: int, skip: int = 0) -> int:
    upstream = load_upstream_annotator(artifact)
    count = 0
    eligible = 0
    with out.open("w") as destination:
        for source_file in sorted(puts.glob("*/*.cpp")):
            source = source_file.read_text(errors="replace")
            statements = annotate(source, upstream)
            if not statements:
                continue
            if eligible < skip:
                eligible += 1
                continue
            eligible += 1
            row = {
                "problem_id": source_file.parent.name,
                "put_name": source_file.name,
                "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
                "annotator": "ConceptCoder_org VD bfs + subscript child-count guard",
                "statements": statements,
            }
            destination.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
            if count >= limit:
                break
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--puts", default="/tmp/TrickCatcher-upstream/Datasets/TrickyBugs/PUT_cpp")
    parser.add_argument("--artifact", default="ConceptCoder_org")
    parser.add_argument("--out", required=True)
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--skip", type=int, default=0, help="Skip this many eligible, sorted PUTs")
    args = parser.parse_args()
    print(json.dumps({"cards": export(Path(args.puts), Path(args.artifact), Path(args.out), args.limit, args.skip)}))


if __name__ == "__main__":
    main()
