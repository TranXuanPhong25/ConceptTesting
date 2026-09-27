"""Fail-closed check that the vendored upstream files are byte-identical to
the pinned commit. These are copied verbatim from FlowRays/TestCase-Eval
@ 45275c6f838566e6e148a9eca18edc00be08a305 (not run directly -- see
testcase_eval/sandbox.py and testcase_eval/metrics.py for why -- but kept
here so any deviation claimed in those modules' docstrings can be diffed
against the real thing instead of taken on faith).
"""

import hashlib
import unittest
from pathlib import Path

VENDOR_DIR = Path(__file__).resolve().parent.parent / "testcase_eval" / "vendor"

PINNED_SHA256 = {
    "upstream_sandbox.py": "a226e080c55f416bf735d788c29b4bc191091df4eb75e5b085b318e9500a58a0",
    "upstream_stat_task1.py": "388276f1a59fc4c9412a06e7f2070037f316c8e8aeaf54ebc11a3ac65056b9ab",
    "upstream_stat_task2.py": "b965af9c18425503a86f2f58c955718fc31cb18129d97a8527bc0b688018deab",
}


class VendorProvenanceTests(unittest.TestCase):
    def test_vendored_files_match_pinned_upstream_hashes(self):
        for name, expected in PINNED_SHA256.items():
            path = VENDOR_DIR / name
            self.assertTrue(path.is_file(), f"missing vendored file: {path}")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(digest, expected, f"{name} no longer matches the pinned upstream commit")
