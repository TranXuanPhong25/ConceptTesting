#!/usr/bin/env python3
"""Oracle vi-phan cho Magma: chay 1 INPUT qua harness tren build VULN va FIXED (trong Docker).

  input + VULN  (CANARY_MODE=1, ISAN=1) -> canary bug muc tieu TRIGGERED + abort (exit>=128)
  input + FIXED (CANARY_MODE=3)          -> SACH (exit 0, khong crash)

DISCRIM = triggered dung bug muc tieu tren VULN & clean tren FIXED. Tin hieu ground-truth = canary
(manh hon ASAN doan mo). Dua tren magma/runonce.sh (in "exit_code N [bug PNGxxx]").

Chay TU REPO ROOT (sau `bash magma/setup.sh`):
    .venv/bin/python magma/oracle.py --selftest PNG003
"""
import os, sys, re, struct, zlib, tempfile, subprocess, argparse

PROGRAM = os.environ.get("MAGMA_PROGRAM", "libpng_read_fuzzer")
TARGET  = os.environ.get("MAGMA_TARGET", "libpng")
IMAGES  = {"vuln": "magma-%s-vuln" % TARGET, "fixed": "magma-%s-fixed" % TARGET}
RUNONCE = "/magma/magma/runonce.sh"          # in-container path (Dockerfile: MAGMA=/magma/magma)


def _run_container(image, input_path, timeout=60):
    """docker run harness tren 1 input -> (exit_code, bug_or_None, raw). exit_code=-1 neu loi docker."""
    d = os.path.dirname(os.path.abspath(input_path)); name = os.path.basename(input_path)
    cmd = ["docker", "run", "--rm", "--platform", "linux/amd64", "-e", "PROGRAM=%s" % PROGRAM,
           "-v", "%s:/host" % d, "--entrypoint", "bash", image, RUNONCE, "/host/%s" % name]
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return (137, None, "TIMEOUT")
    out = (r.stdout or b"").decode(errors="ignore") + (r.stderr or b"").decode(errors="ignore")
    ec, bug = None, None
    for line in out.splitlines():
        if line.startswith("exit_code"):
            parts = line.split()
            try:
                ec = int(parts[1])
            except (IndexError, ValueError):
                pass
            if "bug" in parts:
                bug = parts[parts.index("bug") + 1]
    if ec is None:
        ec = r.returncode
    return (ec, bug, out)


def run_input(data, target_bug, timeout=60):
    """data: bytes. Tra dict {triggered_bug_vuln, exit_vuln, exit_fixed, crash_vuln, crash_fixed}."""
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "tc")
        with open(p, "wb") as f:
            f.write(data if isinstance(data, (bytes, bytearray)) else data.encode())
        ev, bv, _ = _run_container(IMAGES["vuln"], p, timeout)
        ef, bf, _ = _run_container(IMAGES["fixed"], p, timeout)
    return {"bug_vuln": bv, "exit_vuln": ev, "exit_fixed": ef,
            "crash_vuln": int(ev is not None and ev >= 128),
            "crash_fixed": int(ef is not None and ef >= 128), "target": target_bug}


def discrim(res):
    """Kich hoat DUNG bug muc tieu tren vuln, SACH tren fixed."""
    trig = (res["bug_vuln"] == res["target"]) or res["crash_vuln"]  # canary bug HOAC abort tren vuln
    return int(bool(trig) and res["crash_fixed"] == 0)


def render_input(model_text, timeout=10, maxlen=8 << 20):
    """Rut khoi ```python ... ``` dinh nghia build(), chay trong subprocess -> bytes input. None neu loi."""
    m = re.search(r"```(?:python)?\s*([\s\S]*?)```", model_text or "")
    code = (m.group(1) if m else (model_text or "")).strip()
    if "def build" not in code:
        return None
    runner = code + "\n\nimport sys as _s\n_d = build()\n_s.stdout.buffer.write(_d if isinstance(_d,(bytes,bytearray)) else bytes(_d))\n"
    try:
        r = subprocess.run([sys.executable, "-I", "-c", runner], capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None
    data = r.stdout or b""
    return data[:maxlen] if data else None


# ===== Self-test builder: PNG palette voi PLTE VUOT max_palette_length (dieu kien PNG003) =====
def _chunk(typ, data):
    return struct.pack(">I", len(data)) + typ + data + struct.pack(">I", zlib.crc32(typ + data) & 0xffffffff)


def make_plte_png(n_entries=8, bit_depth=1):
    """PNG palette 1x1: bit_depth nho -> max_palette_length = 1<<bit_depth; PLTE n_entries > max -> trigger."""
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", 1, 1, bit_depth, 3, 0, 0, 0)          # 1x1, colortype 3 = palette
    plte = bytes([i & 0xff for i in range(n_entries) for _ in range(3)])  # n_entries * RGB
    idat = zlib.compress(b"\x00\x00")                                     # 1 row: filter(0)+1 byte
    return sig + _chunk(b"IHDR", ihdr) + _chunk(b"PLTE", plte) + _chunk(b"IDAT", idat) + _chunk(b"IEND", b"")


def selftest(bug):
    if bug != "PNG003":
        print("Self-test builder chi ho tro PNG003 (oversized PLTE)."); return 2
    data = make_plte_png(n_entries=8, bit_depth=1)     # num=8 > max=2 -> canary num>max_palette_length
    print("[selftest] PNG %d bytes: PLTE 8 entries, bit_depth 1 (max_palette=2)" % len(data))
    res = run_input(data, bug)
    print("  VULN : exit=%s bug=%s crash=%d" % (res["exit_vuln"], res["bug_vuln"], res["crash_vuln"]))
    print("  FIXED: exit=%s crash=%d" % (res["exit_fixed"], res["crash_fixed"]))
    ok = discrim(res)
    print("  DISCRIM =", ok, "(1 = oracle vi-phan DUNG: no vuln, sach fixed)")
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", metavar="BUG")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest(a.selftest))
    print("Dung: --selftest PNG003")
