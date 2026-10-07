#!/usr/bin/env python3
"""CoSIL with C1-C8 concept tags on the function names it lists to the LLM. Arms: stock | concept | placebo.

Everything here is an additive monkeypatch; vendor/CoSIL stays at the pinned commit, unedited.
Injection points (the only places CoSIL lists function/method names to the LLM): FL_tools.get_functions_of_file
and FL_tools.get_functions_of_class, as called by CoSIL.consturct_bug_file_list, whose text goes into the tool-loop
prompt and twice into the summary prompt. The file stage shows file paths and imports only, so it is shared.
Arm-neutral patches: LiteLLM completion -> Vertex (thinking budget 0, retries, ledger), echoed tags cut from tool
arguments and <name> answers, FL_tools.load_json cached (identical listings, verified by replay), listings saved.

usage: python cosil_concept.py selftest
       python cosil_concept.py files <dataset> [--ids FILE|ID,ID] [--limit N] [--threads N]
       python cosil_concept.py funcs <stock|concept|placebo> <dataset> [--ids ...] [--limit N] [--threads N]
       python cosil_concept.py verify <dataset> [--ids ...]
env:   VERTEX_PROJECT / VERTEX_LOCATION (or VERTEXAI_*), ADC credentials; COSIL_MODEL, COSIL_MAX_USD (per process)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import random
import re
import sys
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
VENDOR = HERE / "vendor" / "CoSIL"
sys.path.insert(0, str(VENDOR))
import CoSIL.util.preprocess_data  # noqa: E402  binds `CoSIL` to the package before fl/ (holding CoSIL.py) joins
sys.path.append(str(VENDOR / "CoSIL" / "fl"))  # CoSIL.py does `from FL_tools import *`
sys.path.append(str(HERE.parent))  # concept_annotator_py lives at the repo root
from concept_annotator_py.functions import annotate_function, render_tags  # noqa: E402
from prepare import STRUCT, load_rows  # noqa: E402

ARMS = ("stock", "concept", "placebo")
MODEL = os.environ.get("COSIL_MODEL", "vertex_ai/gemini-2.5-flash")
SEED = 20251007
OUT, WORK = HERE / "out", HERE / "work"
_state = SimpleNamespace(ds=None, arm="stock", spent=0.0, budget=float(os.environ.get("COSIL_MAX_USD", "inf")))
_ctx = threading.local()
_lock = threading.Lock()


# ---------------------------------------------------------------- tags
@lru_cache(maxsize=4)
def cached_load_json(path: str):
    """FL_tools re-reads the whole repo structure on every listing/tool call (~60 loads per instance; structures reach
    40MB+ for django). Same content, read-only use (extract_structure only re-adds the same "file" keys), all arms."""
    with open(path) as f:
        return json.load(f)


@lru_cache(maxsize=4)
def _extracted(instance_id: str):
    from CoSIL.util.preprocess_data import extract_structure
    return extract_structure(cached_load_json(f"./repo_structures/{instance_id}.json")["structure"])


@lru_cache(maxsize=4096)
def file_tags(instance_id: str, file_name: str) -> dict[tuple, tuple[str, str]]:
    """(class or "", name, start_line) -> (concept tag, placebo tag) for every function/method of one file.
    Placebo: the file's non-empty tag strings rotated over a seeded shuffle, so no function keeps its own tag
    (unless the file has a single tagged function or duplicate strings); untagged functions stay untagged."""
    _, classes, functions = _extracted(instance_id)
    items = [((c["name"], m["name"], m["start_line"]), m["method_content"])
             for c in classes if c["file"] == file_name for m in c["methods"]]
    items += [(("", f["name"], f["start_line"]), f["text"]) for f in functions if f["file"] == file_name]
    concept = {k: render_tags(annotate_function("\n".join(text), k[2] - 1)) for k, text in items}
    order = [k for k, _ in items if concept[k]]
    random.Random(f"{SEED}|{instance_id}|{file_name}").shuffle(order)
    placebo = dict.fromkeys(concept, "")
    for i, k in enumerate(order):
        placebo[k] = concept[order[(i + 1) % len(order)]]
    return {k: (concept[k], placebo[k]) for k in concept}


def _decorate(name: str, tag: str) -> str:
    return f"{name}  [{tag}]" if tag else name


def tagged_functions_of_class(class_name: str, instance_id: str) -> str:
    """FL_tools.get_functions_of_class (same matching and order) with each method's arm tag appended."""
    idx = ARMS.index(_state.arm) - 1
    _, classes, _ = _extracted(instance_id)
    out = []
    for c in classes:
        if c["name"] == class_name:
            tags = file_tags(instance_id, c["file"])
            out += [_decorate(m["name"], tags[(class_name, m["name"], m["start_line"])][idx]) for m in c["methods"]]
    return str(out)


def tagged_functions_of_file(file_name: str, instance_id: str) -> str:
    """FL_tools.get_functions_of_file (same matching and order) with each function's arm tag appended."""
    idx = ARMS.index(_state.arm) - 1
    _, _, functions = _extracted(instance_id)
    tags = file_tags(instance_id, file_name)
    return str([_decorate(f["name"], tags[("", f["name"], f["start_line"])][idx])
                for f in functions if f["file"] == file_name])


# A name never contains whitespace, so anything after it is an echoed tag. Applied in every arm (no-op in stock).
def _first_token(s):
    return s.split()[0] if isinstance(s, str) and s.split() else s


def clean_tool_args(arguments: dict) -> dict:
    return {k: _first_token(v) if k in ("func_name", "class_name") else v for k, v in arguments.items()}


def clean_xml_names(raw: str) -> str:
    return re.sub(r"<name>\s*(\S+)\s[^<]*</name>", r"<name>\1</name>", raw)


# ---------------------------------------------------------------- LLM (Vertex via LiteLLM) + ledger
class BudgetExceeded(RuntimeError):
    pass


def llm_completion(**cfg):
    """Replaces CoSIL.util.model.completion: same LiteLLM call plus Vertex settings, thinking off, retries, ledger."""
    import litellm

    litellm.suppress_debug_info = True  # retries below already log one line each
    if _state.spent >= _state.budget:
        raise BudgetExceeded(f"COSIL_MAX_USD={_state.budget} reached")
    cfg = {**cfg, "thinking": {"type": "enabled", "budget_tokens": 0}, "timeout": 300,
           "vertex_project": os.environ.get("VERTEXAI_PROJECT") or os.environ.get("VERTEX_PROJECT"),
           "vertex_location": os.environ.get("VERTEXAI_LOCATION") or os.environ.get("VERTEX_LOCATION") or "global"}
    retry = tuple(getattr(litellm, n) for n in ("RateLimitError", "ServiceUnavailableError", "InternalServerError",
                                                "APIConnectionError", "Timeout", "BadGatewayError") if hasattr(litellm, n))
    t0 = time.time()
    for attempt in range(10):
        try:
            ret = litellm.completion(**cfg)
            break
        except retry as e:
            if attempt == 9:
                raise
            print(f"[retry {attempt + 1}] {getattr(_ctx, 'iid', '?')}: {type(e).__name__} {' '.join(str(e).split())[:160]}",
                  file=sys.stderr, flush=True)
            time.sleep(min(60, 2 ** attempt) * (0.5 + random.random()))
    u = ret.usage
    details = getattr(u, "completion_tokens_details", None)
    try:
        cost = float(litellm.completion_cost(completion_response=ret))
    except Exception:
        cost = u.prompt_tokens * 0.3e-6 + u.completion_tokens * 2.5e-6  # Gemini 2.5 Flash list price
    rec = {"ts": round(t0), "ds": _state.ds, "stage": getattr(_ctx, "stage", "?"), "arm": getattr(_ctx, "arm", "?"),
           "iid": getattr(_ctx, "iid", "?"), "in": u.prompt_tokens, "out": u.completion_tokens,
           "think": getattr(details, "reasoning_tokens", 0) or 0, "usd": round(cost, 6),
           "s": round(time.time() - t0, 1), "tries": attempt + 1}
    with _lock:
        _state.spent += cost
        _ctx.usd = getattr(_ctx, "usd", 0.0) + cost
        with open(OUT / _state.ds / "ledger.jsonl", "a") as f:
            f.write(json.dumps(rec) + "\n")
    return ret


# ---------------------------------------------------------------- boot + run
def boot(ds: str, arm: str):
    """chdir into work/<ds> (CoSIL reads ./repo_structures/), set PROJECT_FILE_LOC, import CoSIL, patch the arm."""
    _state.ds, _state.arm = ds, arm
    work = WORK / ds
    work.mkdir(parents=True, exist_ok=True)
    (OUT / ds).mkdir(parents=True, exist_ok=True)
    link = work / "repo_structures"
    if not link.is_symlink():
        link.symlink_to(STRUCT / ds, target_is_directory=True)
    os.environ["PROJECT_FILE_LOC"] = str(STRUCT / ds)
    CoSIL.util.preprocess_data.PROJECT_FILE_LOC = str(STRUCT / ds)  # read at import time, before boot()
    os.environ.setdefault("TIKTOKEN_CACHE_DIR", str(HERE / "cache" / "tiktoken"))
    os.chdir(work)
    import CoSIL.util.model as model_mod
    import FL_tools
    import CoSIL.fl.CoSIL as cm
    import CoSIL.fl.CoSIL_localize_file as lfile
    import CoSIL.fl.CoSIL_localize_func as lfunc

    model_mod.completion = llm_completion
    FL_tools.load_json = cached_load_json  # FL_tools only; the localize scripts keep their own (mutated) copy
    if arm in ("concept", "placebo"):
        for mod in (FL_tools, cm):
            mod.get_functions_of_file = tagged_functions_of_file
            mod.get_functions_of_class = tagged_functions_of_class
    dispatch, parse, listing = cm.dispatch_cosil_location_tool, cm.CoSIL._parse_xml_locations, cm.CoSIL.consturct_bug_file_list
    cm.dispatch_cosil_location_tool = lambda name, arguments, iid: dispatch(name, clean_tool_args(arguments), iid)
    cm.CoSIL._parse_xml_locations = lambda self, raw, files: parse(self, clean_xml_names(raw), files)

    def audited_listing(self, file):  # keep exactly what the LLM saw, for verification
        text = listing(self, file)
        d = work / arm / "listings"
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{self.instance_id}.txt").write_text(text)
        return text
    cm.CoSIL.consturct_bug_file_list = audited_listing
    return lfile, lfunc


def run(stage: str, ds: str, arm: str, ids: str | None, limit: int | None, threads: int) -> None:
    from CoSIL.util.utils import cleanup_logger

    rows = load_rows(ds, ids, limit)
    lfile, lfunc = boot(ds, arm)
    name = "files" if stage == "files" else arm
    files_out, preds = OUT / ds / "files.jsonl", OUT / ds / f"{name}.jsonl"
    done = {json.loads(l)["instance_id"] for l in open(preds)} if preds.exists() else set()
    found = {json.loads(l)["instance_id"] for l in open(files_out)} if files_out.exists() else set()
    if stage == "funcs" and (missing := [r["instance_id"] for r in rows if r["instance_id"] not in found]):
        print(f"[{ds}/{name}] {len(missing)} instances lack file-level output; run `files` first: {missing[:5]}")
    todo = [r for r in rows if r["instance_id"] not in done and (stage == "files" or r["instance_id"] in found)]
    k = ARMS.index(arm) * len(todo) // 3 if stage == "funcs" else 0
    todo = todo[k:] + todo[:k]  # parallel arms reach the huge structures (azure-sdk: 3.3GB RAM per copy) at different times
    stage_dir = WORK / ds / name
    (stage_dir / "parts").mkdir(parents=True, exist_ok=True)
    (stage_dir / "localization_logs").mkdir(exist_ok=True)
    print(f"[{ds}/{name}] {len(rows)} selected, {len(rows) - len(todo)} done, {len(todo)} to run, "
          f"threads={threads}, model={MODEL}", flush=True)
    counter = iter(range(1, len(todo) + 1))

    def one(r):
        iid = r["instance_id"]
        if _state.spent >= _state.budget:
            return
        _ctx.stage, _ctx.arm, _ctx.iid, _ctx.usd = stage, (arm if stage == "funcs" else "-"), iid, 0.0
        part = stage_dir / "parts" / f"{iid}.jsonl"
        part.unlink(missing_ok=True)
        t0 = time.time()
        try:
            if stage == "files":
                a = SimpleNamespace(output_folder=str(stage_dir), output_file=str(part), target_id=None,
                                    file_level=True, mock=False, model=MODEL)
                lfile.localize_instance(r, a, [r], None, set(), None)
            else:
                a = SimpleNamespace(output_folder=str(stage_dir), output_file=str(part), loc_file=str(files_out),
                                    top_n=5, max_retry=10, model=MODEL, target_id=None)
                lfunc.localize_instance(r, a, [r], set())
            rec = json.loads(part.read_text().splitlines()[-1])
            keep = {"instance_id": iid, "found_files": rec["found_files"]}
            if stage == "funcs":
                keep["found_related_locs"] = rec["found_related_locs"]
            with _lock:
                with open(preds, "a") as f:
                    f.write(json.dumps(keep) + "\n")
            status = "ok"
        except Exception as e:  # rerun retries it
            status = f"FAIL {type(e).__name__}: {str(e)[:200]}"
        finally:
            cleanup_logger(logging.getLogger(str(stage_dir / "localization_logs" / f"{iid}.log")))
        print(f"[{ds}/{name}] {next(counter)}/{len(todo)} {iid} {status} {time.time() - t0:.0f}s "
              f"${_ctx.usd:.4f} (process total ${_state.spent:.3f})", flush=True)

    with ThreadPoolExecutor(max_workers=threads) as ex:
        list(ex.map(one, todo))
    n = len({json.loads(l)["instance_id"] for l in open(preds)}) if preds.exists() else 0
    print(f"[{ds}/{name}] finished: {n}/{len(rows)} have output; spent ${_state.spent:.3f} this process", flush=True)


# ---------------------------------------------------------------- verification + selftest
_TAG = re.compile(r"  \[(C[1-8].*?)\](?=['\"](?:, |\]))")


def verify(ds: str, ids: str | None) -> None:
    """Did every arm finish, do tags reach the prompts, and is the placebo a true reshuffle of the same tags?"""
    rows = load_rows(ds, ids)
    for arm in ARMS:
        p = OUT / ds / f"{arm}.jsonl"
        got = {json.loads(l)["instance_id"] for l in open(p)} if p.exists() else set()
        print(f"[verify] {arm}: {len(got & {r['instance_id'] for r in rows})}/{len(rows)} instances finished")
    for r in rows:
        iid = r["instance_id"]
        txt = {a: (WORK / ds / a / "listings" / f"{iid}.txt") for a in ARMS}
        if not all(p.exists() for p in txt.values()):
            continue
        txt = {a: p.read_text() for a, p in txt.items()}
        tags = {a: _TAG.findall(t) for a, t in txt.items()}
        bare = {a: _TAG.sub("", t).replace('"', "'") for a, t in txt.items()}  # repr quotes follow the tag text
        same_names = bare["concept"] == bare["placebo"] == bare["stock"]
        moved = sum(a != b for a, b in zip(_concept_pairs(txt["concept"]), _concept_pairs(txt["placebo"])))
        part = WORK / ds / "concept" / "parts" / f"{iid}.jsonl"
        summary = json.loads(part.read_text().splitlines()[-1])["func_traj"]["prompt"][1]["content"] if part.exists() else ""
        in_prompt = sum(t in summary for t in set(tags["concept"]))
        print(f"[verify] {iid}: names identical across arms={same_names}; tagged names concept={len(tags['concept'])} "
              f"placebo={len(tags['placebo'])} stock={len(tags['stock'])}; same tag multiset="
              f"{Counter(tags['concept']) == Counter(tags['placebo'])}; tags moved by placebo={moved}; "
              f"distinct concept tags found in the saved summary prompt={in_prompt}/{len(set(tags['concept']))}")
    ex = next((l for r in rows for l in _lines(WORK / ds / "concept" / "listings" / f"{r['instance_id']}.txt")
               if "  [C" in l), None)
    if ex:
        print("[verify] example concept listing line:\n" + ex[:700])


def _concept_pairs(text: str) -> list[tuple[str, str]]:
    return re.findall(r"['\"](\w+)(?:  \[(C[1-8].*?)\])?(?=['\"](?:, |\]))", text)


def _lines(p: Path) -> list[str]:
    return p.read_text().splitlines() if p.exists() else []


def selftest() -> None:
    import CoSIL.fl.CoSIL  # noqa: F401  vendor imports resolve
    import CoSIL.fl.CoSIL_localize_file  # noqa: F401
    import CoSIL.fl.CoSIL_localize_func  # noqa: F401
    import litellm  # noqa: F401
    import scipy  # noqa: F401
    assert clean_tool_args({"func_name": "f  [C1 x is None]", "file_name": "a b.py"}) == {"func_name": "f", "file_name": "a b.py"}
    assert clean_xml_names("<name>A.f  [C4 raises X]</name><name>g</name>") == "<name>A.f</name><name>g</name>"
    src = "def parse(x=None):\n    if x is None:\n        raise ValueError('x')\n    return x[1:]\n"
    tag = render_tags(annotate_function(src))
    assert tag.startswith("C1") and "C4" in tag, tag
    listing = "file: a.py \n\t static functions:  ['parse  [C1 None-check x is None]', 'g', \"h  [C5 q['a']]\"]"
    assert _TAG.findall(listing) == ["C1 None-check x is None", "C5 q['a']"], _TAG.findall(listing)
    assert _TAG.sub("", listing) == "file: a.py \n\t static functions:  ['parse', 'g', \"h\"]"
    print(f"[selftest] ok: imports, name cleaning, tag rendering ({tag!r})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["selftest", "files", "funcs", "verify"])
    ap.add_argument("rest", nargs="*")
    ap.add_argument("--ids")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--threads", type=int, default=int(os.environ.get("COSIL_THREADS", 4)))
    a = ap.parse_args()
    if a.cmd == "selftest":
        selftest()
    elif a.cmd == "files":
        run("files", a.rest[0], "stock", a.ids, a.limit, a.threads)
    elif a.cmd == "funcs":
        assert a.rest[0] in ARMS, f"arm must be one of {ARMS}"
        run("funcs", a.rest[1], a.rest[0], a.ids, a.limit, a.threads)
    else:
        verify(a.rest[0], a.ids)
