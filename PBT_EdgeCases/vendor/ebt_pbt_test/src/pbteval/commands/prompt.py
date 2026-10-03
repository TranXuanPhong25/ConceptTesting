"""Prompt display commands for PbtEval."""

from typing import Literal

from pbteval.constants import (
    DEFAULT_DATASET_PATH,
    EBT_PROMPT_FILENAME,
    PBT_PROMPT_FILENAME,
    PROMPTS_DIR,
)
from pbteval.core.data import (
    extract_dataset,
)
from pbteval.core.exceptions import DatasetError, GenerationError
from pbteval.utils.logger import get_logger
from pbteval.utils.utils import safe_read_file

logger = get_logger(__name__)


def display_prompt_template(prompt_type: Literal["ebt", "pbt"]) -> str:
    """Display raw prompt template for specified type.

    Args:
        prompt_type: Type of prompt to display ("ebt" or "pbt")

    Returns:
        Raw prompt template content

    Raises:
        GenerationError: If prompt file not found or empty
    """
    # Get the appropriate prompt filename
    prompt_filename = (
        EBT_PROMPT_FILENAME if prompt_type == "ebt" else PBT_PROMPT_FILENAME
    )
    prompt_file_path = PROMPTS_DIR / prompt_filename

    # Read prompt template
    prompt_template = safe_read_file(prompt_file_path)
    if not prompt_template:
        raise GenerationError(
            f"Prompt template file not found or empty: {prompt_file_path}"
        )

    return prompt_template


def display_formatted_prompt(
    prompt_type: Literal["ebt", "pbt"], task_id: str | None = None
) -> str:
    """Display formatted prompt with sample or specific function code.

    Args:
        prompt_type: Type of prompt to display ("ebt" or "pbt")
        task_id: Specific task ID to use (e.g., "HumanEval/0"),
                if None uses first task as sample

    Returns:
        Formatted prompt with function code

    Raises:
        DatasetError: If dataset or task not found
        GenerationError: If prompt template not found
    """
    # Get raw template
    prompt_template = display_prompt_template(prompt_type)

    # Load dataset to get function code
    try:
        data_list = extract_dataset(DEFAULT_DATASET_PATH)
    except Exception as e:
        raise DatasetError(f"Failed to load dataset: {e}") from e

    if not data_list:
        raise DatasetError("Dataset is empty")

    # Get function prompt
    if task_id:
        # Find specific task
        target_data = next(
            (data for data in data_list if data.task_id == task_id), None
        )
        if target_data is None:
            raise DatasetError(f"Task ID {task_id} not found in dataset")
        function_prompt = target_data.prompt  # type: ignore[attr-defined]
    else:
        # Use first task as sample
        function_prompt = data_list[0].prompt  # type: ignore[attr-defined]

    # Format the prompt
    formatted_prompt = f"""
{prompt_template}

**Input Code Snippet**
```python
{function_prompt}
```
"""

    return formatted_prompt


def handle_show_prompt_command(
    prompt_type: Literal["ebt", "pbt", "all"],
    raw: bool = False,
    task_id: str | None = None,
) -> None:
    """Handle show prompt command.

    Args:
        prompt_type: Type of prompt to show ("ebt", "pbt", or "all")
        raw: If True, show raw template only
        task_id: Specific task ID to use for formatted prompt

    Raises:
        Exception: If prompt display fails
    """
    try:
        if prompt_type == "all":
            # Show both EBT and PBT prompts
            print("=" * 60)
            print("EBT (Example-Based Testing) Prompt")
            print("=" * 60)

            if raw:
                content = display_prompt_template("ebt")
            else:
                content = display_formatted_prompt("ebt", task_id)
            print(content)

            print("\n" + "=" * 60)
            print("PBT (Property-Based Testing) Prompt")
            print("=" * 60)

            if raw:
                content = display_prompt_template("pbt")
            else:
                content = display_formatted_prompt("pbt", task_id)
            print(content)

        else:
            # Show single prompt type
            prompt_name = (
                "EBT (Example-Based Testing)"
                if prompt_type == "ebt"
                else "PBT (Property-Based Testing)"
            )
            print("=" * 60)
            print(f"{prompt_name} Prompt")
            print("=" * 60)

            if raw:
                content = display_prompt_template(prompt_type)
            else:
                content = display_formatted_prompt(prompt_type, task_id)
            print(content)

        # Show additional info
        if not raw and task_id:
            print(f"\n📋 Formatted with function from task: {task_id}")
        elif not raw:
            print("\n📋 Formatted with sample function (first task in dataset)")
        else:
            print("\n📋 Raw template (use --formatted for sample with function code)")

    except (DatasetError, GenerationError) as e:
        logger.error(f"Failed to display prompt: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error displaying prompt: {e}")
        raise
