"""Validate the corpus, export cards, and retrieve with SQLite FTS5/BM25.

Only Python's standard library is used. Code inputs are parsed, never executed.
Retrieval results are hypotheses about applicability, not confirmed bug reports.
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
import sqlite3
import string
import unicodedata
from collections import Counter
from contextlib import closing
from pathlib import Path

from .ingest import ROOT, dump_jsonl

DEFAULT_DB = ROOT / "index.sqlite3"
INDEX_VERSION = "3"
STOPWORDS = set("""
a an the and or is are was were be been being to of in on at for with from as by
it its this that these those i we you they he she my your our their do does did
not no can could would should have has had when where how what why which while
into than then if else through after before about me please find show bug bugs
pattern patterns python code
và là của trong khi thì cho có một các những với từ trên dưới cần tìm tôi mình
bị được tại sao gì như nào hay hoặc vì về này đó mà vào ra
""".split())


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def template_slots(card: dict) -> list[str]:
    fields = (
        card["where"]["location_template"], card["how"]["trigger_template"],
        card["what"]["oracle_template"],
    )
    slots = set()
    for template in fields:
        for _, name, spec, conversion in string.Formatter().parse(template):
            if name is not None:
                if not re.fullmatch(r"[a-z][a-z0-9_]*", name) or spec or conversion:
                    raise ValueError(f"Invalid template slot: {name}")
                slots.add(name)
    return sorted(slots)


def source_path(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if not path.is_relative_to((root / "sources").resolve()):
        raise ValueError(f"Source path outside sources/: {relative}")
    return path


def validate(root: Path = ROOT) -> dict:
    manifest = json.loads((root / "data" / "sources.json").read_text())
    patterns = load_jsonl(root / "data" / "patterns.jsonl")
    cards = json.loads((root / "data" / "concepts.json").read_text())
    exclusions = json.loads((root / "data" / "exclusions.json").read_text())
    errors = []
    if not cards or not patterns:
        errors.append("Empty corpus")
    pattern_map = {p["id"]: p for p in patterns}
    if len(pattern_map) != len(patterns):
        errors.append("Duplicate pattern IDs")
    if manifest["pattern_count"] != len(patterns):
        errors.append("Manifest pattern count differs")
    inventory = {}
    for source in manifest["sources"]:
        for item in source["files"]:
            path = source_path(root, item["path"])
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
                errors.append(f"Source hash mismatch: {item['path']}")
            inventory[item["path"]] = (source, item)
    for pattern in patterns:
        ref = pattern["provenance"]
        if ref["path"] not in inventory:
            errors.append(f"Missing inventory entry: {pattern['id']}")
            continue
        source, item = inventory[ref["path"]]
        if ref["sha256"] != item["sha256"] or ref["revision"] != source["revision"] or ref["source"] != source["id"]:
            errors.append(f"Provenance mismatch: {pattern['id']}")
        path = source_path(root, ref["path"])
        if path.is_file() and not (1 <= ref["start_line"] <= ref["end_line"] <= len(path.read_text().splitlines())):
            errors.append(f"Invalid source line span: {pattern['id']}")
        if not pattern["documentation"].strip():
            errors.append(f"Empty pattern documentation: {pattern['id']}")
    seen, linked = set(), set()
    for card in cards:
        name = card.get("id", "<missing>")
        try:
            if not re.fullmatch(r"py\.[a-z0-9]+(?:-[a-z0-9]+)*", name):
                raise ValueError("Invalid concept ID")
            if name in seen:
                raise ValueError("Duplicate concept ID")
            seen.add(name)
            if card["schema_version"] != 1 or card["language"] != "python" or card["evidence_status"] != "curated_hypothesis":
                raise ValueError("Unsupported concept version/language/evidence status")
            for value in (card["title"], card["category"], card["where"]["summary"],
                          card["where"]["location_template"], card["how"]["mechanism"],
                          card["how"]["trigger_template"], card["what"]["observable_failure"],
                          card["what"]["oracle_template"]):
                if not isinstance(value, str) or not value.strip():
                    raise ValueError("Empty or invalid required text")
            for key in ("aliases", "pattern_ids", "applicability_notes"):
                if not isinstance(card[key], list) or not card[key] or not all(isinstance(x, str) and x.strip() for x in card[key]):
                    raise ValueError(f"Empty or invalid {key}")
            if not card["where"]["preconditions"] or not card["where"]["ast_nodes"]:
                raise ValueError("Missing applicability information")
            for node in card["where"]["ast_nodes"]:
                if not isinstance(getattr(ast, node, None), type) or not issubclass(getattr(ast, node), ast.AST):
                    raise ValueError(f"Unknown AST node: {node}")
            for ref in card["pattern_ids"]:
                linked.add(ref)
                if ref not in pattern_map:
                    raise ValueError(f"Unknown pattern: {ref}")
            if len(card["pattern_ids"]) != len(set(card["pattern_ids"])):
                raise ValueError("Duplicate pattern references")
            if template_slots(card) != card["required_bindings"]:
                raise ValueError("Template slots differ from required_bindings")
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"{name}: {exc}")
    excluded = set()
    allowed_kinds = {"style", "redundancy", "typing_convention", "source_spelling", "tool_configuration"}
    for decision in exclusions:
        ref = decision.get("pattern_id")
        if ref not in pattern_map:
            errors.append(f"Unknown excluded pattern: {ref}")
        if ref in excluded:
            errors.append(f"Duplicate exclusion: {ref}")
        excluded.add(ref)
        if ref in linked:
            errors.append(f"Pattern both mapped and excluded: {ref}")
        if decision.get("kind") not in allowed_kinds:
            errors.append(f"Invalid exclusion kind: {ref}")
        if not isinstance(decision.get("reason"), str) or not decision["reason"].strip():
            errors.append(f"Missing exclusion reason: {ref}")
    unresolved = pattern_map.keys() - linked - excluded
    if unresolved:
        errors.append("Unresolved patterns: " + ", ".join(sorted(unresolved)))
    if errors:
        raise ValueError("Corpus validation failed:\n" + "\n".join(errors))
    return {
        "concepts": len(cards), "patterns": len(patterns), "linked_patterns": len(linked),
        "excluded_patterns": len(excluded), "unresolved_patterns": len(unresolved), "source_files": len(inventory),
        "sources": len(manifest["sources"]), "categories": dict(sorted(Counter(c["category"] for c in cards).items())),
    }


def corpus_digest(root: Path = ROOT) -> str:
    digest = hashlib.sha256(INDEX_VERSION.encode())
    for name in ("concepts.json", "patterns.jsonl", "sources.json", "exclusions.json"):
        digest.update((root / "data" / name).read_bytes())
    return digest.hexdigest()


def enriched_cards(root: Path = ROOT) -> list[dict]:
    patterns = {p["id"]: p for p in load_jsonl(root / "data" / "patterns.jsonl")}
    cards = json.loads((root / "data" / "concepts.json").read_text())
    for card in cards:
        card["sources"] = [{
            "pattern_id": ref, "rule_code": patterns[ref].get("rule_code"),
            "kind": patterns[ref]["kind"], "status": patterns[ref]["status"],
            **patterns[ref]["provenance"],
        } for ref in card["pattern_ids"]]
    return cards


def export(root: Path = ROOT) -> None:
    cards = enriched_cards(root)
    dump_jsonl(root / "data" / "concepts.jsonl", cards)
    patterns = load_jsonl(root / "data" / "patterns.jsonl")
    linked = {ref for card in cards for ref in card["pattern_ids"]}
    exclusions = {d["pattern_id"]: d for d in json.loads((root / "data" / "exclusions.json").read_text())}
    decisions = []
    for pattern in patterns:
        ref = pattern["id"]
        if ref in linked:
            decision = {"pattern_id": ref, "disposition": "mapped", "concept_ids": [c["id"] for c in cards if ref in c["pattern_ids"]]}
        elif ref in exclusions:
            decision = {**exclusions[ref], "disposition": "excluded"}
        else:
            decision = {"pattern_id": ref, "disposition": "unresolved"}
        decisions.append({**decision, "name": pattern["name"], "source_status": pattern["status"], "source_url": pattern["provenance"]["url"]})
    unresolved = [d for d in decisions if d["disposition"] == "unresolved"]
    coverage = {
        "schema_version": 2,
        "concept_count": len(cards), "pattern_count": len(patterns),
        "linked_pattern_count": len(linked), "excluded_pattern_count": len(exclusions),
        "unresolved_pattern_count": len(unresolved),
        "concept_to_patterns": {card["id"]: card["pattern_ids"] for card in cards},
        "pattern_decisions": decisions,
        "excluded_patterns": [d for d in decisions if d["disposition"] == "excluded"],
        "unresolved_patterns": unresolved,
    }
    (root / "data" / "coverage.json").write_text(json.dumps(coverage, ensure_ascii=False, indent=2) + "\n")
    coverage_lines = ["# Source pattern coverage", "",
                      f"{len(patterns)} raw records = {len(linked)} mapped + {len(exclusions)} explicitly excluded + {len(unresolved)} unresolved.", "",
                      "Mapped records can share a concept. Exclusions retain their original documentation and provenance in `data/patterns.jsonl`.", "",
                      "## Explicit exclusions", "", "| Pattern | Kind | Reason |", "| --- | --- | --- |"]
    for decision in decisions:
        if decision["disposition"] == "excluded":
            coverage_lines.append(f"| [{decision['pattern_id']}]({decision['source_url']}) | {decision['kind']} | {decision['reason'].replace('|', '&#124;')} |")
    coverage_lines += ["", "## Complete record accounting", "", "| Pattern | Disposition | Concepts / reason |", "| --- | --- | --- |"]
    for decision in decisions:
        detail = ", ".join(decision.get("concept_ids", [])) or decision.get("reason", "Review required")
        coverage_lines.append(f"| [{decision['pattern_id']}]({decision['source_url']}) | {decision['disposition']} | {detail.replace('|', '&#124;')} |")
    (root / "COVERAGE.md").write_text("\n".join(coverage_lines) + "\n")
    lines = ["# Python bug concept catalog", "", "Generated from `data/concepts.json`. Templates require a target contract; cards are hypotheses, not confirmed diagnoses.", ""]
    for card in cards:
        lines += [f"## {card['id']} — {card['title']}", "", f"Category: `{card['category']}`", "",
                  f"**Where:** {card['where']['summary']}",
                  f"**Preconditions:** {' '.join(card['where']['preconditions'])}", "",
                  f"**Where template:** {card['where']['location_template']}", "",
                  f"**How:** {card['how']['mechanism']}",
                  f"**Trigger template:** {card['how']['trigger_template']}", "",
                  f"**What:** {card['what']['observable_failure']}",
                  f"**Oracle template:** {card['what']['oracle_template']}", "",
                  f"**Applicability:** {' '.join(card['applicability_notes'])}", "",
                  "**Sources:** " + ", ".join(f"[{s['pattern_id']}]({s['url']}) ({s['status']})" for s in card["sources"]), ""]
    (root / "CATALOG.md").write_text("\n".join(lines))


def build_index(db: Path = DEFAULT_DB, root: Path = ROOT) -> dict:
    stats = validate(root)
    cards = enriched_cards(root)
    db = Path(db)
    db.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(db)) as connection, connection:
        connection.execute("BEGIN")
        connection.execute("DROP TABLE IF EXISTS concepts_fts")
        connection.execute("DROP TABLE IF EXISTS concept_sources")
        connection.execute("DROP TABLE IF EXISTS concepts")
        connection.execute("DROP TABLE IF EXISTS metadata")
        connection.execute("CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        connection.execute("CREATE TABLE concepts (id TEXT PRIMARY KEY, category TEXT NOT NULL, card TEXT NOT NULL)")
        connection.execute("CREATE TABLE concept_sources (id TEXT NOT NULL, source TEXT NOT NULL, PRIMARY KEY (id, source))")
        connection.execute("""CREATE VIRTUAL TABLE concepts_fts USING fts5(
            id UNINDEXED, title, aliases, where_text, how_text, what_text, evidence, category,
            tokenize='unicode61 remove_diacritics 2'
        )""")
        for card in cards:
            connection.execute("INSERT INTO concepts VALUES (?, ?, ?)", (card["id"], card["category"], json.dumps(card, ensure_ascii=False)))
            connection.executemany("INSERT INTO concept_sources VALUES (?, ?)", [(card["id"], source) for source in sorted({s["source"] for s in card["sources"]})])
            connection.execute("INSERT INTO concepts_fts VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (
                card["id"], normalized(card["title"]), normalized(" ".join(card["aliases"])),
                normalized(" ".join([card["where"]["summary"], *card["where"]["preconditions"], *card["where"]["ast_nodes"]])),
                normalized(" ".join(card["how"].values())), normalized(" ".join(card["what"].values())),
                normalized(" ".join(card["pattern_ids"])), card["category"],
            ))
        connection.execute("INSERT INTO metadata VALUES ('corpus_digest', ?)", (corpus_digest(root),))
    export(root)
    return {**stats, "database": str(db), "corpus_sha256": corpus_digest(root)}


def ensure_index(db: Path = DEFAULT_DB, root: Path = ROOT) -> None:
    stale = True
    if Path(db).is_file():
        try:
            with closing(sqlite3.connect(db)) as connection:
                row = connection.execute("SELECT value FROM metadata WHERE key='corpus_digest'").fetchone()
                stale = row is None or row[0] != corpus_digest(root)
        except sqlite3.DatabaseError:
            stale = True
    if stale:
        build_index(db, root)


def normalized(text: str) -> str:
    text = text.casefold().replace("đ", "d")
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


NORMALIZED_STOPWORDS = {normalized(s) for s in STOPWORDS}


def query_tokens(text: str) -> list[str]:
    # Treat user input as plain text, never as FTS query syntax or SQL.
    tokens = re.findall(r"[^\W_]+", normalized(text), re.UNICODE)
    return list(dict.fromkeys(t for t in tokens if t not in NORMALIZED_STOPWORDS))[:64]


def code_hints(code: str) -> tuple[str, str | None]:
    """Small structural hints for retrieval, deliberately not a bug detector."""
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError, RecursionError) as exc:
        # Fragments remain searchable as lexical input.
        return "", f"AST parsing unavailable: {type(exc).__name__}; lexical retrieval only"
    hints = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            defaults = [*node.args.defaults, *(d for d in node.args.kw_defaults if d is not None)]
            if any(isinstance(d, (ast.List, ast.Dict, ast.Set)) for d in defaults):
                hints.append("mutable argument default B006")
            if any(isinstance(d, ast.Call) for d in defaults):
                hints.append("function call default definition time B008")
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            if any(isinstance(n, (ast.Lambda, ast.FunctionDef, ast.AsyncFunctionDef)) for stmt in node.body for n in ast.walk(stmt)):
                hints.append("loop closure late binding B023")
        elif isinstance(node, ast.Try):
            if any(isinstance(n, (ast.Return, ast.Break, ast.Continue)) for stmt in node.finalbody for n in ast.walk(stmt)):
                hints.append("finally return swallowed exception B012")
        elif isinstance(node, ast.Assert):
            if isinstance(node.test, ast.Tuple):
                hints.append("assert tuple always true F631")
            if isinstance(node.test, ast.GeneratorExp):
                hints.append("assert generator B044")
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult):
            if any(isinstance(side, ast.List) and any(isinstance(e, (ast.List, ast.Dict, ast.Set, ast.BinOp)) for e in side.elts) for side in (node.left, node.right)):
                hints.append("matrix row repetition shared alias")
    return " ".join(dict.fromkeys(hints)), None


def search(query: str = "", *, code: str | None = None, top_k: int = 5,
           category: str | None = None, field: str = "all", source: str | None = None,
           db: Path = DEFAULT_DB, root: Path = ROOT) -> dict:
    if not 1 <= top_k <= 100:
        raise ValueError("top_k must be between 1 and 100")
    fields = {"where": "where_text", "how": "how_text", "what": "what_text"}
    if field not in {"all", *fields}:
        raise ValueError(f"Unknown search field: {field}")
    hints, warning = code_hints(code) if code is not None else ("", None)
    # A source file's identifiers are useful, but structural cues should not be
    # crowded out by the 64-token cap when files contain many unrelated names.
    tokens = query_tokens(" ".join([query, hints, code or ""]))
    if not tokens:
        return {"query": query, "code_hints": hints, "warning": warning, "results": []}
    ensure_index(db, root)
    match = " OR ".join('"' + t + '"' for t in tokens)
    if field != "all":
        match = fields[field] + " : (" + match + ")"
    conditions, args = ["concepts_fts MATCH ?"], [match]
    if category:
        conditions.append("c.category = ?")
        args.append(category)
    if source:
        conditions.append("EXISTS (SELECT 1 FROM concept_sources s WHERE s.id = c.id AND s.source = ?)")
        args.append(source)
    args.append(top_k)
    sql = """SELECT c.card, bm25(concepts_fts, 0, 6, 4, 2, 2, 1.5, 4, 1) AS rank
             FROM concepts_fts JOIN concepts c ON c.id = concepts_fts.id
             WHERE """ + " AND ".join(conditions) + " ORDER BY rank, c.id LIMIT ?"
    with closing(sqlite3.connect(db)) as connection:
        rows = connection.execute(sql, args).fetchall()
    results = []
    for payload, rank in rows:
        card = json.loads(payload)
        results.append({"score": -rank, "concept": card})
        if len(results) == top_k:
            break
    return {"query": query, "code_hints": hints, "warning": warning, "results": results,
            "retrieval": "SQLite FTS5 BM25 (lexical); score is not bug probability"}


def get_concept(concept_id: str, db: Path = DEFAULT_DB, root: Path = ROOT) -> dict:
    ensure_index(db, root)
    with closing(sqlite3.connect(db)) as connection:
        row = connection.execute("SELECT card FROM concepts WHERE id = ?", (concept_id,)).fetchone()
    if row is None:
        raise ValueError(f"Unknown concept: {concept_id}")
    return json.loads(row[0])


def render(card: dict, bindings: dict[str, str]) -> dict[str, str]:
    missing = set(card["required_bindings"]) - set(bindings)
    if missing:
        raise ValueError("Missing template bindings: " + ", ".join(sorted(missing)))
    if not all(isinstance(v, str) for v in bindings.values()):
        raise ValueError("Bindings must contain string values")
    return {
        "where": card["where"]["location_template"].format_map(bindings),
        "how": card["how"]["trigger_template"].format_map(bindings),
        "what": card["what"]["oracle_template"].format_map(bindings),
    }
