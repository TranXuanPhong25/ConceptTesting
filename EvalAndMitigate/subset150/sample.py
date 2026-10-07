"""subset150 sampler (container): checks out the planned bugs one at a time and keeps the methods that pass the
upstream filters, until each project reaches its quota. The filters are the upstream notebooks themselves
(generate_source_data_for_prompt.ipynb -> unify_fixed_and_buggy_bugs.ipynb, via run/nb2py.py with this folder's
gen_src.ovr / unify.ovr, which only restrict the bug list and move the output files to new names).

Per bug, in plan order (out/plan.json):
  1. defects4j checkout of the buggy version; the buggy source data (gen_src) of that bug;
  2. only if a buggy record is invoked by a trigger test and public/protected (necessary for the final filter):
     checkout of the fixed version, fixed source data, unify -> methods kept for this bug.
Checkouts are strictly sequential; a failed checkout is removed and redone once, then the bug is skipped.
Pre-existing checkouts in the volume are never touched. Stops if the volume has < 30 GB free.
Each bug's outcome is appended to out/sampling.jsonl (resume: bugs already there are not redone).

usage (container):  python3 subset150/sample.py run [Project ...]   sample (default: all plan projects, in plan order)
                    python3 subset150/sample.py final              unify all kept bugs at once -> the dataset files
"""
import json, os, shutil, subprocess, sys, time

REPO = "/repo"
D = f"{REPO}/subset150"
OUT = f"{D}/out"
SRC = f"{OUT}/src"   # per-bug drafts / unified records
NB = f"{OUT}/nb"
D4J = f"{REPO}/d4j_proj_base"
LOG = f"{OUT}/sampling.jsonl"
MIN_FREE = 30e9
OLD = f"{REPO}/data/prompts/buggy_source_data_unified_invoked.jsonl"           # the 78 (read only)
NEW = f"{REPO}/data/prompts/buggy_source_data_unified_invoked_s150new.jsonl"   # the new methods
ALL = f"{REPO}/data/prompts/buggy_source_data_unified_invoked_subset150.jsonl"  # the 78 verbatim + the new methods


def sh(cmd, env=None):
    return subprocess.run(cmd, capture_output=True, text=True, env={**os.environ, **(env or {})}, cwd=REPO)


def scripts():
    os.makedirs(NB, exist_ok=True); os.makedirs(SRC, exist_ok=True)
    for nb, keep, ovr, name in (("generate_source_data_for_prompt.ipynb", "0-4,8,75,77", "gen_src.ovr", "gen_src"),
                                ("unify_fixed_and_buggy_bugs.ipynb", "0-9,14-18,20,24,27", "unify.ovr", "unify")):
        r = sh(["python3", "run/nb2py.py", nb, f"{NB}/{name}.py", keep, f"{D}/{ovr}"])
        assert r.returncode == 0, r.stderr


def public_check():
    """unify_fixed_and_buggy_bugs.ipynb cell 4 (is_method_public_or_protected), exec'd verbatim."""
    import javalang.tree as ast, javalang.parse as parse
    cells = [c for c in json.load(open(f"{REPO}/unify_fixed_and_buggy_bugs.ipynb"))["cells"] if c["cell_type"] == "code"]
    ns = {"ast": ast, "parse": parse}
    exec("".join(cells[4]["source"]), ns)
    return ns["is_method_public_or_protected"]


def checkout(bug, v, pre):
    d = f"{D4J}/{bug}/{v}"
    if bug in pre:
        return os.path.isdir(d), 0.0  # pre-existing bug dir: never touched
    ok_marker = f"{OUT}/checkouts/{bug}_{v}.ok"  # our own completed checkouts (markers kept outside the volume)
    if os.path.isdir(d) and os.path.exists(ok_marker):
        return True, 0.0
    t0, err = time.time(), ""
    for _ in range(2):
        shutil.rmtree(d, ignore_errors=True)  # a broken (or interrupted) checkout of ours: remove and redo
        r = sh(["defects4j", "checkout", "-p", bug.rsplit("_", 1)[0], "-v", bug.rsplit("_", 1)[1] + v[0], "-w", d])
        if r.returncode == 0:
            os.makedirs(f"{OUT}/checkouts", exist_ok=True)
            open(ok_marker, "w").close()
            return True, round(time.time() - t0, 1)
        err = (r.stdout + r.stderr)[-300:]
    shutil.rmtree(d, ignore_errors=True)
    print("checkout failed", bug, v, err, flush=True)
    return False, round(time.time() - t0, 1)


def gen_src(bug, v):
    path = f"{SRC}/{bug}_{v}_draft.jsonl"
    r = sh(["python3", f"{NB}/gen_src.py"], {"VERSION": v, "S150_BUGS": bug, "S150_OUT": path})
    assert r.returncode == 0, (bug, v, r.stdout[-2000:], r.stderr[-2000:])
    return [json.loads(l) for l in open(path)]


def unify(buggy_draft, fixed_draft, out):
    r = sh(["python3", f"{NB}/unify.py"], {"S150_BUGGY_DRAFT": buggy_draft, "S150_FIXED_DRAFT": fixed_draft, "S150_OUT": out,
                                           "PYTHONHASHSEED": "0"})  # unify iterates a set: fix the order within a bug
    assert r.returncode == 0, (out, r.stdout[-2000:], r.stderr[-2000:])
    return [json.loads(l) for l in open(out)]


def process(bug, pre, is_public):
    e = {"bug": bug, "project": bug.rsplit("_", 1)[0], "n_methods": 0, "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}
    ok, e["secs_buggy"] = checkout(bug, "buggy", pre)
    if not ok:
        return {**e, "status": "buggy checkout failed"}
    b = gen_src(bug, "buggy")
    cands = [r["source:source_method_signature"] for r in b if r["focal_method_invoked"] and is_public(r["source:source_method_code_format"])]
    e.update(buggy_records=len(b), buggy_candidates=len(cands))
    if not cands:
        return {**e, "status": "no buggy record invoked + public/protected (no fixed checkout)"}
    ok, e["secs_fixed"] = checkout(bug, "fixed", pre)
    if not ok:
        return {**e, "status": "fixed checkout failed"}
    gen_src(bug, "fixed")
    u = unify(f"{SRC}/{bug}_buggy_draft.jsonl", f"{SRC}/{bug}_fixed_draft.jsonl", f"{SRC}/{bug}_unified_invoked.jsonl")
    return {**e, "status": "kept" if u else "no method passes unify", "n_methods": len(u),
            "methods": [r["source:source_method_signature"] for r in u]}


def done():
    return {e["bug"]: e for e in map(json.loads, open(LOG))} if os.path.exists(LOG) else {}


def run(projects):
    plan = json.load(open(f"{OUT}/plan.json"))
    scripts()
    pre_path = f"{OUT}/preexisting_checkouts.json"
    if not os.path.exists(pre_path):  # bug dirs in the volume before subset150 touched it
        json.dump(sorted(os.listdir(D4J)), open(pre_path, "w"))
    pre = set(json.load(open(pre_path)))
    is_public = public_check()
    for p in projects or list(plan["projects"]):
        n = sum(e["n_methods"] for e in done().values() if e["project"] == p)
        for bug in plan["projects"][p]["order"]:
            if n >= plan["projects"][p]["quota"]:
                break
            if bug in done():
                continue
            free = shutil.disk_usage(D4J).free
            if free < MIN_FREE:
                sys.exit(f"stop: {free / 1e9:.1f} GB free in the checkout volume")
            e = process(bug, pre, is_public)
            e["free_gb"] = round(free / 1e9, 1)
            with open(LOG, "a") as f:
                f.write(json.dumps(e) + "\n")
            n += e["n_methods"]
            print(p, bug, e["status"], e["n_methods"], f"-> {n}/{plan['projects'][p]['quota']}", e.get("secs_buggy"), e.get("secs_fixed"), flush=True)
        print(p, "methods", n, flush=True)


def final():
    """all kept bugs unified in one upstream unify run; must equal the per-bug results."""
    log = done()
    kept = [e for e in log.values() if e["n_methods"]]
    cat = lambda v, path: open(path, "w").writelines(l for e in kept for l in open(f"{SRC}/{e['bug']}_{v}_draft.jsonl"))
    cat("buggy", f"{SRC}/all_buggy_draft.jsonl"); cat("fixed", f"{SRC}/all_fixed_draft.jsonl")
    new = unify(f"{SRC}/all_buggy_draft.jsonl", f"{SRC}/all_fixed_draft.jsonl", f"{SRC}/all_unified_invoked.jsonl")
    per_bug = sorted((e["bug"], s) for e in kept for s in e["methods"])
    assert sorted((r["extra:project_name"].replace("_buggy", ""), r["source:source_method_signature"]) for r in new) == per_bug
    old = open(OLD).readlines()
    assert len(old) == 78
    olds = {(json.loads(l)["extra:project_name"], json.loads(l)["source:source_method_signature"]) for l in old}
    assert not olds & {(r["extra:project_name"], r["source:source_method_signature"]) for r in new}
    with open(NEW, "w") as f:
        f.writelines(json.dumps(r) + "\n" for r in new)
    with open(ALL, "w") as f:
        f.writelines(old + [json.dumps(r) + "\n" for r in new])
    plan = json.load(open(f"{OUT}/plan.json"))
    manifest = {"seed": plan["seed"], "quota": plan["quota"], "old_file": OLD.replace(REPO + "/", ""), "new_file": NEW.replace(REPO + "/", ""),
                "all_file": ALL.replace(REPO + "/", ""), "n_old": 78, "n_new": len(new),
                "new_methods": [{"new_idx": i, "all_idx": 78 + i, "bug": r["extra:project_name"].replace("_buggy", ""),
                                 "sig": r["source:source_method_signature"]} for i, r in enumerate(new)],
                "scanned": {p: [{k: log[b][k] for k in ("bug", "status", "n_methods")} for b in v["order"] if b in log]
                            for p, v in plan["projects"].items()}}
    json.dump(manifest, open(f"{D}/manifest.json", "w"), indent=1)
    print(len(new), "new methods ->", NEW, "|", 78 + len(new), "->", ALL)


if __name__ == "__main__":
    {"run": lambda: run(sys.argv[2:]), "final": final}[sys.argv[1]]()
