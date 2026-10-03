"""Report generators for creating Markdown comparison reports."""

from __future__ import annotations

import re
from datetime import datetime

from pbteval.utils.utils import extract_code_block

from .constants import STATUS_MAP
from .models import EBTAnalysis, PBTAnalysis

# Import necessary constants and utilities
REQUIRED_IMPORTS = """
from typing import *
"""


def get_function_pattern(entry_point: str) -> str:
    """Generate regex pattern to match a function definition

    Args:
        entry_point: The function name to match

    Returns:
        Regex pattern string that matches the function definition
    """
    return rf"def\s+{re.escape(entry_point)}\s*\([^)]*\)(?:\s*->\s*[^:]+)?\s*:.*?(?=\n\s*def|\n\s*class|\n\s*@given|\Z)"


def remove_entry_point_function(code: str, entry_point: str) -> str:
    """Remove entry point function definition from code"""
    pattern = get_function_pattern(entry_point)
    return re.sub(pattern, "", code, flags=re.DOTALL)


def join_code_parts(*parts: str) -> str:
    """Join code parts with newlines, filtering out empty parts"""
    return "\n".join(part for part in parts if part)


class MarkdownReportGenerator:
    """Generator for Markdown comparison reports"""

    def generate_comparison_report(
        self,
        task_id: str,
        model: str,
        ebt_analysis: EBTAnalysis,
        pbt_analysis: PBTAnalysis,
        execution_results: dict[str, str] | None = None,
        target_function: str | None = None,
        problem_description: str | None = None,
        canonical_solution: str | None = None,
        entry_point: str | None = None,
        humaneval_test_code: str | None = None,
    ) -> str:
        """Generate comparison report in Markdown format

        Args:
            task_id: Task identifier
            model: Model name
            ebt_analysis: EBT analysis results
            pbt_analysis: PBT analysis results
            execution_results: Optional execution results from CSV
            target_function: Target function implementation
            problem_description: Problem description from dataset prompt
            canonical_solution: Canonical solution from dataset
            entry_point: Entry point function name from dataset
            humaneval_test_code: HumanEval test code string

        Returns:
            Markdown formatted report
        """
        report_lines = [
            f"# Test Comparison Report: {task_id}",
            "",
            "## Overview",
            f"- **Task ID**: {task_id}",
            f"- **Model**: {model}",
            f"- **Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
        ]

        # File Information section
        report_lines.extend(
            self._generate_file_info_section(ebt_analysis, pbt_analysis)
        )

        # Structure Analysis section
        report_lines.extend(
            self._generate_structure_analysis_section(ebt_analysis, pbt_analysis)
        )

        # Testing Approach Comparison section
        report_lines.extend(
            self._generate_approach_comparison_section(ebt_analysis, pbt_analysis)
        )

        # Problem Description section
        if problem_description:
            report_lines.extend(
                self._generate_problem_description_section(
                    problem_description, entry_point
                )
            )

        # Target Function Implementation section
        if target_function:
            report_lines.extend(self._generate_target_function_section(target_function))

        # Canonical Solution section
        if canonical_solution:
            report_lines.extend(
                self._generate_canonical_solution_section(
                    canonical_solution, problem_description, entry_point
                )
            )

        # Content Preview section
        report_lines.extend(
            self._generate_content_preview_section(
                ebt_analysis,
                pbt_analysis,
                humaneval_test_code,
                target_function,
                entry_point,
            )
        )

        # Execution Results section
        if execution_results:
            report_lines.extend(
                self._generate_execution_results_section(execution_results)
            )

        # Statistical Summary section
        report_lines.extend(
            self._generate_statistical_summary_section(ebt_analysis, pbt_analysis)
        )

        # Footer
        report_lines.extend(
            [
                "---",
                f"*Report generated automatically on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
            ]
        )

        return "\n".join(report_lines)

    def _generate_file_info_section(
        self, ebt_analysis: EBTAnalysis, pbt_analysis: PBTAnalysis
    ) -> list[str]:
        """Generate file information section

        Args:
            ebt_analysis: EBT analysis results
            pbt_analysis: PBT analysis results

        Returns:
            List of markdown lines for file information section
        """
        lines = [
            "## File Information",
            "| Type | File Path | Size | Lines | Modified |",
            "|------|-----------|------|-------|----------|",
        ]

        # EBT file info
        if ebt_analysis.exists:
            lines.append(
                f"| EBT  | {ebt_analysis.file_path} | {ebt_analysis.file_size}B | "
                f"{ebt_analysis.line_count} | {ebt_analysis.modified_time.strftime('%Y-%m-%d %H:%M:%S')} |"
            )
        else:
            lines.append("| EBT  | Not found | - | - | - |")

        # PBT file info
        if pbt_analysis.exists:
            lines.append(
                f"| PBT  | {pbt_analysis.file_path} | {pbt_analysis.file_size}B | "
                f"{pbt_analysis.line_count} | {pbt_analysis.modified_time.strftime('%Y-%m-%d %H:%M:%S')} |"
            )
        else:
            lines.append("| PBT  | Not found | - | - | - |")

        lines.append("")
        return lines

    def _generate_structure_analysis_section(
        self, ebt_analysis: EBTAnalysis, pbt_analysis: PBTAnalysis
    ) -> list[str]:
        """Generate structure analysis section

        Args:
            ebt_analysis: EBT analysis results
            pbt_analysis: PBT analysis results

        Returns:
            List of markdown lines for structure analysis section
        """
        lines = ["## Structure Analysis", ""]

        # EBT structure
        if ebt_analysis.exists:
            lines.extend(
                [
                    "### EBT (Example-Based Testing)",
                    f"- **Total Assertions**: {ebt_analysis.assertion_count}",
                    f"- **Test Categories Detected**: {len(ebt_analysis.test_categories)} ({', '.join(ebt_analysis.test_categories)})",
                    f"- **Basic Test Cases**: {ebt_analysis.basic_tests}",
                    f"- **Edge Test Cases**: {ebt_analysis.edge_tests}",
                    f"- **Large Scale Test Cases**: {ebt_analysis.large_scale_tests}",
                    f"- **Code Lines**: {ebt_analysis.code_lines}",
                    f"- **Comment Lines**: {ebt_analysis.comment_lines}",
                    "",
                ]
            )
        else:
            lines.extend(
                ["### EBT (Example-Based Testing)", "- **Status**: File not found", ""]
            )

        # PBT structure
        if pbt_analysis.exists:
            strategies_str = ", ".join(
                [f"`{k}`: {v}" for k, v in pbt_analysis.strategies_used.items()]
            )
            lines.extend(
                [
                    "### PBT (Property-Based Testing)",
                    f"- **Test Functions**: {pbt_analysis.test_function_count}",
                    f"- **@given Decorators**: {pbt_analysis.given_decorator_count}",
                    f"- **Hypothesis Strategies Used**: {strategies_str}",
                ]
            )

            # Strategy parameters
            if pbt_analysis.strategy_parameters:
                lines.append("- **Strategy Parameters Detected**:")
                for param, values in pbt_analysis.strategy_parameters.items():
                    lines.append(f"  - `{param}`: {values}")

            # Special constraints
            if pbt_analysis.special_constraints:
                lines.append(
                    f"- **Special Constraints**: {', '.join(pbt_analysis.special_constraints)}"
                )

            lines.extend(
                [
                    f"- **Code Lines**: {pbt_analysis.code_lines}",
                    f"- **Docstring Lines**: {pbt_analysis.docstring_lines}",
                    "",
                ]
            )
        else:
            lines.extend(
                ["### PBT (Property-Based Testing)", "- **Status**: File not found", ""]
            )

        return lines

    def _generate_approach_comparison_section(
        self, ebt_analysis: EBTAnalysis, pbt_analysis: PBTAnalysis
    ) -> list[str]:
        """Generate testing approach comparison section

        Args:
            ebt_analysis: EBT analysis results
            pbt_analysis: PBT analysis results

        Returns:
            List of markdown lines for approach comparison section
        """
        lines = ["## Testing Approach Comparison", ""]

        # EBT characteristics
        if ebt_analysis.exists:
            lines.extend(["### EBT Characteristics (Detected Patterns)"])
            if ebt_analysis.concrete_values:
                values_str = ", ".join(ebt_analysis.concrete_values[:3])  # Show first 3
                lines.append(f"- **Concrete Values Used**: {values_str}")
            if ebt_analysis.threshold_values:
                thresholds_str = ", ".join(
                    ebt_analysis.threshold_values[:5]
                )  # Show first 5
                lines.append(f"- **Threshold Values**: {thresholds_str}")

            # Detect large scale patterns
            if "1000000" in ebt_analysis.content or "range(" in ebt_analysis.content:
                lines.append(
                    "- **Large Scale Inputs**: Large array generation patterns detected"
                )
            if "[]" in ebt_analysis.content:
                lines.append("- **Edge Cases Detected**: Empty list testing")
            if (
                "1.0, 1.0" in ebt_analysis.content
                or "identical" in ebt_analysis.content.lower()
            ):
                lines.append("- **Edge Cases Detected**: Identical elements testing")

            lines.append("")

        # PBT characteristics
        if pbt_analysis.exists:
            lines.extend(["### PBT Characteristics (Detected Patterns)"])
            if pbt_analysis.strategies_used:
                lines.append(
                    "- **Input Generation**: Random generation using Hypothesis strategies"
                )
            if pbt_analysis.test_function_names:
                names_str = ", ".join(
                    [f"`{name}`" for name in pbt_analysis.test_function_names]
                )
                lines.append(f"- **Test Function Names**: {names_str}")
            if "distance" in pbt_analysis.content.lower():
                lines.append(
                    "- **Validation Approach**: Mathematical property verification"
                )
            if pbt_analysis.special_constraints:
                lines.append("- **Input Filtering**: Explicit constraint handling")

            lines.append("")

        return lines

    def _generate_target_function_section(self, target_function: str) -> list[str]:
        """Generate target function implementation section

        Args:
            target_function: Target function implementation

        Returns:
            List of markdown lines for target function section
        """
        lines = ["## Target Function Implementation", ""]

        lines.extend(
            [
                "```python",
                target_function.strip(),
                "```",
                "*Function extracted from dataset completion*",
                "",
            ]
        )

        return lines

    def _generate_canonical_solution_section(
        self,
        canonical_solution: str,
        problem_description: str | None = None,
        entry_point: str | None = None,
    ) -> list[str]:
        """Generate canonical solution section with proper function signature

        Args:
            canonical_solution: Canonical solution code
            problem_description: Problem description to extract function signature
            entry_point: Entry point function name

        Returns:
            List of markdown lines for canonical solution section
        """
        lines = ["## Canonical Solution", ""]

        # Extract function signature from problem description
        function_signature = None
        if problem_description:
            function_signature = self._extract_function_signature(
                problem_description, entry_point
            )

        # Combine function signature with canonical solution body
        if function_signature and canonical_solution.strip():
            # Remove the colon from function signature if present
            if function_signature.endswith(":"):
                function_signature = function_signature[:-1]

            # Process canonical solution body with proper indentation
            lines_to_process = canonical_solution.split("\n")

            # Find the minimum indentation (excluding empty lines)
            min_indent = float("inf")
            for line in lines_to_process:
                if line.strip():  # Skip empty lines
                    current_indent = len(line) - len(line.lstrip())
                    min_indent = min(min_indent, current_indent)

            # If no non-empty lines found, set min_indent to 0
            if min_indent == float("inf"):
                min_indent = 0
            else:
                min_indent = int(min_indent)

            # Normalize indentation: remove common leading whitespace and add 4 spaces
            normalized_lines = []
            for line in lines_to_process:
                if line.strip():  # Non-empty line
                    # Remove the minimum common indentation and add 4 spaces
                    normalized_line = "    " + line[min_indent:]
                    normalized_lines.append(normalized_line)
                else:  # Empty line
                    normalized_lines.append(line)

            indented_body = "\n".join(normalized_lines)
            complete_function = f"{function_signature}:\n{indented_body}"

            lines.extend(
                [
                    "```python",
                    complete_function.strip(),
                    "```",
                ]
            )
        else:
            # Fallback to original canonical solution if no function signature found
            lines.extend(
                [
                    "```python",
                    canonical_solution.strip(),
                    "```",
                ]
            )

        lines.extend(
            [
                "*Canonical solution extracted from dataset*",
                "",
            ]
        )

        return lines

    def _generate_content_preview_section(
        self,
        ebt_analysis: EBTAnalysis,
        pbt_analysis: PBTAnalysis,
        humaneval_test_code: str | None = None,
        target_function: str | None = None,
        entry_point: str | None = None,
    ) -> list[str]:
        """Generate content preview section with complete test code

        Args:
            ebt_analysis: EBT analysis results
            pbt_analysis: PBT analysis results
            humaneval_test_code: HumanEval test code string
            target_function: Target function implementation
            entry_point: Entry point function name

        Returns:
            List of markdown lines for content preview section
        """
        lines = ["## Complete Test Code", ""]

        # HumanEval complete code
        if humaneval_test_code:
            lines.extend(["### HumanEval Complete Test Implementation", "```python"])
            lines.extend(humaneval_test_code.split("\n"))
            lines.extend(["```", ""])

        # EBT complete code - using the same approach as _make_generated_ebt_string
        if ebt_analysis.exists and target_function:
            lines.extend(["### EBT Complete Test Implementation", "```python"])

            # Extract EBT code blocks
            ebt_code = extract_code_block(ebt_analysis.content)

            # Build complete EBT code like _make_generated_ebt_string
            complete_ebt_code = join_code_parts(
                REQUIRED_IMPORTS.strip(),
                target_function.strip(),
                ebt_code.strip() if ebt_code else "# No code blocks found in EBT file",
            )

            lines.extend(complete_ebt_code.split("\n"))
            lines.extend(["```", ""])

        # PBT complete code - using the same approach as _make_generated_pbt_string
        if pbt_analysis.exists and target_function and entry_point:
            lines.extend(["### PBT Complete Test Implementation", "```python"])

            # Extract PBT code blocks
            pbt_code = extract_code_block(pbt_analysis.content)

            # Remove entry point function from PBT code like _make_generated_pbt_string
            if pbt_code:
                pbt_code = remove_entry_point_function(pbt_code, entry_point)

            # Build complete PBT code like _make_generated_pbt_string
            complete_pbt_code = join_code_parts(
                REQUIRED_IMPORTS.strip(),
                target_function.strip(),
                pbt_code.strip() if pbt_code else "# No code blocks found in PBT file",
            )

            lines.extend(complete_pbt_code.split("\n"))
            lines.extend(["```", ""])

        return lines

    def _generate_execution_results_section(
        self, execution_results: dict[str, str]
    ) -> list[str]:
        """Generate execution results section

        Args:
            execution_results: Dictionary of test type to result

        Returns:
            List of markdown lines for execution results section
        """
        lines = [
            "## Execution Results",
            "| Test Type | Result | Status |",
            "|-----------|--------|--------|",
        ]

        for test_type, result in execution_results.items():
            status = STATUS_MAP.get(result, "❓ UNKNOWN")
            lines.append(f"| {test_type} | {result} | {status} |")

        lines.append("")
        return lines

    def _generate_statistical_summary_section(
        self, ebt_analysis: EBTAnalysis, pbt_analysis: PBTAnalysis
    ) -> list[str]:
        """Generate statistical summary section

        Args:
            ebt_analysis: EBT analysis results
            pbt_analysis: PBT analysis results

        Returns:
            List of markdown lines for statistical summary section
        """
        lines = ["## Statistical Summary", ""]

        if ebt_analysis.exists and pbt_analysis.exists:
            # Calculate metrics
            ebt_density = (
                ebt_analysis.assertion_count / ebt_analysis.line_count
                if ebt_analysis.line_count > 0
                else 0
            )
            pbt_density = (
                pbt_analysis.test_function_count / pbt_analysis.line_count
                if pbt_analysis.line_count > 0
                else 0
            )
            size_diff_pct = (
                (
                    (ebt_analysis.file_size - pbt_analysis.file_size)
                    / pbt_analysis.file_size
                )
                * 100
                if pbt_analysis.file_size > 0
                else 0
            )
            line_diff_pct = (
                (
                    (pbt_analysis.line_count - ebt_analysis.line_count)
                    / ebt_analysis.line_count
                )
                * 100
                if ebt_analysis.line_count > 0
                else 0
            )

            lines.extend(
                [
                    "### Test Coverage Metrics",
                    f"- **EBT Test Density**: {ebt_density:.3f} assertions per line ({ebt_analysis.assertion_count} assertions / {ebt_analysis.line_count} lines)",
                    f"- **PBT Test Density**: {pbt_density:.3f} functions per line ({pbt_analysis.test_function_count} functions / {pbt_analysis.line_count} lines)",
                    "",
                    "### File Comparison",
                    f"- **Size Difference**: EBT is {size_diff_pct:+.1f}% different ({ebt_analysis.file_size}B vs {pbt_analysis.file_size}B)",
                    f"- **Line Count Difference**: PBT has {line_diff_pct:+.1f}% more lines ({pbt_analysis.line_count} vs {ebt_analysis.line_count})",
                    "",
                ]
            )
        elif ebt_analysis.exists:
            lines.extend(
                [
                    "### Available Metrics (EBT only)",
                    f"- **EBT Test Density**: {ebt_analysis.assertion_count / ebt_analysis.line_count:.3f} assertions per line",
                    f"- **EBT File Size**: {ebt_analysis.file_size}B ({ebt_analysis.line_count} lines)",
                    "",
                ]
            )
        elif pbt_analysis.exists:
            lines.extend(
                [
                    "### Available Metrics (PBT only)",
                    f"- **PBT Test Density**: {pbt_analysis.test_function_count / pbt_analysis.line_count:.3f} functions per line",
                    f"- **PBT File Size**: {pbt_analysis.file_size}B ({pbt_analysis.line_count} lines)",
                    "",
                ]
            )
        else:
            lines.extend(["### No files available for comparison", ""])

        return lines

    def _generate_problem_description_section(
        self, problem_description: str, entry_point: str | None = None
    ) -> list[str]:
        """Generate problem description section

        Args:
            problem_description: Problem description from dataset

        Returns:
            List of markdown lines for problem description section
        """
        lines = ["## Problem Description", ""]

        # Parse the prompt to extract function signature, description, and examples
        function_signature = self._extract_function_signature(
            problem_description, entry_point
        )
        docstring_content = self._extract_docstring_content(
            problem_description, entry_point
        )

        if function_signature:
            lines.extend(
                [
                    "### Function Signature",
                    "```python",
                    function_signature.strip(),
                    "```",
                    "",
                ]
            )

        if docstring_content:
            description, examples = self._parse_docstring(docstring_content)

            if description:
                lines.extend(
                    [
                        "### Description",
                        description.strip(),
                        "",
                    ]
                )

            if examples:
                lines.extend(
                    [
                        "### Examples",
                        "```python",
                        examples.strip(),
                        "```",
                        "",
                    ]
                )

        lines.extend(
            [
                "*Problem extracted from dataset prompt*",
                "",
            ]
        )

        return lines

    def _find_function_definition_line(
        self, prompt: str, entry_point: str
    ) -> str | None:
        """Find the line containing the function definition for the specified entry point

        Args:
            prompt: Problem description prompt
            entry_point: Function name to find

        Returns:
            Line containing the function definition or None if not found
        """
        lines = prompt.split("\n")
        for line in lines:
            if line.strip().startswith("def ") and "(" in line and ")" in line:
                match = re.match(r"\s*def\s+(\w+)\s*\(", line)
                if match and match.group(1) == entry_point:
                    return line.strip()
        return None

    def _extract_function_signature(
        self, prompt: str, entry_point: str | None = None
    ) -> str | None:
        """Extract function signature from prompt

        Args:
            prompt: Problem description prompt
            entry_point: Specific function name to extract (optional)

        Returns:
            Function signature or None if not found
        """
        # If entry_point is specified, find the specific function
        if entry_point:
            return self._find_function_definition_line(prompt, entry_point)

        # Otherwise, return the first function signature found
        lines = prompt.split("\n")
        for line in lines:
            if line.strip().startswith("def ") and "(" in line and ")" in line:
                return line.strip()
        return None

    def _extract_docstring_content(
        self, prompt: str, entry_point: str | None = None
    ) -> str | None:
        """Extract docstring content from prompt

        Args:
            prompt: Problem description prompt
            entry_point: Specific function name to extract docstring from (optional)

        Returns:
            Docstring content or None if not found
        """
        if entry_point:
            # Extract docstring for specific function
            # Pattern to match the specific function and its docstring
            # This pattern captures the function definition and its docstring
            pattern = (
                rf"def\s+{re.escape(entry_point)}\s*\([^)]*\)(?:\s*->\s*[^:]+)?\s*:\s*"
                rf'("""(.*?)"""|\'\'\'(.*?)\'\'\')'
            )

            match = re.search(pattern, prompt, re.DOTALL)
            if match:
                # Return the non-None group (either group 2 for """ or group 3 for ''')
                content = (
                    match.group(2) if match.group(2) is not None else match.group(3)
                )
                return content.strip() if content else None

        # Fallback: Find any docstring between triple quotes (both """ and ''')
        docstring_match = re.search(r'"""(.*?)"""|\'\'\'(.*?)\'\'\'', prompt, re.DOTALL)
        if docstring_match:
            # Return the non-None group (either group 1 for """ or group 2 for ''')
            content = (
                docstring_match.group(1)
                if docstring_match.group(1) is not None
                else docstring_match.group(2)
            )
            return content.strip()
        return None

    def _parse_docstring(self, docstring: str) -> tuple[str | None, str | None]:
        """Parse docstring to separate description and examples

        Args:
            docstring: Docstring content

        Returns:
            Tuple of (description, examples)
        """
        lines = docstring.split("\n")
        description_lines = []
        example_lines = []
        in_examples = False

        for line in lines:
            line = line.strip()
            # Check for different example patterns
            if (
                line.startswith(">>>")
                or line.lower().startswith("examples")
                or line.lower().startswith("example:")
                or (
                    line
                    and "(" in line
                    and ")" in line
                    and ("➞" in line or "=>" in line or "->" in line)
                )
            ):
                in_examples = True
                if not line.lower().startswith(
                    "example"
                ):  # Don't include "Examples" header
                    example_lines.append(line)
            elif in_examples and (
                line.startswith(">>>")
                or line.startswith("...")
                or (
                    line
                    and "(" in line
                    and ")" in line
                    and ("➞" in line or "=>" in line or "->" in line)
                )
                or (line and not line.startswith(">>>"))
            ):
                example_lines.append(line)
            elif not in_examples and line and not line.lower().startswith("example"):
                description_lines.append(line)

        description = "\n".join(description_lines) if description_lines else None
        examples = "\n".join(example_lines) if example_lines else None

        return description, examples
