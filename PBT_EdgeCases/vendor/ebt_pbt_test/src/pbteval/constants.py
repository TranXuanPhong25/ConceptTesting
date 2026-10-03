"""Global constants for PbtEval project."""

from pathlib import Path

# Directory paths
OUTPUT_BASE_DIR = Path("output")
RESULTS_DIR = OUTPUT_BASE_DIR / "results"
REPORT_DIR = OUTPUT_BASE_DIR / "report"
DATASET_DIR = Path("dataset")
PROMPTS_DIR = Path("prompts")
CACHE_DIR = Path(".pbteval_cache")

# File extensions
EBT_EXTENSION = ".txt"
PBT_EXTENSION = ".txt"
REPORT_EXTENSION = ".md"
CSV_EXTENSION = ".csv"

# Default values
DEFAULT_MODEL = "openai/gpt-4o-mini"
DEFAULT_DATASET_FILENAME = "gpt-3.5-turbo-1106.json"
DEFAULT_DATASET_PATH = DATASET_DIR / DEFAULT_DATASET_FILENAME

# HumanEval datasets
HUMANEVAL_FILENAME = "humaneval.jsonl"
HUMANEVAL_PATH = DATASET_DIR / HUMANEVAL_FILENAME
HUMANEVAL_PLUS_FILENAME = "humaneval_plus.jsonl"
HUMANEVAL_PLUS_PATH = DATASET_DIR / HUMANEVAL_PLUS_FILENAME

# Test execution
TEST_EXECUTION_TIMEOUT = 15  # seconds

# Cache
CACHE_VERSION = "1.0"
CACHE_FILENAME = "cache.json"
GITIGNORE_FILENAME = ".gitignore"

# Prompt files
EBT_PROMPT_FILENAME = "ebt_generation.txt"
PBT_PROMPT_FILENAME = "pbt_generation.txt"
