"""Pass 2 of the read-only AndroB2O check: minSdk/targetSdk per APK + emulator AVD per bug.
APK: stream the deflated member from its start and stop as soon as the AndroidManifest.xml local entry is decoded
(early close, so only a prefix is transferred). AVD: one *_run_test.sh per bug id. Records are appended to
pass2.jsonl as they finish (resumable). usage: python3 pass2_sdk.py
"""
import json, re, struct, sys, time, urllib.error, urllib.request, zipfile, zlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from inspect_apks import RF, FINAL, axml_uses_sdk, get

OUT = Path(__file__).resolve().parent / "pass2.jsonl"


def stream(a, b):
    req = urllib.request.Request(FINAL, headers={"Range": f"bytes={a}-{b - 1}"})
    for attempt in range(12):
        try:
            return urllib.request.urlopen(req, timeout=60)
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == 11: raise
            time.sleep(int(e.headers.get("Retry-After") or 30))


def manifest_from_stream(info):
    h = get(info.header_offset, info.header_offset + 30 + 1024)
    n, m = struct.unpack("<HH", h[26:30])
    off = info.header_offset + 30 + n + m
    r = stream(off, off + info.compress_size)
    d = zlib.decompressobj(-15) if info.compress_type == 8 else None
    buf, pos = b"", 0
    try:
        while True:
            chunk = r.read(65536)
            if not chunk: return None
            buf += d.decompress(chunk) if d else chunk
            while len(buf) >= pos + 30:  # walk the APK's local file headers
                if buf[pos:pos + 4] != b"PK\x03\x04": return None
                flag, meth = struct.unpack("<HH", buf[pos + 6:pos + 10])
                csz, usz, ln, lx = struct.unpack("<IIHH", buf[pos + 18:pos + 30])
                if flag & 0x08: return None  # sizes in a trailing data descriptor: give up
                name = buf[pos + 30:pos + 30 + ln].decode("utf-8", "replace")
                start = pos + 30 + ln + lx
                if len(buf) < start + csz: break
                if name == "AndroidManifest.xml":
                    data = buf[start:start + csz]
                    return data if meth == 0 else zlib.decompress(data, -15)
                pos = start + csz
    finally:
        r.close()


def apk_job(info):
    rec = {"apk": info.filename}
    try:
        man = manifest_from_stream(info)
        rec["uses_sdk"] = axml_uses_sdk(man) if man else None
    except Exception as e:
        rec["error"] = f"{type(e).__name__}: {e}"[:200]
    return rec


def script_job(info):
    h = get(info.header_offset, info.header_offset + 30 + 1024 + info.compress_size)
    n, m = struct.unpack("<HH", h[26:30])
    raw = h[30 + n + m:30 + n + m + info.compress_size]
    t = (raw if info.compress_type == 0 else zlib.decompress(raw, -15)).decode("utf-8", "replace")
    return {"script": info.filename, "avd": re.findall(r"-avd\s+(\S+)", t)}


if __name__ == "__main__":
    z = zipfile.ZipFile(RF)
    infos = [i for i in z.infolist() if not i.filename.startswith("__MACOSX")]
    done = {json.loads(l).get("apk") or json.loads(l).get("script") for l in OUT.open()} if OUT.exists() else set()
    apks = [i for i in infos if i.filename.lower().endswith(".apk") and i.filename not in done]
    per_bug = {}
    for i in infos:
        m = re.match(r"Artifact/(\w+)/(\d+)(_fixed)?(_decomp_\d)?_run_test\.sh$", i.filename)
        if m: per_bug.setdefault((m.group(1), m.group(2)), i)
    scripts = [i for i in per_bug.values() if i.filename not in done]
    print(f"{len(apks)} apks, {len(scripts)} scripts", file=sys.stderr)
    with ThreadPoolExecutor(3) as pool, OUT.open("a") as fo:
        for rec in pool.map(script_job, scripts):
            fo.write(json.dumps(rec) + "\n"); fo.flush()
        for rec in pool.map(apk_job, apks):
            fo.write(json.dumps(rec) + "\n"); fo.flush()
            print(rec, file=sys.stderr, flush=True)
