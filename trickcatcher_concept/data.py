"""TrickyBugs task loading for the full TrickCatcher pipeline.

Method-visible material follows the paper's problem definition (Sec. 3/4):
specification, PUT source and the *existing* test suite that the PUT passes.
Reference programs and additional (bug-revealing) tests are evaluation-only.
"""

from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass, field
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
TASKS_FILE = PACKAGE_DIR / "tasks.json"
EXCLUSIONS_FILE = PACKAGE_DIR / "exclusions.json"
DEFAULT_ARTIFACT = Path("/tmp/TrickCatcher-upstream")
DEFAULT_PROBLEMS = Path("/home/phong/dev/trickcatcher-concept-data/TrickyBugs/problems")
SUBSET_SEED = 20260926


@dataclass
class Task:
    lang: str
    pid: str
    put_name: str
    put_source: str
    description: str
    existing_tests: list[tuple[str, str]]  # (input, expected output); method-visible
    existing_source: str  # "original_test_cases" or "description_examples"
    references: list[Path] = field(default_factory=list)  # evaluation-only
    additional_tests: list[tuple[str, str]] = field(default_factory=list)  # evaluation-only

    @property
    def key(self) -> str:
        return f"{self.lang}/{self.pid}"


def parse_examples(description: str) -> list[tuple[str, str]]:
    """Extract sample (input, output) pairs from a TrickyBugs problem_description.txt."""
    marker = description.find("EXAMPLES:")
    if marker < 0:
        return []
    body = description[marker + len("EXAMPLES:"):]
    parts = re.split(r"^(INPUT|OUTPUT):[ \t]*$", body, flags=re.M)
    pairs: list[tuple[str, str]] = []
    pending: str | None = None
    for i in range(1, len(parts) - 1, 2):
        label, text = parts[i], parts[i + 1].strip("\n")
        text = text.strip()
        if label == "INPUT":
            pending = text + "\n"
        elif pending is not None:
            pairs.append((pending, text + "\n"))
            pending = None
    return pairs


def _read_pairs(directory: Path, limit_bytes: int = 8_000_000) -> list[tuple[str, str]]:
    pairs = []
    for path in sorted(directory.glob("*.in")):
        out = path.with_suffix(".out")
        if not out.is_file() or path.stat().st_size > limit_bytes:
            continue
        pairs.append((path.read_text(errors="replace"), out.read_text(errors="replace")))
    return pairs


def excluded_keys() -> set[tuple[str, str]]:
    """PUTs that fail to reproduce their own existing tests under our toolchain (see exclusions.json)."""
    if not EXCLUSIONS_FILE.is_file():
        return set()
    data_ = json.loads(EXCLUSIONS_FILE.read_text())
    return {(t["lang"], t["pid"]) for t in data_["tasks"]}


def task_index(include_excluded: bool = False) -> list[dict]:
    tasks = json.loads(TASKS_FILE.read_text())["tasks"]
    if include_excluded:
        return tasks
    excluded = excluded_keys()
    return [t for t in tasks if (t["lang"], t["pid"]) not in excluded]


def load_task(entry: dict, artifact: Path = DEFAULT_ARTIFACT, problems: Path = DEFAULT_PROBLEMS) -> Task:
    lang, pid = entry["lang"], entry["pid"]
    put_dir = Path(artifact) / "Datasets" / "TrickyBugs" / ("PUT_cpp" if lang == "cpp" else "PUT_python") / pid
    put_source = (put_dir / entry["put"]).read_text(errors="replace")
    pdir = Path(problems) / pid
    description = (pdir / "problem_description.txt").read_text(errors="replace")
    original = pdir / "original_test_cases"
    existing = _read_pairs(original) if original.is_dir() else []
    source = "original_test_cases"
    if not existing:
        existing = parse_examples(description)
        source = "description_examples"
    references = sorted((pdir / "reference_programs").glob("*.cpp"))
    additional = _read_pairs(pdir / "additional_test_cases") if (pdir / "additional_test_cases").is_dir() else []
    return Task(lang, pid, entry["put"], put_source, description, existing, source, references, additional)


def seeded_subset(n_cpp: int = 50, n_python: int = 25, seed: int = SUBSET_SEED) -> list[dict]:
    """Fixed tuning subset, drawn before any model call."""
    rng = random.Random(seed)
    tasks = task_index()
    cpp = sorted((t for t in tasks if t["lang"] == "cpp"), key=lambda t: t["pid"])
    py = sorted((t for t in tasks if t["lang"] == "python"), key=lambda t: t["pid"])
    chosen = rng.sample(cpp, n_cpp) + rng.sample(py, n_python)
    return sorted(chosen, key=lambda t: (t["lang"], t["pid"]))


def select(split: str) -> list[dict]:
    tasks = task_index()
    if split == "subset":
        return seeded_subset()
    if split == "full":
        return tasks
    if split == "heldout":
        chosen = {(t["lang"], t["pid"]) for t in seeded_subset()}
        return [t for t in tasks if (t["lang"], t["pid"]) not in chosen]
    if split in {"cpp", "python"}:
        return [t for t in tasks if t["lang"] == split]
    raise ValueError(split)
