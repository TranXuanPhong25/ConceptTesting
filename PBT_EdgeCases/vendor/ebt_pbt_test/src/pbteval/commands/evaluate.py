import csv
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from pbteval.commands.generate import TestType, get_output_directory
from pbteval.constants import CSV_EXTENSION, RESULTS_DIR
from pbteval.core.data import TestRunner, extract_dataset
from pbteval.core.exceptions import TestFileNotFoundError
from pbteval.utils.logger import get_logger
from pbteval.utils.utils import extract_task_number, find_files_by_pattern

logger = get_logger(__name__)


class TestResultStatus(Enum):
    """Test result status enumeration"""

    PASS = "PASS"
    FAIL = "FAIL"
    NOT_AVAILABLE = "N/A"
    ERROR = "ERROR"


class CSVColumn(Enum):
    """CSV column names enumeration"""

    TASK_ID = "task_id"
    HUMANEVAL = "humaneval"
    EBT = "ebt"
    PBT = "pbt"


@dataclass
class TestResult:
    """Container for individual test execution results"""

    task_id: str
    humaneval_result: bool | None = None
    ebt_result: bool | None = None
    pbt_result: bool | None = None
    humaneval_error: Exception | None = None
    ebt_error: Exception | None = None
    pbt_error: Exception | None = None

    def get_status(
        self, result: bool | None, error: Exception | None
    ) -> TestResultStatus:
        """Get formatted status for a test result"""
        if error is not None:
            return (
                TestResultStatus.NOT_AVAILABLE
                if isinstance(error, TestFileNotFoundError)
                else TestResultStatus.ERROR
            )
        if result is None:
            return TestResultStatus.NOT_AVAILABLE
        return TestResultStatus.PASS if result else TestResultStatus.FAIL

    @property
    def humaneval_status(self) -> TestResultStatus:
        """Get HumanEval test status"""
        return self.get_status(self.humaneval_result, self.humaneval_error)

    @property
    def ebt_status(self) -> TestResultStatus:
        """Get EBT test status"""
        return self.get_status(self.ebt_result, self.ebt_error)

    @property
    def pbt_status(self) -> TestResultStatus:
        """Get PBT test status"""
        return self.get_status(self.pbt_result, self.pbt_error)

    def to_csv_dict(self) -> dict[str, str]:
        """Convert to dictionary format for CSV output"""
        return {
            CSVColumn.TASK_ID.value: self.task_id,
            CSVColumn.HUMANEVAL.value: self._format_for_csv(
                self.humaneval_result, self.humaneval_error
            ),
            CSVColumn.EBT.value: self._format_for_csv(self.ebt_result, self.ebt_error),
            CSVColumn.PBT.value: self._format_for_csv(self.pbt_result, self.pbt_error),
        }

    def _format_for_csv(self, result: bool | None, error: Exception | None) -> str:
        """Format test result for CSV output"""
        if error is not None:
            return "N/A" if isinstance(error, TestFileNotFoundError) else "ERROR"
        if result is None:
            return "N/A"
        return "true" if result else "false"


class TestFileManager:
    """Manages test file discovery and organization"""

    def __init__(self, model: str):
        self.model = model
        self.ebt_files: dict[str, Path] = {}
        self.pbt_files: dict[str, Path] = {}
        self._discover_test_files()

    def _discover_test_files(self) -> None:
        """Discover and organize test files by type"""
        if not self.model:
            return

        ebt_directory = get_output_directory(self.model, TestType.EBT)
        pbt_directory = get_output_directory(self.model, TestType.PBT)

        self.ebt_files = self._build_file_mapping(ebt_directory, TestType.EBT)
        self.pbt_files = self._build_file_mapping(pbt_directory, TestType.PBT)

    def _build_file_mapping(
        self, directory: Path, test_type: TestType
    ) -> dict[str, Path]:
        """Build mapping from task IDs to test file paths"""
        if not directory.exists():
            return {}

        test_files = self._find_test_files(directory, test_type)
        file_mapping = {}

        for file_path in test_files:
            task_id = file_path.stem.replace("_", "/")

            # For EBT, prefer .txt files over .py files if both exist
            if task_id not in file_mapping:
                file_mapping[task_id] = file_path
            elif test_type == TestType.EBT and file_path.suffix == ".txt":
                file_mapping[task_id] = file_path

        return file_mapping

    def _find_test_files(self, directory: Path, test_type: TestType) -> list[Path]:
        """Find test files in directory based on test type"""
        if test_type == TestType.EBT:
            # EBT files can be .txt or .py
            txt_files = find_files_by_pattern(directory, "*.txt")
            py_files = find_files_by_pattern(directory, "*.py")
            all_files = txt_files + py_files
            all_files.sort(key=extract_task_number)
            return all_files
        else:
            # PBT files are .py
            return find_files_by_pattern(directory, "*.py")

    def get_test_file(self, task_id: str, test_type: TestType) -> Path | None:
        """Get test file path for given task ID and test type"""
        file_mapping = self.ebt_files if test_type == TestType.EBT else self.pbt_files
        return file_mapping.get(task_id)


class TestEvaluationSummary:
    """Handles evaluation summary statistics"""

    def __init__(self, results: list[TestResult]):
        self.results = results
        self.total_tasks = len(results)

    def get_statistics(self) -> dict[str, int]:
        """Calculate comprehensive evaluation statistics"""
        stats = {
            "total_tasks": self.total_tasks,
            "humaneval_pass": 0,
            "ebt_pass": 0,
            "pbt_pass": 0,
            "humaneval_na": 0,
            "ebt_na": 0,
            "pbt_na": 0,
            "humaneval_error": 0,
            "ebt_error": 0,
            "pbt_error": 0,
        }

        for result in self.results:
            self._count_result_stats(result, stats)

        return stats

    def _count_result_stats(self, result: TestResult, stats: dict[str, int]) -> None:
        """Count statistics for a single test result"""
        # HumanEval statistics
        if result.humaneval_status == TestResultStatus.PASS:
            stats["humaneval_pass"] += 1
        elif result.humaneval_status == TestResultStatus.NOT_AVAILABLE:
            stats["humaneval_na"] += 1
        elif result.humaneval_status == TestResultStatus.ERROR:
            stats["humaneval_error"] += 1

        # EBT statistics
        if result.ebt_status == TestResultStatus.PASS:
            stats["ebt_pass"] += 1
        elif result.ebt_status == TestResultStatus.NOT_AVAILABLE:
            stats["ebt_na"] += 1
        elif result.ebt_status == TestResultStatus.ERROR:
            stats["ebt_error"] += 1

        # PBT statistics
        if result.pbt_status == TestResultStatus.PASS:
            stats["pbt_pass"] += 1
        elif result.pbt_status == TestResultStatus.NOT_AVAILABLE:
            stats["pbt_na"] += 1
        elif result.pbt_status == TestResultStatus.ERROR:
            stats["pbt_error"] += 1


class TestEvaluator:
    """Main test evaluation orchestrator"""

    TASK_ID_PADDING = 15
    CSV_HEADERS = [column.value for column in CSVColumn]

    def __init__(self, dataset_path: Path, model: str):
        """Initialize test evaluator

        Args:
            dataset_path: Path to the dataset file
            model: Model name for test directory construction
        """
        self.dataset_path = dataset_path
        self.model = model
        self.dataset = extract_dataset(dataset_path)
        self.file_manager = TestFileManager(model)
        self.results: list[TestResult] = []

    def evaluate_all_tasks(self) -> list[TestResult]:
        """Evaluate all tasks and return results"""
        logger.info("Starting comprehensive test evaluation")
        self._print_evaluation_header()

        self.results = []
        for test_runner in self.dataset:
            result = self._evaluate_single_task(test_runner)
            self.results.append(result)
            self._print_task_result(result)

        self._print_evaluation_footer()
        return self.results

    def _evaluate_single_task(self, test_runner: TestRunner) -> TestResult:
        """Evaluate a single task with all test types"""
        result = TestResult(task_id=test_runner.task_id)

        # Execute HumanEval test
        result.humaneval_result, result.humaneval_error = self._safe_execute_test(
            test_runner.run_humaneval_tests
        )

        # Execute EBT test
        result.ebt_result, result.ebt_error = self._execute_generated_test(
            test_runner, TestType.EBT, test_runner.run_generated_ebt
        )

        # Execute PBT test
        result.pbt_result, result.pbt_error = self._execute_generated_test(
            test_runner, TestType.PBT, test_runner.run_generated_pbt
        )

        return result

    def _safe_execute_test(
        self, test_function: Callable[[], bool]
    ) -> tuple[bool | None, Exception | None]:
        """Safely execute a test function and capture any exceptions"""
        try:
            return test_function(), None
        except Exception as e:
            logger.debug(f"Test execution failed: {e}")
            return None, e

    def _execute_generated_test(
        self,
        test_runner: TestRunner,
        test_type: TestType,
        test_function: Callable[[Path], bool],
    ) -> tuple[bool | None, Exception | None]:
        """Execute a generated test (EBT or PBT) if the test file exists"""
        test_file = self.file_manager.get_test_file(test_runner.task_id, test_type)

        if test_file is None:
            error = TestFileNotFoundError(
                f"{test_type.value.upper()} test file not found for task {test_runner.task_id}"
            )
            return None, error

        return self._safe_execute_test(lambda: test_function(test_file))

    def _print_evaluation_header(self) -> None:
        """Print evaluation header"""
        print("Starting evaluation...")
        print("-" * 60)
        print(
            f"{'Task ID':<{self.TASK_ID_PADDING}} | {'HumanEval':>9} | {'EBT':>5} | {'PBT':>5}"
        )
        print("-" * 60)

    def _print_task_result(self, result: TestResult) -> None:
        """Print evaluation result for a single task"""
        print(
            f"{result.task_id:<{self.TASK_ID_PADDING}} | "
            f"HumanEval: {result.humaneval_status.value:>5} | "
            f"EBT: {result.ebt_status.value:>5} | "
            f"PBT: {result.pbt_status.value:>5}"
        )

    def _print_evaluation_footer(self) -> None:
        """Print evaluation footer"""
        print("-" * 60)
        print("Evaluation completed.")

    def save_results_to_csv(self, output_path: Path) -> None:
        """Save evaluation results to CSV file"""
        if not self.results:
            logger.warning("No results to save. Run evaluate_all_tasks() first.")
            return

        self._ensure_output_directory(output_path)
        self._write_csv_file(output_path)
        logger.info(f"Results saved to: {output_path}")

    def _ensure_output_directory(self, output_path: Path) -> None:
        """Ensure output directory exists"""
        output_path.parent.mkdir(parents=True, exist_ok=True)

    def _write_csv_file(self, output_path: Path) -> None:
        """Write results to CSV file"""
        try:
            with output_path.open("w", newline="", encoding="utf-8") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=self.CSV_HEADERS)
                writer.writeheader()

                for result in self.results:
                    writer.writerow(result.to_csv_dict())

            logger.info(
                f"Successfully saved {len(self.results)} results to {output_path}"
            )

        except Exception as e:
            logger.error(f"Failed to save results to {output_path}: {e}")
            raise

    def get_evaluation_summary(self) -> TestEvaluationSummary:
        """Get evaluation summary with statistics"""
        return TestEvaluationSummary(self.results)


def handle_evaluate_command(dataset_path: Path, model: str) -> None:
    """Handle evaluate command with comprehensive evaluation logic

    Args:
        dataset_path: Path to dataset file
        model: Model name

    Raises:
        Exception: If evaluation fails
    """
    evaluator = TestEvaluator(dataset_path, model)
    evaluator.evaluate_all_tasks()

    # Save results to CSV

    output_path = RESULTS_DIR / f"{model}{CSV_EXTENSION}"
    evaluator.save_results_to_csv(output_path)
