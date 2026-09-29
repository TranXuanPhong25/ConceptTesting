"""Pinned TrickCatcher artifact and byte-identical prompt templates.

TrickCatcher (Liu et al., ACL 2025) released its prompts under
``Datasets/TrickyBugs/PromptTemplates``. The baseline arm of this package uses
``genprog_tc`` (PUT-guided variant generation, paper Fig. 3) and
``geninput_generator`` (generator-based input generation, paper Fig. 4)
verbatim; loading fails closed if a template differs from the pinned bytes.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

ARTIFACT_URL = "https://github.com/RinCloud/TrickCatcher"
ARTIFACT_COMMIT = "a0d285a77efff7c93fc280d606497d9de5e1defe"
PAPER_URL = "https://aclanthology.org/2025.acl-long.20/"

TRICKYBUGS_TEMPLATE_SHA256 = {
    "genprog_tc": "f61bcecb70f7ec8f5c0e7e63799d749406af93759e07bcd7a6abc7f1a7a9f15c",
    "geninput_generator": "57e1da60da6f2ac745519f735317ffc62ad379cb1b7c4a30d883b573928c8a0a",
    "geninput_direct": "26d075a69cc99a00b7ddd6095634cdc0468fcc54c6a7b09bc6f4a87498f2832b",
}


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_template(artifact: Path, name: str) -> str:
    """Return a TrickyBugs prompt template after verifying its SHA-256."""
    raw = (Path(artifact) / "Datasets" / "TrickyBugs" / "PromptTemplates" / name).read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    expected = TRICKYBUGS_TEMPLATE_SHA256[name]
    if digest != expected:
        raise ValueError(f"TrickCatcher template {name} has SHA-256 {digest}, expected {expected}")
    return raw.decode("utf-8")


def fill(template: str, **values: str) -> str:
    """Substitute ``{name}`` placeholders with str.replace (templates contain other braces)."""
    for key, value in values.items():
        template = template.replace("{" + key + "}", value)
    return template
