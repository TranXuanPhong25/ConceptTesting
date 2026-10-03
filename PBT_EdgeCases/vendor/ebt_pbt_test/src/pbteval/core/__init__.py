"""Core functionality for PbtEval"""

from pbteval.core.cache import (
    TestResultCache,
    handle_cache_stats_command,
    handle_clear_cache_command,
)
from pbteval.core.data import (
    JsonData,
    JsonDataCanonical,
    TestRunner,
    extract_dataset,
    extract_dataset_canonical,
    get_function_pattern,
)
from pbteval.core.exceptions import (
    DatasetError,
    GenerationError,
    PbtEvalError,
    TestExecutionError,
    TestFileNotFoundError,
    handle_error_and_exit,
)

__all__ = [
    # Cache
    "TestResultCache",
    "handle_cache_stats_command",
    "handle_clear_cache_command",
    # Data
    "JsonData",
    "JsonDataCanonical",
    "TestRunner",
    "extract_dataset",
    "extract_dataset_canonical",
    "get_function_pattern",
    # Exceptions
    "PbtEvalError",
    "TestFileNotFoundError",
    "TestExecutionError",
    "DatasetError",
    "GenerationError",
    "handle_error_and_exit",
]
