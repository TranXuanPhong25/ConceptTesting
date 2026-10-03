import json
import os
from collections.abc import Callable
from enum import Enum
from pathlib import Path
from typing import assert_never

from dotenv import load_dotenv
from openai import OpenAI

from pbteval.commands.models import fetch_models
from pbteval.constants import (
    EBT_EXTENSION,
    EBT_PROMPT_FILENAME,
    OUTPUT_BASE_DIR,
    PBT_EXTENSION,
    PBT_PROMPT_FILENAME,
    PROMPTS_DIR,
)
from pbteval.core.data import JsonData, UsageInfo
from pbteval.core.exceptions import DatasetError, GenerationError, ModelError
from pbteval.utils.logger import get_logger
from pbteval.utils.utils import normalize_task_id, safe_read_file

logger = get_logger(__name__)


class TestType(Enum):
    """Test type enumeration for type safety"""

    HUMANEVAL = "humaneval"
    EBT = "ebt"
    PBT = "pbt"


load_dotenv()

# Cache for model pricing information
_model_pricing_cache: dict[str, dict[str, str]] | None = None


def get_model_pricing(model_id: str) -> dict[str, str] | None:
    """Get pricing information for a specific model.

    Args:
        model_id: The model ID (e.g., "openai/gpt-4o-mini")

    Returns:
        Dictionary with prompt and completion pricing, or None if not found
    """
    global _model_pricing_cache

    if _model_pricing_cache is None:
        try:
            models = fetch_models()
            _model_pricing_cache = {
                model["id"]: {
                    "prompt": model["pricing"]["prompt"],
                    "completion": model["pricing"]["completion"],
                }
                for model in models
            }
        except ModelError as e:
            logger.warning(f"Failed to fetch model pricing: {e}")
            return None

    return _model_pricing_cache.get(model_id)


def calculate_cost(usage_data: dict[str, int | float], model: str) -> UsageInfo:
    """Calculate cost based on usage data and model pricing.

    Args:
        usage_data: Usage data from OpenRouter API response
        model: Model ID used for generation

    Returns:
        UsageInfo object with token counts and cost information
    """
    prompt_tokens = int(usage_data.get("prompt_tokens", 0))
    completion_tokens = int(usage_data.get("completion_tokens", 0))
    total_tokens = int(
        usage_data.get("total_tokens", prompt_tokens + completion_tokens)
    )

    # Get model pricing
    pricing = get_model_pricing(model)

    prompt_cost = 0.0
    completion_cost = 0.0

    if pricing:
        try:
            # OpenRouter API returns per-token prices
            prompt_price_per_token = float(pricing.get("prompt", "0"))
            completion_price_per_token = float(pricing.get("completion", "0"))

            prompt_cost = prompt_tokens * prompt_price_per_token
            completion_cost = completion_tokens * completion_price_per_token
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to parse pricing for model {model}: {e}")

    return UsageInfo(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        model=model,
        prompt_cost=prompt_cost,
        completion_cost=completion_cost,
    )


def format_cost_string(cost: float) -> str:
    """Format cost value for display.

    Args:
        cost: Cost value in dollars

    Returns:
        Formatted cost string
    """
    if cost <= 0:
        return "Cost unavailable"
    elif cost < 0.000001:
        return "< $0.000001"
    else:
        return f"${cost:.6f}"


def format_cost_info(usage_info: UsageInfo) -> str:
    """Format usage and cost information for display.

    Args:
        usage_info: Usage information to format

    Returns:
        Formatted cost information string
    """
    cost_str = format_cost_string(usage_info.total_cost)

    return (
        f"Usage: {usage_info.prompt_tokens:,} prompt + {usage_info.completion_tokens:,} completion "
        f"= {usage_info.total_tokens:,} total tokens | Cost: {cost_str}"
    )


def get_output_directory(model: str, test_type: TestType) -> Path:
    """Generate output directory path for test files

    Args:
        model: Model name (e.g., "gpt-4o-mini")
        test_type: Type of test (TestType.HUMANEVAL, TestType.EBT, TestType.PBT)

    Returns:
        Path object for the output directory
    """
    safe_model = model.replace("-", "_")
    return OUTPUT_BASE_DIR / test_type.value / safe_model


def get_output_path(task_id: str, model: str, test_type: TestType) -> Path:
    """Generate output path for test files

    Args:
        task_id: Task ID (e.g., "HumanEval/0")
        model: Model name (e.g., "gpt-4o-mini")
        test_type: Type of test (TestType.HUMANEVAL, TestType.EBT, TestType.PBT)

    Returns:
        Path object for the output file
    """
    safe_task_id = normalize_task_id(task_id)
    directory = get_output_directory(model, test_type)

    # Use appropriate extension based on test type
    extension = EBT_EXTENSION if test_type == TestType.EBT else PBT_EXTENSION
    return directory / f"{safe_task_id}{extension}"


def load_dataset(dataset_path: Path) -> list[JsonData]:
    """Load data from a dataset file

    Args:
        dataset_path: Path to the dataset file

    Returns:
        List of data

    Raises:
        DatasetError: If the dataset file is not found or invalid
    """
    if not dataset_path.exists():
        raise DatasetError(f"Dataset file not found: {dataset_path}")

    try:
        with dataset_path.open("r") as f:
            data = json.load(f)
            return [JsonData(**item) for item in data]
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        raise DatasetError(f"Invalid dataset format in {dataset_path}: {e}") from e


def find_task_by_id(data_list: list[JsonData], task_id: str) -> JsonData:
    """Get data corresponding to a task ID

    Args:
        data_list: List of data
        task_id: Task ID

    Returns:
        Corresponding data

    Raises:
        DatasetError: If data corresponding to the task ID is not found
    """
    target_data = next((data for data in data_list if data.task_id == task_id), None)
    if target_data is None:
        raise DatasetError(f"Task ID {task_id} not found in the dataset")
    return target_data


def _create_prompt(function_prompt: str, test_type: TestType) -> str:
    """Create a prompt for test generation

    Args:
        function_prompt: Function prompt
        test_type: Type of test to generate

    Returns:
        Prompt for test generation

    Raises:
        GenerationError: If prompt template file is not found
    """
    # Different prompt file paths based on test type
    match test_type:
        case TestType.EBT:
            prompt_file_path = PROMPTS_DIR / EBT_PROMPT_FILENAME
        case TestType.PBT:
            prompt_file_path = PROMPTS_DIR / PBT_PROMPT_FILENAME
        case TestType.HUMANEVAL:
            # HumanEval doesn't use prompt generation, but we need this case for type safety
            raise GenerationError("HumanEval tests don't require prompt generation")
        case _:
            assert_never(test_type)

    prompt_template = safe_read_file(prompt_file_path)
    if not prompt_template:
        raise GenerationError(
            f"Prompt template file not found or empty: {prompt_file_path}"
        )

    return f"""
{prompt_template}

**Input Code Snippet**
```python
{function_prompt}
```
"""


def create_ebt_prompt(function_prompt: str) -> str:
    """Create a prompt for EBT generation

    Args:
        function_prompt: Function prompt

    Returns:
        Prompt for EBT generation
    """
    return _create_prompt(function_prompt, TestType.EBT)


def create_pbt_prompt(function_prompt: str) -> str:
    """Create a prompt for PBT generation

    Args:
        function_prompt: Function prompt

    Returns:
        Prompt for PBT generation
    """
    return _create_prompt(function_prompt, TestType.PBT)


def _generate_test(
    task_id: str,
    dataset_path: Path,
    model: str,
    prompt_creator: Callable[[str], str],
) -> tuple[str, UsageInfo]:
    """Generic test generation function

    Args:
        task_id: Task ID
        dataset_path: Path to the dataset file
        model: OpenRouter model to use for generation
        prompt_creator: Function to create the prompt

    Returns:
        Tuple of (generated test content, usage information)

    Raises:
        FileNotFoundError: If the dataset file is not found
        ValueError: If data corresponding to the task ID is not found, or if the OpenRouter API key is not set
    """
    data_list = load_dataset(dataset_path)
    target_data = find_task_by_id(data_list, task_id)

    # Validate API key
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY environment variable is not set")

    # Create prompt
    prompt = prompt_creator(target_data.prompt)

    # Generate test using OpenRouter API
    client = OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "https://github.com/NAIST-SE/PbtEval",
            "X-Title": "PbtEval",
        },
    )
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You are a code developer assistant.",
            },
            {"role": "user", "content": prompt},
        ],
        extra_body={
            "usage": {"include": True}  # Enable usage accounting
        },
    )

    # Extract generated content
    generated_content = response.choices[0].message.content or ""

    # Extract usage information and calculate costs
    usage_data = response.usage
    if usage_data:
        usage_info = calculate_cost(usage_data.model_dump(), model)
    else:
        # Fallback if usage data is not available
        logger.warning("Usage data not available in response")
        usage_info = UsageInfo(
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            model=model,
        )

    return generated_content, usage_info


def generate_ebt(task_id: str, dataset_path: Path, model: str) -> tuple[str, UsageInfo]:
    """Generate EBT for the specified task ID

    Args:
        task_id: Task ID
        dataset_path: Path to the dataset file
        model: OpenRouter model to use for generation

    Returns:
        Tuple of (generated EBT content, usage information)

    Raises:
        FileNotFoundError: If the dataset file is not found
        ValueError: If data corresponding to the task ID is not found, or if the OpenRouter API key is not set
    """
    return _generate_test(task_id, dataset_path, model, create_ebt_prompt)


def generate_pbt(task_id: str, dataset_path: Path, model: str) -> tuple[str, UsageInfo]:
    """Generate PBT for the specified task ID

    Args:
        task_id: Task ID
        dataset_path: Path to the dataset file
        model: OpenRouter model to use for generation

    Returns:
        Tuple of (generated PBT content, usage information)

    Raises:
        FileNotFoundError: If the dataset file is not found
        ValueError: If data corresponding to the task ID is not found, or if the OpenRouter API key is not set
    """
    return _generate_test(task_id, dataset_path, model, create_pbt_prompt)


def handle_generate_command(
    task_id: str,
    range_str: str | None,
    dataset_path: Path,
    model: str,
    test_type: TestType,
) -> None:
    """Handle generate command with all business logic

    Args:
        task_id: Task ID (e.g., HumanEval/0) or task prefix (e.g., HumanEval)
        range_str: Task range (e.g., 0-10, 0,5,10-15,20, all)
        dataset_path: Path to dataset file
        model: Model name
        test_type: Type of test to generate (EBT or PBT)

    Raises:
        Exception: If generation fails
    """
    # Choose the appropriate generation function
    if test_type == TestType.EBT:
        generate_func = generate_ebt
    elif test_type == TestType.PBT:
        generate_func = generate_pbt
    else:
        raise ValueError(f"Unsupported test type for generation: {test_type}")

    if "/" in task_id:
        # Single task ID
        _generate_single_task(task_id, dataset_path, model, generate_func, test_type)
    else:
        # Task range
        _generate_task_range(
            task_id, range_str, dataset_path, model, generate_func, test_type
        )


def _generate_single_task(
    task_id: str,
    dataset_path: Path,
    model: str,
    generate_func: Callable[[str, Path, str], tuple[str, UsageInfo]],
    test_type: TestType,
) -> None:
    """Generate test for a single task"""
    from pbteval.utils.utils import safe_write_file

    generated_code, usage_info = generate_func(task_id, dataset_path, model)
    output_path = get_output_path(task_id, model, test_type)
    safe_write_file(output_path, generated_code)

    # Display generation result with cost information
    print(f"Generated {test_type.value} for {task_id}: {output_path}")
    print(f"  {format_cost_info(usage_info)}")


def _generate_task_range(
    task_prefix: str,
    range_str: str | None,
    dataset_path: Path,
    model: str,
    generate_func: Callable[[str, Path, str], tuple[str, UsageInfo]],
    test_type: TestType,
) -> None:
    """Generate tests for a range of tasks"""
    from pbteval.utils.logger import get_logger
    from pbteval.utils.utils import parse_task_range, safe_write_file

    logger = get_logger(__name__)

    task_ids = parse_task_range(task_prefix, range_str)
    total_cost = 0.0
    total_tokens = 0
    successful_generations = 0

    for task_id in task_ids:
        try:
            generated_code, usage_info = generate_func(task_id, dataset_path, model)
            output_path = get_output_path(task_id, model, test_type)
            safe_write_file(output_path, generated_code)

            # Track totals for summary
            total_cost += usage_info.total_cost
            total_tokens += usage_info.total_tokens
            successful_generations += 1

            # Display individual result
            print(f"Generated {test_type.value} for {task_id}: {output_path}")

        except Exception as e:
            logger.error(f"Failed to generate {test_type.value} for {task_id}: {e}")
            continue

    # Display summary
    if successful_generations > 0:
        avg_cost = total_cost / successful_generations if total_cost > 0 else 0
        cost_str = format_cost_string(total_cost)
        avg_cost_str = format_cost_string(avg_cost)

        print(f"\nSummary: Generated {successful_generations} {test_type.value} tests")
        print(
            f"Total tokens: {total_tokens:,} | Total cost: {cost_str} | Avg cost: {avg_cost_str}"
        )
