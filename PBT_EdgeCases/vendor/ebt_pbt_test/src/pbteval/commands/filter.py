"""
CSV result filtering functionality for PBT evaluation.

This module provides functions to filter and analyze CSV results
from evaluation runs based on test outcomes.
"""

from __future__ import annotations

import csv
from pathlib import Path

from pbteval.constants import CSV_EXTENSION, RESULTS_DIR


def parse_bool_filter(value: str) -> bool:
    """Parse boolean filter value from string

    Args:
        value: String representation of boolean value ("true" or "false")

    Returns:
        Boolean value

    Raises:
        ValueError: If value cannot be parsed as boolean
    """
    if value.lower() == "true":
        return True
    elif value.lower() == "false":
        return False
    else:
        raise ValueError(f"Invalid boolean value: {value}. Expected 'true' or 'false'.")


def filter_csv_results(
    csv_file: Path,
    humaneval_filter: bool | None = None,
    ebt_filter: bool | None = None,
    pbt_filter: bool | None = None,
) -> list[dict[str, str | bool]]:
    """Filter CSV results based on test result criteria

    Args:
        csv_file: Path to the CSV file to filter
        humaneval_filter: Filter for HumanEval test results (None = no filter)
        ebt_filter: Filter for EBT test results (None = no filter)
        pbt_filter: Filter for PBT test results (None = no filter)

    Returns:
        List of filtered result dictionaries

    Raises:
        FileNotFoundError: If CSV file does not exist
    """
    if not csv_file.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_file}")

    filtered_results = []

    with csv_file.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Convert string values to boolean
            humaneval_result = row["humaneval"].lower() == "true"
            ebt_result = row["ebt"].lower() == "true"
            pbt_result = row["pbt"].lower() == "true"

            # Apply filters
            if humaneval_filter is not None and humaneval_result != humaneval_filter:
                continue
            if ebt_filter is not None and ebt_result != ebt_filter:
                continue
            if pbt_filter is not None and pbt_result != pbt_filter:
                continue

            filtered_results.append(
                {
                    "task_id": row["task_id"],
                    "humaneval": humaneval_result,
                    "ebt": ebt_result,
                    "pbt": pbt_result,
                }
            )

    return filtered_results


def format_filter_results(
    results: list[dict[str, str | bool]],
    output_format: str = "list",
) -> str:
    """Format filtered results for output

    Args:
        results: List of filtered result dictionaries
        output_format: Output format ("list", "csv", or "count")

    Returns:
        Formatted output string
    """
    if output_format == "count":
        return f"Found {len(results)} matching tasks"
    elif output_format == "csv":
        lines = ["task_id,humaneval,ebt,pbt"]
        for result in results:
            lines.append(
                f"{result['task_id']},{result['humaneval']},{result['ebt']},{result['pbt']}"
            )
        return "\n".join(lines)
    else:  # list format (default)
        if results:
            return "\n".join(str(result["task_id"]) for result in results)
        else:
            return "No matching tasks found"


def get_csv_file_path(model: str, csv_file: str | None = None) -> Path:
    """Get the path to the CSV file to filter

    Args:
        model: Model name to use for default CSV file path
        csv_file: Explicit CSV file path (overrides model-based path)

    Returns:
        Path to the CSV file
    """
    if csv_file:
        return Path(csv_file)
    else:
        # Use model name to find CSV file in results directory
        return RESULTS_DIR / f"{model}{CSV_EXTENSION}"


def get_filter_summary(results: list[dict[str, str | bool]]) -> str:
    """Generate a summary of filtered results

    Args:
        results: List of filtered result dictionaries

    Returns:
        Summary string
    """
    return f"# Summary: {len(results)} matching tasks"


def handle_filter_command(
    model: str,
    csv_file: str | None = None,
    humaneval: str | None = None,
    ebt: str | None = None,
    pbt: str | None = None,
    output_format: str = "list",
) -> None:
    """Handle filter command with all business logic

    Args:
        model: Model name for default CSV file path
        csv_file: Path to CSV file to filter (overrides model-based path)
        humaneval: Filter by HumanEval test result ("true" or "false")
        ebt: Filter by EBT test result ("true" or "false")
        pbt: Filter by PBT test result ("true" or "false")
        output_format: Output format ("list", "csv", or "count")

    Raises:
        Exception: If filtering fails
    """
    # Determine CSV file path
    csv_file_path = get_csv_file_path(model, csv_file)

    # Parse filter arguments
    humaneval_filter = None
    ebt_filter = None
    pbt_filter = None

    if humaneval is not None:
        humaneval_filter = parse_bool_filter(humaneval)
    if ebt is not None:
        ebt_filter = parse_bool_filter(ebt)
    if pbt is not None:
        pbt_filter = parse_bool_filter(pbt)

    # Filter results
    filtered_results = filter_csv_results(
        csv_file_path, humaneval_filter, ebt_filter, pbt_filter
    )

    # Format and output results
    output = format_filter_results(filtered_results, output_format)
    print(output)

    # Print summary if not in count mode
    if output_format != "count":
        summary = get_filter_summary(filtered_results)
        print(summary)
