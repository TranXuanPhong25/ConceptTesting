"""Main report generation functionality."""

from __future__ import annotations

import csv
from pathlib import Path

from pbteval.commands.generate import (
    TestType,
    get_output_directory,
)
from pbteval.constants import (
    CSV_EXTENSION,
    DEFAULT_DATASET_PATH,
    REPORT_DIR,
    REPORT_EXTENSION,
    RESULTS_DIR,
)
from pbteval.utils.logger import get_logger
from pbteval.utils.utils import normalize_task_id, parse_task_range

from .analyzers import TestFileAnalyzer
from .constants import FILE_EXTENSIONS
from .dataset_utils import DatasetExtractor
from .generators import MarkdownReportGenerator

logger = get_logger(__name__)


class ReportGenerator:
    """Main report generator class for EBT and PBT tests"""

    def __init__(self, dataset_path: Path | None = None) -> None:
        """Initialize the report generator

        Args:
            dataset_path: Path to the dataset file (optional, defaults to DEFAULT_DATASET_PATH)
        """
        self.analyzer = TestFileAnalyzer()
        self.report_generator = MarkdownReportGenerator()
        self.dataset_path = dataset_path or DEFAULT_DATASET_PATH
        self.dataset_extractor = DatasetExtractor(self.dataset_path)

    def generate_report(self, task_id: str, model: str) -> str:
        """Generate comparison report for EBT and PBT tests for a given task

        Args:
            task_id: Task identifier (e.g., "HumanEval/0")
            model: Model name (e.g., "gpt-4o-mini")

        Returns:
            Markdown formatted comparison report
        """
        # Get file paths
        ebt_path = self._get_test_file_path(task_id, model, TestType.EBT)
        pbt_path = self._get_test_file_path(task_id, model, TestType.PBT)

        # Analyze files
        ebt_analysis = self.analyzer.analyze_ebt(ebt_path)
        pbt_analysis = self.analyzer.analyze_pbt(pbt_path)

        # Get execution results if available
        execution_results = self._get_execution_results(task_id, model)

        # Get information from dataset
        target_function = self.dataset_extractor.get_target_function(task_id)
        problem_description = self.dataset_extractor.get_problem_description(task_id)
        canonical_solution = self.dataset_extractor.get_canonical_solution(task_id)
        entry_point = self.dataset_extractor.get_entry_point(task_id)
        humaneval_test_code = self.dataset_extractor.get_humaneval_test_code(task_id)

        # Generate report
        return self.report_generator.generate_comparison_report(
            task_id,
            model,
            ebt_analysis,
            pbt_analysis,
            execution_results,
            target_function,
            problem_description,
            canonical_solution,
            entry_point,
            humaneval_test_code,
        )

    def _get_test_file_path(
        self, task_id: str, model: str, test_type: TestType
    ) -> Path:
        """Get the file path for a test file

        Args:
            task_id: Task identifier
            model: Model name
            test_type: Type of test (EBT or PBT)

        Returns:
            Path to the test file
        """
        safe_task_id = normalize_task_id(task_id)
        directory = get_output_directory(model, test_type)
        extension = FILE_EXTENSIONS[test_type.name]
        return directory / f"{safe_task_id}{extension}"

    def _get_execution_results(self, task_id: str, model: str) -> dict[str, str] | None:
        """Get execution results from CSV file if available

        Args:
            task_id: Task identifier
            model: Model name

        Returns:
            Dictionary of execution results or None if not available
        """
        csv_path = RESULTS_DIR / f"{model}{CSV_EXTENSION}"
        if not csv_path.exists():
            return None

        try:
            with csv_path.open("r", encoding="utf-8") as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if row["task_id"] == task_id:
                        return {
                            "HumanEval": row["humaneval"],
                            "EBT": row["ebt"],
                            "PBT": row["pbt"],
                        }
        except Exception as e:
            logger.warning(f"Failed to read execution results: {e}")

        return None


def handle_report_command(
    task_id: str,
    model: str,
    range_str: str | None = None,
    dataset_path: Path | None = None,
) -> None:
    """Handle report command

    Args:
        task_id: Task ID or prefix (e.g., "HumanEval/0" or "HumanEval")
        model: Model name
        range_str: Optional range specification
        dataset_path: Path to dataset file (optional)
    """
    report_generator = ReportGenerator(dataset_path)

    # Create output directory
    output_dir = REPORT_DIR / model.replace("-", "_")
    output_dir.mkdir(parents=True, exist_ok=True)

    if "/" in task_id:
        # Single task
        _generate_single_report(report_generator, task_id, model, output_dir)
    else:
        # Multiple tasks with range
        _generate_task_range_reports(
            report_generator, task_id, range_str, model, output_dir
        )


def _get_report_output_path(task_id: str, output_dir: Path) -> Path:
    """Get the output path for report

    Args:
        task_id: Task identifier
        output_dir: Output directory

    Returns:
        Path for the report file
    """
    safe_task_id = normalize_task_id(task_id)
    return output_dir / f"{safe_task_id}{REPORT_EXTENSION}"


def _generate_single_report(
    report_generator: ReportGenerator, task_id: str, model: str, output_dir: Path
) -> None:
    """Generate report for a single task

    Args:
        report_generator: Report generator instance
        task_id: Task identifier
        model: Model name
        output_dir: Output directory
    """
    try:
        report = report_generator.generate_report(task_id, model)
        output_path = _get_report_output_path(task_id, output_dir)

        output_path.write_text(report, encoding="utf-8")
        print(f"Generated report for {task_id}: {output_path}")

    except Exception as e:
        logger.error(f"Failed to generate report for {task_id}: {e}")


def _generate_task_range_reports(
    report_generator: ReportGenerator,
    task_prefix: str,
    range_str: str | None,
    model: str,
    output_dir: Path,
) -> None:
    """Generate reports for multiple tasks in a range

    Args:
        report_generator: Report generator instance
        task_prefix: Task prefix (e.g., "HumanEval")
        range_str: Range specification
        model: Model name
        output_dir: Output directory
    """
    try:
        task_ids = parse_task_range(task_prefix, range_str)
        for task_id in task_ids:
            try:
                report = report_generator.generate_report(task_id, model)
                output_path = _get_report_output_path(task_id, output_dir)

                output_path.write_text(report, encoding="utf-8")
                print(f"Generated report for {task_id}: {output_path}")

            except Exception as e:
                logger.error(f"Failed to generate report for {task_id}: {e}")
                continue

    except Exception as e:
        logger.error(f"Failed to parse task range: {e}")
