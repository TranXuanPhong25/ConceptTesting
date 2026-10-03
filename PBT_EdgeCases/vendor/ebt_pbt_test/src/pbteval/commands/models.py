"""Commands for listing and exploring OpenRouter models."""

from __future__ import annotations

import json
from enum import Enum
from typing import TypedDict

import requests
from tabulate import tabulate

from pbteval.core.exceptions import ModelError
from pbteval.utils.logger import get_logger

logger = get_logger(__name__)


class OutputFormat(Enum):
    """Output format options for model listing."""

    TABLE = "table"
    JSON = "json"
    CSV = "csv"


class SortBy(Enum):
    """Sort options for model listing."""

    NAME = "name"
    PRICE = "price"
    CONTEXT = "context"


class Architecture(TypedDict):
    """Model architecture information."""

    input_modalities: list[str]
    output_modalities: list[str]
    tokenizer: str


class Pricing(TypedDict):
    """Model pricing information."""

    prompt: str
    completion: str


class ModelInfo(TypedDict):
    """Model information from OpenRouter API."""

    id: str
    name: str
    created: int
    description: str
    architecture: Architecture
    pricing: Pricing
    context_length: int


class ModelsResponse(TypedDict):
    """Response from OpenRouter models API."""

    data: list[ModelInfo]


def fetch_models(category: str | None = None) -> list[ModelInfo]:
    """Fetch available models from OpenRouter API.

    Args:
        category: Optional category filter (e.g., "programming")

    Returns:
        List of model information

    Raises:
        ModelError: If API request fails
    """
    url = "https://openrouter.ai/api/v1/models"
    params = {}
    if category:
        params["category"] = category

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data: ModelsResponse = response.json()
        return data["data"]
    except requests.RequestException as e:
        raise ModelError(f"Failed to fetch models from OpenRouter: {e}") from e
    except (json.JSONDecodeError, KeyError) as e:
        raise ModelError(f"Invalid response from OpenRouter API: {e}") from e


def filter_models(
    models: list[ModelInfo], search: str | None = None
) -> list[ModelInfo]:
    """Filter models by search term.

    Args:
        models: List of models to filter
        search: Search term to match against model name or description

    Returns:
        Filtered list of models
    """
    if not search:
        return models

    search_lower = search.lower()
    return [
        model
        for model in models
        if search_lower in model["name"].lower()
        or search_lower in model.get("description", "").lower()
    ]


def sort_models(models: list[ModelInfo], sort_by: SortBy) -> list[ModelInfo]:
    """Sort models by specified criteria.

    Args:
        models: List of models to sort
        sort_by: Sort criteria

    Returns:
        Sorted list of models
    """
    if sort_by == SortBy.NAME:
        return sorted(models, key=lambda m: m["name"])
    elif sort_by == SortBy.PRICE:
        # Sort by prompt price
        return sorted(
            models,
            key=lambda m: float(m["pricing"]["prompt"])
            if m["pricing"]["prompt"]
            else float("inf"),
        )
    elif sort_by == SortBy.CONTEXT:
        return sorted(models, key=lambda m: m.get("context_length", 0), reverse=True)
    else:
        return models


def format_price(price_str: str | None) -> str:
    """Format price string for display.

    Args:
        price_str: Price as string or None

    Returns:
        Formatted price string
    """
    if not price_str:
        return "N/A"
    try:
        price = float(price_str)
        if price == 0:
            return "Free"
        elif price < 0.000001:
            return f"${price * 1_000_000:.4f}/M"
        else:
            return f"${price * 1_000_000:.2f}/M"
    except ValueError:
        return price_str


def format_models_table(models: list[ModelInfo]) -> str:
    """Format models as a table.

    Args:
        models: List of models

    Returns:
        Formatted table string
    """
    headers = [
        "Model ID",
        "Name",
        "Context",
        "Input Price",
        "Output Price",
        "Modalities",
    ]
    rows = []

    for model in models:
        modalities = f"{','.join(model['architecture']['input_modalities'])} → {','.join(model['architecture']['output_modalities'])}"
        rows.append(
            [
                model["id"],
                model["name"],
                f"{model.get('context_length', 0):,}",
                format_price(model["pricing"]["prompt"]),
                format_price(model["pricing"]["completion"]),
                modalities,
            ]
        )

    return str(tabulate(rows, headers=headers, tablefmt="grid"))


def format_models_csv(models: list[ModelInfo]) -> str:
    """Format models as CSV.

    Args:
        models: List of models

    Returns:
        CSV formatted string
    """
    import csv
    import io

    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow(
        [
            "model_id",
            "name",
            "description",
            "context_length",
            "prompt_price",
            "completion_price",
            "input_modalities",
            "output_modalities",
            "tokenizer",
        ]
    )

    # Write data
    for model in models:
        writer.writerow(
            [
                model["id"],
                model["name"],
                model.get("description", ""),
                model.get("context_length", 0),
                model["pricing"]["prompt"],
                model["pricing"]["completion"],
                ",".join(model["architecture"]["input_modalities"]),
                ",".join(model["architecture"]["output_modalities"]),
                model["architecture"]["tokenizer"],
            ]
        )

    return output.getvalue()


def format_models_json(models: list[ModelInfo]) -> str:
    """Format models as JSON.

    Args:
        models: List of models

    Returns:
        JSON formatted string
    """
    return json.dumps(models, indent=2)


def handle_list_models_command(
    category: str | None = None,
    format: OutputFormat = OutputFormat.TABLE,
    sort: SortBy = SortBy.NAME,
    search: str | None = None,
) -> None:
    """Handle the list models command.

    Args:
        category: Optional category filter
        format: Output format
        sort: Sort criteria
        search: Search term

    Raises:
        ModelError: If fetching or processing fails
    """
    logger.info("Fetching available models from OpenRouter...")

    # Fetch models
    models = fetch_models(category)
    logger.info(f"Fetched {len(models)} models")

    # Filter by search term
    if search:
        models = filter_models(models, search)
        logger.info(f"Filtered to {len(models)} models matching '{search}'")

    # Sort models
    models = sort_models(models, sort)

    # Format output
    if format == OutputFormat.TABLE:
        output = format_models_table(models)
    elif format == OutputFormat.CSV:
        output = format_models_csv(models)
    elif format == OutputFormat.JSON:
        output = format_models_json(models)
    else:
        raise ModelError(f"Unknown format: {format}")

    print(output)
