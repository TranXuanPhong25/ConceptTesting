#!/usr/bin/env python3
"""Magma FEEDBACK loop (CEGIS, KHONG train): sinh -> oracle(reached/triggered) -> phan hoi -> viet lai <=ROUNDS.

Tin hieu dan duong = canary REACHED (cham ham loi) va TRIGGERED (thoa dieu kien). Phan hoi noi ro model
dang o dau: chua render / chua cham / cham nhung chua thoa fault_cond / pha bua (crash ca fixed).
So blind_fb vs concept_fb. Ground-truth = canary. Giu best (monotonic).

Chay TU REPO ROOT:  GROQ_API_KEY=gsk_... ROUNDS=3 SAMPLES=1 .venv/bin/python magma/loop.py
Env: GROQ_MODEL | GROQ_RPM=30 | ROUNDS=3 | CONDS=magma_blind,magma_concept | GOLD | MAGMA_LOOP_CACHE
"""
import os, sys, json, time, glob, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(ROOT, "bench"))
import lab                                                      # noqa: E402 (bench)
from oracle import run_input, render_input, assert_healthy, have_images                      # noqa: E402 (magma)
_ps = importlib.util.spec_from_file_location("magma_prompts", os.path.join(HERE, "prompts.py"))
_pm = importlib.util.module_from_spec(_ps); _ps.loader.exec_module(_pm)
BUILD, prompt_key = _pm.BUILD, _pm.prompt_key

import llm_client                                                # noqa: E402 (magma) — chon provider qua env
GROQ_MODEL = llm_client.model_id()   # ten model theo LLM_PROVIDER (groq gpt-oss | router gemini) -> tach cache
GROQ_RPM = int(os.environ.get("GROQ_RPM", "30"))
ROUNDS = int(os.environ.get("ROUNDS", "3"))
CONDS = os.environ.get("CONDS", "magma_blind,magma_concept").split(",")
CACHE = os.environ.get("MAGMA_LOOP_CACHE", os.path.join(HERE, "loop_cache.jsonl"))
KEY = os.environ.get("GROQ_API_KEY")   # co the BO TRONG neu cache da du (cham lai mien phi)

# ===== GUARD chong chay TRUNG (them 2026-09-14) =====
# Su co: user lo chay 3 tien trinh song song -> ca 3 nap cache luc KHOI DONG (deu rong) -> cung goi
# CUNG bo API => 5283 call cho 1947 key duy nhat = 63% lang phi. Cache chi chong lap GIUA cac lan chay
# TUAN TU, khong chong duoc song song. Dung lock file de chi cho 1 tien trinh chay mot luc.
import atexit
# Lock THEO cache file (khong con co dinh .loop.lock): 2 loop dung CACHE KHAC nhau -> khoa khac -> chay
# SONG SONG duoc (vd chay CoT canh static+fewshot). Cung CACHE -> cung khoa -> van chan goi trung API.
_LOCK = CACHE + ".lock"
if os.path.exists(_LOCK):
    try:
        _pid = int(open(_LOCK).read().strip())
        os.kill(_pid, 0)                                   # PID con song?
        raise SystemExit("[DANG CHAY] da co loop.py khac (PID %d) dung CUNG cache %s -> se GOI TRUNG API. "
                         "Doi no xong, dung MAGMA_LOOP_CACHE khac de chay song song, hoac: kill %d && rm %s"
                         % (_pid, CACHE, _pid, _LOCK))
    except (ValueError, ProcessLookupError, PermissionError):
        pass                                               # lock mo coi -> ghi de
open(_LOCK, "w").write(str(os.getpid()))
atexit.register(lambda: os.path.exists(_LOCK) and os.remove(_LOCK))

_cache = {}
if os.path.exists(CACHE):
    for l in open(CACHE):
        try:
            o = json.loads(l); _cache[o["key"]] = o["target"]
        except Exception:
            pass

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage  # noqa: E402
llm = llm_client.make_llm(temperature=0.6)   # Groq hoac 9router/Vertex Gemini theo LLM_PROVIDER
mi = 60.0 / max(1, GROQ_RPM); last = [0.0]


def _lc(msgs):
    out = []
    for m in msgs:
        c = m["content"]
        out.append(SystemMessage(content=c) if m["role"] == "system"
                   else AIMessage(content=c) if m["role"] == "assistant" else HumanMessage(content=c))
    return out


def call(msgs, key):
    if key in _cache:
        return _cache[key]
    if llm is None:
        raise SystemExit("Cache thieu key=%s va KHONG co GROQ_API_KEY." % key)
    for a in range(6):
        dt = time.monotonic() - last[0]
        if dt < mi:
            time.sleep(mi - dt)
        last[0] = time.monotonic()
        try:
            o = llm.invoke(_lc(msgs)).content
            _cache[key] = o
            open(CACHE, "a").write(json.dumps({"key": key, "target": o}) + "\n")
            return o
        except Exception as e:
            w = min(60, 4 * 2 ** a); print("[warn] retry %ds: %s" % (w, str(e)[:80])); time.sleep(w)
    return None


def feedback(res, item, rendered):
    """Phan hoi CHI tu tin hieu ORACLE quan sat duoc (rendered/reached/triggered/crash_fixed).

    !! DA SUA LOI RO RI (2026-09-13): ban cu nhet item["fault_cond"] va item["focal"] — ca hai LAY TU PATCH —
    vao MOI nhanh feedback. Nghia la tu vong 2 tro di, MOI dieu kien (ke ca `blind`, `concept_static`,
    `shuffle`, `fewshot`, `learned`) deu duoc mach dieu kien loi => cac so sanh GIUA CAC COND bi nhiem.
    Feedback gio KHONG nhac ten ham/dieu kien loi; chi noi trang thai oracle (giong coverage-feedback cua fuzzer).
    Dieu kien LEAK (`magma_concept`) van giu fault_cond — nhung CHI trong prompt vong 1, dung dinh nghia cua no.
    """
    if not rendered:
        return ("Previous attempt: build() did NOT return valid bytes. Rewrite `def build()` using only "
                "struct/zlib and return bytes.")
    if res.get("crash_fixed"):
        return ("Previous attempt: the input crashed BOTH the patched and vulnerable builds -> it breaks "
                "things indiscriminately, not specific. Produce an input that triggers ONLY the target bug, "
                "without corrupting unrelated state.")
    if res.get("reached"):
        return ("Previous attempt: you REACHED the vulnerable code region, but did NOT satisfy the fault "
                "condition. Keep the same structure, and make the field VALUES (size/index/count) more "
                "extreme.")
    return ("Previous attempt: the input ran but did NOT reach the vulnerable code region (the parser bailed "
            "out early). Fix the header/chunk to be more valid so it goes deeper into the library.")

def _status(data, res):
    if not data:
        return 0                                                # chua render
    if res["triggered"] and not res["crash_fixed"]:
        return 3                                                # DISCRIM (trigger dung, sach fixed)
    if res["reached"]:
        return 2                                                # cham ham loi
    return 1                                                    # render OK, chua cham


def run_item(item, cond):
    msgs = list(BUILD[cond](item)); best = 0
    for r in range(ROUNDS + 1):
        out = call(msgs, prompt_key(GROQ_MODEL, cond, item) + "@r%d" % r)
        if out is None:
            break
        data = render_input(out)
        res = run_input(data, item) if data else {}
        st = _status(data, res)
        best = max(best, st)
        if st == 3:
            break
        msgs = msgs + [{"role": "assistant", "content": out},
                       {"role": "user", "content": feedback(res, item, bool(data))
                        + "\n\nXuat lai DUY NHAT 1 khoi ```python `def build()`."}]
    return best


def main():
    assert_healthy()                 # GATE: oracle phai song moi cham diem
    g = os.environ.get("GOLD")
    files = [g] if g else sorted(glob.glob(os.path.join(HERE, "items", "*.jsonl")))
    items = [json.loads(l) for f in files for l in open(f) if l.strip()]
    skipped = sorted({i["target"] for i in items if not have_images(i["target"])})
    if skipped:
        n0 = len(items); items = [i for i in items if have_images(i["target"])]
        print("[BO QUA] thieu image cho: %s -> loai %d/%d item (KHONG dem la that bai)"
              % (", ".join(skipped), n0 - len(items), n0))
    print("items:", len(items), "| ROUNDS:", ROUNDS, "| conds:", CONDS)
    agg = {c: {"trig": 0, "reach": 0, "rend": 0} for c in CONDS}
    binv = {c: {} for c in CONDS}
    for it in items:
        row = []
        for c in CONDS:
            b = run_item(it, c)
            agg[c]["trig"] += (b == 3); agg[c]["reach"] += (b >= 2); agg[c]["rend"] += (b >= 1)
            binv[c][it["bug_id"]] = int(b == 3)
            row.append("%s=%d" % (c.replace("magma_", ""), b))
        print("  %-10s %s" % (it["bug_id"], " ".join(row)))

    n = len(items) or 1
    print("\n%-14s %10s %10s %10s" % ("cond", "rendered", "REACHED", "TRIGGER"))
    for c in CONDS:
        a = agg[c]
        print("%-14s %8d%% %8d%% %8d%%" % (c, 100 * a["rend"] // n, 100 * a["reach"] // n, 100 * a["trig"] // n))
    for lo, hi in zip(CONDS, CONDS[1:]):                         # McNemar tung cap lien ke (thang ablation)
        b, c_, p = lab.mcnemar(binv[hi], binv[lo])
        print("McNemar %s > %s (TRIGGER): +%d -%d p=%.4f" % (hi, lo, b, c_, p))
    print("status: 0 chua render | 1 render | 2 REACHED ham loi | 3 TRIGGER (discrim).")


if __name__ == "__main__":
    main()
