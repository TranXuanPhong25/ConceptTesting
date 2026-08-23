#!/usr/bin/env python3
"""03 - Distill TEACHER local -> cache (mac dinh GEMINI; van ho tro Groq). CO CONCURRENCY.

2 che do:
  - blind_adv : few-shot + chain-of-thought, KHONG concept  (dieu kien teacher_blind + target cho blind_ft)
  - concept   : concept lines + family_pred + recipe + CoT   (dieu kien teacher_concept + target cho concept_ft)

Goi SONG SONG (ThreadPoolExecutor) + pacer theo RPM -> khai thac tier cao (vd 1000 RPM).
Vi moi call ~1-2s do tre mang, tuan tu se cham; can nhieu WORKERS de bao phu do tre.
Cache key = sha1(TEACHER_MODEL::cond::func) -> notebook Cell 5 PHAI dung dung TEACHER_MODEL.

Chay:
    GEMINI_API_KEY=... RPM=1000 WORKERS=32 python pipeline_v3/03_distill_teacher.py   # tier cao
    GEMINI_API_KEY=... python pipeline_v3/03_distill_teacher.py                        # free (RPM=15)
    TEACHER=groq GROQ_API_KEY=... python pipeline_v3/03_distill_teacher.py             # Groq
Xong -> upload distill_cache_v3.jsonl len Kaggle (Add Data).
"""
import os, sys, json, time, threading, collections
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common import build_blind_adv, build_concept, cache_key

TEACHER        = os.environ.get("TEACHER", "gemini")                  # gemini | groq
_DEFAULT_MODEL = {"gemini": "gemini-2.5-flash", "groq": "openai/gpt-oss-120b"}
TEACHER_MODEL  = os.environ.get("TEACHER_MODEL", _DEFAULT_MODEL.get(TEACHER, "gemini-2.5-flash"))
RPM            = int(os.environ.get("RPM", os.environ.get("GROQ_RPM", "15")))   # so call/phut cho phep
WORKERS        = int(os.environ.get("WORKERS", "8"))                 # so luong goi SONG SONG (tang cho RPM cao)
IN             = os.environ.get("IN", "data/work/with_concept.jsonl")
CACHE          = os.environ.get("CACHE", "distill_cache_v3.jsonl")
CONDS          = os.environ.get("CONDS", "blind_adv,concept").split(",")

BUILD = {"blind_adv": build_blind_adv, "concept": build_concept}
for c in CONDS:
    if c not in BUILD:
        raise SystemExit("CONDS khong hop le: %s (chi ho tro %s)" % (c, list(BUILD)))


def make_llm():
    if TEACHER == "gemini":
        key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not key:
            raise SystemExit("Thieu GEMINI_API_KEY/GOOGLE_API_KEY. "
                             "Chay: GEMINI_API_KEY=... python pipeline_v3/03_distill_teacher.py")
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model=TEACHER_MODEL, temperature=0.3, google_api_key=key)
    if TEACHER == "groq":
        key = os.environ.get("GROQ_API_KEY")
        if not key:
            raise SystemExit("Thieu GROQ_API_KEY. "
                             "Chay: TEACHER=groq GROQ_API_KEY=... python pipeline_v3/03_distill_teacher.py")
        from langchain_groq import ChatGroq
        return ChatGroq(model=TEACHER_MODEL, temperature=0.3, groq_api_key=key)
    raise SystemExit("TEACHER khong ho tro: %s (chi gemini|groq)" % TEACHER)


# ---- cache co san ----
_cache = {}
if os.path.exists(CACHE):
    for l in open(CACHE):
        try:
            o = json.loads(l); _cache[o["key"]] = o["target"]
        except Exception:
            pass
print("cache co san:", len(_cache))

llm = make_llm()
from langchain_core.messages import SystemMessage, HumanMessage

# ---- pacer theo RPM (thread-safe: gian cach thoi diem BAT DAU moi call = 60/RPM) ----
_mi = 60.0 / max(1, RPM)
_pace_lock = threading.Lock()
_next_slot = [0.0]
def _pace():
    with _pace_lock:
        now = time.monotonic()
        wait = max(0.0, _next_slot[0] - now)
        _next_slot[0] = max(now, _next_slot[0]) + _mi
    if wait > 0:
        time.sleep(wait)

# ---- ghi cache thread-safe ----
_io_lock = threading.Lock()
_cf = open(CACHE, "a")
def _save(key, target):
    with _io_lock:
        _cache[key] = target
        _cf.write(json.dumps({"key": key, "target": target}) + "\n"); _cf.flush()


def call_one(func, cond):
    """Goi teacher 1 lan cho (func,cond); tra 1 neu ghi moi, 0 neu bo/that bai."""
    key = cache_key(TEACHER_MODEL, cond, func)
    msgs = BUILD[cond](func_rec[func])
    for a in range(6):
        _pace()
        try:
            r = llm.invoke([SystemMessage(content=msgs[0]["content"]),
                            HumanMessage(content=msgs[1]["content"])]).content
            o = r if isinstance(r, str) else "".join(str(x) for x in r)
            if o and len(o) > 40:
                _save(key, o); return 1
            return 0
        except Exception as e:
            w = min(60, 4 * 2 ** a); print("[warn] retry %ds: %s" % (w, str(e)[:80])); time.sleep(w)
    return 0


func_rec = {}  # func-string -> record (de build_* truy cap family_pred/lines_concept)


def main():
    if not os.path.exists(IN):
        raise SystemExit("Thieu %s. Chay 02_extract_concept.py truoc." % IN)
    rows = [json.loads(l) for l in open(IN) if l.strip()]
    for d in rows:
        func_rec[d["func"]] = d
    work = [(d["func"], cond) for d in rows for cond in CONDS
            if cache_key(TEACHER_MODEL, cond, d["func"]) not in _cache]
    print("pool:", len(rows), "| TEACHER:", TEACHER, "| model:", TEACHER_MODEL,
          "| RPM:", RPM, "| WORKERS:", WORKERS, "| CONDS:", CONDS,
          "| target:", dict(collections.Counter(r.get("target") for r in rows)))
    print("can goi:", len(work), "(da cache:", len(_cache), ")")
    if not work:
        print("Khong co gi de goi (cache day)."); return
    done = 0; t0 = time.monotonic()
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = [ex.submit(call_one, f, c) for f, c in work]
        for i, fut in enumerate(as_completed(futs)):
            try:
                done += fut.result() or 0
            except Exception as e:
                print("[err]", str(e)[:80])
            if (i + 1) % 20 == 0 or (i + 1) == len(work):
                dt = time.monotonic() - t0
                print("  %d/%d (moi %d, %.1f call/s)" % (i + 1, len(work), done, (i + 1) / max(dt, 1e-6)))
    _cf.close()
    print("XONG. cache:", len(_cache), "| file:", CACHE)
    print("-> Notebook Cell 2: dat TEACHER_MODEL='%s' (PHAI khop), roi Run All." % TEACHER_MODEL)


if __name__ == "__main__":
    main()
