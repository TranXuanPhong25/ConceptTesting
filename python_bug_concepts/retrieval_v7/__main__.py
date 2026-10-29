"""Opt-in V7 CLI; default root API remains frozen V2."""
import argparse
import json
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description="Independent full-corpus concept retrieval v7")
    p.add_argument("command", choices=["search", "prepare-model", "validate-evidence"])
    p.add_argument("query", nargs="?", default="")
    p.add_argument("--code", type=Path)
    p.add_argument("--arm", choices=["A", "B", "C", "D"], default="A")
    p.add_argument("--top-k", type=int, default=3)
    args = p.parse_args()
    if args.command == "prepare-model":
        from .dense import prepare
        result = prepare()
    elif args.command == "validate-evidence":
        from .concept_evidence import load_overlay
        overlay = load_overlay()
        result = {"cards": len(overlay), "families": len({r["family"] for r in overlay.values()}),
                  "status": "conditional_documentation_evidence_not_target_truth"}
    else:
        if args.code is None:
            p.error("search requires --code")
        from .hybrid_engine import Retriever
        encoder = None
        if args.arm in ("B", "D"):
            from .dense import Encoder
            encoder = Encoder()
        r = Retriever(encoder=encoder)
        try:
            result = r.search(args.query, code=args.code.read_text(), arm=args.arm, top_k=args.top_k)
            if encoder:
                result["embedding_work"] = {"new_texts": encoder.calls, "cached_texts": encoder.hits,
                                            "truncated_texts": encoder.truncated}
        finally:
            r.close()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
