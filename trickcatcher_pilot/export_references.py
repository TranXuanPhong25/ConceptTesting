"""Export EvalPlus canonical code for a deliberately leaky upper-bound arm."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    from evalplus.data import get_human_eval_plus

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=int, default=13)
    parser.add_argument("--limit", type=int, default=13)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    tasks = get_human_eval_plus()
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w") as handle:
        for task_num in range(args.start, args.start + args.limit):
            task = tasks[f"HumanEval/{task_num}"]
            handle.write(json.dumps({
                "task_num": task_num,
                "canonical_source": task["prompt"] + task["canonical_solution"],
                "entry_point": task["entry_point"],
            }) + "\n")
    print(f"exported {args.limit} private reference records -> {output}")


if __name__ == "__main__":
    main()
