"""Read-only AndroB2O (#67) feasibility check: for every APK inside Zenodo 10.5281/zenodo.15556567 Artifact.zip,
list native libs (lib/<abi>/*.so) and read minSdk/targetSdk from the binary AndroidManifest.xml, using HTTP Range
requests only (no full download, nothing installed, nothing executed). Also collects the AVD names used by the
artifact's *_run_test.sh scripts. usage: python3 inspect_apks.py > apk_report.json
"""
import io, json, re, struct, sys, time, zipfile, zlib
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import urllib.request

URL = "https://zenodo.org/api/records/15556567/files/Artifact.zip/content"
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from remote_zip import RangeFile

RF = RangeFile(URL)
FINAL, SIZE = RF.url, RF.size


def get(a, b):  # bytes [a, b); polite: backs off on Zenodo 429
    import time, urllib.error
    req = urllib.request.Request(FINAL, headers={"Range": f"bytes={a}-{b - 1}"})
    for attempt in range(12):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == 11: raise
            time.sleep(int(e.headers.get("Retry-After") or 30))
        except Exception:
            if attempt == 11: raise
            time.sleep(5)


def member_data(info, extra=4096):
    """compressed bytes of a member of the OUTER zip -> (data_offset, bytes or None if not fetched)."""
    h = get(info.header_offset, info.header_offset + 30 + extra)
    n, m = struct.unpack("<HH", h[26:30])
    return info.header_offset + 30 + n + m


def read_member(info):
    off = member_data(info)
    raw = get(off, off + info.compress_size)
    return raw if info.compress_type == 0 else zlib.decompress(raw, -15)


class Slice:  # file-like view of a STORED member of the outer zip (a nested APK); read-ahead cache
    def __init__(self, base, size):
        self.base, self.size, self.pos = base, size, 0
        t = max(0, size - 262144)
        self.blocks = [(t, get(base + t, base + size))]  # tail: EOCD + central directory
    def seekable(self): return True
    def tell(self): return self.pos
    def seek(self, off, whence=0):
        self.pos = {0: off, 1: self.pos + off, 2: self.size + off}[whence]; return self.pos
    def read(self, n=-1):
        if n is None or n < 0: n = self.size - self.pos
        n = max(0, min(n, self.size - self.pos))
        if n == 0: return b""
        for st, bl in self.blocks:
            if st <= self.pos and self.pos + n <= st + len(bl):
                d = bl[self.pos - st:self.pos - st + n]; self.pos += n; return d
        end = min(self.size, self.pos + max(n, 65536))
        bl = get(self.base + self.pos, self.base + end); self.blocks.append((self.pos, bl))
        d = bl[:n]; self.pos += len(d); return d


def axml_uses_sdk(b):
    """Minimal binary-XML reader: attributes of <uses-sdk>."""
    pos, strings, out = 8, [], {}
    while pos + 8 <= len(b):
        ctype, hsize, csize = struct.unpack("<HHI", b[pos:pos + 8])
        if csize == 0: break
        if ctype == 0x0001:
            count, _, flags, sstart = struct.unpack("<IIII", b[pos + 8:pos + 24])
            offs = struct.unpack(f"<{count}I", b[pos + 28:pos + 28 + 4 * count])
            utf8 = flags & 0x100
            for o in offs:
                p = pos + sstart + o
                if utf8:
                    p += 2 if b[p] & 0x80 else 1
                    ln = b[p]; p += 1
                    if ln & 0x80: ln = ((ln & 0x7F) << 8) | b[p]; p += 1
                    strings.append(b[p:p + ln].decode("utf-8", "replace"))
                else:
                    ln = struct.unpack("<H", b[p:p + 2])[0]; p += 2
                    if ln & 0x8000: ln = ((ln & 0x7FFF) << 16) | struct.unpack("<H", b[p:p + 2])[0]; p += 2
                    strings.append(b[p:p + 2 * ln].decode("utf-16-le", "replace"))
        elif ctype == 0x0102:
            name = struct.unpack("<I", b[pos + 20:pos + 24])[0]
            astart, asize, acount = struct.unpack("<HHH", b[pos + 24:pos + 30])
            if 0 <= name < len(strings) and strings[name] == "uses-sdk":
                for i in range(acount):
                    a = pos + 16 + astart + i * asize
                    _, an, raw, _, _, dtype, data = struct.unpack("<IIIHBBI", b[a:a + 20])
                    key = strings[an] if an < len(strings) else str(an)
                    out[key] = data if dtype in (0x10, 0x11) else (strings[raw] if raw < len(strings) else data)
        pos += csize
    return out


def inspect(info):
    rec = {"apk": info.filename, "bytes": info.file_size, "stored": info.compress_type == 0}
    try:
        if info.compress_type != 0:  # deflated inside Artifact.zip: stream it into memory (never written to disk)
            apk = zipfile.ZipFile(io.BytesIO(read_member(info)))
        else:
            apk = zipfile.ZipFile(Slice(member_data(info), info.compress_size))
        libs = [n for n in apk.namelist() if n.startswith("lib/") and n.endswith(".so")]
        rec["abis"] = sorted({n.split("/")[1] for n in libs})
        rec["n_so"] = len(libs)
        rec["uses_sdk"] = axml_uses_sdk(apk.read("AndroidManifest.xml"))
    except Exception as e:
        rec["error"] = f"{type(e).__name__}: {e}"[:200]
    print(f"{time.strftime('%H:%M:%S')} {info.compress_size} {info.filename} {rec.get('abis')}", file=sys.stderr, flush=True)
    return rec


if __name__ == "__main__":
    z = zipfile.ZipFile(RF)
    infos = [i for i in z.infolist() if not i.filename.startswith("__MACOSX")]
    apks = [i for i in infos if i.filename.lower().endswith(".apk")]
    scripts = [i for i in infos if i.filename.endswith("_run_test.sh")][::10]  # every 10th script is enough for AVD names
    with ThreadPoolExecutor(8) as pool:
        recs = list(pool.map(inspect, apks))
        texts = list(pool.map(lambda i: read_member(i).decode("utf-8", "replace"), scripts))
    avd = Counter(m for t in texts for m in re.findall(r"-avd\s+(\S+)", t))
    abi = Counter("+".join(r.get("abis", [])) or ("pure-Java (no lib/*.so)" if "abis" in r else "not inspected") for r in recs)
    sdk = Counter((r.get("uses_sdk", {}).get("minSdkVersion"), r.get("uses_sdk", {}).get("targetSdkVersion")) for r in recs)
    print(json.dumps({"n_apks": len(recs), "n_run_test_scripts": len(scripts), "avd_names": avd,
                      "abi_sets": abi, "min_target_sdk": {str(k): v for k, v in sdk.items()},
                      "errors": [r for r in recs if "error" in r][:10], "apks": recs}, indent=1, default=str))
