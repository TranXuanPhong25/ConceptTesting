from pathlib import Path
from typing import Literal

import requests

from pbteval.constants import DATASET_DIR, HUMANEVAL_PATH, HUMANEVAL_PLUS_PATH
from pbteval.core.exceptions import handle_error_and_exit
from pbteval.utils.logger import get_logger
from pbteval.utils.utils import validate_file_extension

logger = get_logger(__name__)


def _is_dataset_file(filename: str) -> bool:
    """Check if a file is a dataset file based on its extension"""
    return validate_file_extension(Path(filename), [".json", ".jsonl"])


def _download_file(url: str, destination: Path) -> None:
    """Download a file from URL to destination path

    Args:
        url: URL to download from
        destination: Path to save the file

    Raises:
        requests.RequestException: If download fails
    """
    logger.info(f"Downloading {url}")
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    destination.write_bytes(response.content)


def download_dataset() -> None:
    """
    Download specific AgentCoder dataset file (gpt-3.5-turbo-1106.json).
    """
    dataset_dir = Path("dataset")
    dataset_dir.mkdir(exist_ok=True)

    # Target specific file
    target_filename = "gpt-3.5-turbo-1106.json"
    url = "https://api.github.com/repos/huangd1999/AgentCoder/contents/dataset"
    headers = {"Accept": "application/vnd.github.v3+json"}

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        data = response.json()

        # Find the specific file
        target_file = None
        for item in data:
            if item["name"] == target_filename:
                target_file = item
                break

        if target_file is None:
            raise FileNotFoundError(
                f"Target file '{target_filename}' not found in repository"
            )

        # Download the specific file
        download_url = target_file["download_url"]
        item_path = dataset_dir / target_filename
        _download_file(download_url, item_path)

        logger.info(f"AgentCoder dataset downloaded successfully: {item_path}")
    except requests.RequestException as e:
        handle_error_and_exit("downloading dataset", e)
    except FileNotFoundError as e:
        handle_error_and_exit("finding target dataset file", e)


def download_humaneval_from_github() -> None:
    """Download HumanEval dataset from GitHub (via HTTP API as fallback)

    Tries direct GitHub download first, then falls back to HTTP API.

    Raises:
        requests.RequestException: If download fails
        Exception: If download fails
    """
    dataset_dir = DATASET_DIR
    dataset_dir.mkdir(exist_ok=True)

    try:
        logger.info("Downloading HumanEval dataset from GitHub...")

        # Download from OpenAI's official repository
        url = "https://raw.githubusercontent.com/openai/human-eval/master/data/HumanEval.jsonl.gz"
        output_path = HUMANEVAL_PATH

        # Download compressed file and decompress
        import gzip
        import tempfile

        with tempfile.NamedTemporaryFile() as temp_file:
            _download_file(url, Path(temp_file.name))

            # Decompress the file
            with gzip.open(temp_file.name, "rb") as gz_file:
                output_path.write_bytes(gz_file.read())

        # Count items in the downloaded file
        with output_path.open("r", encoding="utf-8") as f:
            item_count = sum(1 for line in f if line.strip())

        logger.info(
            f"HumanEval dataset downloaded successfully: {output_path} ({item_count} items)"
        )

    except Exception as e:
        handle_error_and_exit("downloading HumanEval dataset from GitHub", e)


def download_humaneval_plus_from_github() -> None:
    """Download HumanEval+ dataset from GitHub

    Downloads from the official EvalPlus release repository:
    https://github.com/evalplus/humanevalplus_release

    Raises:
        requests.RequestException: If download fails
        Exception: If download fails
    """
    dataset_dir = DATASET_DIR
    dataset_dir.mkdir(exist_ok=True)

    try:
        logger.info("Downloading HumanEval+ dataset from GitHub...")

        # Download from EvalPlus official release repository
        url = "https://raw.githubusercontent.com/evalplus/humanevalplus_release/main/HumanEvalPlus.jsonl.gz"
        output_path = HUMANEVAL_PLUS_PATH

        # Download compressed file and decompress
        import gzip
        import tempfile

        with tempfile.NamedTemporaryFile() as temp_file:
            _download_file(url, Path(temp_file.name))

            # Decompress the file
            with gzip.open(temp_file.name, "rb") as gz_file:
                output_path.write_bytes(gz_file.read())

        # Count items in the downloaded file
        with output_path.open("r", encoding="utf-8") as f:
            item_count = sum(1 for line in f if line.strip())

        logger.info(
            f"HumanEval+ dataset downloaded successfully: {output_path} ({item_count} items)"
        )

    except Exception as e:
        handle_error_and_exit("downloading HumanEval+ dataset from GitHub", e)


def download_humaneval_plus(
    source: Literal["huggingface", "github"] = "huggingface",
) -> None:
    """Download HumanEval+ dataset from specified source

    Args:
        source: Download source ('huggingface' or 'github')

    Raises:
        ImportError: If datasets library is not available (for huggingface source)
        Exception: If download fails
    """
    if source == "github":
        download_humaneval_plus_from_github()
        return
    try:
        import json

        from datasets import load_dataset  # type: ignore[import-untyped]
    except ImportError:
        handle_error_and_exit(
            "downloading HumanEval+",
            ImportError("datasets library is required. Install with: uv add datasets"),
        )

    dataset_dir = Path("dataset")
    dataset_dir.mkdir(exist_ok=True)

    try:
        logger.info("Downloading HumanEval+ dataset from HuggingFace...")

        # Load HumanEval+ dataset
        dataset = load_dataset("evalplus/humanevalplus", split="test")

        # Save as JSONL
        output_path = HUMANEVAL_PLUS_PATH

        # Convert to list of dictionaries and save as JSONL
        with output_path.open("w", encoding="utf-8") as f:
            for item in dataset:
                json.dump(item, f, ensure_ascii=False)
                f.write("\n")

        logger.info(
            f"HumanEval+ dataset downloaded successfully: {output_path} ({len(dataset)} items)"
        )

    except Exception as e:
        handle_error_and_exit("downloading HumanEval+ dataset", e)


def download_humaneval(
    source: Literal["huggingface", "github"] = "huggingface",
) -> None:
    """Download HumanEval dataset from specified source

    Args:
        source: Download source ('huggingface' or 'github')

    Raises:
        ImportError: If datasets library is not available (for huggingface source)
        Exception: If download fails
    """
    if source == "github":
        download_humaneval_from_github()
        return
    try:
        import json

        from datasets import load_dataset
    except ImportError:
        handle_error_and_exit(
            "downloading HumanEval",
            ImportError("datasets library is required. Install with: uv add datasets"),
        )

    dataset_dir = DATASET_DIR
    dataset_dir.mkdir(exist_ok=True)

    try:
        logger.info("Downloading HumanEval dataset from HuggingFace...")

        # Load HumanEval dataset
        dataset = load_dataset("openai_humaneval", split="test")

        # Save as JSONL
        output_path = dataset_dir / "humaneval.jsonl"

        # Convert to list of dictionaries and save as JSONL
        with output_path.open("w", encoding="utf-8") as f:
            for item in dataset:
                json.dump(item, f, ensure_ascii=False)
                f.write("\n")

        logger.info(
            f"HumanEval dataset downloaded successfully: {output_path} ({len(dataset)} items)"
        )

    except Exception as e:
        handle_error_and_exit("downloading HumanEval dataset", e)


def handle_download_command() -> None:
    """Handle download command with all business logic

    Raises:
        Exception: If download fails
    """
    download_dataset()
