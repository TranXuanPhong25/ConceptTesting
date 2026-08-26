#!/usr/bin/env python3
"""Huong A — CONCEPT LAI FEEDBACK bang COVERAGE (fusion huong-1 + concept).

Vong feedback thuong chi biet "co no / khong no". Ban nay them tin hieu CONCEPT-COVERAGE:
test co CHAM dong thao tac nguy hiem (ptr_deref/buffer_access/free) ma concept danh dau khong?
-> feedback CU THE: "chua cham dong X (`free(..)`/`*p`) -> lai execution toi do" vs "cham roi nhung
input chua du doc hai". Concept tro thanh MUC TIEU REACHABILITY trong vong lap.

So 4 dieu kien: blind_1shot | concept_1shot | concept_fb (feedback thuong) | concept_fb_cov (co coverage).
Tai dung cache cua feedback/loop.py cho 3 cot dau (cung key) -> chi sinh moi concept_fb_cov.

Chay TU REPO ROOT:  GROQ_API_KEY=... .venv/bin/python feedback/loop_cov.py
Env: ROUNDS=3 | GROQ_MODEL | GROQ_RPM=30 | GOLD | FB_CACHE | CONCEPT_COND=bench_concept
"""
import os, sys, json, time, hashlib, glob, subprocess, tempfile, shutil, collections

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); BENCH = os.path.join(ROOT, "bench")
sys.path.insert(0, BENCH); sys.path.insert(0, os.path.join(ROOT, "pipeline_v3"))
import common                                            # noqa: E402,F401
from prompts import build_bench_blind, BUILD             # noqa: E402
from run_diff import assemble, run_diff, HEADER, CXX     # noqa: E402

CONCEPT_COND = os.environ.get("CONCEPT_COND", "bench_concept")
_concept_builder = BUILD[CONCEPT_COND]
ROUNDS     = int(os.environ.get("ROUNDS", "3"))
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
GROQ_RPM   = int(os.environ.get("GROQ_RPM", "30"))
GOLD       = os.environ.get("GOLD", os.path.join(BENCH, "items", "gold.jsonl"))
CACHE      = os.environ.get("FB_CACHE", os.path.join(HERE, "fb_cache.jsonl"))
KEY        = os.environ.get("GROQ_API_KEY")
GCOV       = shutil.which("gcov")
RISK       = {2, 4, 6}                                   # ptr_deref, buffer_access, free = thao tac nguy hiem
if not KEY:
    raise SystemExit("Thieu GROQ_API_KEY.")
if not CXX:
    raise SystemExit("Khong co compiler.")

_cache = {}
if os.path.exists(CACHE):
    for l in open(CACHE):
        try:
            o = json.loads(l); _cache[o["key"]] = o["target"]
        except Exception:
            pass


def _save(k, v):
    _cache[k] = v
    open(CACHE, "a").write(json.dumps({"key": k, "target": v}) + "\n")


from langchain_groq import ChatGroq                                        # noqa: E402
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage  # noqa: E402
llm = ChatGroq(model=GROQ_MODEL, temperature=0.3, groq_api_key=KEY)
_mi = 60.0 / max(1, GROQ_RPM); _last = [0.0]


def call(msgs):
    for a in range(6):
        dt = time.monotonic() - _last[0]
        if dt < _mi:
            time.sleep(_mi - dt)
        _last[0] = time.monotonic()
        try:
            return llm.invoke(msgs).content
        except Exception as e:
            w = min(60, 4 * 2 ** a); print("[warn] retry %ds: %s" % (w, str(e)[:80])); time.sleep(w)
    return None


# ---- concept risky lines -> vi tri dong trong source da lap rap ----
def _risky_idx(item):
    lc = item.get("lines_concept") or {}
    return sorted(int(i) for i, v in lc.items() if any(len(v) > j and v[j] for j in RISK))


def _risky_src(item):
    pre = item.get("driver_prelude") or ""
    start = (HEADER + pre + "\n").count("\n") + 1        # dong (1-based) noi func_vuln bat dau
    return {start + i for i in _risky_idx(item)}


def _risky_code(item):
    lines = item["func_vuln"].split("\n")
    codes = ["`%s`" % lines[i].strip() for i in _risky_idx(item) if 0 <= i < len(lines)]
    return " / ".join(codes) or "dong thao tac bo nho nguy hiem"


def _gcov_exec(d):
    g = glob.glob(os.path.join(d, "*.gcda"))
    if not (GCOV and g):
        return None
    subprocess.run([GCOV, os.path.basename(g[0])], cwd=d, capture_output=True, timeout=15)
    gp = os.path.join(d, "t.c.gcov")
    if not os.path.exists(gp):
        return None
    ex = set()
    for line in open(gp, errors="ignore"):
        p = line.split(":", 2)
        if len(p) < 2:
            continue
        cnt, ln = p[0].strip(), p[1].strip()
        if ln.isdigit() and cnt and cnt not in ("-", "#####") and cnt[0].isdigit():
            ex.add(int(ln))
    return ex


def _crun_cov(src, risky_src, timeout=20):
    """Compile (ASAN+coverage) + chay. reached = co dong risky nao duoc thuc thi (khi KHONG no)."""
    if "main" not in src:
        return {"compiles": 0, "fires": 0, "reached": None, "err": "thieu main"}
    d = tempfile.mkdtemp(); open(os.path.join(d, "t.c"), "w").write(src)
    try:
        r = subprocess.run([CXX, "-fsanitize=address,undefined", "--coverage", "-g", "-O0", "-w", "t.c", "-o", "t"],
                           cwd=d, capture_output=True, timeout=timeout)
    except Exception:
        shutil.rmtree(d, ignore_errors=True); return {"compiles": 0, "fires": 0, "reached": None, "err": "compile timeout"}
    if r.returncode != 0:
        e = r.stderr.decode(errors="ignore"); shutil.rmtree(d, ignore_errors=True)
        return {"compiles": 0, "fires": 0, "reached": None, "err": "LOI COMPILE:\n" + e[-600:]}
    reached = None
    try:
        run = subprocess.run(["./t"], cwd=d, capture_output=True, timeout=timeout,
                             env={**os.environ, "ASAN_OPTIONS": "detect_leaks=0", "UBSAN_OPTIONS": "halt_on_error=1"})
        e = run.stderr.decode(errors="ignore")
        fires = 1 if ("AddressSanitizer" in e or "runtime error:" in e or "UndefinedBehaviorSanitizer" in e) else 0
        if not fires:                                   # chay-sach -> gcda co du -> tinh reached
            ex = _gcov_exec(d)
            reached = bool(risky_src & ex) if (ex and risky_src) else None
    except subprocess.TimeoutExpired:
        e, fires = "TIMEOUT", 0
    shutil.rmtree(d, ignore_errors=True)
    return {"compiles": 1, "fires": fires, "reached": reached, "err": e[-600:]}


def _crun(src, timeout=20):                             # cho ban fixed (khong can coverage)
    if "main" not in src:
        return {"compiles": 0, "fires": 0}
    d = tempfile.mkdtemp(); open(os.path.join(d, "t.c"), "w").write(src)
    try:
        r = subprocess.run([CXX, "-fsanitize=address,undefined", "-g", "-O0", "-w", "t.c", "-o", "t"],
                           cwd=d, capture_output=True, timeout=timeout)
    except Exception:
        shutil.rmtree(d, ignore_errors=True); return {"compiles": 0, "fires": 0}
    if r.returncode != 0:
        shutil.rmtree(d, ignore_errors=True); return {"compiles": 0, "fires": 0}
    try:
        run = subprocess.run(["./t"], cwd=d, capture_output=True, timeout=timeout,
                             env={**os.environ, "ASAN_OPTIONS": "detect_leaks=0", "UBSAN_OPTIONS": "halt_on_error=1"})
        e = run.stderr.decode(errors="ignore")
        fires = 1 if ("AddressSanitizer" in e or "runtime error:" in e or "UndefinedBehaviorSanitizer" in e) else 0
    except subprocess.TimeoutExpired:
        fires = 0
    shutil.rmtree(d, ignore_errors=True)
    return {"compiles": 1, "fires": fires}


def _scoreVF(v, f):
    if v["compiles"] and f["compiles"] and v["fires"] and not f["fires"]:
        return 3
    if v["compiles"] and v["fires"]:
        return 2
    return 1 if v["compiles"] else 0


def _feedback_cov(v, f, item, risky_code):
    fn = item["focal"]
    if not v["compiles"]:
        return ("Test KHONG bien dich duoc.\n%s\nSua: chi #include header chuan, GOI `%s(...)`, "
                "KHONG dinh nghia lai ham/struct da cung cap, KHONG gtest." % (v["err"], fn))
    if not v["fires"]:
        if v.get("reached") is False:                   # <-- tin hieu concept-coverage
            return ("Test bien dich OK nhung CHUA CHAM thao tac nguy hiem: %s. Execution hien tai KHONG "
                    "di qua dong do -> chinh input/cach goi `%s(...)` de CHAY DUNG duong dan chua thao tac loi." % (risky_code, fn))
        return ("Da cham thao tac nguy hiem (%s) nhung sanitizer CHUA bao -> input CHUA DU DOC HAI. "
                "Tang muc do: chi so/kich thuoc VUOT HAN, hoac con tro = NULL / da bi free." % risky_code)
    if f["fires"]:
        return ("Test lam CA ban DA SUA (an toan) bao loi -> BAO DONG GIA: test tu gay loi trong main. "
                "Chi duoc kich hoat loi BEN TRONG `%s(...)`." % fn)
    return None


def gen_1shot(item, builder, tag):
    k = hashlib.sha1(("%s::%s::%s::%s" % (GROQ_MODEL, tag, item["id"], item["func_vuln"])).encode()).hexdigest()
    if k in _cache:
        return _cache[k]
    m = builder(item)
    out = call([SystemMessage(content=m[0]["content"]), HumanMessage(content=m[1]["content"])]) or ""
    _save(k, out); return out


def gen_feedback(item, seed_out, cov):
    """cov=False -> feedback thuong (khop loop.py, tai dung cache). cov=True -> them coverage."""
    tag = "fbcov" if cov else "fbseed"
    k = hashlib.sha1(("%s::%s%d::%s::%s::%s" % (GROQ_MODEL, tag, ROUNDS, CONCEPT_COND, item["id"], item["func_vuln"])).encode()).hexdigest()
    if k in _cache:
        return _cache[k]
    m = _concept_builder(item)
    hist = [SystemMessage(content=m[0]["content"]), HumanMessage(content=m[1]["content"])]
    risky_src, risky_code = _risky_src(item), _risky_code(item)
    out = seed_out
    v = _crun_cov(assemble(item, "func_vuln", out), risky_src if cov else set())
    f = _crun(assemble(item, "func_fixed", out)); best = (_scoreVF(v, f), out)
    for _ in range(ROUNDS):
        if best[0] == 3:
            break
        fb = _feedback_cov(v, f, item, risky_code)
        hist.append(AIMessage(content=out))
        hist.append(HumanMessage(content=fb + "\n\nVIET LAI test HOAN CHINH (mot khoi ```c ... ```)."))
        out = call(hist) or out
        v = _crun_cov(assemble(item, "func_vuln", out), risky_src if cov else set())
        f = _crun(assemble(item, "func_fixed", out)); sc = _scoreVF(v, f)
        if sc > best[0]:
            best = (sc, out)
    _save(k, best[1]); return best[1]


def disc_of(out, item):
    r = run_diff(out, item)
    return 1 if (r["compiles_vuln"] and r["compiles_fixed"] and r["fires_vuln"] and not r["fires_fixed"]) else 0


def main():
    items = [json.loads(l) for l in open(GOLD) if l.strip()]
    pos = [it for it in items if it["expect"] != "safe"]
    CONDS = ["blind_1shot", "concept_1shot", "concept_fb", "concept_fb_cov"]
    agg = {c: 0 for c in CONDS}; fam = {c: collections.defaultdict(lambda: [0, 0]) for c in CONDS}
    print("items:", len(pos), "| model:", GROQ_MODEL, "| ROUNDS:", ROUNDS,
          "| gcov:", bool(GCOV), "| gold:", os.path.basename(GOLD))
    for i, it in enumerate(pos):
        c1 = gen_1shot(it, _concept_builder, CONCEPT_COND)
        outs = {"blind_1shot": gen_1shot(it, build_bench_blind, "bench_blind"),
                "concept_1shot": c1,
                "concept_fb": gen_feedback(it, c1, cov=False),
                "concept_fb_cov": gen_feedback(it, c1, cov=True)}
        for c in CONDS:
            d = disc_of(outs[c], it)
            agg[c] += d; fam[c][it["family"]][0] += d; fam[c][it["family"]][1] += 1
        if (i + 1) % 5 == 0:
            print("  %d/%d" % (i + 1, len(pos)))
    n = len(pos) or 1
    print("\n=== DISCRIM (%d item, ROUNDS=%d) ===" % (len(pos), ROUNDS))
    for c in CONDS:
        print("  %-16s %3.0f%%  (%d/%d)" % (c, 100 * agg[c] / n, agg[c], len(pos)))
    print("\n=== per-family (disc/n) ===")
    print("  %-13s %11s %12s %11s %13s" % ("family", "blind", "concept", "concept_fb", "concept_fb_cov"))
    for f in sorted({x for c in CONDS for x in fam[c]}):
        cells = " ".join("%9d/%-2d" % (fam[c][f][0], fam[c][f][1]) for c in CONDS)
        print("  %-13s %s" % (f, cells))
    print("\nSo sanh chinh: concept_fb_cov vs concept_fb = tac dung cua COVERAGE-STEERING (concept lai feedback).")


if __name__ == "__main__":
    main()
