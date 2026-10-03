"""Common exception classes and error handling utilities for pbteval package."""

import sys
from typing import NoReturn

from pbteval.utils.logger import get_logger

logger = get_logger(__name__)


class PbtEvalError(Exception):
    """Base exception class for pbteval package."""

    pass


class TestFileNotFoundError(PbtEvalError):
    """Raised when a test file is not found."""

    pass


class TestExecutionError(PbtEvalError):
    """Raised when test execution fails due to an error."""

    pass


class DatasetError(PbtEvalError):
    """Raised when there's an issue with dataset operations."""

    pass


class GenerationError(PbtEvalError):
    """Raised when test generation fails."""

    pass


class ModelError(PbtEvalError):
    """Raised when there's an issue with model operations."""

    pass


def handle_error_and_exit(operation: str, error: Exception) -> NoReturn:
    """Handle and display errors consistently, then exit.

    Args:
        operation: Description of the operation that failed
        error: The exception that occurred
    """
    logger.error(f"Error {operation}: {error}")
    sys.exit(1)
