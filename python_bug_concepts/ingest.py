"""Rebuild pattern records from the checked-in, unmodified source snapshots."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCES = {
    "ruff": ("astral-sh/ruff", "bfa2407e98ee1343caeefd02b4b69043509baa8c", "MIT"),
    "flake8-bugbear": ("PyCQA/flake8-bugbear", "22d0af7812d2d65ae5440cbf2bebfd01e67fd0bb", "MIT"),
    "cpython": ("python/cpython", "d8f88eca61df69eb550d03738905a6a071f8d0e7", "PSF-2.0"),
}
PREFIXES = {
    "flake8_bugbear": "B", "pyflakes": "F", "ruff": "RUF", "pylint": "PL",
    "flake8_async": "ASYNC", "flake8_datetimez": "DTZ", "flake8_return": "RET",
    "flake8_simplify": "SIM",
}


def dump_jsonl(path: Path, records: list[dict]) -> None:
    path.write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in records))


def reference(source: str, path: Path, start: int, end: int) -> dict:
    rel = path.relative_to(ROOT / "sources" / source).as_posix()
    repo, rev, _ = SOURCES[source]
    return {
        "source": source, "revision": rev,
        "path": path.relative_to(ROOT).as_posix(), "start_line": start, "end_line": end,
        "url": f"https://github.com/{repo}/blob/{rev}/{rel}#L{start}-L{end}",
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def sections(text: str) -> dict[str, str]:
    result = {}
    matches = list(re.finditer(r"^## (.+)$", text, re.M))
    for i, m in enumerate(matches):
        result[m[1]] = text[m.end():matches[i + 1].start() if i + 1 < len(matches) else len(text)].strip()
    return result


def ruff_patterns() -> list[dict]:
    base = ROOT / "sources" / "ruff" / "crates" / "ruff_linter" / "src"
    codes = {}
    for m in re.finditer(r'\(\w+,\s*"(\w+)"\)\s*=>\s*rules::(\w+)::rules::(\w+)', (base / "codes.rs").read_text()):
        if m[2] in PREFIXES:
            codes[(m[2], m[3])] = PREFIXES[m[2]] + m[1]
    records = []
    rx = re.compile(r"(?P<docs>(?:^///[^\n]*\n)+)(?P<attrs>(?:#\[[\s\S]*?\]\s*)*)pub(?:\(crate\))? (?:struct|enum) (?P<name>\w+)", re.M)
    for path in sorted((base / "rules").glob("*/rules/*.rs")):
        text = path.read_text()
        family = path.parent.parent.name
        for m in rx.finditer(text):
            category = re.search(r"category = Category::(\w+)", m["attrs"])
            if not category or category[1] not in {"Correctness", "Suspicious"}:
                continue
            docs = "\n".join(line.removeprefix("///").removeprefix(" ") for line in m["docs"].splitlines())
            if "## What it does" not in docs:
                continue
            code = codes.get((family, m["name"]))
            if code is None:
                raise ValueError(f"No rule code: {family}/{m['name']}")
            slug = re.sub(r"(?<!^)(?=[A-Z][a-z]|(?<=[a-z0-9])[A-Z])", "-", m["name"]).lower()
            parts = sections(docs)
            records.append({
                "id": f"ruff:{code}", "rule_code": code, "name": slug, "family": family,
                "category": category[1].lower(), "documentation": docs, "sections": parts,
                "status": "removed" if "removed_since" in m["attrs"] else ("preview" if "preview_since" in m["attrs"] else "stable"),
                "kind": "lint_rule", "documentation_url": f"https://docs.astral.sh/ruff/rules/{slug}/",
                "provenance": reference("ruff", path, text.count("\n", 0, m.start()) + 1, text.count("\n", 0, m.end()) + 1),
            })
    return records


def bugbear_patterns() -> list[dict]:
    path = ROOT / "sources" / "flake8-bugbear" / "README.rst"
    text = path.read_text().split("How to enable opinionated warnings\n")[0]
    matches = list(re.finditer(r"^\*\*(B\d{3})\*\*: (.*)", text, re.M))
    records = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        docs = text[m.start():end].split("\n.. _B")[0].split("\n\nOpinionated warnings")[0].rstrip()
        records.append({
            "id": f"bugbear:{m[1]}", "rule_code": m[1], "name": m[2],
            "family": "flake8_bugbear", "kind": "lint_rule", "category": "upstream_unclassified",
            "status": "moved" if "Moved to B909" in docs else "documented",
            "documentation": docs,
            "provenance": reference("flake8-bugbear", path, text.count("\n", 0, m.start()) + 1, text.count("\n", 0, m.start() + len(docs)) + 1),
        })
    return records


# Anchors/headings refer to the pinned snapshot, not moving HTML documentation.
PYTHON_SECTIONS = [
    ("local-binding", "faq/programming.rst", "Why am I getting an UnboundLocalError when the variable has a value?", "What are the rules for local and global variables in Python?"),
    ("late-binding", "faq/programming.rst", "Why do lambdas defined in a loop with different values all return the same result?", "How do I share global variables across modules?"),
    ("default-arguments", "faq/programming.rst", "Why are default values shared between objects?", "How can I pass optional or keyword parameters from one function to another?"),
    ("assignment-alias", "faq/programming.rst", "Why did changing list 'y' also change list 'x'?", "How do I write a function with output parameters (call by reference)?"),
    ("shallow-copy", "faq/programming.rst", "How do I copy an object in Python?", "How can I find the methods or attributes of an object?"),
    ("floor-division", "faq/programming.rst", "Why does -22 // 10 return -3?", "How do I get int literal attribute instead of SyntaxError?"),
    ("negative-index", "faq/programming.rst", "What's a negative index?", "How do I iterate over a sequence in reverse order?"),
    ("matrix-alias", "faq/programming.rst", "How do I create a multidimensional list?", "How do I apply a method or function to a sequence of objects?"),
    ("augassign-partial-mutation", "faq/programming.rst", "Why does a_tuple[i] += ['item'] raise an exception when the addition works?", "I want to do a complicated sort: can you do a Schwartzian Transform in Python?"),
    ("identity", "faq/programming.rst", "When can I rely on identity tests with the *is* operator?", "How can a subclass control what data is stored in an immutable instance?"),
    ("truth", "builtins/stdtypes.rst", ".. _truth:", ".. _boolean:"),
    ("boolean-operators", "builtins/stdtypes.rst", ".. _boolean:", ".. _stdcomparisons:"),
    ("iterators", "builtins/stdtypes.rst", ".. _typeiter:", ".. _generator-types:"),
    ("sequence-operations", "builtins/stdtypes.rst", ".. _typesseq-common:", ".. _typesseq-immutable:"),
    ("mutable-sequences", "builtins/stdtypes.rst", ".. _typesseq-mutable:", ".. _typesseq-list:"),
    ("list-sort", "builtins/stdtypes.rst", ".. _typesseq-list:", ".. _typesseq-tuple:"),
    ("range", "builtins/stdtypes.rst", ".. _typesseq-range:", ".. _textseq:"),
    ("dict", "builtins/stdtypes.rst", ".. _typesmapping:", ".. _dict-views:"),
    ("dict-views", "builtins/stdtypes.rst", ".. _dict-views:", ".. _typecontextmanager:"),
    ("comparisons", "reference/expressions.rst", ".. _comparisons:", ".. _in:"),
    ("membership", "reference/expressions.rst", ".. _in:", ".. _is:"),
    ("generator-expressions", "reference/expressions.rst", ".. _genexpr:", ".. _yieldexpr:"),
    ("evaluation-order", "reference/expressions.rst", ".. _evalorder:", ".. _operator-summary:"),
    ("precedence", "reference/expressions.rst", ".. _operator-summary:", None),
]


def python_patterns() -> list[dict]:
    records = []
    for name, rel, begin, end in PYTHON_SECTIONS:
        path = ROOT / "sources" / "cpython" / "Doc" / rel
        text = path.read_text()
        start = text.index(begin)
        stop = text.index(end, start + len(begin)) if end else len(text)
        docs = text[start:stop].strip()
        records.append({
            "id": f"python:{name}", "name": name, "kind": "language_semantics",
            "family": "cpython", "category": "language_semantics", "status": "python-3.13",
            "documentation": docs,
            "provenance": reference("cpython", path, text.count("\n", 0, start) + 1, text.count("\n", 0, start + len(docs)) + 1),
        })
    return records


def ingest() -> dict:
    records = sorted(ruff_patterns() + bugbear_patterns() + python_patterns(), key=lambda r: r["id"])
    if len({r["id"] for r in records}) != len(records):
        raise ValueError("Duplicate pattern IDs")
    dump_jsonl(ROOT / "data" / "patterns.jsonl", records)
    manifest = {"schema_version": 1, "snapshot_date": "2026-10-26", "sources": [], "pattern_count": len(records)}
    for name, (repo, revision, license_name) in SOURCES.items():
        files = []
        for path in sorted((ROOT / "sources" / name).rglob("*")):
            if path.is_file():
                files.append({"path": path.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size})
        manifest["sources"].append({"id": name, "repository": f"https://github.com/{repo}", "revision": revision, "license": license_name, "license_path": f"sources/{name}/LICENSE", "files": files})
    (ROOT / "data" / "sources.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    return {"patterns": len(records), "source_files": sum(len(s["files"]) for s in manifest["sources"])}


if __name__ == "__main__":
    print(json.dumps(ingest(), indent=2))
