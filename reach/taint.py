#!/usr/bin/env python3
"""C2 — Reachability + input-field localization (taint DONG qua canary oracle).

Phan tich tinh lien-thu-tuc *sound* tren libpng/openssl khong kha thi o day -> dung ORACLE lam executor cu the:
  - bootstrap_reaching: tim 1 input DA CHAM ham loi (reached) tu cache (loop/gen) + corpus seed. Day la dong
    gop reachability chinh: model duoc cho input BIET la toi duoc sink de mutate (VULEUT-style), thay vi dung tu 0.
  - locate_controlling_bytes: mutate theo vung -> so reached/triggered doi -> vung byte DIEU KHIEN (best-effort;
    noisy tren dinh dang co CRC -> ghi ro).
  - grammar_hint: doc *.dict cua target trong image -> goi y dinh dang.

Import boi concolic/loop_cc.py. Chay TU REPO ROOT.
"""
import os, sys, json, glob, subprocess

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "magma"))
from oracle import run_input, render_input                  # noqa: E402 (magma)

MAGMA = os.path.join(ROOT, "vendor", "magma")
_GRAMMAR = {}


def grammar_hint(target, cap=40):
    """Token dinh dang tu *.dict (libFuzzer dict) trong image vuln. Cache theo target."""
    if target in _GRAMMAR:
        return _GRAMMAR[target]
    cmd = ["docker", "run", "--rm", "--platform", "linux/amd64", "--entrypoint", "bash",
           "magma-%s-vuln" % target, "-c", 'cat $(find $TARGET -name "*.dict" 2>/dev/null | head -1) 2>/dev/null']
    toks = []
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=60)
        for line in r.stdout.decode(errors="ignore").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                toks.append(line.split("=", 1)[1].strip())
            elif line and line.startswith('"'):
                toks.append(line)
    except Exception:
        pass
    _GRAMMAR[target] = toks[:cap]
    return _GRAMMAR[target]


def _cache_inputs(item):
    """Re-render moi output model trong loop/gen cache thuoc item nay -> list bytes (bootstrap pool)."""
    outs = []
    for name in ("loop_cache.jsonl", "gen_cache.jsonl"):
        p = os.path.join(ROOT, "magma", name)
        if not os.path.exists(p):
            continue
        for l in open(p):
            try:
                o = json.loads(l)
            except Exception:
                continue
            if item["id"] in o.get("key", ""):
                d = render_input(o["target"])
                if d:
                    outs.append(d)
    return outs


def _corpus_seeds(item, cap=20):
    d = os.path.join(MAGMA, "targets", item["target"], "corpus", item["program"])
    out = []
    for f in sorted(glob.glob(os.path.join(d, "*")))[:cap]:
        try:
            out.append(open(f, "rb").read())
        except Exception:
            pass
    return out


def bootstrap_reaching(item, budget=25):
    """Tra {seed, reached, triggered} cho input DAU TIEN cham ham loi; None neu khong tim thay trong budget."""
    seen = set(); cands = _cache_inputs(item) + _corpus_seeds(item)
    tried = 0
    for d in cands:
        if tried >= budget:
            break
        h = hash(d)
        if h in seen:
            continue
        seen.add(h); tried += 1
        res = run_input(d, item)
        if res["reached"]:
            return {"seed": d, "reached": 1, "triggered": res["triggered"]}
    return None


def locate_controlling_bytes(seed, item, window=2, max_probes=48):
    """Best-effort: vung byte lam doi reached/triggered khi mutate (flip cao/thap). Noisy voi CRC-format."""
    base = run_input(seed, item)
    if not base["reached"]:
        return []
    n = len(seed); step = max(window, (n // max_probes) or window); ctrl = []
    off = 0
    while off < n and len(ctrl) < max_probes:
        mut = bytearray(seed)
        for k in range(off, min(off + window, n)):
            mut[k] = mut[k] ^ 0xFF
        r = run_input(bytes(mut), item)
        eff = None
        # FAULT-controlling: van CHAM sink (reached giu) nhung TRIGGER doi -> byte cua dieu kien loi.
        if r["reached"] and r["triggered"] != base["triggered"]:
            eff = "fault"
        # STRUCTURE: lam MAT reached -> byte dinh dang/di duong (vd CRC, magic, length khien parser bo).
        elif base["reached"] and not r["reached"]:
            eff = "structure"
        if eff:
            ctrl.append({"offset": off, "len": window, "effect": eff})
        off += step
    return ctrl


def seed_repr(seed, cap=512):
    """Bieu dien input cho prompt: hex + preview ascii (cat)."""
    b = seed[:cap]
    hx = b.hex()
    asc = "".join(chr(c) if 32 <= c < 127 else "." for c in b)
    return "len=%d\nhex: %s%s\nascii: %s" % (len(seed), hx, ("..." if len(seed) > cap else ""), asc)


if __name__ == "__main__":
    # Selftest PNG003: bootstrap tu cache/corpus + grammar. (Can images + cache.)
    it = [json.loads(l) for l in open(os.path.join(ROOT, "magma", "items", "libpng.jsonl"))
          if '"PNG003"' in l][0]
    print("grammar libpng:", grammar_hint("libpng")[:8])
    b = bootstrap_reaching(it)
    print("bootstrap PNG003:", None if not b else "reached seed %d bytes, triggered=%d" % (len(b["seed"]), b["triggered"]))
