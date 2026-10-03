"""File analyzers for test files."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

from pbteval.utils.utils import extract_code_block

from .constants import (
    PARAM_PATTERNS,
    REGEX_PATTERNS,
    SPECIAL_CONSTRAINTS,
    STRATEGY_PATTERNS,
    TEST_CATEGORIES,
)
from .models import EBTAnalysis, PBTAnalysis


class FileMetadata(NamedTuple):
    """File metadata container"""

    file_size: int
    line_count: int
    modified_time: datetime
    content: str
    lines: list[str]


class BaseFileAnalyzer:
    """Base analyzer with common functionality"""

    def _extract_file_metadata(self, file_path: Path) -> FileMetadata:
        """Extract common file metadata

        Args:
            file_path: Path to the file

        Returns:
            FileMetadata containing basic file information
        """
        content = file_path.read_text(encoding="utf-8")
        lines = content.split("\n")

        file_size = file_path.stat().st_size
        line_count = len(lines)
        modified_time = datetime.fromtimestamp(file_path.stat().st_mtime)

        return FileMetadata(
            file_size=file_size,
            line_count=line_count,
            modified_time=modified_time,
            content=content,
            lines=lines,
        )


class EBTAnalyzer(BaseFileAnalyzer):
    """Analyzer for EBT files"""

    def analyze(self, file_path: Path) -> EBTAnalysis:
        """Analyze EBT file and extract structural information

        Args:
            file_path: Path to the EBT file

        Returns:
            EBTAnalysis object with extracted information
        """
        if not file_path.exists():
            return self._create_empty_analysis(file_path)

        # Extract common file metadata
        metadata = self._extract_file_metadata(file_path)

        # Extract code blocks from markdown
        code_content = extract_code_block(metadata.content)

        # Count assertions
        assertion_count = len(REGEX_PATTERNS["assertion"].findall(code_content))

        # Detect test categories
        categories = [
            category for category in TEST_CATEGORIES if category in metadata.content
        ]

        # Count tests by category
        basic_tests = len(REGEX_PATTERNS["basic_test_case"].findall(metadata.content))
        edge_tests = len(REGEX_PATTERNS["edge_test_case"].findall(metadata.content))
        large_scale_tests = len(
            REGEX_PATTERNS["large_scale_test_case"].findall(metadata.content)
        )

        # Count comment and code lines
        comment_lines = len(
            [line for line in metadata.lines if line.strip().startswith("#")]
        )
        code_lines = len(
            [
                line
                for line in metadata.lines
                if line.strip()
                and not line.strip().startswith("#")
                and not line.strip().startswith("```")
                and line.strip() != ""
            ]
        )

        # Extract concrete values and thresholds
        concrete_values = self._extract_concrete_values(code_content)
        threshold_values = self._extract_threshold_values(code_content)

        return EBTAnalysis(
            file_path=file_path,
            file_size=metadata.file_size,
            line_count=metadata.line_count,
            modified_time=metadata.modified_time,
            content=metadata.content,
            exists=True,
            assertion_count=assertion_count,
            test_categories=categories,
            basic_tests=basic_tests,
            edge_tests=edge_tests,
            large_scale_tests=large_scale_tests,
            comment_lines=comment_lines,
            code_lines=code_lines,
            concrete_values=concrete_values,
            threshold_values=threshold_values,
        )

    def _create_empty_analysis(self, file_path: Path) -> EBTAnalysis:
        """Create empty EBT analysis for non-existent files

        Args:
            file_path: Path to the file

        Returns:
            Empty EBTAnalysis object
        """
        return EBTAnalysis(
            file_path=file_path,
            file_size=0,
            line_count=0,
            modified_time=datetime.now(),
            content="",
            exists=False,
            assertion_count=0,
            test_categories=[],
            basic_tests=0,
            edge_tests=0,
            large_scale_tests=0,
            comment_lines=0,
            code_lines=0,
            concrete_values=[],
            threshold_values=[],
        )

    def _extract_concrete_values(self, content: str) -> list[str]:
        """Extract concrete values from EBT content

        Args:
            content: EBT content

        Returns:
            List of concrete values found
        """
        # Look for list patterns like [1.0, 2.0, 3.0]
        list_patterns = REGEX_PATTERNS["list_patterns"].findall(content)
        return list_patterns[:5]  # Limit to first 5 examples

    def _extract_threshold_values(self, content: str) -> list[str]:
        """Extract threshold values from EBT content

        Args:
            content: EBT content

        Returns:
            List of threshold values found
        """
        # Look for threshold values in function calls
        threshold_patterns = REGEX_PATTERNS["threshold_patterns"].findall(content)
        return list(dict.fromkeys(threshold_patterns))[
            :10
        ]  # Preserve order while deduplicating


class PBTAnalyzer(BaseFileAnalyzer):
    """Analyzer for PBT files"""

    def analyze(self, file_path: Path) -> PBTAnalysis:
        """Analyze PBT file and extract structural information

        Args:
            file_path: Path to the PBT file

        Returns:
            PBTAnalysis object with extracted information
        """
        if not file_path.exists():
            return self._create_empty_analysis(file_path)

        # Extract common file metadata
        metadata = self._extract_file_metadata(file_path)

        # Count @given decorators and test functions
        given_decorator_count = len(
            REGEX_PATTERNS["given_decorator"].findall(metadata.content)
        )
        test_function_count = len(
            REGEX_PATTERNS["test_function"].findall(metadata.content)
        )

        # Extract test function names
        test_function_names = REGEX_PATTERNS["test_function_names"].findall(
            metadata.content
        )

        # Extract Hypothesis strategies
        strategies_used = self._extract_strategies(metadata.content)

        # Extract strategy parameters
        strategy_parameters = self._extract_strategy_parameters(metadata.content)

        # Extract special constraints
        special_constraints = self._extract_special_constraints(metadata.content)

        # Count docstring and code lines
        docstring_lines = len(REGEX_PATTERNS["docstring"].findall(metadata.content))
        code_lines = len(
            [
                line
                for line in metadata.lines
                if line.strip()
                and not line.strip().startswith("#")
                and not line.strip().startswith('"""')
                and not line.strip().endswith('"""')
            ]
        )

        return PBTAnalysis(
            file_path=file_path,
            file_size=metadata.file_size,
            line_count=metadata.line_count,
            modified_time=metadata.modified_time,
            content=metadata.content,
            exists=True,
            test_function_count=test_function_count,
            given_decorator_count=given_decorator_count,
            strategies_used=strategies_used,
            strategy_parameters=strategy_parameters,
            docstring_lines=docstring_lines,
            code_lines=code_lines,
            test_function_names=test_function_names,
            special_constraints=special_constraints,
        )

    def _create_empty_analysis(self, file_path: Path) -> PBTAnalysis:
        """Create empty PBT analysis for non-existent files

        Args:
            file_path: Path to the file

        Returns:
            Empty PBTAnalysis object
        """
        return PBTAnalysis(
            file_path=file_path,
            file_size=0,
            line_count=0,
            modified_time=datetime.now(),
            content="",
            exists=False,
            test_function_count=0,
            given_decorator_count=0,
            strategies_used={},
            strategy_parameters={},
            docstring_lines=0,
            code_lines=0,
            test_function_names=[],
            special_constraints=[],
        )

    def _extract_strategies(self, content: str) -> dict[str, int]:
        """Extract Hypothesis strategies and their counts

        Args:
            content: PBT content

        Returns:
            Dictionary of strategy names and their counts
        """
        strategies = {}
        for strategy_name, pattern in STRATEGY_PATTERNS:
            count = len(re.findall(pattern, content))
            if count > 0:
                strategies[strategy_name] = count
        return strategies

    def _extract_strategy_parameters(self, content: str) -> dict[str, list[str]]:
        """Extract strategy parameters

        Args:
            content: PBT content

        Returns:
            Dictionary of parameter names and their values
        """
        parameters = {}
        for param_name, pattern in PARAM_PATTERNS:
            matches = re.findall(pattern, content)
            if matches:
                parameters[param_name] = list(set(matches))  # Deduplicate
        return parameters

    def _extract_special_constraints(self, content: str) -> list[str]:
        """Extract special constraints from PBT content

        Args:
            content: PBT content

        Returns:
            List of special constraints found
        """
        constraints = []
        for constraint in SPECIAL_CONSTRAINTS:
            if constraint in content:
                constraints.append(constraint)
        return constraints


class TestFileAnalyzer:
    """Main analyzer that delegates to specific analyzers"""

    def __init__(self) -> None:
        """Initialize the test file analyzer"""
        self.ebt_analyzer = EBTAnalyzer()
        self.pbt_analyzer = PBTAnalyzer()

    def analyze_ebt(self, file_path: Path) -> EBTAnalysis:
        """Analyze EBT file

        Args:
            file_path: Path to the EBT file

        Returns:
            EBTAnalysis object
        """
        return self.ebt_analyzer.analyze(file_path)

    def analyze_pbt(self, file_path: Path) -> PBTAnalysis:
        """Analyze PBT file

        Args:
            file_path: Path to the PBT file

        Returns:
            PBTAnalysis object
        """
        return self.pbt_analyzer.analyze(file_path)
