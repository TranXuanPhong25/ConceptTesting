#!/usr/bin/env python3
"""Huong 1 — EXECUTION-FEEDBACK LOOP (KHONG train).

concept-gen -> run_diff (compile+ASAN vuln|fixed) -> FEEDBACK (loi compile / chua no /
no ca ban fixed) -> model VIET LAI -> lap <=ROUNDS. Concept dan huong vong 1, ORACLE tinh chinh.

So 3 dieu kien tren CUNG gold (DISCRIM = compile ca 2 & no vuln & KHONG no fixed):
  blind_1shot | concept_1shot | concept_fb (concept + feedback loop)

Tai dung bench/{run_diff,prompts,common}. Teacher qua magma/llm_client (Groq | router/9router | vertex
native) — them 2026-09-16 de chay Juliet voi Gemini, dong bo voi magma/loop.py. Resumable (cache ket qua
CUOI moi item, key da gom MODEL -> doi provider/model KHONG dam cache cu).

Chay TU REPO ROOT (Groq, mac dinh, ban tieng Viet cu):
  GROQ_API_KEY=... .venv/bin/python feedback/loop.py

Chay voi Gemini qua 9router (English prompt — tranh confound ngon ngu):
  LLM_PROVIDER=router ROUTER_BASE_URL=https://.../v1 ROUTER_API_KEY=... LLM_MODEL=vertex/gemini-3-flash-preview \\
  GOLD=bench/items/gold_juliet.jsonl FB_CACHE=feedback/fb_juliet_en_gemini.jsonl \\
  CONCEPT_COND=bench_concept_en BLIND_COND=bench_blind_en \\
      .venv/bin/python feedback/loop.py

Env: ROUNDS=3 | GROQ_RPM=30 | GOLD | FB_CACHE | CONCEPT_COND=bench_concept|bench_concept2|bench_concept_en
     | BLIND_COND=bench_blind|bench_blind_en | LLM_PROVIDER=groq|router|vertex (xem magma/llm_client.py)
"""
import os, sys, json, time, hashlib, subprocess, tempfile, shutil, collections, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); BENCH = os.path.join(ROOT, "bench")
sys.path.insert(0, BENCH); sys.path.insert(0, os.path.join(ROOT, "pipeline_v3"))
import common                                                  # noqa: E402,F401
from prompts import BUILD                                      # noqa: E402
from run_diff import assemble, run_diff, CXX                   # noqa: E402
# magma/llm_client.py nap qua importlib (KHONG sys.path.insert(0,"magma")): magma/ CUNG co prompts.py
# trung ten voi bench/prompts.py -> insert vao sys.path se DE `from prompts import BUILD` o tren nhap NHAM
# module cua magma (BUILD khac schema, thieu key bench_concept/bench_blind).
_llc = importlib.util.spec_from_file_location("magma_llm_client", os.path.join(ROOT, "magma", "llm_client.py"))
llm_client = importlib.util.module_from_spec(_llc); _llc.loader.exec_module(llm_client)

CONCEPT_COND = os.environ.get("CONCEPT_COND", "bench_concept")  # bench_concept | bench_concept2 | bench_concept_en
BLIND_COND = os.environ.get("BLIND_COND", "bench_blind")        # bench_blind | bench_blind_en
_concept_builder = BUILD[CONCEPT_COND]
_blind_builder = BUILD[BLIND_COND]
ROUNDS   = int(os.environ.get("ROUNDS", "3"))
MODEL    = llm_client.model_id()          # ten model theo LLM_PROVIDER (groq | router | vertex) -> tach cache
GROQ_RPM = int(os.environ.get("GROQ_RPM", "30"))
GOLD     = os.environ.get("GOLD", os.path.join(BENCH, "items", "gold_juliet.jsonl"))
CACHE    = os.environ.get("FB_CACHE", os.path.join(HERE, "fb_juliet.jsonl"))
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


from langchain_core.messages import SystemMessage, HumanMessage, AIMessage  # noqa: E402
llm = llm_client.make_llm(temperature=0.3)   # None neu thieu key -> chi doc duoc tu cache co san
_mi = 60.0 / max(1, GROQ_RPM); _last = [0.0]


def call(msgs):
    if llm is None:
        raise SystemExit("Cache mieng va KHONG co LLM (thieu key/base_url cho LLM_PROVIDER=%s)."
                          % os.environ.get("LLM_PROVIDER", "groq"))
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


def _crun(src, timeout=20):
    """Compile+chay, tra {compiles, fires, err} (err = stderr cho feedback)."""
    if "main" not in src:
        return {"compiles": 0, "fires": 0, "err": "thieu int main()"}
    d = tempfile.mkdtemp(); cf = os.path.join(d, "t.c"); b = os.path.join(d, "t.bin")
    open(cf, "w").write(src)
    try:
        r = subprocess.run([CXX, "-fsanitize=address,undefined", "-g", "-O0", "-w", cf, "-o", b],
                           capture_output=True, timeout=timeout)
    except Exception:
        shutil.rmtree(d, ignore_errors=True); return {"compiles": 0, "fires": 0, "err": "compile timeout"}
    if r.returncode != 0:
        e = r.stderr.decode(errors="ignore"); shutil.rmtree(d, ignore_errors=True)
        return {"compiles": 0, "fires": 0, "err": "LOI COMPILE:\n" + e[-700:]}
    try:
        run = subprocess.run([b], capture_output=True, timeout=timeout,
                             env={**os.environ, "ASAN_OPTIONS": "detect_leaks=0", "UBSAN_OPTIONS": "halt_on_error=1"})
        e = run.stderr.decode(errors="ignore")
        fires = 1 if ("AddressSanitizer" in e or "runtime error:" in e or "UndefinedBehaviorSanitizer" in e) else 0
    except subprocess.TimeoutExpired:
        e, fires = "TIMEOUT khi chay", 0
    shutil.rmtree(d, ignore_errors=True)
    return {"compiles": 1, "fires": fires, "err": e[-700:]}


def _diag(test, item):
    return _crun(assemble(item, "func_vuln", test)), _crun(assemble(item, "func_fixed", test))


def _scoreVF(v, f):
    """3=discriminate > 2=compile+no vuln > 1=compile > 0. De giu output TOT NHAT qua cac vong."""
    if v["compiles"] and f["compiles"] and v["fires"] and not f["fires"]:
        return 3
    if v["compiles"] and v["fires"]:
        return 2
    if v["compiles"]:
        return 1
    return 0


def _feedback(v, f, fn):
    """Thong diep sua loi dua tren ket qua thuc thi. None = da discriminate (dung)."""
    if not v["compiles"]:
        return ("Test KHONG bien dich duoc.\n%s\nSua: chi #include header chuan, GOI `%s(...)`, "
                "KHONG dinh nghia lai ham/struct da cung cap, KHONG dung gtest/EXPECT_DEATH." % (v["err"], fn))
    if not v["fires"]:
        return ("Test bien dich OK nhung AddressSanitizer/UBSan KHONG bao loi tren ban CO lo hong "
                "-> chua kich hoat bug. Dung input DOC HAI hon, dam bao `%s(...)` di dung duong dan loi "
                "(vd: truyen NULL / kich thuoc vuot buffer / con tro da free) de sanitizer bao loi." % fn)
    if f["fires"]:
        return ("Test lam CA ban DA SUA (an toan) bao loi -> BAO DONG GIA: test tu gay loi bo nho "
                "(vd tu overflow trong main) chu khong phai loi cua `%s(...)`. Chi duoc kich hoat loi "
                "BEN TRONG `%s(...)`; main khong duoc tu crash." % (fn, fn))
    return None


# EN (2026-09-16): feedback tieng Anh — dung khi CONCEPT_COND/BLIND_COND la ban _en (Gemini), de khong
# tron ngon ngu GIUA vong 0 (English) va cac vong feedback sau (se la Vietnamese neu dung ham cu).
def _feedback_en(v, f, fn):
    if not v["compiles"]:
        return ("The test did NOT compile.\n%s\nFix: only #include standard headers, CALL `%s(...)`, "
                "do NOT redefine the provided functions/structs, do NOT use gtest/EXPECT_DEATH." % (v["err"], fn))
    if not v["fires"]:
        return ("The test compiled OK but AddressSanitizer/UBSan did NOT report an error on the vulnerable "
                "build -> the bug was not triggered. Use a more malicious input, make sure `%s(...)` goes "
                "down the faulty path (e.g. pass NULL / a size beyond the buffer / an already-freed pointer) "
                "so the sanitizer fires." % fn)
    if f["fires"]:
        return ("The test makes the PATCHED (safe) build fire too -> FALSE POSITIVE: the test itself causes "
                "a memory error (e.g. an overflow in `main`) rather than a bug in `%s(...)`. Only trigger the "
                "error INSIDE `%s(...)`; `main` itself must not crash." % (fn, fn))
    return None


_EN = CONCEPT_COND.endswith("_en") or BLIND_COND.endswith("_en")   # 1 cong tac dong bo ngon ngu ca 2 nhanh


def gen_1shot(item, builder, tag):
    k = hashlib.sha1(("%s::%s::%s::%s" % (MODEL, tag, item["id"], item["func_vuln"])).encode()).hexdigest()
    if k in _cache:
        return _cache[k]
    m = builder(item)
    out = call([SystemMessage(content=m[0]["content"]), HumanMessage(content=m[1]["content"])]) or ""
    _save(k, out); return out


def gen_feedback(item, seed_out):
    """concept_fb = concept_1shot (seed_out, vong 0) + refine bang feedback <=ROUNDS lan.
    Giu output TOT NHAT -> concept_fb LUON >= concept_1shot (co lap dung dong gop feedback)."""
    k = hashlib.sha1(("%s::fbseed%d::%s::%s::%s" % (MODEL, ROUNDS, CONCEPT_COND, item["id"], item["func_vuln"])).encode()).hexdigest()
    if k in _cache:
        return _cache[k]
    m = _concept_builder(item)
    hist = [SystemMessage(content=m[0]["content"]), HumanMessage(content=m[1]["content"])]
    fn = item["focal"]; out = seed_out
    v, f = _diag(out, item); best = (_scoreVF(v, f), out)      # vong 0 = concept_1shot
    _fb = _feedback_en if _EN else _feedback
    _rewrite = "\n\nRewrite the COMPLETE test (a single ```c ... ``` block)." if _EN \
        else "\n\nVIET LAI test HOAN CHINH (mot khoi ```c ... ```)."
    for _ in range(ROUNDS):
        if best[0] == 3:
            break                                              # da discriminate -> dung
        hist.append(AIMessage(content=out))
        hist.append(HumanMessage(content=_fb(v, f, fn) + _rewrite))
        out = call(hist) or out
        v, f = _diag(out, item); sc = _scoreVF(v, f)
        if sc > best[0]:
            best = (sc, out)
    _save(k, best[1]); return best[1]


def disc_of(out, item):
    r = run_diff(out, item)
    return 1 if (r["compiles_vuln"] and r["compiles_fixed"] and r["fires_vuln"] and not r["fires_fixed"]) else 0


def main():
    items = [json.loads(l) for l in open(GOLD) if l.strip()]
    pos = [it for it in items if it["expect"] != "safe"]
    CONDS = ["blind_1shot", "concept_1shot", "concept_fb"]
    agg = {c: 0 for c in CONDS}
    fam = {c: collections.defaultdict(lambda: [0, 0]) for c in CONDS}
    print("items:", len(pos), "| model:", MODEL, "| ROUNDS:", ROUNDS, "| gold:", os.path.basename(GOLD),
          "| CONCEPT_COND:", CONCEPT_COND, "| BLIND_COND:", BLIND_COND)
    for i, it in enumerate(pos):
        c1 = gen_1shot(it, _concept_builder, CONCEPT_COND)
        outs = {"blind_1shot": gen_1shot(it, _blind_builder, BLIND_COND),
                "concept_1shot": c1,
                "concept_fb": gen_feedback(it, c1)}          # feedback bat dau tu concept_1shot
        for c in CONDS:
            d = disc_of(outs[c], it)
            agg[c] += d; fam[c][it["family"]][0] += d; fam[c][it["family"]][1] += 1
        if (i + 1) % 5 == 0:
            print("  %d/%d" % (i + 1, len(pos)))
    n = len(pos) or 1
    print("\n=== DISCRIM (%d item, ROUNDS=%d) ===" % (len(pos), ROUNDS))
    for c in CONDS:
        print("  %-14s %3.0f%%  (%d/%d)" % (c, 100 * agg[c] / n, agg[c], len(pos)))
    print("\n=== per-family (disc/n) ===")
    print("  %-13s %10s %12s %12s" % ("family", "blind", "concept", "concept_fb"))
    for f in sorted({x for c in CONDS for x in fam[c]}):
        b, c1, cf = fam["blind_1shot"][f], fam["concept_1shot"][f], fam["concept_fb"][f]
        print("  %-13s %8d/%-2d %10d/%-2d %10d/%-2d" % (f, b[0], b[1], c1[0], c1[1], cf[0], cf[1]))
    print("\nSo sanh chinh: concept_fb vs concept_1shot = tac dung cua VONG PHAN HOI.")


if __name__ == "__main__":
    main()
