import argparse
import json
from pathlib import Path

from .engine import build, search

parser = argparse.ArgumentParser(description="Semantic Python concept retrieval v6")
parser.add_argument("command", choices=["build", "search"])
parser.add_argument("query", nargs="?", default="")
parser.add_argument("--code", type=Path)
parser.add_argument("--top-k", type=int, default=3)
parser.add_argument("--mode", choices=["hybrid", "lexical"], default="hybrid")
parser.add_argument("--json", action="store_true")
parser.add_argument("--policy", choices=["coverage", "balanced", "precise"], default="balanced")
args = parser.parse_args()
if args.command == "build":
    print(json.dumps(build(), indent=2))
else:
    result = search(
        args.query,
        code=args.code.read_text() if args.code else None,
        top_k=args.top_k,
        mode=args.mode,
        policy=args.policy,
    )
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        for hit in result["results"]:
            card = hit["concept"]
            print(f"\n{card['id']} — {card['title']}")
            for row in hit["evidence"][:3]:
                print(f"  L{row['line']}: {row['expression'].replace(chr(10), ' ')[:150]}")
                print("    " + row["reason"])
            print("  how: " + card["how"]["trigger_template"])
            print("  what: " + card["what"]["oracle_template"])
