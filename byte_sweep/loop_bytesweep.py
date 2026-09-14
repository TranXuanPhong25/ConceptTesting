#!/usr/bin/env python3
"""C3 — BYTE-SWEEP solver-in-the-loop, ghep C1 (de-leak) + C2 (reachability/taint).

!! DOI TEN 2026-09-13: truoc day goi la "concolic" — SAI/phong dai. Cai nay KHONG co symbolic execution,
KHONG thu thap path constraint, KHONG dung SMT solver. No chi la: do byte mu (XOR-flip cua so 2 byte,
lay mau ~20 vi tri) roi thu 4 GIA TRI HARDCODE (0xFF/0x7F/0x01/0x00), oracle xac nhan. ~36 lan chay.
Dung ten: mutational byte-sweep / black-box sensitivity analysis.
Concolic THAT co san trong Magma: fuzzers/symcc_afl (SymCC + Z3) — xem ghi chu cuoi file.

Dieu kien (thang ablation, so voi loop.py cho blind/concept/concept_static):
  magma_concept_reach : concept_static + SEED da cham sink (bootstrap) + grammar -> LLM MUTATE (feedback).
  magma_concept_bytesweep    : concept_reach + BYTE-SWEEP — khi reached-chua-trigger, quet gia tri tren cac byte
                        'fault' (taint) de solve concrete (oracle-verify). Bo tro cho LLM-as-solver.
Ground-truth = canary reached/triggered. Giu best (monotonic).

Chay TU REPO ROOT:  GROQ_API_KEY=gsk_... ROUNDS=3 .venv/bin/python byte_sweep/loop_bytesweep.py
Env: GROQ_MODEL | GROQ_RPM=30 | ROUNDS=3 | CONDS | GOLD | MAGMA_LOOP_CACHE(byte_sweep/bs_cache.jsonl)
"""
import os, sys, json, time, glob, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "reach")); sys.path.insert(0, os.path.join(ROOT, "magma"))
sys.path.insert(0, os.path.join(ROOT, "bench"))
import lab                                                      # noqa: E402 (bench)
import taint                                                    # noqa: E402 (reach)
from oracle import run_input, render_input, assert_healthy                      # noqa: E402 (magma)
import concept_static as cs                                     # noqa: E402 (magma)
_ps = importlib.util.spec_from_file_location("magma_prompts", os.path.join(ROOT, "magma", "prompts.py"))
_pm = importlib.util.module_from_spec(_ps); _ps.loader.exec_module(_pm)
BUILD, prompt_key = _pm.BUILD, _pm.prompt_key

GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
GROQ_RPM = int(os.environ.get("GROQ_RPM", "30"))
ROUNDS = int(os.environ.get("ROUNDS", "3"))
CONDS = os.environ.get("CONDS", "magma_concept_static,magma_concept_reach,magma_concept_bytesweep").split(",")
CACHE = os.environ.get("MAGMA_LOOP_CACHE", os.path.join(HERE, "bs_cache.jsonl"))
KEY = os.environ.get("GROQ_API_KEY")
if not KEY:
    raise SystemExit("Thieu GROQ_API_KEY.")

_cache = {}
if os.path.exists(CACHE):
    for l in open(CACHE):
        try:
            o = json.loads(l); _cache[o["key"]] = o["target"]
        except Exception:
            pass

from langchain_groq import ChatGroq                              # noqa: E402
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage  # noqa: E402
llm = ChatGroq(model=GROQ_MODEL, temperature=0.6, groq_api_key=KEY)
mi = 60.0 / max(1, GROQ_RPM); last = [0.0]


def _lc(msgs):
    return [SystemMessage(content=m["content"]) if m["role"] == "system"
            else AIMessage(content=m["content"]) if m["role"] == "assistant"
            else HumanMessage(content=m["content"]) for m in msgs]


def call(msgs, key):
    if key in _cache:
        return _cache[key]
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


def _init_msgs(item, cond, boot):
    """Prompt khoi tao. reach/cc: concept_static + SEED reaching + grammar. Con lai: BUILD[cond]."""
    if cond in ("magma_concept_reach", "magma_concept_bytesweep") and boot:
        gram = ", ".join(taint.grammar_hint(item["target"])[:16])
        extra = ("\n\nAN input that REACHES the faulty function but does NOT yet trigger it — modify it to "
                 "satisfy the fault condition:\n%s"
                 "\n\nFormat tokens: %s" % (taint.seed_repr(boot["seed"]), gram))
        hp = ("Library `%s`.\n%s\n\nSOURCE of the vulnerable function:\n```c\n%s\n```%s\n\n%s"
              % (item["target"], cs.concept_text(item), cs.func_excerpt(item), extra,
                 _pm._OUT % (item["program"], item["target"])))
        return [{"role": "system", "content": _pm._SYS}, {"role": "user", "content": hp}]
    base = "magma_concept_static" if cond in ("magma_concept_reach", "magma_concept_bytesweep") else cond
    return list(BUILD[base](item))


def byte_sweep_solve(data, item, budget=16):
    """Quet 4 gia tri hardcode tren byte 'fault' (taint) -> oracle-verify. Tra bytes trigger hoac None.
    KHONG phai concolic: khong symbolic, khong path constraint, khong SMT solver.
    Han che THAT: dinh dang co CRC/length-coupled (PNG...) it khi solve duoc byte-level -> LLM-as-solver lo phan do."""
    ctrl = taint.locate_controlling_bytes(data, item, window=2, max_probes=20)
    faults = [c for c in ctrl if c["effect"] == "fault"] or ctrl[:3]
    for c in faults:
        o = c["offset"]
        for val in (0xFF, 0x7F, 0x01, 0x00):
            if budget <= 0:
                return None
            budget -= 1
            mut = bytearray(data)
            for k in range(o, min(o + c["len"], len(data))):
                mut[k] = val
            r = run_input(bytes(mut), item)
            if r["triggered"] and not r["crash_fixed"]:
                return bytes(mut)
    return None


def feedback(res, item, rendered):
    """CHI tin hieu oracle quan sat duoc — KHONG nhac ten ham/dieu kien loi (dong bo voi magma/loop.py sau khi
    sua lo ro 2026-09-13). Cac cond o day deu da co source trong prompt vong 1 nen khong mat thong tin."""
    if not rendered:
        return ("Previous attempt: build() did NOT return valid bytes. Rewrite `def build()` using only "
                "struct/zlib and return bytes.")
    if res.get("crash_fixed"):
        return ("Previous attempt: it crashed BOTH the patched and vulnerable builds -> it breaks things "
                "indiscriminately. Produce an input that triggers ONLY the target bug, without corrupting "
                "unrelated state.")
    if res.get("reached"):
        return ("Previous attempt: you REACHED the vulnerable code region but did NOT satisfy the fault "
                "condition. Keep the structure, make the field VALUES (size/index/count) more extreme.")
    return ("Previous attempt: did NOT reach the vulnerable code region (the parser bailed out early). "
            "Fix the header/chunk to be more valid so it goes deeper into the library.")

def run_item(item, cond, boot=None):
    msgs = _init_msgs(item, cond, boot); best = 0
    for r in range(ROUNDS + 1):
        out = call(msgs, prompt_key(GROQ_MODEL, cond, item) + "@r%d" % r)
        if out is None:
            break
        data = render_input(out)
        res = run_input(data, item) if data else {}
        st = 3 if (data and res["triggered"] and not res["crash_fixed"]) else (2 if data and res["reached"] else (1 if data else 0))
        if cond == "magma_concept_bytesweep" and st == 2:               # reached-chua-trigger -> thu byte-sweep solve
            solved = byte_sweep_solve(data, item)
            if solved is not None:
                st = 3
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
    files = [g] if g else sorted(glob.glob(os.path.join(ROOT, "magma", "items", "*.jsonl")))
    items = [json.loads(l) for f in files for l in open(f) if l.strip()]
    print("items:", len(items), "| ROUNDS:", ROUNDS, "| conds:", CONDS)
    agg = {c: {"trig": 0, "reach": 0, "rend": 0} for c in CONDS}; binv = {c: {} for c in CONDS}
    need_boot = any(c in ("magma_concept_reach", "magma_concept_bytesweep") for c in CONDS)
    boot_ok = 0
    for it in items:
        boot = taint.bootstrap_reaching(it) if need_boot else None   # 1 LAN/bug, dung lai cho moi cond
        if boot:
            boot_ok += 1
        row = []
        for c in CONDS:
            b = run_item(it, c, boot)
            agg[c]["trig"] += (b == 3); agg[c]["reach"] += (b >= 2); agg[c]["rend"] += (b >= 1)
            binv[c][it["bug_id"]] = int(b == 3)
            row.append("%s=%d" % (c.replace("magma_concept_", "").replace("magma_", ""), b))
        print("  %-10s %s" % (it["bug_id"], " ".join(row)))

    n = len(items) or 1
    print("\nbootstrap reaching duoc: %d/%d bug\n" % (boot_ok, len(items)))
    print("%-22s %10s %10s %10s" % ("cond", "rendered", "REACHED", "TRIGGER"))
    for c in CONDS:
        a = agg[c]
        print("%-22s %8d%% %8d%% %8d%%" % (c, 100 * a["rend"] // n, 100 * a["reach"] // n, 100 * a["trig"] // n))
    for lo, hi in zip(CONDS, CONDS[1:]):
        b, c_, p = lab.mcnemar(binv[hi], binv[lo])
        print("McNemar %s > %s (TRIGGER): +%d -%d p=%.4f" % (hi, lo, b, c_, p))


if __name__ == "__main__":
    main()


# ===== GHI CHU: concolic THAT (chua lam) =====
# Magma ship san fuzzers/symcc_afl va fuzzers/klee — SymCC clone kem Z3 solver. Muon concolic dung nghia:
#   FUZZER=symcc_afl TARGET=libpng  -> instrument chuong trinh, thu path constraint, Z3 giai input lat nhanh.
# Nang (build LLVM/SymCC/Z3 duoi QEMU). Xem README.md trong thu muc nay.
