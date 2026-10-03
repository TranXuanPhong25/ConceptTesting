import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, assert_never

from pbteval.commands.generate import TestType, get_output_directory
from pbteval.core.data import TestRunner, extract_dataset, extract_dataset_canonical
from pbteval.utils.logger import get_logger
from pbteval.utils.utils import (
    extract_code_block,
    extract_task_number,
    find_files_by_pattern,
)

logger = get_logger(__name__)


@dataclass
class TestExecutionStatistics:
    """Statistics for test execution tracking"""

    total_tests: int = 0
    passed_tests: int = 0
    cache_hits: int = 0
    execution_times: list[float] = field(default_factory=list)
    total_execution_time: float = 0.0

    @property
    def failed_tests(self) -> int:
        """Number of failed tests"""
        return self.total_tests - self.passed_tests

    @property
    def pass_percentage(self) -> float:
        """Pass rate percentage"""
        return (
            (self.passed_tests / self.total_tests) * 100 if self.total_tests > 0 else 0
        )

    @property
    def cache_hit_percentage(self) -> float:
        """Cache hit rate percentage"""
        return (self.cache_hits / self.total_tests) * 100 if self.total_tests > 0 else 0

    @property
    def average_execution_time(self) -> float:
        """Average execution time"""
        return (
            sum(self.execution_times) / len(self.execution_times)
            if self.execution_times
            else 0.0
        )

    @property
    def min_execution_time(self) -> float:
        """Minimum execution time"""
        return min(self.execution_times) if self.execution_times else 0.0

    @property
    def max_execution_time(self) -> float:
        """Maximum execution time"""
        return max(self.execution_times) if self.execution_times else 0.0

    def add_execution_time(self, execution_time: float) -> None:
        """Add execution time to statistics"""
        self.execution_times.append(execution_time)
        self.total_execution_time += execution_time

    def get_percentile(self, percentile: float) -> float:
        """Get percentile of execution times"""
        if not self.execution_times:
            return 0.0
        sorted_times = sorted(self.execution_times)
        index = int(len(sorted_times) * percentile / 100)
        # Ensure index is within bounds
        index = max(0, min(index, len(sorted_times) - 1))
        return sorted_times[index]

    def print_summary(self, test_type: TestType) -> None:
        """Print comprehensive test execution summary"""
        print("-" * 50)
        print(f"{test_type.value.upper()} Test Results Summary:")
        print(f"  Total tests: {self.total_tests}")
        print(f"  Passed: {self.passed_tests}")
        print(f"  Failed: {self.failed_tests}")
        print(f"  Pass rate: {self.pass_percentage:.1f}%")
        print(f"  Cache hits: {self.cache_hits} ({self.cache_hit_percentage:.1f}%)")
        if self.cache_hits > 0:
            print(
                f"  Skipped {self.cache_hits} test{'s' if self.cache_hits != 1 else ''} (cached results)"
            )

        # Print timing statistics if we have execution times
        if self.execution_times:
            print()
            print("Execution Time Statistics:")
            print(f"  Total time: {self.total_execution_time:.3f}s")
            print(f"  Average time: {self.average_execution_time:.3f}s")
            print(f"  Min time: {self.min_execution_time:.3f}s")
            print(f"  Max time: {self.max_execution_time:.3f}s")
            print(f"  P50 (median): {self.get_percentile(50.0):.3f}s")
            print(f"  P90: {self.get_percentile(90.0):.3f}s")
            print(f"  P95: {self.get_percentile(95.0):.3f}s")


class TestFileDiscovery:
    """Handles test file discovery and organization"""

    @staticmethod
    def find_test_files(test_directory: Path, test_type: TestType) -> list[Path]:
        """Find and sort all test files in the given directory

        Args:
            test_directory: Directory containing test files
            test_type: Type of test to determine file extension

        Returns:
            Sorted list of test file paths
        """
        if not test_directory.exists():
            return []

        if test_type == TestType.EBT:
            # EBT files can use both .txt and .py extensions
            txt_files = find_files_by_pattern(test_directory, "*.txt")
            py_files = find_files_by_pattern(test_directory, "*.py")
            all_files = txt_files + py_files
            all_files.sort(key=extract_task_number)
            return all_files
        elif test_type == TestType.PBT:
            # PBT files can use both .txt and .py extensions (for backward compatibility)
            txt_files = find_files_by_pattern(test_directory, "*.txt")
            py_files = find_files_by_pattern(test_directory, "*.py")
            all_files = txt_files + py_files
            all_files.sort(key=extract_task_number)
            return all_files
        else:
            # Other test types use .py extension
            return find_files_by_pattern(test_directory, "*.py")


class TestExecutionHandler:
    """Handles individual test execution with proper error handling"""

    def __init__(self, test_runner_data: TestRunner):
        self.test_runner_data = test_runner_data
        self._last_error_info: str | None = None
        self._cached_error_info: str | None = None

    def execute_test(self, test_type: TestType, test_file: Path | None = None) -> bool:
        """Execute a test based on type

        Args:
            test_type: Type of test to execute
            test_file: Path to test file (required for EBT and PBT)

        Returns:
            True if test passed, False otherwise
        """
        self._last_error_info = None

        try:
            match test_type:
                case TestType.HUMANEVAL:
                    result = self.test_runner_data.run_humaneval_tests()
                case TestType.EBT:
                    if test_file is None:
                        raise ValueError("Test file required for EBT execution")
                    result = self.test_runner_data.run_generated_ebt(test_file)
                case TestType.PBT:
                    if test_file is None:
                        raise ValueError("Test file required for PBT execution")
                    result = self.test_runner_data.run_generated_pbt(test_file)
                case _:
                    assert_never(test_type)

            # If test failed, try to get error info from the test runner
            if not result:
                self._last_error_info = self.test_runner_data.get_last_error_info()

            # If result was cached, get cached error info
            if self.was_last_result_cached():
                self._cached_error_info = self.test_runner_data.get_last_error_info()

            return result

        except Exception as e:
            self._last_error_info = f"{type(e).__name__}: {e}"
            return False

    def print_generated_code(self, test_type: TestType, test_file: Path) -> None:
        """Print generated code for EBT and PBT tests"""
        if test_type == TestType.EBT:
            self.test_runner_data.print_generated_ebt_string(test_file)
        elif test_type == TestType.PBT:
            self.test_runner_data.print_generated_pbt_string(test_file)

    def was_last_result_cached(self) -> bool:
        """Check if the last test result was from cache"""
        return self.test_runner_data.was_last_result_cached()

    def get_last_error_info(self) -> str | None:
        """Get the last error information"""
        # Return cached error info if result was cached, otherwise return the last error
        if self.was_last_result_cached() and self._cached_error_info is not None:
            return self._cached_error_info
        return self._last_error_info

    def get_last_execution_time(self) -> float | None:
        """Get the last execution time from the test runner"""
        return self.test_runner_data.get_last_execution_time()

    def set_cached_error_info(self, error_info: str | None) -> None:
        """Set cached error information"""
        self._cached_error_info = error_info


class TestExecutor:
    """Main test execution orchestrator with improved organization"""

    def __init__(
        self,
        dataset_path: Path,
        model: str,
        use_canonical: bool = False,
        use_plus_tests: bool = False,
        dataset_type: Literal["standard", "plus"] | None = None,
        save_test_code: bool = False,
        show_failures: bool = False,
        log_failures: bool = False,
    ):
        """Initialize test executor

        Args:
            dataset_path: Path to the dataset file
            model: Model name for test directory construction
            use_canonical: Whether to use canonical solutions
            use_plus_tests: Whether to use HumanEval+ test cases
            dataset_type: Specify dataset source for canonical solutions ("standard" or "plus")
            save_test_code: Whether to save test code to files
            show_failures: Whether to show detailed error messages for failed tests
            log_failures: Whether to save detailed failure logs to file
        """
        self.dataset_path = dataset_path
        self.model = model
        self.use_canonical = use_canonical
        self.use_plus_tests = use_plus_tests
        self.dataset_type = dataset_type
        self.save_test_code = save_test_code
        self.show_failures = show_failures
        self.log_failures = log_failures
        self.saved_test_count = 0
        self._log_file_path: Path | None = None

        # Initialize log file if log_failures is enabled
        if self.log_failures:
            self._initialize_log_file()

        # Load appropriate dataset
        if use_canonical:
            self.dataset = extract_dataset_canonical(use_plus_tests, dataset_type)
        else:
            self.dataset = extract_dataset(dataset_path)

        # Set use_plus_tests flag for all data instances
        for data in self.dataset:
            data.use_plus_tests = use_plus_tests

        self.dataset_dict = {data.task_id: data for data in self.dataset}
        self.statistics = TestExecutionStatistics()
        self.file_discovery = TestFileDiscovery()

    def execute_all_tests(self, test_type: TestType) -> None:
        """Execute all tests of the specified type for tasks in the dataset

        Args:
            test_type: Type of tests to run (HUMANEVAL, EBT, or PBT)
        """
        if test_type == TestType.HUMANEVAL:
            # HumanEval tests are embedded in the dataset, no external files needed
            self._execute_humaneval_tests()
        else:
            # EBT and PBT tests require external test files
            target_directory = get_output_directory(self.model, test_type)

            if not self._validate_test_directory(target_directory, test_type):
                return

            test_files = self.file_discovery.find_test_files(
                target_directory, test_type
            )

            if not test_files:
                print(
                    f"No {test_type.value.upper()} test files found in {target_directory}"
                )
                return

            self._initialize_test_execution(test_files, test_type)
            self._execute_test_files(test_files, test_type)
            self.statistics.print_summary(test_type)

            # Print saved test code summary if applicable
            if self.save_test_code and self.saved_test_count > 0:
                self._print_saved_test_code_summary(test_type)

    def _execute_humaneval_tests(self) -> None:
        """Execute HumanEval tests for all tasks in the dataset"""
        self.statistics = TestExecutionStatistics()
        self.statistics.total_tests = len(self.dataset)

        print(f"Running {self.statistics.total_tests} HUMANEVAL tests...")
        print("-" * 50)

        for test_runner_data in self.dataset:
            success = self._execute_single_humaneval_test(test_runner_data)

            if success:
                self.statistics.passed_tests += 1

            if test_runner_data.was_last_result_cached():
                self.statistics.cache_hits += 1

            # Add execution time to statistics
            execution_time = test_runner_data.get_last_execution_time()
            if execution_time is not None:
                self.statistics.add_execution_time(execution_time)

        self.statistics.print_summary(TestType.HUMANEVAL)

        # Write log summary if logging is enabled
        if self.log_failures and self._log_file_path:
            self._write_log_summary(self.statistics)

        # Print saved test code summary if applicable
        if self.save_test_code and self.saved_test_count > 0:
            print("-" * 50)
            print(f"Saved {self.saved_test_count} test code files")

            # Determine output directory path for display
            source_type = "canonical" if self.use_canonical else "agentcoder"
            test_type = "plus" if self.use_plus_tests else "standard"
            safe_model = self.model.replace("-", "_")

            if source_type == "canonical" and self.dataset_type:
                subdir = f"{self.dataset_type}_{test_type}"
            else:
                subdir = test_type

            from pbteval.constants import OUTPUT_BASE_DIR

            output_dir = (
                OUTPUT_BASE_DIR / "humaneval_tests" / source_type / subdir / safe_model
            )
            print(f"Output directory: {output_dir}")

    def _execute_single_humaneval_test(self, test_runner_data: TestRunner) -> bool:
        """Execute a single HumanEval test

        Args:
            test_runner_data: The TestRunner data for the task

        Returns:
            True if the test passed, False otherwise
        """
        task_id = test_runner_data.task_id
        test_execution_handler = TestExecutionHandler(test_runner_data)

        # Save test code if requested
        if self.save_test_code:
            # Get the test code string
            test_code = test_runner_data._make_humaneval_tests_string()

            # Determine source type and dataset type
            source_type = "canonical" if self.use_canonical else "agentcoder"
            dataset_type_value = None
            if self.use_canonical and self.dataset_type:
                dataset_type_value = self.dataset_type

            # Determine test type based on use_plus_tests flag
            test_type = "plus" if self.use_plus_tests else "standard"

            # Save the test code
            saved = test_runner_data.save_humaneval_test_code(
                test_code=test_code,
                task_id=task_id,
                model=self.model,
                source_type=source_type,
                dataset_type=dataset_type_value,
                test_type=test_type,
            )

            if saved:
                self.saved_test_count += 1

        try:
            success = test_execution_handler.execute_test(TestType.HUMANEVAL)
        except Exception as e:
            logger.error(f"Test execution failed for {task_id}: {e}")
            success = False

        # Print result with cache indicator and timing
        cache_indicator = (
            " (cached)" if test_execution_handler.was_last_result_cached() else ""
        )
        status = "passed" if success else "failed"

        # Format timing information
        execution_time = test_execution_handler.get_last_execution_time()
        timing_info = f" ({execution_time:.3f}s)" if execution_time is not None else ""

        print(f"humaneval for task {task_id:13} {status}{cache_indicator}{timing_info}")

        # Show detailed error message if test failed and show_failures is enabled
        if not success and self.show_failures:
            error_info = test_execution_handler.get_last_error_info()
            if error_info:
                print(f"  {error_info}")

        # Log detailed failure information if test failed and log_failures is enabled
        if not success and self.log_failures:
            self._log_failure_details(task_id, test_execution_handler)

        return success

    def _print_saved_test_code_summary(self, test_type: TestType) -> None:
        """Print summary of saved test code files

        Args:
            test_type: Type of test (EBT or PBT)
        """
        print("-" * 50)
        print(
            f"Saved {self.saved_test_count} {test_type.value.upper()} test code files"
        )

        # Determine output directory path for display
        safe_model = self.model.replace("-", "_")

        from pbteval.constants import OUTPUT_BASE_DIR

        if test_type == TestType.EBT:
            output_dir = OUTPUT_BASE_DIR / "ebt_tests" / safe_model
        else:  # TestType.PBT
            output_dir = OUTPUT_BASE_DIR / "pbt_tests" / safe_model

        print(f"Output directory: {output_dir}")

    def _initialize_log_file(self) -> None:
        """Initialize log file for this execution session"""
        from datetime import datetime

        from pbteval.constants import OUTPUT_BASE_DIR

        logs_dir = OUTPUT_BASE_DIR / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self._log_file_path = logs_dir / f"humaneval_failures_{timestamp}.log"

        # Write session header
        with self._log_file_path.open("w", encoding="utf-8") as f:
            f.write("=== HUMANEVAL FAILURE LOG SESSION ===\n")
            f.write(f"Start Time: {datetime.now().isoformat()}\n")
            f.write(f"Model: {self.model}\n")
            f.write(f"Use Canonical: {self.use_canonical}\n")
            f.write(f"Use Plus Tests: {self.use_plus_tests}\n")
            f.write(f"Dataset Type: {self.dataset_type}\n")
            f.write(f"{'=' * 50}\n\n")

    def _log_failure_details(
        self, task_id: str, test_execution_handler: TestExecutionHandler
    ) -> None:
        """Log detailed failure information to file"""
        if not self._log_file_path:
            return

        from datetime import datetime

        # Get error information
        error_info = test_execution_handler.get_last_error_info()

        # Append failure details to the same log file
        with self._log_file_path.open("a", encoding="utf-8") as f:
            f.write(f"--- FAILURE: {task_id} ---\n")
            f.write(f"Time: {datetime.now().strftime('%H:%M:%S')}\n")
            f.write(f"Error: {error_info}\n")
            f.write(f"{'-' * 30}\n\n")

    def _write_log_summary(self, stats: TestExecutionStatistics) -> None:
        """Write execution summary to log file"""
        if not self._log_file_path:
            return

        from datetime import datetime

        with self._log_file_path.open("a", encoding="utf-8") as f:
            f.write(f"\n{'=' * 50}\n")
            f.write("=== EXECUTION SUMMARY ===\n")
            f.write(f"End Time: {datetime.now().isoformat()}\n")
            f.write(f"Total Tests: {stats.total_tests}\n")
            f.write(f"Failed Tests: {stats.failed_tests}\n")
            f.write(f"Pass Rate: {stats.pass_percentage:.1f}%\n")
            f.write(
                f"Cache Hits: {stats.cache_hits} ({stats.cache_hit_percentage:.1f}%)\n"
            )
            f.write(f"{'=' * 50}\n")

    def _validate_test_directory(
        self, target_directory: Path, test_type: TestType
    ) -> bool:
        """Validate that the test directory exists"""
        if not target_directory.exists():
            logger.warning(
                f"{test_type.value} directory for model {self.model} not found: {target_directory}"
            )
            return False
        return True

    def _initialize_test_execution(
        self, test_files: list[Path], test_type: TestType
    ) -> None:
        """Initialize test execution statistics and print header"""
        self.statistics = TestExecutionStatistics()
        self.statistics.total_tests = len(test_files)

        print(
            f"Running {self.statistics.total_tests} {test_type.value.upper()} tests..."
        )
        print("-" * 50)

    def _execute_test_files(self, test_files: list[Path], test_type: TestType) -> None:
        """Execute all test files and track statistics"""
        for test_file in test_files:
            task_id = test_file.stem.replace("_", "/")
            test_runner_data = self.dataset_dict.get(task_id)

            if test_runner_data is None:
                logger.warning(
                    f"{test_type.value} file for task {task_id} not found in dataset"
                )
                continue

            success = self._execute_single_test(test_file, test_runner_data, test_type)

            if success:
                self.statistics.passed_tests += 1

            if test_runner_data.was_last_result_cached():
                self.statistics.cache_hits += 1

            # Add execution time to statistics
            execution_time = test_runner_data.get_last_execution_time()
            if execution_time is not None:
                self.statistics.add_execution_time(execution_time)

    def _execute_single_test(
        self, test_file: Path, test_runner_data: TestRunner, test_type: TestType
    ) -> bool:
        """Execute a single test file with the provided TestRunner data

        Args:
            test_file: Path to the test file
            test_runner_data: The TestRunner data for the task
            test_type: Type of test (HUMANEVAL, EBT, or PBT)

        Returns:
            True if the test passed, False otherwise
        """
        task_id = test_file.stem.replace("_", "/")
        test_execution_handler = TestExecutionHandler(test_runner_data)

        # Save test code if requested
        if self.save_test_code and test_type in (TestType.EBT, TestType.PBT):
            # Read the test file content
            test_content = test_file.read_text(encoding="utf-8")

            # Extract the actual test code
            from pbteval.utils.utils import extract_code_block

            test_code = extract_code_block(test_content)

            # Save the test code
            if test_type == TestType.EBT:
                saved = test_runner_data.save_ebt_test_code(
                    test_code=test_code,
                    task_id=task_id,
                    model=self.model,
                    use_canonical=self.use_canonical,
                )
            else:  # TestType.PBT
                saved = test_runner_data.save_pbt_test_code(
                    test_code=test_code,
                    task_id=task_id,
                    model=self.model,
                    use_canonical=self.use_canonical,
                )

            if saved:
                self.saved_test_count += 1

        # Print generated code for EBT and PBT tests
        if test_type in (TestType.EBT, TestType.PBT):
            test_execution_handler.print_generated_code(test_type, test_file)

        try:
            success = test_execution_handler.execute_test(test_type, test_file)
        except Exception as e:
            logger.error(f"Test execution failed for {task_id}: {e}")
            success = False

        # Print result with cache indicator and timing
        cache_indicator = (
            " (cached)" if test_execution_handler.was_last_result_cached() else ""
        )
        status = "passed" if success else "failed"

        # Format timing information
        execution_time = test_execution_handler.get_last_execution_time()
        timing_info = f" ({execution_time:.3f}s)" if execution_time is not None else ""

        print(
            f"{test_type.value} for task {task_id:13} {status}{cache_indicator}{timing_info}"
        )

        # Show detailed error message if test failed and show_failures is enabled
        if not success and self.show_failures:
            error_info = test_execution_handler.get_last_error_info()
            if error_info:
                print(f"  {error_info}")

        return success


class DirectPBTExecutor:
    """Executor for running PBT files directly with pytest"""

    @staticmethod
    def execute_pbt_file(pbt_file_path: Path) -> bool:
        """Run a specified PBT file directly with pytest

        Args:
            pbt_file_path: Path to the PBT file to run

        Returns:
            True if the test passed, False otherwise
        """
        if not pbt_file_path.exists():
            logger.error(f"PBT file not found: {pbt_file_path}")
            return False

        try:
            pbt_content = pbt_file_path.read_text(encoding="utf-8")
            pbt_code = extract_code_block(pbt_content)

            if not pbt_code.strip():
                logger.error(f"No code found in PBT file: {pbt_file_path}")
                return False

            return DirectPBTExecutor._execute_with_pytest(pbt_code, pbt_file_path)

        except Exception as e:
            logger.error(f"Error running PBT {pbt_file_path}: {e}")
            return False

    @staticmethod
    def _execute_with_pytest(pbt_code: str, pbt_file_path: Path) -> bool:
        """Execute PBT code using pytest in a temporary file"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as temp_file:
            temp_file.write(pbt_code)
            temp_file_path = temp_file.name

        try:
            result = subprocess.run(
                ["python", "-m", "pytest", temp_file_path, "-v"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            # Log results
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr)

            success = result.returncode == 0
            status = "passed" if success else "failed"
            print(f"PBT test {pbt_file_path.name}: {status}")

            return success

        except subprocess.TimeoutExpired:
            logger.error(f"PBT execution timed out: {pbt_file_path}")
            return False
        finally:
            # Clean up temporary file
            Path(temp_file_path).unlink(missing_ok=True)


# Command handlers
def handle_run_command(
    dataset_path: Path,
    model: str,
    test_type: TestType,
    use_plus_tests: bool = False,
    save_test_code: bool = False,
    show_failures: bool = False,
    log_failures: bool = False,
) -> None:
    """Handle run command with comprehensive test execution logic

    Args:
        dataset_path: Path to dataset file
        model: Model name
        test_type: Type of test to run
        use_plus_tests: Whether to use HumanEval+ test cases
        save_test_code: Whether to save test code to files
        show_failures: Whether to show detailed error messages for failed tests
        log_failures: Whether to save detailed failure logs to file

    Raises:
        ValueError: If unsupported test type is provided
        Exception: If test execution fails
    """
    executor = TestExecutor(
        dataset_path,
        model,
        use_plus_tests=use_plus_tests,
        save_test_code=save_test_code,
        show_failures=show_failures,
        log_failures=log_failures,
    )
    executor.execute_all_tests(test_type)


def handle_run_ebt_canonical_command(
    model: str,
    dataset_type: Literal["standard", "plus"] = "standard",
    show_failures: bool = False,
    save_test_code: bool = False,
) -> None:
    """Handle run EBT canonical command with canonical solutions

    Args:
        model: Model name
        dataset_type: Dataset source for canonical solutions ("standard" or "plus")
        show_failures: Whether to show detailed error messages for failed tests
        save_test_code: Whether to save test code to files

    Raises:
        Exception: If test execution fails
    """
    # Pass a dummy path since canonical mode doesn't use it
    from pbteval.constants import DEFAULT_DATASET_PATH

    executor = TestExecutor(
        DEFAULT_DATASET_PATH,
        model,
        use_canonical=True,
        dataset_type=dataset_type,
        show_failures=show_failures,
        save_test_code=save_test_code,
    )
    executor.execute_all_tests(TestType.EBT)


def handle_run_pbt_canonical_command(
    model: str,
    dataset_type: Literal["standard", "plus"] = "standard",
    show_failures: bool = False,
    save_test_code: bool = False,
) -> None:
    """Handle run PBT canonical command with canonical solutions

    Args:
        model: Model name
        dataset_type: Dataset source for canonical solutions ("standard" or "plus")
        show_failures: Whether to show detailed error messages for failed tests
        save_test_code: Whether to save test code to files

    Raises:
        Exception: If test execution fails
    """
    # Pass a dummy path since canonical mode doesn't use it
    from pbteval.constants import DEFAULT_DATASET_PATH

    executor = TestExecutor(
        DEFAULT_DATASET_PATH,
        model,
        use_canonical=True,
        dataset_type=dataset_type,
        show_failures=show_failures,
        save_test_code=save_test_code,
    )
    executor.execute_all_tests(TestType.PBT)


def handle_run_command_canonical(
    dataset_path: Path,
    model: str,
    test_type: TestType,
    use_plus_tests: bool = False,
    dataset_type: Literal["standard", "plus"] | None = None,
    save_test_code: bool = False,
    show_failures: bool = False,
    log_failures: bool = False,
) -> None:
    """Handle run command with canonical solutions

    Args:
        dataset_path: Path to dataset file
        model: Model name
        test_type: Type of test to run
        use_plus_tests: Whether to use HumanEval+ test cases
        dataset_type: Specify dataset source for canonical solutions ("standard" or "plus")
        save_test_code: Whether to save test code to files
        show_failures: Whether to show detailed error messages for failed tests
        log_failures: Whether to save detailed failure logs to file

    Raises:
        ValueError: If unsupported test type is provided
        Exception: If test execution fails
    """
    executor = TestExecutor(
        dataset_path,
        model,
        use_canonical=True,
        use_plus_tests=use_plus_tests,
        dataset_type=dataset_type,
        save_test_code=save_test_code,
        show_failures=show_failures,
        log_failures=log_failures,
    )
    executor.execute_all_tests(test_type)


def handle_run_specified_pbt_command(pbt_file: Path) -> bool:
    """Handle run specified PBT command for direct file execution

    Args:
        pbt_file: Path to the PBT file to run

    Returns:
        True if successful, False otherwise

    Raises:
        Exception: If test execution fails
    """
    return DirectPBTExecutor.execute_pbt_file(pbt_file)
