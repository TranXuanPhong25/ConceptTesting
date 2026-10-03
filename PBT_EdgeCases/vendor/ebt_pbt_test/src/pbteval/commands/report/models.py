"""Data models for report generation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class FileAnalysis:
    """Base class for file analysis results"""

    file_path: Path
    file_size: int
    line_count: int
    modified_time: datetime
    content: str
    exists: bool


@dataclass
class EBTAnalysis(FileAnalysis):
    """Analysis results for EBT files"""

    assertion_count: int
    test_categories: list[str]
    basic_tests: int
    edge_tests: int
    large_scale_tests: int
    comment_lines: int
    code_lines: int
    concrete_values: list[str]
    threshold_values: list[str]


@dataclass
class PBTAnalysis(FileAnalysis):
    """Analysis results for PBT files"""

    test_function_count: int
    given_decorator_count: int
    strategies_used: dict[str, int]
    strategy_parameters: dict[str, list[str]]
    docstring_lines: int
    code_lines: int
    test_function_names: list[str]
    special_constraints: list[str]
