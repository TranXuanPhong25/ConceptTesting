#!/usr/bin/env python3
"""CONCOLIC THAT (SymCC + Z3) tren Magma — baseline program-analysis de dat canh LLM.

Khac han `byte_sweep/` (truoc day toi goi sai la "concolic"): o day binary duoc BIEN DICH co instrument
SymCC, chay 1 seed se thu PATH CONSTRAINT thuc su, roi Z3 phu dinh tung dieu kien nhanh va GIAI ra
input moi. Khong he co XOR-flip do byte.

Vong lap (concolic exploration, BFS theo vong):
    seed cham ham loi  --SymCC+Z3-->  cac input lat nhanh  --oracle canary-->  reached/triggered
    input nao CON cham ham loi  -->  lam seed cho vong sau

Cham diem dung DUNG oracle vi-phan cua magma/oracle.py (cap image vuln/fixed + canary) => so sanh
truc tiep duoc voi bang LLM.

Chay TU REPO ROOT:
    .venv/bin/python symcc/loop_symcc.py                       # tat ca target co image symcc
    GOLD=/tmp/png001.jsonl ROUNDS=2 .venv/bin/python symcc/loop_symcc.py
Env: ROUNDS=2 | SOLVE_TIMELIMIT=300s | MAX_CAND=200 | SEED_BUDGET=25
"""
import os, sys, json, glob, time, shutil, tempfile, subprocess

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "magma")); sys.path.insert(0, os.path.join(ROOT, "reach"))
from oracle import run_input, have_images, assert_healthy      # noqa: E402
import taint                                                   # noqa: E402 (bootstrap_reaching)

ROUNDS = int(os.environ.get("ROUNDS", "2"))
SOLVE_TIMELIMIT = os.environ.get("SOLVE_TIMELIMIT", "300s")
MAX_CAND = int(os.environ.get("MAX_CAND", "200"))
SEED_BUDGET = int(os.environ.get("SEED_BUDGET", "25"))
DOCKER_TIMEOUT = int(os.environ.get("DOCKER_TIMEOUT", "900"))

# Chay solve.sh trong container: seed vao /host/seed, cac input giai duoc do ra /host/out.
_SOLVE = ('set -e; mkdir -p /tmp/out; cp /host/seed /tmp/seed; '
          '"$FUZZER/solve.sh" /tmp/seed /tmp/out || true; '
          'cp -a /tmp/out/. /host/out/ 2>/dev/null || true; '
          'echo "N=$(find /tmp/out -type f | wc -l)"')


def have_symcc(target):
    r = subprocess.run(["docker", "image", "inspect", "magma-%s-symcc" % target], capture_output=True)
    return r.returncode == 0


def symcc_solve(seed, item):
    """1 buoc concolic: seed -> list[bytes] cac input SymCC/Z3 giai ra (lat nhanh tren duong da chay)."""
    d = tempfile.mkdtemp(prefix="symcc_")
    try:
        out = os.path.join(d, "out"); os.makedirs(out)
        with open(os.path.join(d, "seed"), "wb") as f:
            f.write(seed)
        os.chmod(d, 0o777); os.chmod(out, 0o777)              # container chay uid 1000, phai ghi duoc
        cmd = ["docker", "run", "--rm", "--platform", "linux/amd64",
               "-e", "PROGRAM=%s" % item["program"], "-e", "SOLVE_TIMELIMIT=%s" % SOLVE_TIMELIMIT,
               "-v", "%s:/host" % d, "--entrypoint", "bash",
               "magma-%s-symcc" % item["target"], "-c", _SOLVE]
        try:
            subprocess.run(cmd, capture_output=True, timeout=DOCKER_TIMEOUT)
        except subprocess.TimeoutExpired:
            return []
        cands = []
        for p in sorted(glob.glob(os.path.join(out, "*")))[:MAX_CAND]:
            if os.path.isfile(p):
                with open(p, "rb") as f:
                    cands.append(f.read())
        return cands
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _status(res):
    if res["triggered"] and not res["crash_fixed"]:
        return 3
    return 2 if res["reached"] else 1


def run_item(item):
    """Tra (best_status, so_input_da_giai, co_seed_khong). best: 0 khong co seed cham | 1 | 2 | 3."""
    boot = taint.bootstrap_reaching(item, budget=SEED_BUDGET)
    if not boot:
        return 0, 0, False                                     # khong co seed nao CHAM ham loi => SymCC vo phuong
    seeds, best, nsolved, seen = [boot["seed"]], 2 + boot["triggered"], 0, set()
    if best == 3:                                              # seed da trigger san (hiem) -> khong can giai
        return 3, 0, True
    for _ in range(ROUNDS):
        nxt = []
        for s in seeds:
            for c in symcc_solve(s, item):
                h = hash(c)
                if h in seen or not c:
                    continue
                seen.add(h); nsolved += 1
                st = _status(run_input(c, item))
                best = max(best, st)
                if st == 3:
                    return 3, nsolved, True
                if st == 2:
                    nxt.append(c)                              # con cham ham loi -> dao sau vong sau
        if not nxt:
            break
        seeds = nxt[:8]                                        # chan no bung so nhanh
    return best, nsolved, True


def main():
    assert_healthy()
    g = os.environ.get("GOLD")
    files = [g] if g else sorted(glob.glob(os.path.join(ROOT, "magma", "items", "*.jsonl")))
    items = [json.loads(l) for f in files for l in open(f) if l.strip()]
    items = [i for i in items if have_images(i["target"])]
    miss = sorted({i["target"] for i in items if not have_symcc(i["target"])})
    if miss:
        n0 = len(items); items = [i for i in items if have_symcc(i["target"])]
        print("[BO QUA] chua co image symcc cho: %s -> con %d/%d item" % (", ".join(miss), len(items), n0))
    print("items:", len(items), "| ROUNDS:", ROUNDS, "| SOLVE_TIMELIMIT:", SOLVE_TIMELIMIT)

    agg = {"seed": 0, "reach": 0, "trig": 0, "solved": 0}
    per = {}
    for it in items:
        t0 = time.time()
        b, n, has_seed = run_item(it)
        agg["seed"] += has_seed; agg["reach"] += (b >= 2); agg["trig"] += (b == 3); agg["solved"] += n
        per[it["bug_id"]] = int(b == 3)
        print("  %-10s best=%d  input_giai=%-4d  %.0fs%s"
              % (it["bug_id"], b, n, time.time() - t0, "" if has_seed else "  (KHONG co seed cham)"))
        sys.stdout.flush()

    n = len(items) or 1
    print("\n%-22s %6s" % ("SymCC (concolic that)", "/%d" % n))
    print("%-22s %6d   (seed bootstrap cham ham loi)" % ("co seed", agg["seed"]))
    print("%-22s %6d" % ("REACHED", agg["reach"]))
    print("%-22s %6d" % ("TRIGGER", agg["trig"]))
    print("%-22s %6d   (tong input Z3 giai ra)" % ("input da giai", agg["solved"]))
    out = os.path.join(HERE, "results_symcc.json")
    json.dump({"per_bug": per, "agg": agg, "n": n, "rounds": ROUNDS}, open(out, "w"), indent=1)
    print("-> ghi", out, "(dung lab.mcnemar de so voi bang LLM)")


if __name__ == "__main__":
    main()
