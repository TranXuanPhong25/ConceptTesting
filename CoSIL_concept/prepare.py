#!/usr/bin/env python3
"""Datasets, CoSIL repo structures and ground truth for the CoSIL concept/placebo experiment.

usage: python prepare.py data
       python prepare.py structures <dataset> [--ids FILE|ID,ID] [--limit N] [--jobs N]

`structures` builds vendor/CoSIL-format `structures/<dataset>/<instance_id>.json` with CoSIL's own
`get_repo_structure.create_structure`, from one partial bare clone per repo (`clones/`) plus a temporary
`git worktree` per base commit. It is resumable (finished JSONs are skipped) and also writes the patch-derived
ground truth `data/<dataset>_gt_patch.json` (the official gt for swebench_live).
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
VENDOR = HERE / "vendor" / "CoSIL"
DATA, STRUCT, CLONES, WT = HERE / "data", HERE / "structures", HERE / "clones", HERE / "work" / "wt"
CUTOFF = "2025-02-01"  # Gemini 2.5 Flash knowledge cutoff: January 2025
SOURCES = {  # dataset -> (HF repo, pinned revision, parquet files)
    "swebench_live": ("SWE-bench-Live/SWE-bench-Live", "b51a86422e10cfd403beb4773e5a2947953e36ec",
                      ["data/verified-00000-of-00001.parquet", "data/lite-00000-of-00001.parquet"]),
    "locbench": ("czlll/Loc-Bench_V1", "c44cf3b74e07ca642cec841b471a9939907c12a7",
                 ["data/test-00000-of-00001.parquet"]),
    "swebench_lite": ("princeton-nlp/SWE-bench_Lite", "6ec7bb89b9342f664a54a6e0a6ea6501d3437cc2",
                      ["data/test-00000-of-00001.parquet"]),
}
FIELDS = ["instance_id", "repo", "base_commit", "problem_statement", "patch", "created_at"]
HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def load_rows(ds: str, ids: str | None = None, limit: int | None = None) -> list[dict]:
    rows = [json.loads(l) for l in open(DATA / f"{ds}.jsonl")]
    if ids:
        wanted = Path(ids).read_text().split() if Path(ids).is_file() else ids.split(",")
        rows = [r for r in rows if r["instance_id"] in set(wanted)]
    return rows[:limit] if limit else rows


# ---------------------------------------------------------------- data
def data() -> None:
    import pandas as pd
    from huggingface_hub import hf_hub_download

    DATA.mkdir(exist_ok=True)
    vendor_gt = json.load(open(VENDOR / "evaluation" / "gt.json"))
    for ds, (repo, rev, files) in SOURCES.items():
        df = pd.concat([pd.read_parquet(hf_hub_download(repo, f, repo_type="dataset", revision=rev)) for f in files])
        df = df.drop_duplicates("instance_id")
        if ds == "locbench":
            df["created_at"] = pd.to_datetime(df["created_at"], unit="ms")
            df = df[df["category"] == "Bug Report"]
        df["created_at"] = pd.to_datetime(df["created_at"], utc=True).dt.strftime("%Y-%m-%dT%H:%M:%S")
        post = int((df["created_at"] >= CUTOFF).sum())
        if ds == "swebench_live":
            df = df[df["created_at"] >= CUTOFF]
        rows = df.sort_values("instance_id").to_dict("records")
        with open(DATA / f"{ds}.jsonl", "w") as f:
            for r in rows:
                rec = {k: r[k] for k in FIELDS}
                if ds == "locbench":
                    rec["edit_functions"] = list(r["edit_functions"])
                f.write(json.dumps(rec) + "\n")
        (DATA / f"{ds}_ids.txt").write_text("".join(r["instance_id"] + "\n" for r in rows))
        if ds == "swebench_lite":  # the authors' own ground truth
            gt = {r["instance_id"]: vendor_gt[r["instance_id"]] for r in rows if r["instance_id"] in vendor_gt}
        elif ds == "locbench":  # LocBench's edit_functions ("path:Name") plus every patched .py file
            gt = {r["instance_id"]: sorted({e.replace(":", "::", 1) for e in r["edit_functions"]}
                                           | set(patch_py_files(r["patch"]))) for r in rows}
        else:
            gt = None  # derived from the patch + base structure by `structures`
        if gt is not None:
            json.dump(gt, open(DATA / f"{ds}_gt.json", "w"), indent=0, sort_keys=True)
        print(f"[data] {ds}: {len(rows)} instances, {df['repo'].nunique()} repos, "
              f"created >= {CUTOFF}: {post} ({repo}@{rev[:8]})")


# ---------------------------------------------------------------- patch -> ground truth
def patch_changes(patch: str) -> dict[str, dict]:
    """{old path: {"deleted": {old line}, "inserted": {(old line before, indent)}, "added_new": {new line},
    "new_path": str}} for every file in a unified diff (new files have old path None -> keyed by new path)."""
    out: dict[str, dict] = {}
    cur, a_path, old, new, rem_old, rem_new = None, None, 0, 0, 0, 0
    for line in patch.splitlines():
        if rem_old > 0 or rem_new > 0:
            if line.startswith("\\"):
                continue
            tag, body = line[:1], line[1:]
            if tag == "-":
                cur["deleted"].add(old)
                old, rem_old = old + 1, rem_old - 1
            elif tag == "+":
                if body.strip():
                    cur["inserted"].add((old - 1, len(body) - len(body.lstrip())))
                cur["added_new"].add(new)
                new, rem_new = new + 1, rem_new - 1
            else:
                old, new, rem_old, rem_new = old + 1, new + 1, rem_old - 1, rem_new - 1
            continue
        if line.startswith("--- "):
            a_path = None if line[4:].strip() == "/dev/null" else line[4:].strip().removeprefix("a/")
        elif line.startswith("+++ "):
            b_path = None if line[4:].strip() == "/dev/null" else line[4:].strip().removeprefix("b/")
            cur = out.setdefault(a_path or b_path, {"deleted": set(), "inserted": set(), "added_new": set(),
                                                    "new_path": b_path, "is_new": a_path is None})
        elif (m := HUNK.match(line)) and cur is not None:
            old, rem_old, new, rem_new = int(m[1]), int(m[2] or 1), int(m[3]), int(m[4] or 1)
            if rem_old == 0:  # "-N,0": pure insertion after old line N
                old += 1
    return out


def patch_py_files(patch: str) -> list[str]:
    return sorted(p for p, c in patch_changes(patch).items() if p.endswith(".py") and not c["is_new"])


def file_spans(structure: dict) -> dict[str, list[tuple]]:
    """file path -> [(kind, label, class, name, start, end, def indent)] using CoSIL's own extract_structure."""
    sys.path.insert(0, str(VENDOR))
    from CoSIL.util.preprocess_data import extract_structure

    def indent(text):
        return len(text[0]) - len(text[0].lstrip()) if text else 0

    _, classes, functions = extract_structure(structure)
    spans: dict[str, list[tuple]] = defaultdict(list)
    for c in classes:
        spans[c["file"]].append(("class", c["name"], c["name"], "", c["start_line"], c["end_line"], indent(c["class_content"])))
        for m in c["methods"]:
            spans[c["file"]].append(("method", f"{c['name']}.{m['name']}", c["name"], m["name"], m["start_line"],
                                     m["end_line"], indent(m["method_content"])))
    for f in functions:
        spans[f["file"]].append(("func", f["name"], "", f["name"], f["start_line"], f["end_line"], indent(f["text"])))
    return spans


def locate(spans: list[tuple], line: int, ins_indent: int | None = None) -> tuple | None:
    """Span owning a changed line: a method beats a function (outermost) beats a class (innermost).
    Insertions (ins_indent set) after `line` count when the next line is inside, or the added code is indented
    deeper than the def/class line (appending at the end of a body)."""
    def inside(s):
        if ins_indent is None:
            return s[4] <= line <= s[5]
        return s[4] <= line and (line + 1 <= s[5] or (line <= s[5] and ins_indent > s[6]))
    hits = [s for s in spans if inside(s)]
    for kind, pick in (("method", min), ("func", max), ("class", min)):
        cands = [s for s in hits if s[0] == kind]
        if cands:
            return pick(cands, key=lambda s: s[5] - s[4])
    return None


def gt_from_patch(patch: str, structure: dict) -> tuple[list[str], list[tuple]]:
    """CoSIL-format gt entries ("file::Class.method", "file::func", "file::Class", or "file") plus the gold spans."""
    spans_by_file = file_spans(structure)
    entries, gold = set(), []
    for path, ch in patch_changes(patch).items():
        if not path.endswith(".py") or ch["is_new"]:
            continue
        spans = spans_by_file.get(path, [])
        owners = {locate(spans, l) for l in ch["deleted"]} | {locate(spans, a, k) for a, k in ch["inserted"]}
        owners.discard(None)
        entries.add(path)
        entries |= {f"{path}::{s[1]}" for s in owners}
        gold += [(path, s) for s in owners]
    return sorted(entries), gold


# ---------------------------------------------------------------- structures
def git(*args, cwd=None, check=True, quiet=True):
    return subprocess.run(["git", *args], cwd=cwd, check=check, text=True,
                          stdout=subprocess.PIPE if quiet else None, stderr=subprocess.PIPE if quiet else None)


def build_repo(ds: str, repo: str, rows: list[dict]) -> list[tuple]:
    sys.path.insert(0, str(VENDOR))
    from get_repo_structure.get_repo_structure import create_structure  # CoSIL's own structure builder

    bare = CLONES / (repo.replace("/", "__") + ".git")
    if not bare.exists():
        tmp = bare.with_suffix(".partial")
        shutil.rmtree(tmp, ignore_errors=True)
        git("clone", "-q", "--bare", "--filter=blob:none", f"https://github.com/{repo}.git", str(tmp))
        tmp.rename(bare)
    stats = []
    for r in rows:
        iid, sha = r["instance_id"], r["base_commit"]
        out = STRUCT / ds / f"{iid}.json"
        if out.exists() and out.with_suffix(".gt.json").exists():
            continue
        t0 = time.time()
        try:
            if out.exists():
                d = json.load(open(out))
            else:
                if git("cat-file", "-e", f"{sha}^{{commit}}", cwd=bare, check=False).returncode:
                    git("fetch", "-q", "origin", sha, cwd=bare)
                wt = WT / iid / repo.split("/")[1]  # basename = repo name, as CoSIL's repo_to_top_folder
                if wt.parent.exists():
                    shutil.rmtree(wt.parent)
                    git("worktree", "prune", cwd=bare)
                git("worktree", "add", "-q", "--detach", str(wt), sha, cwd=bare)
                noise = io.StringIO()
                with contextlib.redirect_stdout(noise):
                    structure = create_structure(str(wt))
                git("worktree", "remove", "--force", str(wt), cwd=bare)
                shutil.rmtree(wt.parent, ignore_errors=True)
                d = {"repo": repo, "base_commit": sha, "structure": structure, "instance_id": iid}
                tmp = out.with_suffix(".tmp")
                json.dump(d, open(tmp, "w"))
                os.replace(tmp, out)
            entries, _ = gt_from_patch(r["patch"], d["structure"])
            json.dump(entries, open(out.with_suffix(".gt.json"), "w"))
            mb = out.stat().st_size / 1e6
            stats.append((iid, time.time() - t0, mb))
            print(f"[structures] {iid}: {time.time() - t0:.0f}s {mb:.1f}MB gt={len(entries)}", flush=True)
        except Exception as e:  # keep going; a rerun retries the instance
            print(f"[structures] FAIL {iid}: {e} {getattr(e, 'stderr', '') or ''}".strip(), flush=True)
    return stats


def structures(ds: str, ids: str | None, limit: int | None, jobs: int) -> None:
    rows = load_rows(ds, ids, limit)
    (STRUCT / ds).mkdir(parents=True, exist_ok=True)
    CLONES.mkdir(exist_ok=True)
    by_repo = defaultdict(list)
    for r in rows:
        by_repo[r["repo"]].append(r)
    t0 = time.time()
    print(f"[structures] {ds}: {len(rows)} instances in {len(by_repo)} repos, jobs={jobs}", flush=True)
    with ProcessPoolExecutor(max_workers=jobs) as ex:
        built = sum((f.result() for f in [ex.submit(build_repo, ds, repo, rs) for repo, rs in by_repo.items()]), [])
    have = {r["instance_id"] for r in rows if (STRUCT / ds / f"{r['instance_id']}.gt.json").exists()}
    gt_path = DATA / f"{ds}_gt_patch.json"
    gt = json.load(open(gt_path)) if gt_path.exists() else {}
    gt.update({i: json.load(open(STRUCT / ds / f"{i}.gt.json")) for i in have})
    json.dump(gt, open(gt_path, "w"), indent=0, sort_keys=True)
    du = lambda p: sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) / 1e9
    print(f"[structures] {ds}: {len(have)}/{len(rows)} ready, built {len(built)} in {time.time() - t0:.0f}s; "
          f"disk structures/{ds}={du(STRUCT / ds):.2f}GB clones={du(CLONES):.2f}GB", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["data", "structures"])
    ap.add_argument("dataset", nargs="?", choices=list(SOURCES))
    ap.add_argument("--ids")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--jobs", type=int, default=4)
    a = ap.parse_args()
    if a.cmd == "data":
        data()
    else:
        structures(a.dataset, a.ids, a.limit, a.jobs)
