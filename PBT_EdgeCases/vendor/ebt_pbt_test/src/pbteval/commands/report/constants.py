"""Constants for report generation."""

import re

# Regex patterns
REGEX_PATTERNS = {
    "assertion": re.compile(r"assert\s+"),
    "given_decorator": re.compile(r"@given\("),
    "test_function": re.compile(r"def test_\w+\("),
    "test_function_names": re.compile(r"def (test_\w+)\("),
    "basic_test_case": re.compile(r"Test Case \d+:"),
    "edge_test_case": re.compile(r"Edge Test Case \d+:"),
    "large_scale_test_case": re.compile(r"Large Scale Test Case \d+:"),
    "docstring": re.compile(r'""".*?"""', re.DOTALL),
    "function_signature": re.compile(r"def\s+\w+\s*\([^)]*\)\s*:"),
    "docstring_content": re.compile(r'"""(.*?)"""|\'\'\'(.*?)\'\'\'', re.DOTALL),
    "list_patterns": re.compile(r"\[[\d\.,\s]+\]"),
    "threshold_patterns": re.compile(r"has_close_elements\([^,]+,\s*([^)]+)\)"),
}

# Test categories
TEST_CATEGORIES = [
    "Basic Test Cases",
    "Edge Test Cases",
    "Large Scale Test Cases",
]

# Strategy patterns for Hypothesis
STRATEGY_PATTERNS = [
    ("st.lists", r"st\.lists\("),
    ("st.floats", r"st\.floats\("),
    ("st.integers", r"st\.integers\("),
    ("st.text", r"st\.text\("),
    ("st.booleans", r"st\.booleans\("),
]

# Parameter patterns
PARAM_PATTERNS = [
    ("min_size", r"min_size=(\d+)"),
    ("max_size", r"max_size=(\d+)"),
    ("min_value", r"min_value=([0-9.-]+)"),
    ("max_value", r"max_value=([0-9.-]+)"),
]

# Special constraints
SPECIAL_CONSTRAINTS = [
    "allow_nan=False",
    "allow_infinity=False",
    "exclude_min=True",
    "exclude_max=True",
]

# Status mapping for execution results
STATUS_MAP = {
    "true": "✅ PASS",
    "false": "❌ FAIL",
    "N/A": "⚠️ N/A",
    "ERROR": "🔴 ERROR",
}

# File extensions
FILE_EXTENSIONS = {
    "EBT": ".txt",
    "PBT": ".py",
}
