#!/usr/bin/env python3
"""C1 — DE-LEAKED static concept: suy TU `func_vuln` (tree-sitter 8-concept + slice trong-ham).
KHONG dung fault_cond / fix_hint tu patch Magma (do la 'dap an'). Model phai TU suy dieu kien vi pham.

static_facts(item): tu lines_concept (da co san trong item, do extract.py chay load_annotator tren func_vuln):
  - buffer (buffer_allocation), sink (buffer_access | free), guard (bound_check) hien co, bien tu input (params
    xuat hien tai sink), family (family_of tinh — KHONG dung fault_cond).
Tra concept_text (chi tro vao sink/buffer/guard/bien) + func_excerpt (source, cat quanh sink neu qua dai).
"""
import os, sys, re

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "bench"))          # concepts.family_of
sys.path.insert(0, os.path.join(ROOT, "pipeline_v3"))    # common.PROPS
from concepts import family_of                            # noqa: E402
import common                                             # noqa: E402

# index 8-concept: 0 null_assign 1 null_check 2 ptr_deref 3 buffer_alloc 4 buffer_access 5 bound_check 6 free 7 if


def _lines_with(lc, idx):
    return sorted(int(k) for k, v in (lc or {}).items() if len(v) > idx and v[idx])


def _params(func):
    m = re.search(r"[A-Za-z_]\w*\s*\(([^)]*)\)\s*\{", func)
    out = []
    if m:
        for p in m.group(1).split(","):
            w = re.findall(r"[A-Za-z_]\w*", p)
            if w and w[-1] not in ("void",):
                out.append(w[-1])
    return out


def static_facts(item):
    func = item["func_vuln"]; lc = item.get("lines_concept") or {}
    lines = func.split("\n")
    txt = lambda i: lines[i].strip() if 0 <= i < len(lines) else ""
    alloc, access, free, bound = (_lines_with(lc, 3), _lines_with(lc, 4),
                                  _lines_with(lc, 6), _lines_with(lc, 5))
    sink = sorted(set(access) | set(free))
    params = _params(func)
    svars = set()
    for i in sink:
        svars |= set(re.findall(r"[A-Za-z_]\w*", txt(i)))
    danger = [p for p in params if p in svars] or params            # param chay vao sink = input dieu khien
    return {"family": family_of(func, lc), "params": params, "danger": danger,
            "buffers": [(i, txt(i)) for i in alloc], "sinks": [(i, txt(i)) for i in sink],
            "guards": [(i, txt(i)) for i in bound], "sink_lines": sink}


def concept_text(item):
    """Chi tro vao sink/buffer/guard/bien — KHONG noi dieu kien loi. Model tu suy."""
    f = static_facts(item)
    L = ["Ham CO lo hong bo nho (source ben duoi). Phan tich TINH (tree-sitter, khong dung ban va):"]
    if f["family"]:
        L.append("- Loai (suy tu concept): %s" % f["family"])
    if f["buffers"]:
        L.append("- Buffer: " + " ; ".join("L%d `%s`" % (i, t[:50]) for i, t in f["buffers"][:4]))
    if f["sinks"]:
        L.append("- Thao tac NGUY HIEM (sink can lam vuot bien / dung-sau-free): "
                 + " ; ".join("L%d `%s`" % (i, t[:50]) for i, t in f["sinks"][:6]))
    if f["guards"]:
        L.append("- Guard hien co (CO THE chua du): " + " ; ".join("L%d `%s`" % (i, t[:50]) for i, t in f["guards"][:4]))
    if f["danger"]:
        L.append("- Bien tu INPUT (test dieu khien duoc): %s" % ", ".join(f["danger"]))
    L.append("=> HAY TU SUY dieu kien input can thoa de sink vuot bien / UAF, roi tao input kich hoat.")
    return "\n".join(L)


def concept_text_shuffle(item):
    """PLACEBO: cung SHAPE (source + facts) nhung XAO nhan (dong nao la sink/buffer/guard bi hoan vi) +
    family SAI + bien SAI. Neu concept_static > shuffle -> NOI DUNG concept la nhan-qua (khong phai prompt dai)."""
    import hashlib, random
    f = static_facts(item)
    rnd = random.Random(int(hashlib.sha1(("shuf::" + item["id"]).encode()).hexdigest(), 16) % (2 ** 32))
    cats = [("Buffer", f["buffers"]), ("Thao tac NGUY HIEM (sink)", f["sinks"]), ("Guard hien co", f["guards"])]
    pool = [t for _, lst in cats for _, t in lst]; rnd.shuffle(pool)
    it = iter(pool)
    FAMS = ["oob", "null_deref", "uaf", "double_free", "int_overflow"]
    fam = rnd.choice([x for x in FAMS if x != f["family"]] or FAMS)
    toks = list({w for w in re.findall(r"[A-Za-z_]\w{2,}", item["func_vuln"]) if w not in f["params"]})
    rnd.shuffle(toks)
    L = ["Ham CO lo hong bo nho (source ben duoi). Phan tich TINH (tree-sitter, khong dung ban va):",
         "- Loai (suy tu concept): %s" % fam]
    for name, lst in cats:
        cells = [next(it) for _ in lst]
        if cells:
            L.append("- %s: %s" % (name, " ; ".join("`%s`" % c[:50] for c in cells)))
    L.append("- Bien tu INPUT (test dieu khien duoc): %s" % ", ".join(toks[:3] or f["params"][:3]))
    L.append("=> HAY TU SUY dieu kien input can thoa de sink vuot bien / UAF, roi tao input kich hoat.")
    return "\n".join(L)


def func_excerpt(item, cap=3500):
    """Source func_vuln; neu qua dai -> cua so quanh sink dau tien."""
    func = item["func_vuln"] or ""
    if len(func) <= cap:
        return func
    f = static_facts(item)
    lines = func.split("\n")
    c = f["sink_lines"][0] if f["sink_lines"] else 0
    lo = max(0, c - 40); hi = min(len(lines), c + 40)
    return "// ... (rut gon)\n" + "\n".join(lines[lo:hi]) + "\n// ..."
