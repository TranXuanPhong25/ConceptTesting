from __future__ import annotations

import argparse
import json
from pathlib import Path

from .dataset import seeded_tuning_subset, validate_manifest, write_manifest
from .metrics import paired_comparison, project_rbdr, rbdr
from .pit import parse_pit_report


def main() -> None:
    parser = argparse.ArgumentParser(description="KITE concept-extension research utilities")
    commands = parser.add_subparsers(dest="command", required=True)
    pit = commands.add_parser("parse-pit")
    pit.add_argument("report")
    pit.add_argument("--out", required=True)
    subset = commands.add_parser("tuning-subset")
    subset.add_argument("manifest")
    subset.add_argument("--out", required=True)
    subset.add_argument("--size", type=int, default=40)
    subset.add_argument("--seed", type=int, default=260711573)
    score = commands.add_parser("score")
    score.add_argument("results")
    score.add_argument("--left", default="kite")
    score.add_argument("--right", default="mutgen")
    args = parser.parse_args()
    if args.command == "parse-pit":
        rows = parse_pit_report(args.report)
        Path(args.out).write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))
    elif args.command == "tuning-subset":
        payload = json.loads(Path(args.manifest).read_text())
        rows = validate_manifest(payload["tasks"])
        chosen = seeded_tuning_subset(rows, args.size, args.seed)
        write_manifest(Path(args.out), chosen, {"source_manifest": args.manifest, "seed": args.seed, "size": args.size})
    else:
        rows = [json.loads(line) for line in Path(args.results).read_text().splitlines() if line.strip()]
        by_arm = {arm: {row["task_id"]: bool(row["detected"]) for row in rows if row["arm"] == arm}
                  for arm in {row["arm"] for row in rows}}
        summary = {arm: {"rbdr": rbdr([{"detected": value} for value in values.values()])}
                   for arm, values in by_arm.items()}
        summary["paired"] = paired_comparison(by_arm[args.left], by_arm[args.right])
        print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

