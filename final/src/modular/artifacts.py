"""A single place for artifact I/O and read-only checkpoint replay."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Any

from final.src.runtime.artifacts import save


class ArtifactStore:
    def __init__(self, directory: Path, *, read_only: bool = False):
        self.directory = directory.resolve()
        self.read_only = read_only

    def path(self, relative_path: str) -> Path:
        resolved_path = (self.directory / relative_path).resolve()
        if not resolved_path.is_relative_to(self.directory):
            raise ValueError("Artifact path must remain inside the run directory")
        return resolved_path

    def exists(self, relative_path: str) -> bool:
        return self.path(relative_path).is_file()

    def read(self, relative_path: str) -> Any:
        return json.loads(self.path(relative_path).read_text())

    def write(self, relative_path: str, value: Any) -> None:
        if self.exists(relative_path):
            if self.read(relative_path) != value:
                raise ValueError(f"Artifact changed: {relative_path}; use a new run directory")
            return
        if self.read_only:
            raise FileNotFoundError(f"Read-only replay requires {relative_path}")
        save(self.path(relative_path), value)

    def load_or_compute(self, relative_path: str, compute: Callable[[], Any]) -> Any:
        if self.exists(relative_path):
            return self.read(relative_path)
        if self.read_only:
            raise FileNotFoundError(f"Read-only replay requires {relative_path}")
        result = compute()
        self.write(relative_path, result)
        return result
