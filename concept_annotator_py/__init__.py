"""Python concept annotation helpers: TestEval targets (annotator) and function-level C1-C8 tags (functions)."""

from .annotator import annotate_record, render_prompt_block
from .functions import annotate_function, render_tags

__all__ = ["annotate_record", "render_prompt_block", "annotate_function", "render_tags"]
