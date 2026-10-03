"""Read-only inspection of a remote zip via HTTP Range requests (no full download).
usage: python3 remote_zip.py <url> list [pattern] | python3 remote_zip.py <url> get <member> <out>"""
import io, re, sys, urllib.request, zipfile


class RangeFile:
    def __init__(self, url):
        self.url, self.pos = url, 0
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req) as r:
            self.url, self.size = r.geturl(), int(r.headers["Content-Length"])

    def seekable(self): return True
    def readable(self): return True
    def tell(self): return self.pos

    def seek(self, off, whence=0):
        self.pos = {0: off, 1: self.pos + off, 2: self.size + off}[whence]
        return self.pos

    def read(self, n=-1):
        if n is None or n < 0: n = self.size - self.pos
        if n == 0 or self.pos >= self.size: return b""
        end = min(self.size, self.pos + n) - 1
        req = urllib.request.Request(self.url, headers={"Range": f"bytes={self.pos}-{end}"})
        with urllib.request.urlopen(req) as r:
            data = r.read()
        self.pos += len(data)
        return data


if __name__ == "__main__":
    z = zipfile.ZipFile(RangeFile(sys.argv[1]))
    if sys.argv[2] == "list":
        pat = re.compile(sys.argv[3] if len(sys.argv) > 3 else ".")
        for i in z.infolist():
            if pat.search(i.filename): print(i.file_size, i.filename)
    else:
        open(sys.argv[4], "wb").write(z.read(sys.argv[3]))
