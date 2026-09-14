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

# ===== CHONG RO RI (them 2026-09-14) =====
# SEED_SRC: nguon seed khoi dong.
#   corpus (MAC DINH) — chi dung corpus goc cua thu vien. Dung DUNG giao thuc cua paper Magma
#       ("bootstrapped with the same set of seed files, sourced from the original target codebase")
#       va KHONG dinh gi tu LLM => SymCC la baseline doc lap that su.
#   llm    — them cac input LLM da sinh (taint._cache_inputs). CANH BAO: cache do gom ca cond
#       `magma_concept` (bê fault_cond tu PATCH) va ca cac key v1 tu truoc khi va lo ro feedback.
#       Dung cai nay thi SymCC KHONG con doc lap — no thua huong dap an qua seed. Chi dung khi muon
#       do "SymCC noi tiep LLM" (hybrid) va PHAI goi dung ten nhu vay.
# GUIDE: chon input nao de dao sau o vong sau.
#   canary (MAC DINH) — giu input con `reached`. Tin hieu nay lay tu CANARY, ma canary duoc dat DUNG
#       cho patch => la thong tin tu dap an. Day la concolic CO DAN DUONG, phai khai bao.
#   none   — khong dung canary, giu input dau tien theo thu tu SymCC sinh ra (vanilla SymCC).
SEED_SRC = os.environ.get("SEED_SRC", "corpus")
GUIDE = os.environ.get("GUIDE", "canary")

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


# ===== XUAT HINT NGAY TRONG LUC CHAM (EMIT_HINTS=1) =====
# loop_symcc (cham baseline SymCC-thuan) va export_hints (lay hint cho hybrid) DEU solve SymCC cung 100 bug.
# De khoi solve 2 lan (~2-4h), khi EMIT_HINTS=1 loop_symcc luu luon hint: mot input SymCC giai ra ma CHAM
# ham loi + cac byte no doi so voi seed. Sau do run_hybrid.sh bo qua export (hint da co) va chi gen.
EMIT_HINTS = os.environ.get("EMIT_HINTS") == "1"
HINTDIR = os.path.join(HERE, "hints")
HINT_MAXBYTES = int(os.environ.get("HINT_MAXBYTES", "192"))


def _hex(b, cap=HINT_MAXBYTES):
    b = b[:cap]
    return " ".join("%02x" % c for c in b)


def _changed(seed, solved, topk=12):
    n = min(len(seed), len(solved)); diffs = []
    for i in range(n):
        if seed[i] != solved[i]:
            diffs.append((i, seed[i], solved[i]))
    return diffs[:topk]


def _save_hint(item, seed, solved, n_solved):
    os.makedirs(HINTDIR, exist_ok=True)
    ch = _changed(seed, solved)
    json.dump({"bug_id": item["bug_id"], "target": item["target"], "pick_mode": "loop-reached",
               "n_solved": n_solved, "seed_len": len(seed), "solved_len": len(solved),
               "solved_hex": _hex(solved), "seed_hex": _hex(seed),
               "changed": [{"off": o, "from": "0x%02x" % a, "to": "0x%02x" % b} for (o, a, b) in ch]},
              open(os.path.join(HINTDIR, "%s.json" % item["bug_id"]), "w"), indent=1)


def _bootstrap(item):
    """Nhu taint.bootstrap_reaching nhung KIEM SOAT nguon seed (xem ghi chu SEED_SRC o dau file).
    Mac dinh corpus-only => khong thua huong bat ky input nao do LLM sinh (ke ca cond co leak)."""
    pool = taint._corpus_seeds(item)
    if SEED_SRC == "llm":
        pool = taint._cache_inputs(item) + pool
    seen, tried = set(), 0
    for d in pool:
        if tried >= SEED_BUDGET:
            break
        h = hash(d)
        if h in seen or not d:
            continue
        seen.add(h); tried += 1
        res = run_input(d, item)
        if res["reached"]:
            return {"seed": d, "reached": 1, "triggered": res["triggered"]}
    return None


def run_item(item):
    """Tra (best_status, so_input_da_giai, co_seed_khong). best: 0 khong co seed cham | 1 | 2 | 3."""
    boot = _bootstrap(item)
    if not boot:
        return 0, 0, False                                     # khong co seed nao CHAM ham loi => SymCC vo phuong
    seeds, best, nsolved, seen = [boot["seed"]], 2 + boot["triggered"], 0, set()
    hint_saved = [False]

    def _maybe_hint(solved):                                   # luu 1 input CHAM ham loi lam hint (lan dau)
        if EMIT_HINTS and not hint_saved[0]:
            _save_hint(item, boot["seed"], solved, nsolved); hint_saved[0] = True

    if best == 3:                                              # seed da trigger san (hiem) -> khong can giai
        if EMIT_HINTS:
            _save_hint(item, boot["seed"], boot["seed"], 0)
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
                if st >= 2:
                    _maybe_hint(c)                             # input nay CHAM ham loi -> dung lam hint
                if st == 3:
                    return 3, nsolved, True
                # GUIDE=canary: chi dao sau input CON cham ham loi — tin hieu nay tu canary (= tu patch),
                # nen day la concolic CO DAN DUONG. GUIDE=none: khong dung canary (vanilla SymCC).
                if GUIDE != "canary" or st == 2:
                    nxt.append(c)
        if not nxt:
            break
        seeds = nxt[:8]                                        # chan no bung so nhanh
    return best, nsolved, True


def main():
    # GUARD chong chay TRUNG (su co 2026-09-14: chay 2 lan song song -> 2x RAM Z3 + de len run100.log/
    # results_symcc.json/oracle_cache). Chi cho 1 tien trinh loop_symcc mot luc.
    import atexit
    lock = os.path.join(HERE, ".loop_symcc.lock")
    if os.path.exists(lock):
        try:
            pid = int(open(lock).read().strip()); os.kill(pid, 0)
            raise SystemExit("[DANG CHAY] da co loop_symcc.py khac (PID %d). Chay song song se tranh RAM "
                             "va de len ket qua. Doi no xong, hoac: kill %d && rm %s" % (pid, pid, lock))
        except (ValueError, ProcessLookupError, PermissionError):
            pass
    open(lock, "w").write(str(os.getpid()))
    atexit.register(lambda: os.path.exists(lock) and os.remove(lock))

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
    print("SEED_SRC=%s%s | GUIDE=%s%s"
          % (SEED_SRC, "" if SEED_SRC == "corpus" else "  <-- KHONG doc lap: seed tu cache LLM (co cond leak)",
             GUIDE, "  <-- co dan duong bang canary (tin hieu tu patch)" if GUIDE == "canary" else ""))

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
