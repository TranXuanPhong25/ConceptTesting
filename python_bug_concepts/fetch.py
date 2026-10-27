"""Re-download pinned source files into a NEW destination and verify hashes.

Existing checked-in snapshots are never overwritten. The manifest controls both
the revision and expected content; this command does not update upstream pins.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import tarfile
import urllib.request
from pathlib import Path

from .ingest import ROOT


def download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "ConceptTester-source-snapshot/1"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def fetch(destination: Path) -> dict:
    destination = destination.resolve()
    if destination.exists():
        raise ValueError("Destination already exists; choose a new directory to preserve source snapshots")
    manifest = json.loads((ROOT / "data/sources.json").read_text())
    # Verify all downloads before creating any output directory.
    files = {}
    for source in manifest["sources"]:
        repo = source["repository"].removeprefix("https://github.com/")
        prefix = f"sources/{source['id']}/"
        if source["id"] in {"ruff", "flake8-bugbear"}:
            archive = download(f"https://codeload.github.com/{repo}/tar.gz/{source['revision']}")
            with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
                members = {m.name.split("/", 1)[1]: m for m in tar.getmembers() if m.isfile() and "/" in m.name}
                for item in source["files"]:
                    rel = item["path"].removeprefix(prefix)
                    stream = tar.extractfile(members[rel])
                    if stream is None:
                        raise ValueError(f"Missing archive file: {rel}")
                    files[item["path"]] = stream.read()
        else:
            for item in source["files"]:
                rel = item["path"].removeprefix(prefix)
                files[item["path"]] = download(f"https://raw.githubusercontent.com/{repo}/{source['revision']}/{rel}")
        for item in source["files"]:
            content = files[item["path"]]
            if len(content) != item["bytes"] or hashlib.sha256(content).hexdigest() != item["sha256"]:
                raise ValueError(f"Downloaded content differs from pinned snapshot: {item['path']}")
    destination.mkdir(parents=True, exist_ok=False)
    for relative, content in files.items():
        path = destination / relative
        if not path.resolve().is_relative_to(destination):
            raise ValueError(f"Invalid manifest path: {relative}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    return {"destination": str(destination), "verified_files": len(files), "sources": len(manifest["sources"])}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", required=True, type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(fetch(args.destination), indent=2))
    except (OSError, ValueError) as exc:
        parser.exit(2, str(exc) + "\n")
