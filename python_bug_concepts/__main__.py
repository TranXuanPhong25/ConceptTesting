from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .base import DEFAULT_DB, build_index, render, validate
from .api import get_concept, search as routed_search


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Retrieve source-grounded Python bug concepts with where/how/what templates")
    parser.add_argument("--db", type=Path, help="Optional SQLite index path (otherwise chosen for the command/retriever)")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("build", help="Validate, build FTS5 index and export JSONL/Markdown")
    commands.add_parser("validate", help="Check concept references, template slots and source hashes")
    find = commands.add_parser("search", help="Retrieve hypotheses from plain text or a Python source file")
    find.add_argument("query", nargs="?", default="")
    find.add_argument("--code", type=Path, help="Parse and search this file; never execute it")
    find.add_argument("--top-k", type=int, default=5)
    find.add_argument("--category")
    find.add_argument("--source", choices=["ruff", "flake8-bugbear", "cpython"])
    find.add_argument("--field", choices=["all", "where", "how", "what"], default="all")
    find.add_argument("--json", action="store_true")
    find.add_argument("--retriever", choices=["auto", "original", "v2", "v5", "v6"], default="auto",
                      help="Auto uses structure-aware v2 for code/all-fields; original preserves lexical-only search")
    find.add_argument("--policy", choices=["coverage", "balanced", "precise"],
                      help="V6 only: balanced preserves a weak fallback; precise abstains without semantic support")
    show = commands.add_parser("show", help="Show a complete concept card, with its sources")
    show.add_argument("concept_id")
    bind = commands.add_parser("render", help="Bind the where/how/what template to a concrete target")
    bind.add_argument("concept_id")
    bind.add_argument("--bindings", type=Path, required=True, help="JSON file mapping template slots to strings")
    args = parser.parse_args(argv)
    try:
        if args.command == "build":
            result = build_index(args.db or DEFAULT_DB)
        elif args.command == "validate":
            result = validate()
        elif args.command == "show":
            result = get_concept(args.concept_id, args.db or DEFAULT_DB)
        elif args.command == "render":
            result = render(get_concept(args.concept_id, args.db or DEFAULT_DB), json.loads(args.bindings.read_text()))
        else:
            result = routed_search(args.query, code=args.code.read_text() if args.code else None,
                            top_k=args.top_k, category=args.category, field=args.field,
                            source=args.source, db=args.db, retriever=args.retriever, policy=args.policy)
            if not args.json:
                if result["warning"]:
                    print(result["warning"], file=sys.stderr)
                if result["code_hints"]:
                    print("Code retrieval hints: " + result["code_hints"])
                if not result["results"]:
                    print("No matching concepts.")
                for item in result["results"]:
                    card = item["concept"]
                    print(f"\n{card['id']} — {card['title']}")
                    print("  where: " + card["where"]["summary"])
                    print("  how:   " + card["how"]["trigger_template"])
                    print("  what:  " + card["what"]["oracle_template"])
                    print("  sources: " + ", ".join(card["pattern_ids"]))
                    for site in item.get("evidence", [])[:3]:
                        print(f"  L{site['line']}: " + site["expression"].replace("\n", " ")[:180])
                return 0
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(2, str(exc) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
