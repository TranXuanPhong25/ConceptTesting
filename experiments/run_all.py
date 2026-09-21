#!/usr/bin/env python3
"""Run the five bounded, local concept-guided C testing smoke experiments."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
COMMANDS = (
    ("STRUT", ["python3", "experiments/strut/run.py"]),
    ("HGFuzzer", ["python3", "experiments/hgfuzzer/run.py", "--smoke", "--cases", "4", "--timeout", "2"]),
    ("CKGFuzzer", ["python3", "experiments/ckgfuzzer/run_experiment.py"]),
    ("G2FUZZ", ["uv", "run", "python", "experiments/g2fuzz/run.py", "--mutations", "16"]),
    ("LLAMAFUZZ", ["python3", "experiments/llamafuzz/structured_mutation.py"]),
)


def main() -> int:
    failed: list[str] = []
    for name, command in COMMANDS:
        print(f"\n=== {name} ===", flush=True)
        result = subprocess.run(command, cwd=ROOT, check=False)
        if result.returncode:
            failed.append(name)
            print(f"{name}: FAIL ({result.returncode})", file=sys.stderr)
        else:
            print(f"{name}: PASS")

    if failed:
        print(f"\nFailed tracks: {', '.join(failed)}", file=sys.stderr)
        return 1
    print("\nAll five bounded smoke tracks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
