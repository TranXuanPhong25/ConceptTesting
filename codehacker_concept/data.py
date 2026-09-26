"""Dataset access for CodeHacker-Plus (authors' release) and CodeContests+.

The CodeHacker authors released two HuggingFace datasets under ``sjw712``:

* ``sjw712/CodeHacker-Plus`` -- 2,000 problems (``traditional_judge/`` and
  ``special_judge/``, 5 parquet batches each). This matches the paper's
  2,000-problem CodeContests++ (1,000 standard + 1,000 special judge).
* ``sjw712/CodeHacker`` -- 5,039 problems with the same schema.

Schema: ``id, incorrect_codes[list], correct_code, description, checker,
validator, test_cases[list{input,output}], hack_url, time_limit, memory_limit``.
``validator`` and ``checker`` are testlib programs (the calibrated, human
audited Phase I tools); ``incorrect_codes`` are the target submissions.

``test_cases`` is tens of GB, so everything here reads parquet column chunks
with HTTP range requests and caches the small columns as JSONL under
``data_dir()`` (outside git).
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import random
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Iterator

HF = "https://huggingface.co/datasets"
PLUS_REPO = "sjw712/CodeHacker-Plus"
FULL_REPO = "sjw712/CodeHacker"
CCPLUS_REPO = "ByteDance-Seed/Code-Contests-Plus"
PLUS_FILES = [f"{kind}/batch_{i:03d}.parquet" for kind in ("traditional_judge", "special_judge") for i in range(1, 6)]
FULL_FILES = [f"part-{i:05d}-of-00030_filtered.parquet" for i in range(30)]
CCPLUS_FILES = [f"part-{i:05d}-of-00010.parquet" for i in range(10)]
SMALL_COLUMNS = [
    "id",
    "incorrect_codes",
    "correct_code",
    "description",
    "checker",
    "validator",
    "hack_url",
    "time_limit",
    "memory_limit",
]


def data_dir() -> Path:
    path = Path(os.environ.get("CH_DATA_DIR", Path.home() / ".cache" / "codehacker_concept"))
    path.mkdir(parents=True, exist_ok=True)
    return path


class HttpRangeFile(io.RawIOBase):
    """Seekable read-only file over HTTP range requests (for pyarrow)."""

    def __init__(self, url: str, timeout: float = 300.0, retries: int = 5):
        super().__init__()
        self.url = url
        self.timeout = timeout
        self.retries = retries
        request = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(request, timeout=60) as response:
            self.final_url = response.geturl()
            self.size = int(response.headers["Content-Length"])
        self.pos = 0
        self.bytes_fetched = 0

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        return self.pos

    def seek(self, offset: int, whence: int = 0) -> int:
        if whence == 0:
            self.pos = offset
        elif whence == 1:
            self.pos += offset
        else:
            self.pos = self.size + offset
        return self.pos

    def read(self, n: int = -1) -> bytes:
        if n is None or n < 0:
            n = self.size - self.pos
        if n == 0 or self.pos >= self.size:
            return b""
        end = min(self.size, self.pos + n) - 1
        last: Exception | None = None
        for attempt in range(self.retries):
            try:
                request = urllib.request.Request(self.final_url, headers={"Range": f"bytes={self.pos}-{end}"})
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    data = response.read()
                break
            except Exception as exc:  # noqa: BLE001 - transient network errors
                last = exc
                time.sleep(2 * (attempt + 1))
                # signed CDN URLs expire; refresh through the canonical URL
                try:
                    head = urllib.request.Request(self.url, method="HEAD")
                    with urllib.request.urlopen(head, timeout=60) as response:
                        self.final_url = response.geturl()
                except Exception:  # noqa: BLE001
                    pass
        else:
            raise OSError(f"range read failed for {self.url}: {last}")
        self.pos += len(data)
        self.bytes_fetched += len(data)
        return data

    def readinto(self, buffer) -> int:  # type: ignore[override]
        data = self.read(len(buffer))
        buffer[: len(data)] = data
        return len(data)


def _resolve(repo: str, path: str) -> str:
    return f"{HF}/{repo}/resolve/main/{path}"


def read_parquet_columns(repo: str, path: str, columns: list[str]) -> list[dict[str, Any]]:
    import pyarrow.parquet as pq

    handle = HttpRangeFile(_resolve(repo, path))
    parquet = pq.ParquetFile(handle)
    rows: list[dict[str, Any]] = []
    for group in range(parquet.metadata.num_row_groups):
        rows.extend(parquet.read_row_group(group, columns=columns).to_pylist())
    return rows


@dataclass
class Problem:
    """One CodeHacker-Plus problem (small columns only)."""

    id: str
    description: str
    correct_code: str
    incorrect_codes: list[str]
    validator: str
    checker: str
    time_limit_ms: int
    memory_limit_mb: int
    judge_type: str  # "traditional" | "special"
    source_file: str
    hack_url: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def contest_id(self) -> str:
        return self.id.split("_")[0]

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "correct_code": self.correct_code,
            "incorrect_codes": self.incorrect_codes,
            "validator": self.validator,
            "checker": self.checker,
            "time_limit_ms": self.time_limit_ms,
            "memory_limit_mb": self.memory_limit_mb,
            "judge_type": self.judge_type,
            "source_file": self.source_file,
            "hack_url": self.hack_url,
            "extra": self.extra,
        }

    @classmethod
    def from_json(cls, row: dict[str, Any]) -> "Problem":
        return cls(**row)


def _problem_from_row(row: dict[str, Any], source_file: str) -> Problem:
    judge_type = "special" if source_file.startswith("special_judge") else "traditional"
    return Problem(
        id=str(row["id"]),
        description=row["description"] or "",
        correct_code=row["correct_code"] or "",
        incorrect_codes=list(row["incorrect_codes"] or []),
        validator=row["validator"] or "",
        checker=row["checker"] or "",
        time_limit_ms=int(row["time_limit"] or 1000),
        memory_limit_mb=int(row["memory_limit"] or 256),
        judge_type=judge_type,
        source_file=source_file,
        hack_url=row.get("hack_url") or "",
    )


def plus_cache_path() -> Path:
    return data_dir() / "codehacker_plus_small.jsonl"


def fetch_plus_metadata(force: bool = False) -> Path:
    """Download the small columns of all CodeHacker-Plus batches (resume-safe)."""
    out = plus_cache_path()
    done: set[str] = set()
    if out.exists() and not force:
        with out.open() as handle:
            for line in handle:
                if line.strip():
                    done.add(json.loads(line)["source_file"])
    with out.open("a") as handle:
        for path in PLUS_FILES:
            if path in done:
                continue
            rows = read_parquet_columns(PLUS_REPO, path, SMALL_COLUMNS)
            for row in rows:
                handle.write(json.dumps(_problem_from_row(row, path).to_json(), ensure_ascii=False) + "\n")
            handle.flush()
            print(f"fetched {path}: {len(rows)} problems", flush=True)
    return out


def load_plus() -> list[Problem]:
    path = plus_cache_path()
    if not path.exists():
        raise FileNotFoundError(f"{path} missing; run `python -m codehacker_concept.data fetch-plus`")
    seen: dict[str, Problem] = {}
    with path.open() as handle:
        for line in handle:
            if line.strip():
                problem = Problem.from_json(json.loads(line))
                seen.setdefault(problem.id, problem)
    return list(seen.values())


def full_ids_cache_path() -> Path:
    return data_dir() / "codehacker_full_small.jsonl"


def fetch_full_metadata(files: Iterable[str] | None = None) -> Path:
    """Small columns of the 5,039-problem ``sjw712/CodeHacker`` (KB source pool)."""
    out = full_ids_cache_path()
    done: set[str] = set()
    if out.exists():
        with out.open() as handle:
            for line in handle:
                if line.strip():
                    done.add(json.loads(line)["source_file"])
    with out.open("a") as handle:
        for path in files or FULL_FILES:
            if path in done:
                continue
            rows = read_parquet_columns(FULL_REPO, path, SMALL_COLUMNS)
            for row in rows:
                problem = _problem_from_row(row, path)
                problem.judge_type = "unknown"
                handle.write(json.dumps(problem.to_json(), ensure_ascii=False) + "\n")
            handle.flush()
            print(f"fetched {path}: {len(rows)} problems", flush=True)
    return out


def load_full() -> list[Problem]:
    path = full_ids_cache_path()
    seen: dict[str, Problem] = {}
    if path.exists():
        with path.open() as handle:
            for line in handle:
                if line.strip():
                    problem = Problem.from_json(json.loads(line))
                    seen.setdefault(problem.id, problem)
    return list(seen.values())


# ---------------------------------------------------------------- CodeContests+

CCPLUS_COLUMNS = ["id", "source", "validator", "generator", "generator_cmd", "correct_submissions"]
MAX_CORRECT = 12


def _is_cpp(language: str) -> bool:
    lang = (language or "").lower()
    return "c++" in lang or "cpp" in lang or lang in {"cpp", "c++"}


def ccplus_cache_path() -> Path:
    return data_dir() / "ccplus_small.jsonl"


def ccplus_id(problem_id: str) -> str:
    """CodeHacker-Plus and CodeContests+ share Codeforces ids such as ``1419_B``."""
    return problem_id


def fetch_ccplus(wanted_ids: set[str]) -> Path:
    """Fetch CodeContests+ rows (generator + submissions) for the given CH ids."""
    import pyarrow.parquet as pq

    out = ccplus_cache_path()
    have: set[str] = set()
    if out.exists():
        with out.open() as handle:
            for line in handle:
                if line.strip():
                    have.add(json.loads(line)["ch_id"])
    targets = {ccplus_id(pid): pid for pid in wanted_ids if pid not in have}
    if not targets:
        return out
    with out.open("a") as sink:
        for path in CCPLUS_FILES:
            if not targets:
                break
            handle = HttpRangeFile(_resolve(CCPLUS_REPO, path))
            parquet = pq.ParquetFile(handle)
            for group in range(parquet.metadata.num_row_groups):
                ids = parquet.read_row_group(group, columns=["id"]).column(0).to_pylist()
                hit = [i for i, value in enumerate(ids) if str(value) in targets]
                if not hit:
                    continue
                table = parquet.read_row_group(group, columns=CCPLUS_COLUMNS)
                rows = table.to_pylist()
                for index in hit:
                    row = rows[index]
                    ch = targets.pop(str(row["id"]))
                    row["ch_id"] = ch
                    correct = [s for s in (row.get("correct_submissions") or []) if _is_cpp(s.get("language", ""))]
                    row["n_correct_cpp"] = len(correct)
                    row["correct_submissions"] = correct[:MAX_CORRECT]
                    sink.write(json.dumps(row, ensure_ascii=False) + "\n")
                sink.flush()
            print(f"scanned {path}; remaining {len(targets)}", flush=True)
    return out


def load_ccplus() -> dict[str, dict[str, Any]]:
    path = ccplus_cache_path()
    rows: dict[str, dict[str, Any]] = {}
    if path.exists():
        with path.open() as handle:
            for line in handle:
                if line.strip():
                    row = json.loads(line)
                    rows[row["ch_id"]] = row
    return rows


# ---------------------------------------------------------------- test cases


def testcase_dir() -> Path:
    path = data_dir() / "testcases"
    path.mkdir(parents=True, exist_ok=True)
    return path


def fetch_plus_testcases(source_file: str, wanted_ids: set[str], max_tests: int = 400) -> dict[str, int]:
    """Download one CodeHacker-Plus batch's ``test_cases`` and keep wanted ids.

    The column chunk spans the whole file, so this streams it once (GBs) and
    writes per-problem JSONL files (first ``max_tests`` tests).
    """
    import pyarrow.parquet as pq

    handle = HttpRangeFile(_resolve(PLUS_REPO, source_file), timeout=900)
    parquet = pq.ParquetFile(handle, buffer_size=1 << 26)
    written: dict[str, int] = {}
    for group in range(parquet.metadata.num_row_groups):
        table = parquet.read_row_group(group, columns=["id", "test_cases"])
        ids = table.column("id").to_pylist()
        for index, pid in enumerate(ids):
            if pid not in wanted_ids:
                continue
            tests = table.column("test_cases")[index].as_py() or []
            out = testcase_dir() / f"{pid}.jsonl"
            with out.open("w") as sink:
                for test in tests[:max_tests]:
                    sink.write(json.dumps({"input": test["input"], "output": test["output"]}) + "\n")
            written[pid] = min(len(tests), max_tests)
    return written


def load_testcases(problem_id: str) -> list[dict[str, str]]:
    path = testcase_dir() / f"{problem_id}.jsonl"
    if not path.exists():
        return []
    with path.open() as handle:
        return [json.loads(line) for line in handle if line.strip()]


# ---------------------------------------------------------------- pairs


@dataclass(frozen=True)
class Pair:
    problem_id: str
    index: int  # index into Problem.incorrect_codes

    @property
    def key(self) -> str:
        return f"{self.problem_id}#{self.index}"


def code_fingerprint(code: str) -> str:
    return hashlib.sha1(" ".join(code.split()).encode()).hexdigest()[:12]


def all_pairs(problems: Iterable[Problem]) -> list[Pair]:
    pairs = []
    for problem in problems:
        seen: set[str] = set()
        for index, code in enumerate(problem.incorrect_codes):
            fp = code_fingerprint(code)
            if fp in seen:
                continue
            seen.add(fp)
            pairs.append(Pair(problem.id, index))
    return pairs


def seeded_subset(pairs: list[Pair], n: int, seed: int, one_per_problem: bool = True) -> list[Pair]:
    rng = random.Random(seed)
    shuffled = pairs[:]
    rng.shuffle(shuffled)
    chosen: list[Pair] = []
    used: set[str] = set()
    for pair in shuffled:
        if one_per_problem and pair.problem_id in used:
            continue
        chosen.append(pair)
        used.add(pair.problem_id)
        if len(chosen) >= n:
            break
    return sorted(chosen, key=lambda p: p.key)


def iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    if not path.exists():
        return
    with path.open() as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Fetch CodeHacker datasets into the local cache")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("fetch-plus")
    full = sub.add_parser("fetch-full")
    full.add_argument("--files", nargs="*")
    sub.add_parser("stats")
    sub.add_parser("fetch-ccplus")
    args = parser.parse_args()
    if args.cmd == "fetch-plus":
        print(fetch_plus_metadata())
    elif args.cmd == "fetch-full":
        print(fetch_full_metadata(args.files))
    elif args.cmd == "fetch-ccplus":
        print(fetch_ccplus({p.id for p in load_plus()}))
    elif args.cmd == "stats":
        problems = load_plus()
        pairs = all_pairs(problems)
        by_type: dict[str, int] = {}
        for problem in problems:
            by_type[problem.judge_type] = by_type.get(problem.judge_type, 0) + 1
        print(json.dumps({"problems": len(problems), "by_type": by_type, "dedup_pairs": len(pairs),
                          "raw_pairs": sum(len(p.incorrect_codes) for p in problems)}, indent=1))


if __name__ == "__main__":
    main()
