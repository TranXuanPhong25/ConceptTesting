#!/usr/bin/env python3
"""Few-shot examples cho prompt sinh-input Magma. 2 NGUON (2 ban):
  - authored (tu che): vi du build()->bytes viet tay, generic (day dinh dang OUTPUT + reasoning size/index).
  - juliet: cap vuln/fixed THAT tu Juliet (C, tu-chua) lam vi du day REASONING (guard thieu -> gia tri vi pham).
KHONG leak: vi du tu codebase KHAC (synthetic/generic), khong lien quan bug Magma dang test.
"""
import os, json

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)

# ============ Ban 1: TU CHE — vi du build() (khop dinh dang Magma: Python -> bytes) ============
AUTHORED = """VI DU (cach suy tu concept -> input, va DINH DANG output `build()`):

Vi du A — buffer overflow do TRUONG KICH THUOC khong chan tren:
  Concept: ghi N byte vao buffer 16B; N doc tu header; guard chi kiem N>0 (thieu chan tren).
  Suy luan: de vuot bien, dat truong size LON hon 16.
```python
def build():
    import struct
    body = b"A" * 64
    return struct.pack("<I", len(body)) + body   # size=64 >> 16 -> tran
```

Vi du B — CHI SO mang tu input khong chan tren:
  Concept: doc buffer[idx] (mang 10 phan tu); idx tu input; guard chi kiem idx>=0.
  Suy luan: dat idx VUOT so phan tu.
```python
def build():
    import struct
    return struct.pack("<i", 100000)   # idx qua lon -> doc ngoai bien
```
"""


def _fmt_juliet(it):
    """Vi du phai MIRROR dung format bai that: [block CONCEPT] -> [suy luan] -> [input kich hoat].

    !! SUA 2026-09-13: ban cu CHI dua source + test, KHONG dua block concept => model khong he duoc day
    'doc block concept nhu the nao'. Bai that lai dua dung block do (Buffer/sink/guard/bien) => vi du va
    bai that LECH FORMAT, few-shot mat phan lon tac dung. Gio chay CHINH `concept_static.concept_text()`
    (cung ham dung cho bai that) len vi du Juliet -> day tron chuoi suy luan concept -> input.
    """
    import os as _os, sys as _sys
    _sys.path.insert(0, _os.path.join(ROOT, "magma"))
    import concept_static as cs                                   # cung bo trich concept voi bai that
    block = cs.concept_text(it)
    # bo dong ket "=> HAY TU SUY..." cua vi du: o day ta TRA LOI thay vi hoi
    block = "\n".join(l for l in block.split("\n") if not l.startswith("=> HAY TU SUY"))
    return ("--- Vi du (Juliet %s) ---\n%s\nSOURCE:\n```c\n%s\n```\n"
            "SUY LUAN: guard hien co khong chan het mien gia tri cua bien input -> chon gia tri VI PHAM bien.\n"
            "INPUT KICH HOAT: `%s`\n"
            % (it.get("cwe", ""), block, (it["func_vuln"] or "").strip(), it.get("ref_test", "")))


def juliet_examples(k=2):
    """Lay k cap vuln/fixed THAT tu Juliet gold (da-dang ho) lam few-shot day reasoning."""
    p = os.path.join(ROOT, "bench", "items", "gold_juliet.jsonl")
    if not os.path.exists(p):
        return ""
    items = [json.loads(l) for l in open(p) if l.strip()]
    pick, seen = [], set()
    # da-dang theo `family_pred` (= truong bai that dung), KHONG theo `family`:
    # dedup theo `family` cho ra oob_write+oob_read -> ca hai deu map ve family_pred "oob" (trung lap).
    # Magma phan bo: oob 48, null_deref 31, double_free 13, uaf 3 -> can 1 spatial + 1 temporal.
    for it in items:
        f = it.get("family_pred") or it.get("family")
        if f not in seen and it.get("func_vuln") and it.get("ref_test"):
            seen.add(f); pick.append(it)
        if len(pick) >= k:
            break
    if not pick:
        return ""
    return ("VI DU (cap vuln/fixed THAT — hoc cach: guard thieu gi -> gia tri nao vi pham):\n\n"
            + "\n".join(_fmt_juliet(it) for it in pick)
            + "\n(Voi thu vien duoi day, ap dung cung loi suy luan roi xuat `build()`->bytes.)\n")
