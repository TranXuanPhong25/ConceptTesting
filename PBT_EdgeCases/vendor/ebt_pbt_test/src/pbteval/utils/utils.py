"""Common utility functions for pbteval package."""

import re
from pathlib import Path
from typing import Protocol

from pbteval.utils.logger import get_logger

logger = get_logger(__name__)


class FileContent(Protocol):
    """Protocol for objects that have file content operations."""

    def read_text(self, encoding: str = "utf-8") -> str:
        """Read text content from file."""
        ...

    def write_text(self, data: str, encoding: str = "utf-8") -> int:
        """Write text content to file."""
        ...

    def exists(self) -> bool:
        """Check if file exists."""
        ...


def safe_read_file(file_path: Path, default: str = "") -> str:
    """Safely read file content, returning default if file doesn't exist.

    Args:
        file_path: Path to the file to read
        default: Default content to return if file doesn't exist

    Returns:
        File content or default value
    """
    try:
        if file_path.exists():
            return file_path.read_text(encoding="utf-8")
        return default
    except Exception as e:
        logger.warning(f"Failed to read file {file_path}: {e}")
        return default


def safe_write_file(file_path: Path, content: str, create_dirs: bool = True) -> bool:
    """Safely write content to file.

    Args:
        file_path: Path to the file to write
        content: Content to write
        create_dirs: Whether to create parent directories if they don't exist

    Returns:
        True if successful, False otherwise
    """
    try:
        if create_dirs:
            file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return True
    except Exception as e:
        logger.error(f"Failed to write file {file_path}: {e}")
        return False


def extract_task_number(file_path: Path) -> int:
    """Extract task number from a file path.

    Args:
        file_path: Path to extract task number from

    Returns:
        Task number or 0 if not found
    """
    task_id = file_path.stem.replace("_", "/")
    if "/" in task_id:
        match = re.search(r"(\d+)$", task_id)
        if match:
            return int(match.group(1))
    return 0


def normalize_task_id(task_id: str) -> str:
    """Normalize task ID for file operations.

    Args:
        task_id: Original task ID

    Returns:
        Normalized task ID safe for file operations
    """
    return task_id.replace("/", "_")


def denormalize_task_id(normalized_task_id: str) -> str:
    """Convert normalized task ID back to original format.

    Args:
        normalized_task_id: Normalized task ID

    Returns:
        Original task ID format
    """
    return normalized_task_id.replace("_", "/")


def validate_file_extension(file_path: Path, expected_extensions: list[str]) -> bool:
    """Validate that file has one of the expected extensions.

    Args:
        file_path: Path to validate
        expected_extensions: List of valid extensions (e.g., ['.py', '.json'])

    Returns:
        True if file has valid extension, False otherwise
    """
    return file_path.suffix.lower() in [ext.lower() for ext in expected_extensions]


def find_files_by_pattern(directory: Path, pattern: str = "*.py") -> list[Path]:
    """Find files in directory matching pattern, sorted by task number.

    Args:
        directory: Directory to search in
        pattern: Glob pattern to match files

    Returns:
        Sorted list of matching file paths
    """
    if not directory.exists():
        return []

    files = list(directory.glob(pattern))
    files.sort(key=extract_task_number)
    return files


def parse_task_range(
    task_prefix: str, range_str: str | None, max_tasks: int = 164
) -> list[str]:
    """Parse task prefix and range string to return list of task IDs.

    Args:
        task_prefix: Task prefix (e.g., "HumanEval")
        range_str: Range string (e.g., "0-10", "0,5,10-15,20", "all", or None)
        max_tasks: Maximum number of tasks available (default: 164 for HumanEval)

    Returns:
        Sorted list of task IDs in format "prefix/number"

    Examples:
        parse_task_range("HumanEval", "0-5") -> ["HumanEval/0", "HumanEval/1", ..., "HumanEval/5"]
        parse_task_range("HumanEval", "0,5,10") -> ["HumanEval/0", "HumanEval/5", "HumanEval/10"]
        parse_task_range("HumanEval", "all") -> ["HumanEval/0", "HumanEval/1", ..., "HumanEval/163"]
        parse_task_range("HumanEval", None) -> ["HumanEval/0", "HumanEval/1", ..., "HumanEval/163"]
    """
    if range_str is None or range_str.lower() == "all":
        task_numbers = list(range(max_tasks))
    else:
        collected_numbers: list[int] = []
        try:
            for part in range_str.split(","):
                part = part.strip()
                if "-" in part:
                    # Handle range like "0-10"
                    start_str, end_str = part.split("-", 1)
                    start = int(start_str.strip())
                    end = int(end_str.strip())
                    if start > end:
                        raise ValueError(
                            f"Invalid range: start ({start}) > end ({end})"
                        )
                    if start < 0 or end >= max_tasks:
                        raise ValueError(
                            f"Range {start}-{end} is out of bounds (0-{max_tasks - 1})"
                        )
                    collected_numbers.extend(range(start, end + 1))
                else:
                    # Handle single number like "5"
                    task_id = int(part.strip())
                    if task_id < 0 or task_id >= max_tasks:
                        raise ValueError(
                            f"Task ID {task_id} is out of bounds (0-{max_tasks - 1})"
                        )
                    collected_numbers.append(task_id)
        except ValueError as e:
            logger.error(f"Failed to parse task range '{range_str}': {e}")
            raise ValueError(f"Invalid task range format: {e}")

        # Remove duplicates and sort
        task_numbers = sorted(set(collected_numbers))

    # Convert to full task IDs
    return [f"{task_prefix}/{num}" for num in task_numbers]


def extract_code_block(text: str | None) -> str:
    """Extract all code blocks from text and concatenate them

    Args:
        text: Input text

    Returns:
        Concatenated code blocks
    """
    if text is None:
        return ""

    code_blocks = []

    # Find all code blocks with ```python or ``` markers
    start_pos = 0
    while True:
        # Look for python code blocks first
        python_start = text.find("```python", start_pos)
        generic_start = text.find("```", start_pos)

        # If no more code blocks found, break
        if generic_start == -1:
            break

        # Determine which type of code block we found
        if python_start != -1 and python_start == generic_start:
            # Found ```python
            code_start = python_start + 10  # len("```python") + 1 for newline
            end_marker_start = text.find("```", code_start)
        else:
            # Found generic ```
            code_start = generic_start + 3  # len("```")
            end_marker_start = text.find("```", code_start)

        # If no closing ``` found, break
        if end_marker_start == -1:
            break

        # Extract the code block
        code_block = text[code_start:end_marker_start].strip()
        if code_block:  # Only add non-empty code blocks
            code_blocks.append(code_block)

        # Move to next position after the closing ```
        start_pos = end_marker_start + 3

    # If no code blocks found, return the original text
    if not code_blocks:
        return text

    # Join all code blocks with double newlines
    return "\n\n".join(code_blocks)
