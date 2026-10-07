#!/usr/bin/env python3
"""CoverUp (FSE'25) with concept facts in its segment prompt.

Arms (identical CoverUp settings, model, budget and seeds; only the first prompt of each segment differs):
  coverup         stock CoverUp gpt-v2 prompt
  concept         + C1-C8 facts (concept_annotator_py.functions) of the segment's functions that still miss coverage
  concept_reason  + the facts + a fixed testing recipe for each concept present
  placebo_reason  + the recipe, with facts taken from another function/class of the same package (seeded, closest
                    fact count, lines remapped into the segment), recipe rendered from the shown facts
  ide             + ruff warnings (CoSIL_concept rule set) on the segment's lines instead of facts

Injection point: GptV2Prompter.initial_prompt (vendor/coverup/src/coverup/prompt/gpt_v2.py). We register subclasses
in coverup.coverup.prompter_registry and append one block after the code excerpt; error and missing-coverage
follow-up prompts are untouched. Nothing under vendor/ is edited.

Arm-neutral patches: litellm.acreate (what coverup.llm.Chatter calls) gets Vertex settings (thinking budget 0, seed,
project/location, in-memory ADC credentials), one ledger line per call, and a global USD cap. Sandbox: the ADC JSON is
read into memory, then credential env vars are deleted and HOME points to an empty dir before CoverUp spawns any
pytest, so LLM-written tests see no credentials in their environment (see README, "Sandbox").

usage: python cu_concept.py selftest
       python cu_concept.py gen <arm> <pkg> [--seed K]     one CoverUp pass + final coverage for one package
env:   VERTEX_PROJECT/VERTEX_LOCATION (or VERTEXAI_*), ADC; CU_MODEL, CU_MAX_USD (default 40, all arms together),
       CU_CONCURRENCY (CoverUp --max-concurrency, default 16), CU_RUN (work/<run>, out/<run>; default main)
"""

from __future__ import annotations

import ast
import contextvars
import csv
import json
import os
import random
import re
import shutil
import subprocess
import sys
import time
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).resolve().parent
VENDOR = HERE / "vendor"
APPS = VENDOR / "codamosa" / "replication" / "test-apps"
RUN = os.environ.get("CU_RUN", "main")  # smoke uses its own run name so the full run never resumes from it
WORK, OUT = HERE / "work" / RUN, HERE / "out" / RUN
sys.path.insert(0, str(VENDOR / "coverup" / "src"))  # the pinned, unedited CoverUp
sys.path.append(str(HERE.parent))  # concept_annotator_py lives at the repo root (stdlib only)
from concept_annotator_py.functions import CONCEPTS, annotate_function  # noqa: E402

ARMS = ("coverup", "concept", "concept_reason", "placebo_reason", "ide")
MODEL = os.environ.get("CU_MODEL", "vertex_ai/gemini-2.5-flash")
MAX_FACTS = 12
SIGNATURE_KINDS = {"none-default", "optional", "mutable-default", "cached", "unchecked-none"}  # anchored at the def line

RECIPE = {
    "C1": "None/null: call it once with None and once with a non-None value; assert both outcomes.",
    "C2": "empty/blank: pass an empty value, a whitespace-only value and a one-element value.",
    "C3": "boundary: use a value exactly at the boundary, one below it and one above it.",
    "C4 raise": "raise: trigger the raise and assert the exception type with pytest.raises.",
    "C4 except": "except: force the exception path (e.g. monkeypatch the callee to raise) and assert the handling.",
    "C5": "parse/format: use an empty string, special characters and escaped/quoted strings.",
    "C6": "numeric: use 0, a negative value and extremes (very large values; inf/nan where accepted).",
    "C7": "chars/case/encoding: use mixed case, non-ASCII text and undecodable bytes where accepted.",
    "C8": "state: make repeated or sequenced calls and check the state after each one.",
}


# ---------------------------------------------------------------- facts per segment
def _source(path: Path) -> tuple[str, ast.Module]:
    text = path.read_text(encoding="utf-8")
    return text, ast.parse(text)


@lru_cache(maxsize=256)
def file_units(path: Path) -> tuple:
    """Every function/method/class of a file: (begin, end_inclusive, is_class, facts of each function inside)."""
    text, tree = _source(path)
    lines = text.splitlines()
    funcs = []
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            b = min([d.lineno for d in n.decorator_list] + [n.lineno])
            facts = annotate_function("\n".join(lines[b - 1: n.end_lineno]), b - 1)["facts"]
            funcs.append((b, n.end_lineno, facts))
    units = [(b, e, False) for b, e, _ in funcs]
    units += [(min([d.lineno for d in n.decorator_list] + [n.lineno]), n.end_lineno, True)
              for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
    return tuple(funcs), tuple(sorted(units))


def span_facts(path: Path, begin: int, end: int, loi: set[int]) -> list[dict]:
    """Facts of the functions inside [begin, end) that still have a line of interest, deduplicated (nested functions
    are annotated twice), capped at MAX_FACTS preferring facts on lines of interest, sorted by line."""
    funcs, _ = file_units(path)
    seen, facts = set(), []
    for b, e, fs in funcs:
        if begin <= b and e < end and loi & set(range(b, e + 1)):
            for f in fs:
                key = (f["line"], f["concept"], f["detail"])
                if key not in seen:
                    seen.add(key)
                    facts.append(f)
    facts.sort(key=lambda f: (f["line"] not in loi, f["line"]))
    return sorted(facts[:MAX_FACTS], key=lambda f: (f["line"], f["concept"]))


def placebo_facts(path: Path, begin: int, end: int, loi: set[int], pool_files: list[Path], seed: int) -> tuple:
    """Facts of another function/class of the package (no overlap with the segment) whose fact count is closest to the
    real one (seeded tie-break), line numbers remapped proportionally into the segment. ([], None) if no real facts."""
    n = len(span_facts(path, begin, end, loi))
    if not n:
        return [], None
    cands = []
    for p in pool_files:
        for b, e, _ in file_units(p)[1]:
            if p == path and b < end and e >= begin:
                continue  # overlaps the segment (its own code, or an enclosing class)
            fs = span_facts(p, b, e + 1, set(range(b, e + 1)))
            if fs:
                cands.append((abs(len(fs) - n), str(p), b, e, fs))
    if not cands:
        return [], None
    best = min(c[0] for c in cands)
    _, donor, b, e, fs = random.Random(f"{seed}|{path.name}|{begin}").choice(sorted(c for c in cands if c[0] == best))
    scale = (end - 1 - begin) / max(1, e - b)
    moved = [{**f, "line": begin + round((f["line"] - b) * scale)} for f in fs]
    return sorted(moved, key=lambda f: (f["line"], f["concept"])), f"{Path(donor).name}:{b}-{e}"


def render_facts(facts: list[dict], loi: set[int]) -> str:
    rows = [f"- line {f['line']}{' (not yet executed)' if f['line'] in loi else ''}: "
            f"{f['concept']} {CONCEPTS[f['concept']]}: {f['detail']}" for f in facts]
    return ("Fault-relevant concepts in the code above (static analysis; each is a spot where a bug could hide):\n"
            + "\n".join(rows))


def render_recipe(facts: list[dict]) -> str:
    keys = []
    for f in facts:
        k = f["concept"] if f["concept"] != "C4" else ("C4 except" if f["kind"] == "except" else "C4 raise")
        if k not in keys:
            keys.append(k)
    return ("How to test these concepts (cover each listed spot this way):\n"
            + "\n".join(f"- {RECIPE[k]}" for k in sorted(keys)))


# ---------------------------------------------------------------- ide arm: ruff warnings
RUFF_ARGS = ["--select", "F,B,PLE,PLW,RUF,S",  # identical to CoSIL_concept/prepare.py
             "--ignore", "S101,RUF001,RUF002,RUF003,RUF100,RUF005,RUF010,RUF021,RUF022,RUF023",
             "--target-version", "py313"]


@lru_cache(maxsize=256)
def ruff_warnings(path: Path) -> tuple:
    ruff = str(Path(sys.executable).with_name("ruff"))
    out = subprocess.run([ruff, "check", "--isolated", "--no-cache", "--exit-zero", "--output-format", "json",
                          *RUFF_ARGS, str(path)], capture_output=True, text=True, check=True).stdout
    return tuple(sorted((d["location"]["row"], d["code"], " ".join(d["message"].split()))
                        for d in json.loads(out) if d.get("code")))


def render_ide(path: Path, begin: int, end: int, loi: set[int]) -> str:
    rows = [(r, c, m) for r, c, m in ruff_warnings(path) if begin <= r < end][:MAX_FACTS]
    if not rows:
        return ""
    return ("Static-analysis warnings (ruff) in the code above:\n"
            + "\n".join(f"- line {r}{' (not yet executed)' if r in loi else ''}: {c} {m}" for r, c, m in rows))


def injection(arm: str, path: Path, begin: int, end: int, loi: set[int], pool: list[Path], seed: int) -> tuple:
    """(block appended to CoverUp's first segment prompt, donor) for one arm; ("", None) means the stock prompt."""
    if arm == "coverup":
        return "", None
    if arm == "ide":
        return render_ide(path, begin, end, loi), None
    if arm == "placebo_reason":
        facts, donor = placebo_facts(path, begin, end, loi, pool, seed)
    else:
        facts, donor = span_facts(path, begin, end, loi), None
    if not facts:
        return "", donor
    block = render_facts(facts, loi)
    return (block + "\n\n" + render_recipe(facts) if arm != "concept" else block), donor


# ---------------------------------------------------------------- CoverUp prompter subclass (the injection point)
_seg = contextvars.ContextVar("seg", default="startup")


def make_prompter(arm: str, seed: int, audit: Path):
    from coverup.prompt.gpt_v2 import GptV2Prompter

    class ConceptPrompter(GptV2Prompter):
        def initial_prompt(self, segment):
            messages = super().initial_prompt(segment)
            _seg.set(segment.identify())  # per asyncio task: tags this segment's LLM calls in the ledger
            pool = list(self.args.source_files) or sorted(Path(self.args.package_dir).rglob("*.py"))
            block, donor = injection(arm, segment.path, segment.begin, segment.end, set(segment.lines_of_interest),
                                     pool, seed)
            if block:
                messages[0]["content"] += "\n" + block + "\n"
            with audit.open("a") as f:
                f.write(json.dumps({"seg": segment.identify(), "arm": arm, "seed": seed, "donor": donor,
                                    "block": block, "prompt": messages[0]["content"]}) + "\n")
            return messages

    return ConceptPrompter


# ---------------------------------------------------------------- credentials, sandbox, LLM ledger
SECRET_ENV = re.compile(r"(KEY|TOKEN|SECRET|PASSWORD|CREDENTIALS?|AUTH)$|^(GOOGLE_|CLOUDSDK_|GCLOUD|GCE_|AWS_|AZURE_"
                        r"|OPENAI|ANTHROPIC|GEMINI|HF_|HUGGING|GITHUB|GH_|SSH_AUTH)", re.I)


def load_adc() -> dict:
    path = Path(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
                or Path.home() / ".config" / "gcloud" / "application_default_credentials.json")
    if not path.is_file():
        sys.exit(f"no ADC credentials at {path} (gcloud auth application-default login)")
    return json.loads(path.read_text())


def scrub_env(home: Path) -> None:
    """Child processes (pytest running LLM-written tests, slipcover, mutmut) inherit no credentials: secret-looking
    env vars are removed and HOME is an empty dir, so ~/.config/gcloud is not found by default lookups."""
    for k in list(os.environ):
        if SECRET_ENV.search(k):
            del os.environ[k]
    home.mkdir(parents=True, exist_ok=True)
    os.environ["HOME"] = str(home)


class Ledger:
    def __init__(self, arm: str, seed: int, pkg: str):
        self.tags = {"arm": arm, "seed": seed, "pkg": pkg}
        self.path = OUT / "ledger.jsonl"
        self.cap = float(os.environ.get("CU_MAX_USD", "40"))
        self.base, self.own, self.read_at = 0.0, 0.0, 0.0

    def total(self) -> float:
        if time.time() - self.read_at > 60:  # other arms/processes append to the same ledger
            self.base = sum(json.loads(l)["usd"] for l in open(self.path)) if self.path.exists() else 0.0
            self.own, self.read_at = 0.0, time.time()
        return self.base + self.own

    def write(self, rec: dict) -> None:
        self.own += rec["usd"]
        with self.path.open("a") as f:
            f.write(json.dumps({**self.tags, **rec}) + "\n")


def patch_llm(ledger: Ledger, seed: int, creds: dict) -> None:
    import litellm

    orig = litellm.acreate

    async def acreate(**req):
        if ledger.total() >= ledger.cap:
            print(f"\n[budget] CU_MAX_USD={ledger.cap} reached (ledger {ledger.total():.2f}); stopping", flush=True)
            os._exit(3)  # CoverUp's checkpoint is saved after every segment, so a rerun resumes
        req = {**req, "thinking": {"type": "enabled", "budget_tokens": 0}, "seed": seed, "timeout": 300,
               "vertex_credentials": creds,
               "vertex_project": os.environ.get("VERTEXAI_PROJECT") or os.environ.get("VERTEX_PROJECT"),
               "vertex_location": os.environ.get("VERTEXAI_LOCATION") or os.environ.get("VERTEX_LOCATION") or "global"}
        t0 = time.time()
        rec = {"ts": round(t0), "seg": _seg.get()}
        try:
            resp = await orig(**req)
        except Exception as e:  # CoverUp's Chatter decides about retries; we only log
            ledger.write({**rec, "in": 0, "out": 0, "think": 0, "usd": 0.0, "s": round(time.time() - t0, 1),
                          "err": type(e).__name__})
            raise
        u = resp.usage
        details = getattr(u, "completion_tokens_details", None)
        try:
            usd = float(litellm.completion_cost(completion_response=resp))
        except Exception:
            usd = u.prompt_tokens * 0.3e-6 + u.completion_tokens * 2.5e-6  # Gemini 2.5 Flash list price
        ledger.write({**rec, "in": u.prompt_tokens, "out": u.completion_tokens,
                      "think": getattr(details, "reasoning_tokens", 0) or 0, "usd": round(usd, 6),
                      "s": round(time.time() - t0, 1), "tools": bool(resp.choices[0].message.tool_calls)})
        return resp

    litellm.acreate = acreate


# ---------------------------------------------------------------- benchmark + one CoverUp pass
def subset() -> dict[str, dict]:
    """pkg -> {app, files}; data/subset.csv rows are copied verbatim from the authors' cm_modules.csv."""
    pkgs: dict[str, dict] = {}
    for app, mod in csv.reader(open(HERE / "data" / "subset.csv")):
        pkg = mod.split(".")[0]
        pkgs.setdefault(pkg, {"app": app.split("/", 1)[1], "files": []})["files"].append(mod.replace(".", "/") + ".py")
    return pkgs


PYTEST_ARGS = "--rootdir . -c /dev/null"  # authors' run_coverup.sh: ignore package pytest config


def final_coverage(pkg: str) -> int:
    """The authors' final measurement (run_coverup.sh), in cwd = workspace."""
    cmd = [sys.executable, "-m", "slipcover", "--source", pkg, "--branch", "--json", "--out", "final.json",
           "-m", "pytest", "-qq", "--disable-warnings", *PYTEST_ARGS.split(), "--cleanslate", "coverup-tests"]
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=3600)
    Path("final.log").write_bytes(p.stdout)
    return p.returncode


def gen(arm: str, pkg: str, seed: int) -> int:
    meta = subset()[pkg]
    ws = WORK / arm / f"s{seed}" / pkg
    if (ws / "done.json").exists():
        print(f"[gen] {arm}/s{seed}/{pkg}: done, skipping")
        return 0
    if not (ws / pkg).exists():
        shutil.copytree(APPS / meta["app"] / pkg, ws / pkg, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for d in ("coverup-tests", "coverage"):
        (ws / d).mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    creds = load_adc()
    scrub_env(ws / ".home")
    os.environ.setdefault("VERTEXAI_PROJECT", os.environ.get("VERTEX_PROJECT", ""))
    os.environ.setdefault("VERTEXAI_LOCATION", os.environ.get("VERTEX_LOCATION", "global"))
    os.chdir(ws)
    os.environ["PYTHONPATH"] = str(ws)  # authors: export PYTHONPATH=$SRC
    patch_llm(Ledger(arm, seed, pkg), seed, creds)
    import coverup.coverup as cu

    cu.prompter_registry[f"cu-{arm}"] = make_prompter(arm, seed, ws / "prompts.jsonl")
    # the authors' gpt4o-v2 configuration (coverup-eval/config/gpt4o-v2.sh + run_coverup.sh), one CoverUp pass,
    # minus --install-missing-modules (shared venv; see README)
    sys.argv = ["coverup", "--model", MODEL, "--max-attempts", "3", "--isolate-tests", "--prompt-family", f"cu-{arm}",
                "--repeat-tests", "5", "--package-dir", pkg, "--tests-dir", "coverup-tests",
                "--save-coverage-to", "coverage", "--pytest-args", PYTEST_ARGS, "--log-file", "coverup-log",
                "--checkpoint", "coverup-ckpt.json", "--max-concurrency", os.environ.get("CU_CONCURRENCY", "16"),
                *meta["files"]]
    t0 = time.time()
    rc = cu.main()
    if rc:
        return rc
    rc_final = final_coverage(pkg)
    ckpt = json.load(open("coverup-ckpt.json"))
    done = {"arm": arm, "seed": seed, "pkg": pkg, "model": MODEL, "files": meta["files"],
            "coverup_cost_usd": ckpt["cost"], "counters": ckpt["counters"], "final_rc": rc_final,
            "tests": len(list(Path("coverup-tests").glob("test_*.py"))), "seconds": round(time.time() - t0)}
    Path("done.json").write_text(json.dumps(done, indent=1))
    print(f"[gen] {arm}/s{seed}/{pkg}: {done['counters']} tests={done['tests']} final_rc={rc_final}")
    return 0


# ---------------------------------------------------------------- selftest (no LLM, no network)
def selftest() -> None:
    import tempfile

    src = '''import re

def parse(text, sep=None):
    if text is None:
        return None
    if len(text) > 10:
        raise ValueError("too long")
    try:
        n = int(text)
    except ValueError:
        n = 0
    return n


class Box:
    def put(self, x):
        self.items.append(x)
        return self.items[len(self.items) - 1]

    def get(self, i):
        if i >= len(self.items):
            raise IndexError(i)
        return self.items[i]


def plain(a):
    return a
'''
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp, "m.py")
        p.write_text(src)
        q = Path(tmp, "n.py")
        q.write_text("def other(s):\n    if not s:\n        return s.lower()\n    return s.strip()\n")
        loi = set(range(3, 13))
        facts = span_facts(p, 3, 13, loi)
        kinds = {(f["concept"], f["kind"]) for f in facts}
        assert {("C1", "none-check"), ("C4", "raise"), ("C4", "except"), ("C3", "bound")} <= kinds, kinds
        assert all(3 <= f["line"] <= 12 for f in facts)
        # a segment whose function has no uncovered line gets no facts
        assert span_facts(p, 3, 13, {20}) == []
        block, _ = injection("concept_reason", p, 3, 13, loi, [p, q], 0)
        assert "line 4 (not yet executed): C1 null/None: None-check text is None" in block, block
        assert RECIPE["C4 raise"] in block and RECIPE["C4 except"] in block and RECIPE["C3"] in block, block
        assert "How to test" not in injection("concept", p, 3, 13, loi, [p, q], 0)[0]
        assert injection("coverup", p, 3, 13, loi, [p, q], 0) == ("", None)
        assert injection("concept", p, 27, 29, {27, 28}, [p, q], 0) == ("", None)  # plain(): no facts -> stock prompt
        # placebo: donor never overlaps the segment, lines land inside it, deterministic per seed
        fp, donor = placebo_facts(p, 3, 13, loi, [p, q], 1)
        assert donor and not donor.startswith("m.py:3-") and all(3 <= f["line"] <= 12 for f in fp), (donor, fp)
        assert placebo_facts(p, 3, 13, loi, [p, q], 1) == (fp, donor)
        fs, d2 = placebo_facts(p, 16, 19, set(range(16, 19)), [p, q], 0)  # Box.put: donor can't be Box (encloses it)
        assert d2 and not d2.startswith("m.py:15-"), d2
        pr, _ = injection("placebo_reason", p, 3, 13, loi, [p, q], 1)
        assert pr.startswith("Fault-relevant") and "How to test" in pr
        # ide: ruff finds B904-style issues only where they exist; stock prompt otherwise
        r = Path(tmp, "r.py")
        r.write_text("def f(x):\n    try:\n        return int(x)\n    except ValueError:\n        raise KeyError(x)\n")
        ide, _ = injection("ide", r, 1, 6, set(range(1, 6)), [r], 0)
        assert "line 5 (not yet executed): B904" in ide, ide
        assert injection("ide", q, 1, 5, set(range(1, 5)), [q], 0) == ("", None)
    # the vendored prompt is a prefix of ours: the block is appended, nothing else changes
    from coverup.segment import CodeSegment
    from coverup.prompt.gpt_v2 import GptV2Prompter
    import argparse
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp, "m.py")
        p.write_text(src)
        seg = CodeSegment(str(p), "parse", 3, 13, set(range(3, 13)), set(range(3, 13)), set(), set(), [], ["import re"])
        args = argparse.Namespace(src_base_dir=Path(tmp).resolve(), source_files=[p.resolve()], package_dir=Path(tmp))
        base = GptV2Prompter(args).initial_prompt(seg)[0]["content"]
        for arm in ARMS:
            ours = make_prompter(arm, 0, Path(tmp, "audit.jsonl"))(args).initial_prompt(seg)[0]["content"]
            assert ours.startswith(base) and (ours == base) == (arm in ("coverup", "ide")), arm  # src: no ruff hits
        assert len(Path(tmp, "audit.jsonl").read_text().splitlines()) == len(ARMS)
    env = {"GOOGLE_APPLICATION_CREDENTIALS": "x", "OPENAI_API_KEY": "x", "VERTEXAI_PROJECT": "p", "PATH": "/bin"}
    saved = dict(os.environ)
    try:
        os.environ.clear()
        os.environ.update(env)
        with tempfile.TemporaryDirectory() as tmp:
            scrub_env(Path(tmp, "h"))
            assert set(os.environ) == {"VERTEXAI_PROJECT", "PATH", "HOME"}, dict(os.environ)
    finally:
        os.environ.clear()
        os.environ.update(saved)
    assert sum(len(v["files"]) for v in subset().values()) > 0
    print(f"selftest ok: {len(facts)} facts; arms {', '.join(ARMS)}")


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["selftest", "gen"])
    ap.add_argument("arm", nargs="?", choices=ARMS)
    ap.add_argument("pkg", nargs="?")
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    if a.cmd == "selftest":
        selftest()
    else:
        sys.exit(gen(a.arm, a.pkg, a.seed))
