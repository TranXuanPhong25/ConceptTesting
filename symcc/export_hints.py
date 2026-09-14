#!/usr/bin/env python3
"""Xuat HINT tu SymCC de nhet vao prompt LLM (hybrid SymCC->LLM).

Y tuong (tu micro-experiment PNG001): LLM GIAI rang buoc tot nhung KHONG suy ra duoc rang buoc tu source.
SymCC tinh duoc phan do bang thuc thi symbolic. Ta rut 2 thu SymCC CO ma LLM KHONG co, roi dua vao prompt:
  1) mot input CU THE do SymCC/Z3 giai ra va van CHAM duoc ham loi (bang chung cau truc di sau vao lib);
  2) cac byte SymCC phai DOI so voi seed lanh de di qua cac nhanh kiem tra (poor-man constraint).

KHAI BAO RO RI (leakage):
  - Ca 2 thu tren den tu THUC THI CU THE cua seed CORPUS goc (khong phai tu patch) => hop le.
  - NHUNG buoc loc "input nao con CHAM ham loi" dung canary reached = tin hieu dat theo patch. Nghia la
    hint duoc chon CO dinh chut thong tin vi tri lo hong. Day la hybrid CO DAN DUONG — phai goi dung ten,
    khong duoc coi la "LLM tu lam". (Muon sach tuyet doi: HINT_PICK=first — lay input SymCC dau tien,
    khong loc bang canary; kem dinh huong hon.)

Chay TU REPO ROOT (can image magma-<t>-symcc + magma-<t>-{vuln,fixed}):
    .venv/bin/python symcc/export_hints.py                 # tat ca target co image symcc
    GOLD=/tmp/png001.jsonl .venv/bin/python symcc/export_hints.py
Ghi symcc/hints/<bug_id>.json. prompts.build_hybrid_symcc doc file do.
"""
import os, sys, json, glob

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(ROOT, "magma"))
from oracle import run_input, have_images                     # noqa: E402
import loop_symcc as ls                                       # noqa: E402 (symcc_solve, _bootstrap, have_symcc)

HINT_PICK = os.environ.get("HINT_PICK", "reached")            # reached (dan duong) | first (sach hon)
MAXHEX = int(os.environ.get("HINT_MAXBYTES", "192"))          # cat hexdump cho prompt gon
OUTDIR = os.path.join(HERE, "hints")


_hex = ls._hex                                                # dung chung ham voi loop_symcc (EMIT_HINTS)
_changed = ls._changed


def make_hint(item):
    boot = ls._bootstrap(item)                                # seed CORPUS cham ham loi (khai bao SEED_SRC)
    if not boot:
        return None
    seed = boot["seed"]
    cands = ls.symcc_solve(seed, item)                        # SymCC/Z3 giai -> nhieu input
    if not cands:
        return None
    pick = None
    if HINT_PICK == "first":
        pick = cands[0]                                       # khong loc bang canary (sach hon, kem dinh huong)
    else:
        for c in cands:                                       # loc: input SymCC-solved van CHAM ham loi
            if c and run_input(c, item)["reached"]:
                pick = c; break
        pick = pick or cands[0]
    ch = _changed(seed, pick)
    return {"bug_id": item["bug_id"], "target": item["target"], "pick_mode": HINT_PICK,
            "n_solved": len(cands), "seed_len": len(seed), "solved_len": len(pick),
            "solved_hex": _hex(pick), "seed_hex": _hex(seed),
            "changed": [{"off": o, "from": (None if a is None else "0x%02x" % a), "to": "0x%02x" % b}
                        for (o, a, b) in ch]}


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    g = os.environ.get("GOLD")
    files = [g] if g else sorted(glob.glob(os.path.join(ROOT, "magma", "items", "*.jsonl")))
    items = [json.loads(l) for f in files for l in open(f) if l.strip()]
    items = [i for i in items if have_images(i["target"]) and ls.have_symcc(i["target"])]
    print("items:", len(items), "| HINT_PICK:", HINT_PICK,
          "" if HINT_PICK == "first" else "(loc bang canary reached -> hybrid CO DAN DUONG)")
    force = os.environ.get("HINT_FORCE") == "1"
    ok = 0
    for it in items:
        p = os.path.join(OUTDIR, "%s.json" % it["bug_id"])
        if os.path.exists(p) and not force:                  # da co hint -> bo qua (mo rong len 100 khong xuat lai)
            ok += 1; print("  %-8s da co (bo qua; HINT_FORCE=1 de lam lai)" % it["bug_id"]); continue
        h = make_hint(it)
        if h:
            json.dump(h, open(p, "w"), indent=1); ok += 1
            print("  %-8s OK  n_solved=%d changed=%d -> %s" % (it["bug_id"], h["n_solved"], len(h["changed"]), p))
        else:
            print("  %-8s KHONG co hint (khong seed cham / SymCC 0 input)" % it["bug_id"])
    print("xong: %d/%d hint" % (ok, len(items)))


if __name__ == "__main__":
    main()
