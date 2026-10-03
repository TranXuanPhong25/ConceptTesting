import contextlib
import io
import json
import os
import re
import signal
import subprocess
import tempfile
import time
import types
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Protocol, cast

from pbteval.constants import (
    HUMANEVAL_PATH,
    HUMANEVAL_PLUS_PATH,
    TEST_EXECUTION_TIMEOUT,
)
from pbteval.core.cache import TestResultCache
from pbteval.utils.logger import get_logger
from pbteval.utils.utils import extract_code_block, safe_read_file

logger = get_logger(__name__)

REQUIRED_IMPORTS = """
from typing import *
"""


def format_assertion_error(error_msg: str) -> str:
    """Format assertion error to show clearer got vs expected information

    Args:
        error_msg: The original assertion error message

    Returns:
        Formatted error message with improved readability
    """
    # If the error message is empty or just whitespace, return as is
    if not error_msg or not error_msg.strip():
        return error_msg

    # Try to extract assertion details for better formatting
    # Look for patterns like "assert x == y" in error message
    if "AssertionError:" in error_msg:
        # Extract the actual error part
        actual_error = error_msg.replace("AssertionError:", "").strip()

        # If there's a custom message after comma, extract it
        if ", " in actual_error and '"' in actual_error:
            parts = actual_error.split(", ", 1)
            if len(parts) == 2 and parts[1].startswith('"') and parts[1].endswith('"'):
                custom_msg = parts[1].strip('"')
                return f"AssertionError: {custom_msg}\nDetails: {parts[0]}"

        # Return formatted version
        if actual_error:
            return f"AssertionError: {actual_error}"

    return error_msg


def format_pytest_error(stdout: str, stderr: str, return_code: int) -> str:
    """Format pytest error output to show clearer failure information

    Args:
        stdout: Pytest stdout output
        stderr: Pytest stderr output
        return_code: Pytest exit code

    Returns:
        Formatted error message with improved readability
    """
    formatted_lines = [f"Pytest failed (exit code {return_code})"]

    if stdout and stdout.strip():
        # Extract key information from pytest output
        lines = stdout.split("\n")
        failure_lines = []

        # Look for assertion failures and failures summary
        in_failure_section = False
        in_short_summary = False

        for line in lines:
            line = line.strip()

            # Mark start of failure sections
            if "FAILURES" in line or "FAILED" in line:
                in_failure_section = True
                failure_lines.append(line)
            elif "short test summary info" in line.lower():
                in_short_summary = True
                failure_lines.append(line)
            elif in_failure_section or in_short_summary:
                # Include failure details
                if line and not line.startswith("="):
                    failure_lines.append(line)
                elif line.startswith("=") and len(line) > 10:
                    # End of section
                    in_failure_section = False
                    in_short_summary = False

            # Also capture assertion errors directly
            if "AssertionError" in line:
                failure_lines.append(line)

        if failure_lines:
            formatted_lines.append("\nFailure Details:")
            formatted_lines.extend(failure_lines)
        else:
            # If no specific failures found, include full stdout
            formatted_lines.append("\nSTDOUT:")
            formatted_lines.append(stdout.strip())

    if stderr and stderr.strip():
        formatted_lines.append("\nSTDERR:")
        formatted_lines.append(stderr.strip())

    return "\n".join(formatted_lines)


def create_detailed_assertion_function() -> str:
    """Create a detailed assertion function that shows got vs expected values"""
    return '''
def detailed_assert(actual, expected, msg=""):
    """Custom assertion function that shows detailed got vs expected information"""
    if actual != expected:
        error_parts = []
        if msg:
            error_parts.append(f"Message: {msg}")
        error_parts.append(f"Got:      {repr(actual)}")
        error_parts.append(f"Expected: {repr(expected)}")
        if hasattr(actual, '__len__') and hasattr(expected, '__len__'):
            try:
                error_parts.append(f"Got length:      {len(actual)}")
                error_parts.append(f"Expected length: {len(expected)}")
            except TypeError:
                pass  # Some objects with __len__ might not support len()
        if type(actual) != type(expected):
            error_parts.append(f"Got type:      {type(actual).__name__}")
            error_parts.append(f"Expected type: {type(expected).__name__}")
        raise AssertionError("\\n".join(error_parts))
    return True
'''


def transform_test_code_for_detailed_assertions(test_code: str) -> str:
    """Transform test code to use detailed assertions for better error reporting

    Args:
        test_code: Original test code with standard assert statements

    Returns:
        Transformed test code with detailed_assert function calls
    """

    # Add the detailed assertion function at the beginning
    transformed_code = create_detailed_assertion_function() + "\n" + test_code

    # Process line by line to handle complex expressions properly
    lines = transformed_code.split("\n")
    result_lines = []

    for line in lines:
        # Skip lines that already have detailed_assert or are part of the function definition
        if (
            "detailed_assert" in line
            or "def detailed_assert" in line
            or line.strip().startswith('"""')
            or line.strip().startswith("'''")
        ):
            result_lines.append(line)
            continue

        # Look for assert statements with safer parsing
        stripped = line.strip()
        if stripped.startswith("assert "):
            try:
                # Try to parse the assert statement safely
                transformed_line = _safe_transform_assert_line(line)
                result_lines.append(transformed_line)
            except Exception:
                # If parsing fails, keep the original line as fallback
                result_lines.append(line)
            continue

        # If we get here, it's not an assert statement
        result_lines.append(line)

    return "\n".join(result_lines)


def _safe_transform_assert_line(line: str) -> str:
    """Safely transform a single assert line to use detailed_assert

    Args:
        line: Line containing an assert statement

    Returns:
        Transformed line using detailed_assert, or original line if parsing fails

    Raises:
        Exception: If parsing fails (caught by caller for fallback)
    """
    stripped = line.strip()
    assert_content = stripped[7:]  # Remove "assert "

    # Handle simple case: assert condition, "message"
    if ", " in assert_content and (
        assert_content.endswith('"') or assert_content.endswith("'")
    ):
        # Find the last comma that's not inside quotes or f-strings
        last_comma = _find_last_comma_outside_quotes(assert_content)
        if last_comma > 0:
            condition_part = assert_content[:last_comma].strip()
            message_part = assert_content[last_comma + 1 :].strip()

            # Try to parse the condition part
            eq_pos = _find_last_equality_outside_quotes(condition_part)
            if eq_pos > 0:
                actual_part = condition_part[:eq_pos].strip()
                expected_part = condition_part[eq_pos + 2 :].strip()

                indent = len(line) - len(line.lstrip())
                return f"{' ' * indent}detailed_assert({actual_part}, {expected_part}, {message_part})"

    # Handle simple case: assert condition
    eq_pos = _find_last_equality_outside_quotes(assert_content)
    if eq_pos > 0:
        actual_part = assert_content[:eq_pos].strip()
        expected_part = assert_content[eq_pos + 2 :].strip()

        indent = len(line) - len(line.lstrip())
        return f"{' ' * indent}detailed_assert({actual_part}, {expected_part})"

    # If we can't parse it, raise an exception to fall back to original
    raise ValueError("Could not parse assert statement")


def _find_last_comma_outside_quotes(text: str) -> int:
    """Find the position of the last comma that's not inside quotes or f-strings

    Args:
        text: Text to search in

    Returns:
        Position of last comma outside quotes, or -1 if not found
    """
    last_comma = -1
    in_quotes = False
    quote_char = None
    in_fstring = False
    brace_depth = 0
    i = 0

    while i < len(text):
        char = text[i]

        if char == "f" and i + 1 < len(text) and text[i + 1] in ['"', "'"]:
            in_fstring = True
            i += 1
            char = text[i]

        if char in ['"', "'"]:
            if not in_quotes:
                in_quotes = True
                quote_char = char
            elif char == quote_char:
                in_quotes = False
                quote_char = None
                in_fstring = False
        elif char == "\\" and in_quotes:
            i += 1  # Skip the next character
        elif in_fstring and char == "{":
            brace_depth += 1
        elif in_fstring and char == "}":
            brace_depth -= 1
        elif not in_quotes and brace_depth == 0 and char == ",":
            last_comma = i

        i += 1

    return last_comma


def _find_last_equality_outside_quotes(text: str) -> int:
    """Find the position of the last == that's not inside quotes or f-strings

    Args:
        text: Text to search in

    Returns:
        Position of last == outside quotes, or -1 if not found
    """
    last_eq_pos = -1
    in_quotes = False
    quote_char = None
    in_fstring = False
    brace_depth = 0
    i = 0

    while i < len(text):
        char = text[i]

        if char == "f" and i + 1 < len(text) and text[i + 1] in ['"', "'"]:
            in_fstring = True
            i += 1
            char = text[i]

        if char in ['"', "'"]:
            if not in_quotes:
                in_quotes = True
                quote_char = char
            elif char == quote_char:
                in_quotes = False
                quote_char = None
                in_fstring = False
        elif char == "\\" and in_quotes:
            i += 1  # Skip the next character
        elif in_fstring and char == "{":
            brace_depth += 1
        elif in_fstring and char == "}":
            brace_depth -= 1
        elif (
            not in_quotes
            and brace_depth == 0
            and char == "="
            and i + 1 < len(text)
            and text[i + 1] == "="
        ):
            last_eq_pos = i

        i += 1

    return last_eq_pos


# Global caches for HumanEval test cases
_humaneval_tests_cache: dict[str, str] | None = None
_humaneval_plus_tests_cache: dict[str, str] | None = None


def generate_humaneval_plus_test_code(
    _test_code: str,
    entry_point: str,
    base_input: list[list[str | int | float | bool]],
    plus_input: list[list[str | int | float | bool]],
    contract: str,
    atol: float,
    canonical_solution: str,
    prompt: str,
) -> str:
    """Generate HumanEval+ test code with all test cases

    Args:
        _test_code: Original test code from dataset (unused)
        entry_point: Function name to test
        base_input: Base test inputs
        plus_input: Extended test inputs
        contract: Contract validation code
        atol: Absolute tolerance for floating point comparisons
        canonical_solution: Canonical solution for computing expected outputs
        prompt: Problem prompt

    Returns:
        Extended test code string with all HumanEval+ tests
    """
    # Parse the original test to understand its structure
    lines = []

    # Add imports
    lines.append("import math")
    lines.append("import numpy as np")
    lines.append("import sys")
    lines.append("")

    # Extract imports and helper functions from prompt and canonical solution
    prompt_lines = prompt.split("\n")
    for line in prompt_lines:
        line_stripped = line.strip()
        # More strict import detection:
        # - Must start with 'import ' or 'from '
        # - For 'from ', must have ' import ' in the line
        if line_stripped.startswith("import ") or (
            line_stripped.startswith("from ") and " import " in line_stripped
        ):
            if line_stripped not in ["import math", "import numpy as np"]:
                lines.append(line)

    # Add any helper functions that might be in the prompt (before the main function)
    in_docstring = False
    in_helper_function = False
    for line in prompt_lines:
        # Track docstrings
        if '"""' in line:
            in_docstring = not in_docstring

        # Detect helper function definitions
        if (
            not in_docstring
            and line.strip().startswith("def ")
            and entry_point not in line
        ):
            in_helper_function = True
            lines.append(line)
        elif in_helper_function:
            # Continue adding lines until we reach the main function or empty line pattern
            if line.strip() == "" and not in_docstring:
                # Check if next non-empty line starts a new function
                continue
            elif line.strip().startswith("def " + entry_point):
                # We've reached the main function, stop
                in_helper_function = False
                break
            else:
                lines.append(line)

    lines.append("")

    # Create canonical function for computing expected outputs
    lines.append("# Canonical solution for computing expected outputs")
    canonical_func = make_canonical_function(prompt, canonical_solution, entry_point)
    # Rename the canonical function to avoid conflicts
    canonical_func = canonical_func.replace(
        f"def {entry_point}(", f"def _canonical_{entry_point}("
    )
    lines.append(canonical_func)
    lines.append("")

    # Combine all test inputs
    all_inputs = base_input + plus_input

    # Build the check function
    lines.append("def check(candidate):")

    # Add any necessary helper functions from contract inside check
    if contract and "poly(" in contract:
        lines.append("    def poly(xs, x):")
        lines.append(
            "        return sum([coeff * math.pow(x, i) for i, coeff in enumerate(xs)])"
        )
        lines.append("")

    # Generate test cases
    for i, test_input in enumerate(all_inputs):
        if isinstance(test_input, list) and len(test_input) > 0:
            # Convert input to proper format
            args_str = ", ".join(repr(arg) for arg in test_input)

            lines.append(f"    # Test case {i}")
            lines.append("    try:")

            # Note: Allowing all special_factorial tests to run with extended timeout

            # Compute expected output using canonical solution
            lines.append(f"        expected = _canonical_{entry_point}({args_str})")
            lines.append(f"        result = candidate({args_str})")

            # Compare results with appropriate tolerance
            if atol > 0:
                lines.append(
                    "        if isinstance(result, (int, float)) and isinstance(expected, (int, float)):"
                )
                lines.append(
                    f"            assert abs(result - expected) <= {atol}, f'Failed test {i}: got {{result}}, expected {{expected}}'"
                )
                lines.append(
                    "        elif isinstance(result, list) and isinstance(expected, list) and len(result) == len(expected):"
                )
                lines.append(
                    "            for j, (r, e) in enumerate(zip(result, expected)):"
                )
                lines.append(
                    "                if isinstance(r, (int, float)) and isinstance(e, (int, float)):"
                )
                lines.append(
                    f"                    assert abs(r - e) <= {atol}, f'Failed test {i} at index {{j}}: got {{r}}, expected {{e}}'"
                )
                lines.append("                else:")
                lines.append(
                    f"                    assert r == e, f'Failed test {i} at index {{j}}: got {{r}}, expected {{e}}'"
                )
                lines.append("        else:")
                lines.append(
                    f"            assert result == expected, f'Failed test {i}: got {{result}}, expected {{expected}}'"
                )
            else:
                lines.append(
                    f"        assert result == expected, f'Failed test {i}: got {{result}}, expected {{expected}}'"
                )

            lines.append("    except Exception as e:")
            lines.append(
                f"        raise AssertionError(f'Test {i} raised exception: {{type(e).__name__}}: {{e}}')"
            )

    # Ensure at least one test exists
    if not all_inputs:
        lines.append("    pass  # No test inputs provided")

    return "\n".join(lines)


def load_humaneval_plus_tests() -> dict[str, str]:
    """Load HumanEval+ test cases mapped by task_id

    Returns:
        Dictionary mapping task_id to test code
    """
    global _humaneval_plus_tests_cache

    if _humaneval_plus_tests_cache is not None:
        return _humaneval_plus_tests_cache

    if not HUMANEVAL_PLUS_PATH.exists():
        logger.warning(f"HumanEval+ dataset not found at {HUMANEVAL_PLUS_PATH}")
        return {}

    tests_map = {}

    try:
        for line in HUMANEVAL_PLUS_PATH.read_text().splitlines():
            if line.strip():
                item = json.loads(line)
                task_id = item.get("task_id")

                # Extract all necessary fields for HumanEval+ test generation
                entry_point = item.get("entry_point")
                base_input = item.get("base_input", [])
                plus_input = item.get("plus_input", [])
                contract = item.get("contract", "")
                atol = item.get("atol", 0.0)
                canonical_solution = item.get("canonical_solution", "")
                prompt = item.get("prompt", "")
                test_code = item.get("test", "")

                if task_id and entry_point and (base_input or plus_input):
                    # Generate proper HumanEval+ test code with all test cases
                    generated_test = generate_humaneval_plus_test_code(
                        _test_code=test_code,
                        entry_point=entry_point,
                        base_input=base_input,
                        plus_input=plus_input,
                        contract=contract,
                        atol=atol,
                        canonical_solution=canonical_solution,
                        prompt=prompt,
                    )
                    tests_map[task_id] = generated_test
                    total_tests = len(base_input) + len(plus_input)
                    logger.debug(
                        f"Generated HumanEval+ test for {task_id} with {total_tests} test cases"
                    )
                elif task_id and test_code:
                    # Fallback to standard test if no inputs available
                    tests_map[task_id] = test_code

    except Exception as e:
        logger.error(f"Error loading HumanEval+ tests: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return {}

    _humaneval_plus_tests_cache = tests_map
    logger.debug(f"Loaded {len(tests_map)} HumanEval+ test suites")
    return tests_map


def load_humaneval_tests() -> dict[str, str]:
    """Load standard HumanEval test cases mapped by task_id

    Returns:
        Dictionary mapping task_id to test code
    """
    global _humaneval_tests_cache

    if _humaneval_tests_cache is not None:
        return _humaneval_tests_cache

    if not HUMANEVAL_PATH.exists():
        logger.warning(f"HumanEval dataset not found at {HUMANEVAL_PATH}")
        return {}

    tests_map = {}
    try:
        for line in HUMANEVAL_PATH.read_text().splitlines():
            if line.strip():
                item = json.loads(line)
                task_id = item.get("task_id")
                test_code = item.get("test")
                if task_id and test_code:
                    tests_map[task_id] = test_code
    except Exception as e:
        logger.error(f"Error loading HumanEval tests: {e}")
        return {}

    _humaneval_tests_cache = tests_map
    logger.debug(f"Loaded {len(tests_map)} HumanEval test cases")
    return tests_map


@contextmanager
def timeout(seconds: int) -> Generator[None]:
    """Context manager for setting a timeout on code execution

    Args:
        seconds: Timeout duration in seconds

    Raises:
        TimeoutError: If the code execution exceeds the timeout
    """

    def timeout_handler(_signum: int, _frame: types.FrameType | None) -> None:
        raise TimeoutError("Code execution timed out")

    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


class TestRunner(Protocol):
    """Protocol for objects that can run tests"""

    task_id: str
    use_plus_tests: bool
    completion: str
    entry_point: str

    def run_humaneval_tests(self) -> bool:
        """Run HumanEval tests"""
        ...

    def run_generated_ebt(self, ebt_path: Path) -> bool:
        """Run generated EBT"""
        ...

    def run_generated_pbt(self, pbt_path: Path) -> bool:
        """Run generated PBT"""
        ...

    def is_ebt_passed(self, ebt_path: Path | None = None) -> bool:
        """Whether the generated EBT passed the test"""
        ...

    def is_pbt_passed(self, pbt_path: Path | None = None) -> bool:
        """Whether the generated PBT passed the test"""
        ...

    def print_generated_ebt_string(self, ebt_path: Path) -> None:
        """Print generated EBT string"""
        ...

    def print_generated_pbt_string(self, pbt_path: Path) -> None:
        """Print generated PBT string"""
        ...

    def was_last_result_cached(self) -> bool:
        """Check if the last test execution was from cache"""
        ...

    def _make_humaneval_tests_string(self) -> str:
        """Create a string to execute HumanEval tests"""
        ...

    def save_humaneval_test_code(
        self,
        test_code: str,
        task_id: str,
        model: str,
        source_type: str = "agentcoder",
        dataset_type: str | None = None,
        test_type: str = "standard",
    ) -> bool:
        """Save HumanEval test code to file"""
        ...

    def save_ebt_test_code(
        self,
        test_code: str,
        task_id: str,
        model: str,
        use_canonical: bool = False,
    ) -> bool:
        """Save EBT test code to file"""
        ...

    def save_pbt_test_code(
        self,
        test_code: str,
        task_id: str,
        model: str,
        use_canonical: bool = False,
    ) -> bool:
        """Save PBT test code to file"""
        ...

    def get_last_error_info(self) -> str | None:
        """Get the last error information from test execution"""
        ...

    def get_last_execution_time(self) -> float | None:
        """Get the last execution time in seconds from test execution"""
        ...


def get_function_pattern(entry_point: str) -> str:
    """Generate regex pattern to match a function definition

    Args:
        entry_point: The function name to match

    Returns:
        Regex pattern string that matches the function definition
    """
    return rf"def\s+{re.escape(entry_point)}\s*\([^)]*\)(?:\s*->\s*[^:]+)?\s*:.*?(?=\n\s*def|\n\s*class|\n\s*@given|\Z)"


def _extract_imports(prompt: str) -> list[str]:
    """Extract all import statements from the prompt

    Args:
        prompt: The problem prompt containing potential import statements

    Returns:
        List of import statements found in the prompt
    """
    import_lines = []
    for line in prompt.strip().split("\n"):
        line = line.strip()
        # More strict import detection:
        # - Must start with 'import ' or 'from '
        # - For 'from ', must have ' import ' in the line
        if line.startswith("import ") or (
            line.startswith("from ") and " import " in line
        ):
            import_lines.append(line)
    return import_lines


def _extract_helper_functions(prompt: str, entry_point: str) -> str:
    """Extract all function definitions that appear before the main function

    Args:
        prompt: The problem prompt containing function definitions
        entry_point: The main function name to stop extraction at

    Returns:
        String containing all helper function definitions
    """
    lines = prompt.strip().split("\n")
    helper_functions = []
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        # Skip empty lines and imports
        if not line or line.startswith("import ") or line.startswith("from "):
            i += 1
            continue

        # Check if this is a function definition
        if line.startswith("def "):
            # Extract function name
            func_name_match = re.match(r"def\s+(\w+)\s*\(", line)
            if func_name_match:
                func_name = func_name_match.group(1)

                # If this is the main function, stop extraction
                if func_name == entry_point:
                    break

                # This is a helper function, extract it completely
                func_lines = [lines[i]]
                i += 1

                # Extract the complete function including docstring and body
                while i < len(lines):
                    line = lines[i]
                    # If we hit a non-indented line that's not empty, function is complete
                    if (
                        line.strip()
                        and not line.startswith(" ")
                        and not line.startswith("\t")
                    ):
                        break
                    func_lines.append(line)
                    i += 1

                helper_functions.extend(func_lines)
                helper_functions.append("")  # Add blank line between functions
            else:
                i += 1
        else:
            i += 1

    return "\n".join(helper_functions).rstrip()


def make_canonical_function(
    prompt: str, canonical_solution: str, entry_point: str
) -> str:
    """Create canonical function from prompt and canonical_solution

    Args:
        prompt: The problem prompt containing function signature
        canonical_solution: The canonical solution code
        entry_point: The function name

    Returns:
        Complete function code with signature and implementation

    Raises:
        ValueError: If function definition cannot be found in prompt
    """
    # Create a robust regex pattern that matches:
    # 1. Function definition with the entry point name
    # 2. Optional parameters (including multi-line)
    # 3. Optional return type annotation
    # 4. Function body start (:)
    # 5. Optional docstring with various delimiters (""", ''', ", ')

    # Escape the entry point name for regex
    escaped_entry_point = re.escape(entry_point)

    # Pattern explanation:
    # - def\s+ : 'def' keyword followed by whitespace
    # - {escaped_entry_point} : the function name
    # - \s*\( : optional whitespace and opening parenthesis
    # - [^)]* : any characters except closing parenthesis (parameters)
    # - \) : closing parenthesis
    # - (?:\s*->\s*[^:]+)? : optional return type annotation
    # - \s*: : colon to start function body
    # - (?:\s*(?:\"\"\".*?\"\"\"|'''.*?'''|\".*?\"|'.*?'))? : optional docstring
    pattern = (
        rf"(def\s+{escaped_entry_point}\s*\([^)]*\)"
        rf"(?:\s*->\s*[^:]+)?\s*:"
        rf"(?:\s*(?:\"\"\".*?\"\"\"|'''.*?'''|\"[^\"]*\"|'[^']*'))?)"
    )

    # Search for the pattern in the prompt
    match = re.search(pattern, prompt, re.DOTALL)

    if not match:
        raise ValueError(
            f"Could not find function definition for {entry_point} in prompt"
        )

    # Extract the matched function signature and docstring
    func_signature = match.group(1).strip()

    # Extract imports and helper functions from prompt
    imports = _extract_imports(prompt)
    # Also extract imports from canonical_solution
    canonical_imports = _extract_imports(canonical_solution)
    # Combine and deduplicate imports
    all_imports = list(dict.fromkeys(imports + canonical_imports))
    helper_functions = _extract_helper_functions(prompt, entry_point)

    # Build the complete function code
    code_parts = []

    # Add imports at the top
    if all_imports:
        code_parts.extend(all_imports)
        code_parts.append("")  # Add blank line after imports

    # Add helper functions
    if helper_functions:
        code_parts.append(helper_functions)
        code_parts.append("")  # Add blank line after helper functions

    # Remove import statements from canonical_solution since they're now at the top
    cleaned_canonical_solution = "\n".join(
        line
        for line in canonical_solution.split("\n")
        if not (line.strip().startswith("import ") or line.strip().startswith("from "))
    )

    # Add main function with cleaned canonical solution
    code_parts.append(f"{func_signature}\n{cleaned_canonical_solution}")

    return "\n".join(code_parts)


class TestExecutionMixin:
    """Mixin class providing test execution functionality"""

    # Type declarations for attributes expected from classes using this mixin
    completion: str
    entry_point: str

    def __init__(self) -> None:
        """Initialize test execution mixin"""
        self._cache = TestResultCache()
        self.use_plus_tests = False
        self._last_cache_hit = False
        self._last_error_info: str | None = None
        self._last_execution_time: float | None = None

    def _remove_entry_point_function(self, code: str, entry_point: str) -> str:
        """Remove entry point function definition from code"""
        pattern = get_function_pattern(entry_point)
        return re.sub(pattern, "", code, flags=re.DOTALL)

    def _join_code_parts(self, *parts: str) -> str:
        """Join code parts with newlines, filtering out empty parts"""
        return "\n".join(part for part in parts if part)

    def _get_test_code(self, task_id: str, default_test: str) -> str:
        """Get test code, using HumanEval+ or standard HumanEval tests based on use_plus_tests flag"""
        if self.use_plus_tests:
            plus_tests = load_humaneval_plus_tests()
            return plus_tests.get(task_id, default_test)
        else:
            # Use standard HumanEval tests instead of default_test
            humaneval_tests = load_humaneval_tests()
            return humaneval_tests.get(task_id, default_test)

    def _execute_code(self, code_string: str) -> bool:
        """Execute code string and handle exceptions"""
        self._last_error_info = None
        self._last_execution_time = None
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        start_time = time.time()
        try:
            # Redirect output to capture any print statements or error details
            with (
                contextlib.redirect_stdout(stdout_capture),
                contextlib.redirect_stderr(stderr_capture),
                timeout(TEST_EXECUTION_TIMEOUT),
            ):
                exec(code_string, globals())
            self._last_execution_time = time.time() - start_time
            return True
        except TimeoutError:
            self._last_execution_time = time.time() - start_time
            self._last_error_info = "Execution timed out"
            logger.debug("EBT execution timed out")
            return False
        except AssertionError as e:
            # Enhanced assertion error handling to show more details
            error_msg = str(e)
            stdout_content = stdout_capture.getvalue()
            stderr_content = stderr_capture.getvalue()

            # Format detailed error information using the new formatter
            formatted_error = format_assertion_error(f"AssertionError: {error_msg}")

            if stdout_content.strip():
                formatted_error += f"\nSTDOUT:\n{stdout_content.strip()}"
            if stderr_content.strip():
                formatted_error += f"\nSTDERR:\n{stderr_content.strip()}"

            self._last_error_info = formatted_error
            self._last_execution_time = time.time() - start_time
            logger.debug(f"AssertionError: {error_msg}")
            return False
        except Exception as e:
            # Enhanced general exception handling
            error_msg = f"{type(e).__name__}: {e}"
            stdout_content = stdout_capture.getvalue()
            stderr_content = stderr_capture.getvalue()

            detailed_error = error_msg
            if stdout_content.strip():
                detailed_error += f"\nSTDOUT:\n{stdout_content.strip()}"
            if stderr_content.strip():
                detailed_error += f"\nSTDERR:\n{stderr_content.strip()}"

            self._last_error_info = detailed_error
            self._last_execution_time = time.time() - start_time
            logger.debug(f"{type(e).__name__}: {e}")
            return False

    def _execute_code_with_pytest(self, code_string: str) -> bool:
        """Execute PBT code using pytest"""
        self._last_error_info = None
        self._last_execution_time = None
        start_time = time.time()
        try:
            # Create a temporary file with the PBT code
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False
            ) as temp_file:
                temp_file.write(code_string)
                temp_file_path = temp_file.name

            # Set up environment with Hypothesis health check suppression
            test_env = {
                **os.environ,
                "HYPOTHESIS_SUPPRESS_HEALTH_CHECK": "filter_too_much,too_slow,data_too_large,function_scoped_fixture",
            }

            logger.debug(
                f"Running pytest with env HYPOTHESIS_SUPPRESS_HEALTH_CHECK={test_env.get('HYPOTHESIS_SUPPRESS_HEALTH_CHECK')}"
            )

            # Run pytest on the temporary file with more detailed output
            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "pytest",
                    temp_file_path,
                    "-v",
                    "--tb=long",
                    "--no-header",
                    "--no-summary",
                    "--showlocals",
                ],
                env=test_env,
                capture_output=True,
                text=True,
                timeout=TEST_EXECUTION_TIMEOUT,  # 10 second timeout
            )

            # Log pytest execution results for debugging
            logger.debug(f"Pytest return code: {result.returncode}")
            if result.stdout:
                logger.debug(f"Pytest stdout:\n{result.stdout}")
            if result.stderr:
                logger.debug(f"Pytest stderr:\n{result.stderr}")

            # Clean up temporary file
            Path(temp_file_path).unlink(missing_ok=True)

            # Record execution time
            self._last_execution_time = time.time() - start_time

            # Capture error info if pytest failed
            if result.returncode != 0:
                self._last_error_info = format_pytest_error(
                    result.stdout or "", result.stderr or "", result.returncode
                )

            # Return True if pytest succeeded (exit code 0)
            return result.returncode == 0

        except subprocess.TimeoutExpired:
            self._last_execution_time = time.time() - start_time
            self._last_error_info = "PBT execution timed out"
            logger.debug("PBT execution timed out")
            return False
        except Exception as e:
            self._last_execution_time = time.time() - start_time
            self._last_error_info = f"PBT execution error: {type(e).__name__}: {e}"
            logger.debug(f"PBT execution error: {type(e).__name__}: {e}")
            return False

    def run_humaneval_tests(self) -> bool:
        """Execute HumanEval tests"""
        return self._execute_code(self._make_humaneval_tests_string())

    def run_generated_ebt(self, ebt_path: Path) -> bool:
        """Execute generated EBT with caching"""
        source_code = self._get_source_code()

        # Check cache first
        cached_result = self._cache.get_cached_result_with_validation(
            ebt_path, source_code, "EBT"
        )
        if cached_result is not None:
            result, cached_error_info, cached_execution_time = cached_result
            logger.debug(f"Cache hit for EBT {ebt_path.name}")
            self._last_cache_hit = True
            # Store cached error info and execution time for retrieval by TestExecutionHandler
            self._last_error_info = cached_error_info
            self._last_execution_time = cached_execution_time
            return result

        # Execute test and cache result
        result = self._execute_code(self._make_generated_ebt_string(ebt_path))
        # Get current error info and execution time to cache
        error_info = self._last_error_info
        execution_time = self._last_execution_time
        self._cache.cache_result_with_metadata(
            ebt_path, source_code, "EBT", result, error_info, execution_time
        )
        logger.debug(f"Cache miss for EBT {ebt_path.name}, result cached")
        self._last_cache_hit = False
        return result

    def run_generated_pbt(self, pbt_path: Path) -> bool:
        """Execute generated PBT with caching"""
        source_code = self._get_source_code()

        # Check cache first
        cached_result = self._cache.get_cached_result_with_validation(
            pbt_path, source_code, "PBT"
        )
        if cached_result is not None:
            result, cached_error_info, cached_execution_time = cached_result
            logger.debug(f"Cache hit for PBT {pbt_path.name}")
            self._last_cache_hit = True
            # Store cached error info and execution time for retrieval by TestExecutionHandler
            self._last_error_info = cached_error_info
            self._last_execution_time = cached_execution_time
            return result

        # Execute test and cache result
        result = self._execute_code_with_pytest(
            self._make_generated_pbt_string(pbt_path)
        )
        # Get current error info and execution time to cache
        error_info = self._last_error_info
        execution_time = self._last_execution_time
        self._cache.cache_result_with_metadata(
            pbt_path, source_code, "PBT", result, error_info, execution_time
        )
        logger.debug(f"Cache miss for PBT {pbt_path.name}, result cached")
        self._last_cache_hit = False
        return result

    def is_ebt_passed(self, ebt_path: Path | None = None) -> bool:
        """Whether the generated EBT passed the test"""
        if ebt_path is None:
            # Use a default path or handle appropriately
            return False
        return self.run_generated_ebt(ebt_path)

    def is_pbt_passed(self, pbt_path: Path | None = None) -> bool:
        """Whether the generated PBT passed the test"""
        if pbt_path is None:
            # Use a default path or handle appropriately
            return False
        return self.run_generated_pbt(pbt_path)

    def print_humaneval_tests_string(self) -> None:
        """Print HumanEval tests string"""
        logger.debug(self._make_humaneval_tests_string())

    def print_generated_ebt_string(self, ebt_path: Path) -> None:
        """Print generated EBT string"""
        logger.debug(self._make_generated_ebt_string(ebt_path))

    def print_generated_pbt_string(self, pbt_path: Path) -> None:
        """Print generated PBT string"""
        logger.debug(self._make_generated_pbt_string(pbt_path))

    def was_last_result_cached(self) -> bool:
        """Check if the last test execution was from cache"""
        return getattr(self, "_last_cache_hit", False)

    def get_last_error_info(self) -> str | None:
        """Get the last error information from test execution"""
        return getattr(self, "_last_error_info", None)

    def get_last_execution_time(self) -> float | None:
        """Get the last execution time in seconds from test execution"""
        return getattr(self, "_last_execution_time", None)

    def get_humaneval_test_output_path(
        self,
        task_id: str,
        model: str,
        source_type: str = "agentcoder",
        dataset_type: str | None = None,
        test_type: str = "standard",
    ) -> Path:
        """Generate output path for HumanEval test code files

        Args:
            task_id: Task ID (e.g., "HumanEval/0")
            model: Model name (e.g., "gpt-4o-mini")
            source_type: "agentcoder" or "canonical"
            dataset_type: "standard" or "plus" (only for canonical)
            test_type: "standard" or "plus" (based on use_plus_tests flag)

        Returns:
            Path object for the output file
        """
        # Normalize task ID for filename
        safe_task_id = task_id.replace("/", "_")

        # Normalize model name (replace hyphens with underscores)
        safe_model = model.replace("-", "_")

        # Determine directory structure based on source type
        if source_type == "canonical" and dataset_type:
            # For canonical: source_type/dataset_type_test_type/model/
            subdir = f"{dataset_type}_{test_type}"
        else:
            # For agentcoder: source_type/test_type/model/
            subdir = test_type

        # Build full path
        from pbteval.constants import OUTPUT_BASE_DIR

        output_dir = (
            OUTPUT_BASE_DIR / "humaneval_tests" / source_type / subdir / safe_model
        )
        output_path = output_dir / f"{safe_task_id}.py"

        return output_path

    def save_humaneval_test_code(
        self,
        test_code: str,
        task_id: str,
        model: str,
        source_type: str = "agentcoder",
        dataset_type: str | None = None,
        test_type: str = "standard",
    ) -> bool:
        """Save HumanEval test code to file

        Args:
            test_code: The test code to save
            task_id: Task ID (e.g., "HumanEval/0")
            model: Model name
            source_type: "agentcoder" or "canonical"
            dataset_type: "standard" or "plus" (only for canonical)
            test_type: "standard" or "plus"

        Returns:
            True if saved successfully, False otherwise
        """
        from datetime import datetime

        from pbteval.utils.utils import safe_write_file

        # Get output path
        output_path = self.get_humaneval_test_output_path(
            task_id, model, source_type, dataset_type, test_type
        )

        # Create metadata header
        metadata_lines = [
            "# Generated HumanEval test code",
            f"# Task ID: {task_id}",
            f"# Source Type: {source_type}",
        ]
        if dataset_type and source_type == "canonical":
            metadata_lines.append(f"# Dataset Type: {dataset_type}")
        metadata_lines.extend(
            [
                f"# Test Type: {test_type}",
                f"# Model: {model}",
                f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "",
            ]
        )

        # Combine metadata and test code
        full_content = "\n".join(metadata_lines) + test_code

        # Save to file
        success = safe_write_file(output_path, full_content)

        if success:
            logger.debug(f"Saved test code to {output_path}")
        else:
            logger.error(f"Failed to save test code to {output_path}")

        return success

    def save_ebt_test_code(
        self,
        test_code: str,
        task_id: str,
        model: str,
        use_canonical: bool = False,
    ) -> bool:
        """Save complete executable EBT test code to file

        Args:
            test_code: The generated test code (without imports and function implementation)
            task_id: Task ID (e.g., "HumanEval/0")
            model: Model name
            use_canonical: Whether using canonical solutions

        Returns:
            True if saved successfully, False otherwise
        """
        from datetime import datetime

        from pbteval.constants import OUTPUT_BASE_DIR
        from pbteval.utils.utils import safe_write_file

        # Create output directory structure
        safe_model = model.replace("-", "_")
        safe_task_id = task_id.replace("/", "_")

        output_dir = OUTPUT_BASE_DIR / "ebt_tests" / safe_model
        output_dir.mkdir(parents=True, exist_ok=True)

        output_path = output_dir / f"{safe_task_id}.py"

        # Create metadata header
        metadata_lines = [
            "# Complete executable EBT test code",
            f"# Task ID: {task_id}",
            f"# Model: {model}",
            f"# Canonical: {use_canonical}",
            f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
        ]

        # Construct the complete executable test code
        # This mirrors the logic in _make_generated_ebt_string
        complete_code_parts = [
            REQUIRED_IMPORTS.strip(),
            "",
            "# Function implementation",
        ]

        # Get the function implementation
        if use_canonical and hasattr(self, "_make_canonical_function"):
            # Use canonical solution
            complete_code_parts.append(self._make_canonical_function())
        else:
            # Use completion
            complete_code_parts.append(self.completion)

        complete_code_parts.extend(["", "# Test code", test_code])

        # Combine all parts
        complete_test_code = "\n".join(complete_code_parts)
        full_content = "\n".join(metadata_lines) + complete_test_code

        # Save to file
        success = safe_write_file(output_path, full_content)

        if success:
            logger.debug(f"Saved complete EBT test code to {output_path}")
        else:
            logger.error(f"Failed to save EBT test code to {output_path}")

        return success

    def save_pbt_test_code(
        self,
        test_code: str,
        task_id: str,
        model: str,
        use_canonical: bool = False,
    ) -> bool:
        """Save complete executable PBT test code to file

        Args:
            test_code: The generated test code (without imports and function implementation)
            task_id: Task ID (e.g., "HumanEval/0")
            model: Model name
            use_canonical: Whether using canonical solutions

        Returns:
            True if saved successfully, False otherwise
        """
        from datetime import datetime

        from pbteval.constants import OUTPUT_BASE_DIR
        from pbteval.utils.utils import safe_write_file

        # Create output directory structure
        safe_model = model.replace("-", "_")
        safe_task_id = task_id.replace("/", "_")

        output_dir = OUTPUT_BASE_DIR / "pbt_tests" / safe_model
        output_dir.mkdir(parents=True, exist_ok=True)

        output_path = output_dir / f"{safe_task_id}.py"

        # Create metadata header
        metadata_lines = [
            "# Complete executable PBT test code",
            f"# Task ID: {task_id}",
            f"# Model: {model}",
            f"# Canonical: {use_canonical}",
            f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
        ]

        # Construct the complete executable test code
        # This mirrors the logic in _make_generated_pbt_string
        complete_code_parts = [
            REQUIRED_IMPORTS.strip(),
            "",
            "# Function implementation",
        ]

        # Get the function implementation
        if use_canonical and hasattr(self, "_make_canonical_function"):
            # Use canonical solution
            complete_code_parts.append(self._make_canonical_function())
        else:
            # Use completion
            complete_code_parts.append(self.completion)

        # For PBT, we need to remove the entry point function from test code
        # This is done in _make_generated_pbt_string using _remove_entry_point_function
        processed_test_code = self._remove_entry_point_function(
            test_code, self.entry_point
        )

        complete_code_parts.extend(["", "# Property-based tests", processed_test_code])

        # Combine all parts
        complete_test_code = "\n".join(complete_code_parts)
        full_content = "\n".join(metadata_lines) + complete_test_code

        # Save to file
        success = safe_write_file(output_path, full_content)

        if success:
            logger.debug(f"Saved complete PBT test code to {output_path}")
        else:
            logger.error(f"Failed to save PBT test code to {output_path}")

        return success

    # Abstract methods that must be implemented by classes using this mixin
    def _make_humaneval_tests_string(self) -> str:
        """Create a string to execute HumanEval tests"""
        raise NotImplementedError

    def _make_generated_ebt_string(self, ebt_path: Path) -> str:
        """Create a string to execute generated EBT"""
        raise NotImplementedError

    def _make_generated_pbt_string(self, pbt_path: Path) -> str:
        """Create a string to execute generated PBT"""
        raise NotImplementedError

    def _get_source_code(self) -> str:
        """Get source code for cache key generation"""
        raise NotImplementedError


@dataclass
class UsageInfo:
    """Information about API usage and costs for a generation request."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    model: str
    prompt_cost: float = 0.0
    completion_cost: float = 0.0
    total_cost: float = 0.0

    def __post_init__(self) -> None:
        """Calculate total cost if not provided."""
        if self.total_cost == 0.0:
            self.total_cost = self.prompt_cost + self.completion_cost


@dataclass
class JsonData(TestExecutionMixin):
    task_id: str
    prompt: str
    canonical_solution: str
    test: str
    entry_point: str
    completion_list: list[str]
    test_case_list: list[str]
    full_code: str
    completion: str
    need_reproduce: bool | None = None
    idx: int | None = None
    max_correct: int | None = None

    def __post_init__(self) -> None:
        """Initialize cache after dataclass initialization"""
        super().__init__()

    def _make_humaneval_tests_string(self) -> str:
        """Create a string to execute HumanEval test cases"""
        test_code = self._get_test_code(self.task_id, self.test)
        return self._join_code_parts(
            REQUIRED_IMPORTS,
            self.completion,
            test_code,
            f"check({self.entry_point})",
        )

    def _make_generated_ebt_string(self, ebt_path: Path) -> str:
        """Create a string to execute generated EBT"""
        ebt_code = extract_code_block(safe_read_file(ebt_path))

        # Transform the test code to use detailed assertions for better error reporting
        transformed_ebt_code = transform_test_code_for_detailed_assertions(ebt_code)

        return self._join_code_parts(
            REQUIRED_IMPORTS,
            self.completion,
            transformed_ebt_code,
        )

    def _make_generated_pbt_string(self, pbt_path: Path) -> str:
        """Create a string to execute generated PBT"""
        pbt_code = extract_code_block(safe_read_file(pbt_path))
        pbt_code = self._remove_entry_point_function(pbt_code, self.entry_point)
        return self._join_code_parts(
            REQUIRED_IMPORTS,
            self.completion,
            pbt_code,
        )

    def _get_source_code(self) -> str:
        """Get source code for cache key generation"""
        return self.completion


@dataclass
class JsonDataCanonical(JsonData):
    """JsonData variant that uses canonical solution instead of completion for EBT execution"""

    def _make_humaneval_tests_string(self) -> str:
        """Create a string to execute HumanEval test cases with canonical solution"""
        canonical_function = self._make_canonical_function()
        test_code = self._get_test_code(self.task_id, self.test)
        return self._join_code_parts(
            REQUIRED_IMPORTS,
            canonical_function,
            test_code,
            f"check({self.entry_point})",
        )

    def _make_canonical_function(self) -> str:
        """Create canonical function from prompt and canonical_solution"""
        return make_canonical_function(
            self.prompt, self.canonical_solution, self.entry_point
        )

    def _make_generated_ebt_string(self, ebt_path: Path) -> str:
        """Create a string to execute generated EBT with canonical solution"""
        ebt_code = extract_code_block(safe_read_file(ebt_path))
        canonical_function = self._make_canonical_function()

        # Transform the test code to use detailed assertions for better error reporting
        transformed_ebt_code = transform_test_code_for_detailed_assertions(ebt_code)

        return self._join_code_parts(
            REQUIRED_IMPORTS,
            canonical_function,
            transformed_ebt_code,
        )

    def _get_source_code(self) -> str:
        """Get canonical solution for cache key generation"""
        return self.canonical_solution


@dataclass
class JsonlDataHumanEvalPlus(TestExecutionMixin):
    """HumanEval+ dataset variant for JSONL format"""

    task_id: str
    prompt: str
    entry_point: str
    canonical_solution: str
    test: str
    # Optional fields for GitHub HumanEval+ format compatibility
    contract: str = ""
    base_input: list[str] = field(default_factory=list)
    atol: float = 0.0
    plus_input: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Initialize cache after dataclass initialization"""
        super().__init__()

    def _make_canonical_function(self) -> str:
        """Create canonical function from prompt and canonical_solution"""
        return make_canonical_function(
            self.prompt, self.canonical_solution, self.entry_point
        )

    def _make_humaneval_tests_string(self) -> str:
        """Create a string to execute HumanEval tests"""
        canonical_function = self._make_canonical_function()
        test_code = self._get_test_code(self.task_id, self.test)
        return self._join_code_parts(
            REQUIRED_IMPORTS,
            canonical_function,
            test_code,
            f"check({self.entry_point})",
        )

    def _make_generated_ebt_string(self, ebt_path: Path) -> str:
        """Create a string to execute generated EBT"""
        ebt_code = extract_code_block(safe_read_file(ebt_path))
        canonical_function = self._make_canonical_function()

        # Transform the test code to use detailed assertions for better error reporting
        transformed_ebt_code = transform_test_code_for_detailed_assertions(ebt_code)

        return self._join_code_parts(
            REQUIRED_IMPORTS,
            canonical_function,
            transformed_ebt_code,
        )

    def _make_generated_pbt_string(self, pbt_path: Path) -> str:
        """Create a string to execute generated PBT"""
        pbt_code = extract_code_block(safe_read_file(pbt_path))
        pbt_code = self._remove_entry_point_function(pbt_code, self.entry_point)
        canonical_function = self._make_canonical_function()
        return self._join_code_parts(
            REQUIRED_IMPORTS,
            canonical_function,
            pbt_code,
        )

    def _get_source_code(self) -> str:
        """Get canonical solution for cache key generation"""
        return self.canonical_solution


def extract_dataset(dataset_path: Path) -> list[TestRunner]:
    """
    Load dataset from specified path and convert to appropriate data type.

    Args:
        dataset_path: Path to the dataset file

    Returns:
        list[TestRunner]: List of loaded data

    Raises:
        ValueError: If file extension is not supported
        FileNotFoundError: If file does not exist
    """
    # Import here to avoid circular import

    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset file not found: {dataset_path}")

    if dataset_path.suffix == ".json":
        with dataset_path.open("r") as f:
            return cast(list[TestRunner], [JsonData(**item) for item in json.load(f)])
    elif dataset_path.suffix == ".jsonl":
        # Check if this is HumanEval+ dataset
        if dataset_path == HUMANEVAL_PLUS_PATH:
            return cast(
                list[TestRunner],
                [
                    JsonlDataHumanEvalPlus(**json.loads(line))
                    for line in dataset_path.read_text().splitlines()
                    if line.strip()  # Skip empty lines
                ],
            )
        else:
            # For other JSONL files, check if it's a standard HumanEval dataset
            # If it has the basic fields, use JsonlDataHumanEvalPlus which can handle it
            try:
                # Read first line to check format
                first_line = next(
                    (
                        line
                        for line in dataset_path.read_text().splitlines()
                        if line.strip()
                    ),
                    None,
                )
                if first_line:
                    first_item = json.loads(first_line)
                    # Check if it has the basic HumanEval format
                    if all(
                        key in first_item
                        for key in [
                            "task_id",
                            "prompt",
                            "canonical_solution",
                            "test",
                            "entry_point",
                        ]
                    ):
                        return cast(
                            list[TestRunner],
                            [
                                JsonlDataHumanEvalPlus(**json.loads(line))
                                for line in dataset_path.read_text().splitlines()
                                if line.strip()  # Skip empty lines
                            ],
                        )
                    else:
                        raise ValueError(
                            f"Unsupported JSONL format in {dataset_path}. Expected HumanEval format with fields: task_id, prompt, canonical_solution, test, entry_point"
                        )
                else:
                    raise ValueError(f"Empty JSONL file: {dataset_path}")
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in JSONL file {dataset_path}: {e}")
    else:
        raise ValueError(f"Unsupported file extension: {dataset_path.suffix}")


def extract_dataset_canonical(
    use_plus_tests: bool = False,
    dataset_type: Literal["standard", "plus"] | None = None,
) -> list[TestRunner]:
    """
    Load canonical dataset and convert to canonical solution variant.

    Args:
        use_plus_tests: If True, use HumanEval+ test cases (for backward compatibility)
        dataset_type: Specify dataset source for canonical solutions ("standard" or "plus")
                     If None, uses use_plus_tests flag for backward compatibility

    Returns:
        list[TestRunner]: List of loaded data using canonical solutions

    Raises:
        ValueError: If file extension is not supported
        FileNotFoundError: If canonical dataset file does not exist
    """
    # Select appropriate dataset file based on dataset_type or use_plus_tests flag
    if dataset_type is not None:
        # New explicit dataset type selection
        if dataset_type == "plus":
            target_dataset_path = HUMANEVAL_PLUS_PATH
        else:  # standard
            target_dataset_path = HUMANEVAL_PATH
    else:
        # Backward compatibility: use_plus_tests flag
        if use_plus_tests:
            target_dataset_path = HUMANEVAL_PLUS_PATH
        else:
            target_dataset_path = HUMANEVAL_PATH

    if not target_dataset_path.exists():
        raise FileNotFoundError(
            f"Canonical dataset file not found: {target_dataset_path}"
        )

    if target_dataset_path.suffix == ".json":
        with target_dataset_path.open("r") as f:
            return cast(
                list[TestRunner], [JsonDataCanonical(**item) for item in json.load(f)]
            )
    elif target_dataset_path.suffix == ".jsonl":
        # Check if this is HumanEval+ dataset
        if target_dataset_path == HUMANEVAL_PLUS_PATH:
            # For HumanEval+, use JsonlDataHumanEvalPlus which already uses canonical solutions
            return cast(
                list[TestRunner],
                [
                    JsonlDataHumanEvalPlus(**json.loads(line))
                    for line in target_dataset_path.read_text().splitlines()
                    if line.strip()  # Skip empty lines
                ],
            )
        else:
            # For other JSONL files, check if it's a standard HumanEval dataset
            # If it has the basic fields, use JsonlDataHumanEvalPlus which already uses canonical solutions
            try:
                # Read first line to check format
                first_line = next(
                    (
                        line
                        for line in target_dataset_path.read_text().splitlines()
                        if line.strip()
                    ),
                    None,
                )
                if first_line:
                    first_item = json.loads(first_line)
                    # Check if it has the basic HumanEval format
                    if all(
                        key in first_item
                        for key in [
                            "task_id",
                            "prompt",
                            "canonical_solution",
                            "test",
                            "entry_point",
                        ]
                    ):
                        return cast(
                            list[TestRunner],
                            [
                                JsonlDataHumanEvalPlus(**json.loads(line))
                                for line in target_dataset_path.read_text().splitlines()
                                if line.strip()  # Skip empty lines
                            ],
                        )
                    else:
                        raise ValueError(
                            f"Unsupported JSONL format in {target_dataset_path}. Expected HumanEval format with fields: task_id, prompt, canonical_solution, test, entry_point"
                        )
                else:
                    raise ValueError(f"Empty JSONL file: {target_dataset_path}")
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"Invalid JSON in JSONL file {target_dataset_path}: {e}"
                )
    else:
        raise ValueError(f"Unsupported file extension: {target_dataset_path.suffix}")
