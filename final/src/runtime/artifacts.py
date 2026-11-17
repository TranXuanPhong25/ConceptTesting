"""Stable content hashes and atomic JSON writes for run artifacts."""
import hashlib
import json
import os
import stat
from pathlib import Path

def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

def save(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
    temporary.replace(path)


def read_sandbox_file(directory: Path, relative: str, *, max_bytes: int = 8 << 20) -> bytes:
    """Read bounded regular child output without following any symlink component."""
    path = Path(relative)
    if path.is_absolute() or not path.parts or '..' in path.parts or type(max_bytes) is not int or max_bytes < 1:
        raise ValueError('unsafe sandbox artifact path or size limit')
    descriptors = []
    try:
        directory_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        descriptors.append(directory_fd)
        for part in path.parts[:-1]:
            directory_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory_fd)
            descriptors.append(directory_fd)
        descriptor = os.open(path.parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory_fd)
        descriptors.append(descriptor)
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError('sandbox artifact must be a regular file')
        if metadata.st_size > max_bytes:
            raise ValueError('sandbox artifact exceeds size limit')
        chunks, remaining = [], max_bytes + 1
        while remaining:
            chunk = os.read(descriptor, min(65536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        result = b''.join(chunks)
        if len(result) > max_bytes:
            raise ValueError('sandbox artifact exceeds size limit')
        return result
    except OSError:
        raise ValueError('unsafe or missing sandbox artifact') from None
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)
