import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from concept_annotator import (
    annotate_function,
    annotate_item,
    render_prompt_block,
    to_testeval_metadata,
)


OOB_FUNC = """int copy_into(char *src, int n) {
    char buf[8];
    if (n > 0) {
        memcpy(buf, src, n);
    }
    return buf[0];
}"""


UAF_FUNC = """void write_after_free(int *p) {
    free(p);
    if (p != NULL) {
        *p = 1;
    }
}"""


class ConceptAnnotatorTests(unittest.TestCase):
    def test_oob_function_gets_target_line_branch_and_path_tasks(self):
        ann = annotate_function(OOB_FUNC)

        self.assertEqual(ann["schema"], "concept_annotator.v1")
        self.assertEqual(ann["family_pred"], "oob")

        meta = to_testeval_metadata(ann)
        self.assertIn(3, meta["target_lines"])
        self.assertIn({"start": 2, "end": 3}, meta["blocks"])
        self.assertTrue(
            any(path == [2, 3] for path in meta["sampled_paths"]),
            meta["sampled_paths"],
        )

        first_target = ann["targets"][0]
        self.assertEqual(first_target["kind"], "target_line")
        self.assertEqual(first_target["line"], 3)
        self.assertIn("buffer_access", first_target["tags"])
        self.assertEqual(first_target["controllable_vars"], ["n", "src"])

    def test_uaf_path_keeps_free_before_deref(self):
        ann = annotate_function(UAF_FUNC)

        self.assertEqual(ann["family_pred"], "uaf")
        path_targets = [t for t in ann["targets"] if t["kind"] == "target_path"]
        self.assertTrue(path_targets)
        self.assertEqual(path_targets[0]["waypoints"], [1, 2, 3])
        self.assertIn("free first", path_targets[0]["goal"])

    def test_prompt_block_is_compact_and_testeval_shaped(self):
        ann = annotate_function(OOB_FUNC)
        block = render_prompt_block(ann, max_targets=2)

        self.assertIn("TEstEval-inspired concept targets", block)
        self.assertIn("target line L3", block)
        self.assertIn("branch L2 -> L3", block)
        self.assertIn("memcpy(buf, src, n);", block)

    def test_annotate_item_preserves_input_and_adds_metadata(self):
        item = {"id": "toy_oob", "func_vuln": OOB_FUNC}
        out = annotate_item(item)

        self.assertEqual(out["id"], "toy_oob")
        self.assertIn("concept_annotation", out)
        self.assertIn("testeval", out["concept_annotation"])
        self.assertEqual(out["concept_annotation"]["testeval"]["target_lines"][0], 3)

    def test_cli_reads_jsonl_and_writes_annotated_jsonl(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "in.jsonl"
            dst = Path(td) / "out.jsonl"
            src.write_text(json.dumps({"id": "toy", "func_vuln": OOB_FUNC}) + "\n")

            subprocess.run(
                [sys.executable, "-m", "concept_annotator.run", "--in", str(src), "--out", str(dst)],
                check=True,
            )

            rows = [json.loads(line) for line in dst.read_text().splitlines()]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["concept_annotation"]["family_pred"], "oob")

    def test_null_comparison_is_not_tagged_as_null_assignment(self):
        ann = annotate_function(
            """int guarded(int *p) {
    if (p == NULL) return 0;
    return *p;
}"""
        )
        tags_by_line = {item["line"]: item["tags"] for item in ann["concept_lines"]}

        self.assertIn("null_check", tags_by_line[1])
        self.assertNotIn("null_assignment", tags_by_line[1])


if __name__ == "__main__":
    unittest.main()
