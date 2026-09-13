#!/usr/bin/env python3
"""CLONE cua magma/loop.py — chay tren CONCEPT HOC-DUOC (ConceptCoder) thay vi tree-sitter.
Tach rieng folder + cache rieng de KHONG dung cham ket qua/cache cua ban tree-sitter.

Magma FEEDBACK loop (CEGIS, KHONG train): sinh -> oracle(reached/triggered) -> phan hoi -> viet lai <=ROUNDS.

Tin hieu dan duong = canary REACHED (cham ham loi) va TRIGGERED (thoa dieu kien). Phan hoi noi ro model
dang o dau: chua render / chua cham / cham nhung chua thoa fault_cond / pha bua (crash ca fixed).
So blind_fb vs concept_fb. Ground-truth = canary. Giu best (monotonic).

Chay TU REPO ROOT:  GROQ_API_KEY=gsk_... ROUNDS=3 SAMPLES=1 .venv/bin/python magma/loop.py
Env: GROQ_MODEL | GROQ_RPM=30 | ROUNDS=3 | CONDS=magma_blind,magma_concept | GOLD | MAGMA_LOOP_CACHE
"""
import os, sys, json, time, glob, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
MAGMA = os.path.join(ROOT, "magma")
sys.path.insert(0, MAGMA); sys.path.insert(0, os.path.join(ROOT, "bench"))
import lab                                                      # noqa: E402 (bench)
from oracle import run_input, render_input, assert_healthy, have_images                      # noqa: E402 (magma)
_ps = importlib.util.spec_from_file_location("magma_prompts", os.path.join(MAGMA, "prompts.py"))
_pm = importlib.util.module_from_spec(_ps); _ps.loader.exec_module(_pm)
BUILD, _pk = _pm.BUILD, _pm.prompt_key


def prompt_key(model, cond, item):
    """LEARNED-SALT: prompt_key goc chi hash model::cond::item_id (KHONG hash noi dung prompt) ->
    item learned va item tree-sitter se ra KEY TRUNG NHAU. Them salt de tuyet doi khong lan cache."""
    return "learned::" + _pk(model, cond, item)

GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
GROQ_RPM = int(os.environ.get("GROQ_RPM", "30"))
ROUNDS = int(os.environ.get("ROUNDS", "3"))
CONDS = os.environ.get("CONDS", "magma_blind,magma_concept").split(",")
CACHE = os.environ.get("LEARNED_CACHE", os.path.join(HERE, "loop_cache.jsonl"))  # cache RIENG
KEY = os.environ.get("GROQ_API_KEY")   # co the BO TRONG neu cache da du (cham lai mien phi)

_cache = {}
if os.path.exists(CACHE):
    for l in open(CACHE):
        try:
            o = json.loads(l); _cache[o["key"]] = o["target"]
        except Exception:
            pass

from langchain_groq import ChatGroq                              # noqa: E402
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage  # noqa: E402
llm = ChatGroq(model=GROQ_MODEL, temperature=0.6, groq_api_key=KEY) if KEY else None
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
    """Phan hoi theo dung trang thai oracle -> dan model tien tung buoc toi trigger."""
    foc = item.get("focal") or "ham loi"; fc = item.get("fault_cond") or "dieu kien loi"
    if not rendered:
        return "Lan truoc: build() KHONG tra ve bytes hop le. Viet lai `def build()` chi dung struct/zlib, return bytes."
    if res.get("crash_fixed"):
        return ("Lan truoc: input lam CRASH ca ban DA VA -> pha bua, khong dac hieu. "
                "Can input CHI thoa `%s` tai `%s`, khong lam hong linh tinh." % (fc, foc))
    if res.get("reached"):
        return ("Lan truoc: ĐA cham `%s` nhung CHUA thoa dieu kien loi `%s`. "
                "Chinh gia tri input de `%s` thanh DUNG (dieu chinh truong/kich thuoc lien quan)." % (foc, fc, fc))
    return ("Lan truoc: input chay nhung KHONG cham `%s` (parser bo som). "
            "Sua header/chunk cho hop le hon de di toi `%s`, roi moi thoa `%s`." % (foc, foc, fc))


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
    files = sorted(glob.glob(g)) if g else sorted(glob.glob(os.path.join(ROOT, "magma", "items_learned", "*.jsonl")))
    items = [json.loads(l) for f in files for l in open(f) if l.strip()]
    skipped = sorted({i["target"] for i in items if not have_images(i["target"])})
    if skipped:
        n0 = len(items); items = [i for i in items if have_images(i["target"])]
        print("[BO QUA] thieu image cho: %s -> loai %d/%d item (KHONG dem la that bai)"
              % (", ".join(skipped), n0 - len(items), n0))
    print("[LEARNED concept] items:", len(items), "| ROUNDS:", ROUNDS, "| conds:", CONDS,
      "| nguon:", os.path.basename(os.path.dirname(files[0])) if files else "?")
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
