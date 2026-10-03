"""CLI with hierarchical command structure for PbtEval."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from pbteval.commands.download import (
    download_humaneval,
    download_humaneval_plus,
    handle_download_command,
)
from pbteval.commands.evaluate import handle_evaluate_command
from pbteval.commands.filter import handle_filter_command
from pbteval.commands.generate import (
    TestType,
    handle_generate_command,
)
from pbteval.commands.models import (
    OutputFormat,
    SortBy,
    handle_list_models_command,
)
from pbteval.commands.prompt import handle_show_prompt_command
from pbteval.commands.report import handle_report_command
from pbteval.commands.run_tests import (
    handle_run_command,
    handle_run_ebt_canonical_command,
    handle_run_pbt_canonical_command,
    handle_run_specified_pbt_command,
)
from pbteval.constants import DEFAULT_DATASET_PATH, DEFAULT_MODEL
from pbteval.core.cache import (
    handle_cache_stats_command,
    handle_clear_cache_command,
)
from pbteval.core.exceptions import handle_error_and_exit
from pbteval.utils.logger import get_logger, setup_logger

logger = get_logger(__name__)


class CommandGroup:
    """Base class for command groups"""

    def __init__(self, name: str, description: str) -> None:
        self.name = name
        self.description = description

    def add_subcommands(
        self, subparsers: argparse._SubParsersAction[argparse.ArgumentParser]
    ) -> None:
        """Add subcommands to the parser"""
        raise NotImplementedError


class DatasetCommandGroup(CommandGroup):
    """Dataset management commands"""

    def __init__(self) -> None:
        super().__init__("dataset", "Dataset management operations")

    def add_subcommands(
        self, subparsers: argparse._SubParsersAction[argparse.ArgumentParser]
    ) -> None:
        """Add dataset-related subcommands"""
        dataset_parser = subparsers.add_parser(self.name, help=self.description)
        dataset_subparsers = dataset_parser.add_subparsers(
            dest="dataset_action", help="Dataset actions"
        )

        # Download command
        download_parser = dataset_subparsers.add_parser(
            "download", help="Download datasets"
        )
        download_parser.add_argument(
            "dataset_type",
            nargs="?",
            default="all",
            choices=["agentcoder", "humaneval", "humaneval-plus", "all"],
            help="Type of dataset to download (default: all)",
        )
        download_parser.add_argument(
            "--source",
            default="huggingface",
            choices=["huggingface", "github"],
            help="Download source for HumanEval datasets (default: huggingface)",
        )
        download_parser.set_defaults(func=self.handle_download)

        # List command
        list_parser = dataset_subparsers.add_parser(
            "list", help="List available datasets"
        )
        list_parser.set_defaults(func=self.handle_list)

        # Info command
        info_parser = dataset_subparsers.add_parser(
            "info", help="Show dataset information"
        )
        info_parser.add_argument("dataset_path", type=Path, help="Path to dataset file")
        info_parser.set_defaults(func=self.handle_info)

    def handle_download(self, args: argparse.Namespace) -> None:
        """Handle dataset download command"""
        try:
            source = args.source
            source_msg = (
                f" from {source.title()}"
                if args.dataset_type in ["humaneval", "humaneval-plus", "all"]
                else ""
            )

            if args.dataset_type == "all":
                print(f"Downloading all datasets{source_msg}...")
                print("=" * 50)

                # Download AgentCoder dataset
                print("1/3 Downloading AgentCoder dataset...")
                handle_download_command()

                # Download HumanEval dataset
                print(f"2/3 Downloading HumanEval dataset from {source.title()}...")
                download_humaneval(source)

                # Download HumanEval+ dataset
                print(f"3/3 Downloading HumanEval+ dataset from {source.title()}...")
                download_humaneval_plus(source)

                print("=" * 50)
                print("All datasets downloaded successfully!")
            elif args.dataset_type == "humaneval-plus":
                download_humaneval_plus(source)
            elif args.dataset_type == "humaneval":
                download_humaneval(source)
            elif args.dataset_type == "agentcoder":
                handle_download_command()
        except Exception as e:
            handle_error_and_exit(f"downloading {args.dataset_type} dataset", e)

    def handle_list(self, _args: argparse.Namespace) -> None:
        """Handle dataset list command"""
        dataset_dir = Path("dataset")
        if not dataset_dir.exists():
            print("No dataset directory found. Run 'pbteval dataset download' first.")
            return

        print("Available datasets:")
        for file in dataset_dir.glob("*.json*"):
            print(f"  {file.name}")

    def handle_info(self, args: argparse.Namespace) -> None:
        """Handle dataset info command"""
        import json

        dataset_path = args.dataset_path
        if not dataset_path.exists():
            print(f"Dataset file not found: {dataset_path}")
            return

        try:
            if dataset_path.suffix == ".json":
                with dataset_path.open() as f:
                    data = json.load(f)
                    print(f"Dataset: {dataset_path.name}")
                    print("Format: JSON")
                    print(f"Items: {len(data)}")
            elif dataset_path.suffix == ".jsonl":
                lines = [
                    line
                    for line in dataset_path.read_text().splitlines()
                    if line.strip()
                ]
                print(f"Dataset: {dataset_path.name}")
                print("Format: JSONL")
                print(f"Items: {len(lines)}")

                # Show sample task_id if available
                if lines:
                    sample = json.loads(lines[0])
                    if "task_id" in sample:
                        print(f"Sample task_id: {sample['task_id']}")
        except Exception as e:
            print(f"Error reading dataset: {e}")


class GenerateCommandGroup(CommandGroup):
    """Test generation commands"""

    def __init__(self) -> None:
        super().__init__("generate", "Generate test cases")

    def add_subcommands(
        self, subparsers: argparse._SubParsersAction[argparse.ArgumentParser]
    ) -> None:
        """Add generate-related subcommands"""
        generate_parser = subparsers.add_parser(self.name, help=self.description)
        generate_subparsers = generate_parser.add_subparsers(
            dest="generate_action", help="Generation actions"
        )

        # EBT generation
        ebt_parser = generate_subparsers.add_parser(
            "ebt", help="Generate Example-Based Tests"
        )
        self._add_common_generate_args(ebt_parser)
        ebt_parser.set_defaults(func=self.handle_generate_ebt)

        # PBT generation
        pbt_parser = generate_subparsers.add_parser(
            "pbt", help="Generate Property-Based Tests"
        )
        self._add_common_generate_args(pbt_parser)
        pbt_parser.set_defaults(func=self.handle_generate_pbt)

        # Generate all
        all_parser = generate_subparsers.add_parser(
            "all", help="Generate both EBT and PBT tests"
        )
        self._add_common_generate_args(all_parser)
        all_parser.set_defaults(func=self.handle_generate_all)

    def _add_common_generate_args(self, parser: argparse.ArgumentParser) -> None:
        """Add common arguments for generation commands"""
        parser.add_argument(
            "task_id",
            help="Task ID (e.g., HumanEval/0) or task prefix (e.g., HumanEval)",
        )
        parser.add_argument(
            "-r", "--range", help="Task range (e.g., 0-10, 0,5,10-15,20, all)"
        )
        parser.add_argument(
            "-m",
            "--model",
            default=DEFAULT_MODEL,
            help=f"Model name (default: {DEFAULT_MODEL})",
        )

    def handle_generate_ebt(self, args: argparse.Namespace) -> None:
        """Handle EBT generation"""
        try:
            handle_generate_command(
                args.task_id, args.range, DEFAULT_DATASET_PATH, args.model, TestType.EBT
            )
        except Exception as e:
            handle_error_and_exit(f"generating {TestType.EBT.value}", e)

    def handle_generate_pbt(self, args: argparse.Namespace) -> None:
        """Handle PBT generation"""
        try:
            handle_generate_command(
                args.task_id, args.range, DEFAULT_DATASET_PATH, args.model, TestType.PBT
            )
        except Exception as e:
            handle_error_and_exit(f"generating {TestType.PBT.value}", e)

    def handle_generate_all(self, args: argparse.Namespace) -> None:
        """Handle generation of both EBT and PBT"""
        try:
            print("Generating EBT tests...")
            handle_generate_command(
                args.task_id, args.range, DEFAULT_DATASET_PATH, args.model, TestType.EBT
            )
            print("Generating PBT tests...")
            handle_generate_command(
                args.task_id, args.range, DEFAULT_DATASET_PATH, args.model, TestType.PBT
            )
            print("Generation completed for both EBT and PBT tests.")
        except Exception as e:
            handle_error_and_exit("generating tests", e)


class RunCommandGroup(CommandGroup):
    """Test execution commands"""

    def __init__(self) -> None:
        super().__init__("run", "Execute test cases")

    def add_subcommands(
        self, subparsers: argparse._SubParsersAction[argparse.ArgumentParser]
    ) -> None:
        """Add run-related subcommands"""
        run_parser = subparsers.add_parser(self.name, help=self.description)
        run_subparsers = run_parser.add_subparsers(
            dest="run_action", help="Run actions"
        )

        # EBT execution
        ebt_parser = run_subparsers.add_parser("ebt", help="Run Example-Based Tests")
        self._add_common_run_args(ebt_parser)
        ebt_parser.add_argument(
            "--canonical", action="store_true", help="Use canonical solutions"
        )
        ebt_parser.add_argument(
            "--dataset-type",
            choices=["standard", "plus"],
            default="standard",
            help="Dataset source for canonical solutions (default: standard)",
        )
        ebt_parser.add_argument(
            "--show-failures",
            action="store_true",
            help="Show detailed error messages for failed tests",
        )
        ebt_parser.add_argument(
            "--save-test-code",
            action="store_true",
            help="Save generated test code to files",
        )
        ebt_parser.set_defaults(func=self.handle_run_ebt)

        # PBT execution
        pbt_parser = run_subparsers.add_parser("pbt", help="Run Property-Based Tests")
        self._add_common_run_args(pbt_parser)
        pbt_parser.add_argument(
            "--canonical", action="store_true", help="Use canonical solutions"
        )
        pbt_parser.add_argument(
            "--dataset-type",
            choices=["standard", "plus"],
            default="standard",
            help="Dataset source for canonical solutions (default: standard)",
        )
        pbt_parser.add_argument(
            "--show-failures",
            action="store_true",
            help="Show detailed error messages for failed tests",
        )
        pbt_parser.add_argument(
            "--save-test-code",
            action="store_true",
            help="Save generated test code to files",
        )
        pbt_parser.set_defaults(func=self.handle_run_pbt)

        # HumanEval execution
        humaneval_parser = run_subparsers.add_parser(
            "humaneval", help="Run HumanEval tests"
        )
        humaneval_parser.add_argument(
            "--plus",
            action="store_true",
            help="Use HumanEval+ test cases for more comprehensive testing",
        )
        humaneval_parser.add_argument(
            "--source-type",
            choices=["agentcoder", "canonical"],
            default="agentcoder",
            help="Source code type to test (default: agentcoder)",
        )
        humaneval_parser.add_argument(
            "--dataset-type",
            choices=["standard", "plus"],
            help="Dataset source for canonical solutions (only for --source-type canonical)",
        )
        humaneval_parser.add_argument(
            "--save-test-code",
            action="store_true",
            help="Save generated test code to files",
        )
        humaneval_parser.add_argument(
            "--show-failures",
            action="store_true",
            help="Show detailed error messages for failed tests",
        )
        humaneval_parser.add_argument(
            "--log-failures",
            action="store_true",
            help="Save detailed failure logs to file",
        )
        self._add_common_run_args(humaneval_parser)
        humaneval_parser.set_defaults(func=self.handle_run_humaneval)

        # File execution
        file_parser = run_subparsers.add_parser("file", help="Run specific test file")
        file_parser.add_argument("test_file", type=Path, help="Path to test file")
        file_parser.set_defaults(func=self.handle_run_file)

        # Run all
        all_parser = run_subparsers.add_parser("all", help="Run all test types")
        self._add_common_run_args(all_parser)
        all_parser.set_defaults(func=self.handle_run_all)

    def _add_common_run_args(self, parser: argparse.ArgumentParser) -> None:
        """Add common arguments for run commands"""
        parser.add_argument(
            "-m",
            "--model",
            default=DEFAULT_MODEL,
            help=f"Model name (default: {DEFAULT_MODEL})",
        )

    def handle_run_ebt(self, args: argparse.Namespace) -> None:
        """Handle EBT execution"""
        try:
            if args.canonical:
                from typing import Literal, cast

                dataset_type = cast(
                    Literal["standard", "plus"],
                    getattr(args, "dataset_type", "standard"),
                )
                handle_run_ebt_canonical_command(
                    args.model, dataset_type, args.show_failures, args.save_test_code
                )
            else:
                handle_run_command(
                    DEFAULT_DATASET_PATH,
                    args.model,
                    TestType.EBT,
                    show_failures=args.show_failures,
                    save_test_code=args.save_test_code,
                )
        except Exception as e:
            handle_error_and_exit("running EBT tests", e)

    def handle_run_pbt(self, args: argparse.Namespace) -> None:
        """Handle PBT execution"""
        try:
            if args.canonical:
                from typing import Literal, cast

                dataset_type = cast(
                    Literal["standard", "plus"],
                    getattr(args, "dataset_type", "standard"),
                )
                handle_run_pbt_canonical_command(
                    args.model, dataset_type, args.show_failures, args.save_test_code
                )
            else:
                handle_run_command(
                    DEFAULT_DATASET_PATH,
                    args.model,
                    TestType.PBT,
                    show_failures=args.show_failures,
                    save_test_code=args.save_test_code,
                )
        except Exception as e:
            handle_error_and_exit("running PBT tests", e)

    def handle_run_humaneval(self, args: argparse.Namespace) -> None:
        """Handle HumanEval execution"""
        try:
            # Always use the default dataset path
            dataset_path = DEFAULT_DATASET_PATH

            # Choose run function based on source type
            if args.source_type == "canonical":
                from pbteval.commands.run_tests import handle_run_command_canonical

                handle_run_command_canonical(
                    dataset_path,
                    args.model,
                    TestType.HUMANEVAL,
                    use_plus_tests=args.plus,
                    dataset_type=getattr(args, "dataset_type", None),
                    save_test_code=args.save_test_code,
                    show_failures=args.show_failures,
                    log_failures=args.log_failures,
                )
            else:  # agentcoder
                handle_run_command(
                    dataset_path,
                    args.model,
                    TestType.HUMANEVAL,
                    use_plus_tests=args.plus,
                    save_test_code=args.save_test_code,
                    show_failures=args.show_failures,
                    log_failures=args.log_failures,
                )
        except Exception as e:
            handle_error_and_exit("running HumanEval tests", e)

    def handle_run_file(self, args: argparse.Namespace) -> None:
        """Handle file execution"""
        try:
            success = handle_run_specified_pbt_command(args.test_file)
            if not success:
                sys.exit(1)
        except Exception as e:
            handle_error_and_exit("running test file", e)

    def handle_run_all(self, args: argparse.Namespace) -> None:
        """Handle running all test types"""
        try:
            print("Running EBT tests...")
            handle_run_command(DEFAULT_DATASET_PATH, args.model, TestType.EBT)
            print("Running PBT tests...")
            handle_run_command(DEFAULT_DATASET_PATH, args.model, TestType.PBT)
            print("Running HumanEval tests...")
            handle_run_command(DEFAULT_DATASET_PATH, args.model, TestType.HUMANEVAL)
            print("All tests completed.")
        except Exception as e:
            handle_error_and_exit("running all tests", e)


class AnalyzeCommandGroup(CommandGroup):
    """Analysis and reporting commands"""

    def __init__(self) -> None:
        super().__init__("analyze", "Analyze test results")

    def add_subcommands(
        self, subparsers: argparse._SubParsersAction[argparse.ArgumentParser]
    ) -> None:
        """Add analyze-related subcommands"""
        analyze_parser = subparsers.add_parser(self.name, help=self.description)
        analyze_subparsers = analyze_parser.add_subparsers(
            dest="analyze_action", help="Analysis actions"
        )

        # Evaluate command
        evaluate_parser = analyze_subparsers.add_parser(
            "evaluate", help="Run comprehensive evaluation"
        )
        evaluate_parser.add_argument(
            "-m",
            "--model",
            default=DEFAULT_MODEL,
            help=f"Model name (default: {DEFAULT_MODEL})",
        )
        evaluate_parser.set_defaults(func=self.handle_evaluate)

        # Report command
        report_parser = analyze_subparsers.add_parser(
            "report", help="Generate comparison reports"
        )
        report_parser.add_argument(
            "task_id",
            help="Task ID (e.g., HumanEval/0) or task prefix (e.g., HumanEval)",
        )
        report_parser.add_argument(
            "-r", "--range", help="Task range (e.g., 0-10, 0,5,10-15,20, all)"
        )
        report_parser.add_argument(
            "-m",
            "--model",
            default=DEFAULT_MODEL,
            help=f"Model name (default: {DEFAULT_MODEL})",
        )
        report_parser.set_defaults(func=self.handle_report)

        # Filter command
        filter_parser = analyze_subparsers.add_parser(
            "filter", help="Filter test results"
        )
        filter_parser.add_argument(
            "-m",
            "--model",
            default=DEFAULT_MODEL,
            help=f"Model name for default CSV file path (default: {DEFAULT_MODEL})",
        )
        filter_parser.add_argument(
            "--csv-file", help="Path to CSV file to filter (overrides model-based path)"
        )
        filter_parser.add_argument(
            "-he",
            "--humaneval",
            choices=["true", "false"],
            help="Filter by HumanEval test result",
        )
        filter_parser.add_argument(
            "-e", "--ebt", choices=["true", "false"], help="Filter by EBT test result"
        )
        filter_parser.add_argument(
            "-p", "--pbt", choices=["true", "false"], help="Filter by PBT test result"
        )
        filter_parser.add_argument(
            "--output-format",
            choices=["list", "csv", "count"],
            default="list",
            help="Output format (default: list)",
        )
        filter_parser.set_defaults(func=self.handle_filter)

    def handle_evaluate(self, args: argparse.Namespace) -> None:
        """Handle evaluate command"""
        try:
            handle_evaluate_command(DEFAULT_DATASET_PATH, args.model)
        except Exception as e:
            handle_error_and_exit("running evaluation", e)

    def handle_report(self, args: argparse.Namespace) -> None:
        """Handle report command"""
        try:
            handle_report_command(
                args.task_id, args.model, args.range, DEFAULT_DATASET_PATH
            )
        except Exception as e:
            handle_error_and_exit("generating report", e)

    def handle_filter(self, args: argparse.Namespace) -> None:
        """Handle filter command"""
        try:
            handle_filter_command(
                args.model,
                args.csv_file,
                args.humaneval,
                args.ebt,
                args.pbt,
                args.output_format,
            )
        except Exception as e:
            handle_error_and_exit("filtering results", e)


class ModelCommandGroup(CommandGroup):
    """Command group for model operations"""

    def __init__(self) -> None:
        super().__init__("model", "List and explore available models")

    def add_subcommands(
        self, subparsers: argparse._SubParsersAction[argparse.ArgumentParser]
    ) -> None:
        """Add model subcommands"""
        model_parser = subparsers.add_parser(
            self.name, help=self.description, aliases=["models"]
        )
        model_subparsers = model_parser.add_subparsers(
            dest="model_action", help="Model actions"
        )

        # List models
        list_parser = model_subparsers.add_parser(
            "list", help="List available models from OpenRouter"
        )
        list_parser.add_argument(
            "--category",
            "-c",
            type=str,
            help="Filter by category (e.g., programming)",
        )
        list_parser.add_argument(
            "--format",
            "-f",
            type=OutputFormat,
            choices=list(OutputFormat),
            default=OutputFormat.TABLE,
            help="Output format (default: table)",
        )
        list_parser.add_argument(
            "--sort",
            "-s",
            type=SortBy,
            choices=list(SortBy),
            default=SortBy.NAME,
            help="Sort criteria (default: name)",
        )
        list_parser.add_argument(
            "--search",
            type=str,
            help="Search models by name or description",
        )
        list_parser.set_defaults(func=self.handle_list)

    def handle_list(self, args: argparse.Namespace) -> None:
        """Handle list models command"""
        try:
            handle_list_models_command(
                category=args.category,
                format=args.format,
                sort=args.sort,
                search=args.search,
            )
        except Exception as e:
            handle_error_and_exit("listing models", e)


class PromptCommandGroup(CommandGroup):
    """Prompt display commands"""

    def __init__(self) -> None:
        super().__init__("prompt", "Display and inspect prompts")

    def add_subcommands(
        self, subparsers: argparse._SubParsersAction[argparse.ArgumentParser]
    ) -> None:
        """Add prompt-related subcommands"""
        prompt_parser = subparsers.add_parser(self.name, help=self.description)
        prompt_subparsers = prompt_parser.add_subparsers(
            dest="prompt_action", help="Prompt actions"
        )

        # Show command
        show_parser = prompt_subparsers.add_parser(
            "show", help="Display prompts used for test generation"
        )
        show_parser.add_argument(
            "prompt_type",
            choices=["ebt", "pbt", "all"],
            help="Type of prompt to display (ebt, pbt, or all)",
        )
        show_parser.add_argument(
            "--raw",
            action="store_true",
            help="Show raw template only (without sample function code)",
        )
        show_parser.add_argument(
            "--task-id",
            type=str,
            help="Specific task ID to use for formatted prompt (e.g., HumanEval/0)",
        )
        show_parser.set_defaults(func=self.handle_show)

    def handle_show(self, args: argparse.Namespace) -> None:
        """Handle show prompt command"""
        try:
            handle_show_prompt_command(
                prompt_type=args.prompt_type,
                raw=args.raw,
                task_id=args.task_id,
            )
        except Exception as e:
            handle_error_and_exit("displaying prompt", e)


class CacheCommandGroup(CommandGroup):
    """Cache management commands"""

    def __init__(self) -> None:
        super().__init__("cache", "Cache management operations")

    def add_subcommands(
        self, subparsers: argparse._SubParsersAction[argparse.ArgumentParser]
    ) -> None:
        """Add cache-related subcommands"""
        cache_parser = subparsers.add_parser(self.name, help=self.description)
        cache_subparsers = cache_parser.add_subparsers(
            dest="cache_action", help="Cache actions"
        )

        # Stats command
        stats_parser = cache_subparsers.add_parser(
            "stats", help="Show cache statistics"
        )
        stats_parser.set_defaults(func=self.handle_stats)

        # Clear command
        clear_parser = cache_subparsers.add_parser("clear", help="Clear cache entries")
        clear_parser.add_argument(
            "target",
            nargs="?",
            default="all",
            choices=["all"],
            help="Target to clear (default: all)",
        )
        clear_parser.add_argument(
            "--model",
            type=str,
            help="Clear cache for specific model (e.g., anthropic/claude-sonnet-4)",
        )
        clear_parser.add_argument(
            "--type",
            type=str,
            choices=["ebt", "pbt"],
            help="Clear cache for specific test type",
        )
        clear_parser.add_argument(
            "--task",
            type=str,
            help="Clear cache for specific task (e.g., HumanEval/55)",
        )
        clear_parser.set_defaults(func=self.handle_clear)

    def handle_stats(self, _args: argparse.Namespace) -> None:
        """Handle cache stats command"""
        try:
            handle_cache_stats_command()
        except Exception as e:
            handle_error_and_exit("getting cache stats", e)

    def handle_clear(self, args: argparse.Namespace) -> None:
        """Handle cache clear command"""
        try:
            target = args.target
            model = getattr(args, "model", None)
            test_type = getattr(args, "type", None)
            task_id = getattr(args, "task", None)

            # Determine target type based on arguments
            if model or test_type or task_id:
                target = "filtered"

            handle_clear_cache_command(target, model, test_type, task_id)
        except Exception as e:
            handle_error_and_exit("clearing cache", e)


class PbtEvalCLI:
    """CLI with hierarchical command structure"""

    def __init__(self) -> None:
        self.command_groups = [
            DatasetCommandGroup(),
            GenerateCommandGroup(),
            RunCommandGroup(),
            AnalyzeCommandGroup(),
            ModelCommandGroup(),
            PromptCommandGroup(),
            CacheCommandGroup(),
        ]
        self.parser = self._create_main_parser()

    def _create_main_parser(self) -> argparse.ArgumentParser:
        """Create the main argument parser with hierarchical command groups"""
        parser = argparse.ArgumentParser(
            description="PbtEval: Property-Based Testing Evaluation Tool",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Command Groups:
  dataset     Download and manage datasets
  generate    Generate test cases (EBT/PBT)
  run         Execute test cases
  analyze     Analyze and report test results
  model       List and explore available models
  prompt      Display and inspect prompts
  cache       Manage cache operations

Examples:
  pbteval dataset download                # Download all datasets
  pbteval dataset download humaneval-plus # Download specific dataset
  pbteval generate ebt HumanEval/0
  pbteval run humaneval --plus
  pbteval analyze report HumanEval -r 0-10
  pbteval prompt show ebt                 # Show EBT prompt with sample
  pbteval prompt show all --raw           # Show both prompts without formatting
  pbteval cache stats
            """,
        )

        parser.add_argument(
            "--verbose",
            "-v",
            action="store_true",
            help="Enable detailed logging output",
        )

        subparsers = parser.add_subparsers(dest="command_group", help="Command groups")

        # Add all command groups
        for group in self.command_groups:
            group.add_subcommands(subparsers)

        return parser

    def parse_args(self) -> argparse.Namespace:
        """Parse command line arguments"""
        return self.parser.parse_args()

    def run(self) -> None:
        """Main entry point for CLI execution"""
        args = self.parse_args()

        # Setup logging
        if args.verbose:
            setup_logger(level=logging.INFO)
        else:
            setup_logger(level=logging.WARNING)

        # Execute command
        if hasattr(args, "func"):
            args.func(args)
        else:
            self.parser.print_help()


def main() -> None:
    """Main entry point"""
    cli = PbtEvalCLI()
    cli.run()


if __name__ == "__main__":
    main()
