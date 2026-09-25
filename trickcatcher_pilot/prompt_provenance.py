"""Fail-closed provenance for TrickCatcher's released EvalPlus prompt templates."""

from __future__ import annotations

import hashlib
from pathlib import Path


ARTIFACT_COMMIT = "a0d285a77efff7c93fc280d606497d9de5e1defe"
TEMPLATE_SHA256 = {
    "geninput_direct_sys": "b1b5f38811222eef6b0b6e1d5badd39248f48f09cb085648a7f441dae495e902",
    "geninput_usr": "ce7b4adbf8d6c00a4f855191256c76ef7bf7dbad18362a8e0f73b1d3e3129317",
}


def read_original_templates(template_dir: Path) -> tuple[str, str]:
    """Load only byte-identical templates from the pinned official artifact."""
    result = []
    for name in ("geninput_direct_sys", "geninput_usr"):
        raw = (template_dir / name).read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if digest != TEMPLATE_SHA256[name]:
            raise ValueError(
                f"Official TrickCatcher template {name} has SHA-256 {digest}, "
                f"expected {TEMPLATE_SHA256[name]}; refusing an untracked prompt change"
            )
        result.append(raw.decode("utf-8"))
    return result[0], result[1]
