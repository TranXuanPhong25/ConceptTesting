import hashlib
import json
import time
from pathlib import Path
from threading import Lock

from pbteval.constants import (
    CACHE_DIR,
    CACHE_FILENAME,
    CACHE_VERSION,
    GITIGNORE_FILENAME,
)
from pbteval.utils.logger import get_logger

logger = get_logger(__name__)

# Type aliases for better readability
CacheEntry = dict[str, bool | float | str | None]
CacheData = dict[str, str | dict[str, CacheEntry]]


class TestResultCache:
    """Cache system for test execution results with model/test-type based organization"""

    def __init__(self, cache_dir: Path | None = None):
        """
        Initialize cache system

        Args:
            cache_dir: Directory to store cache files
        """

        self.cache_dir = cache_dir or CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._create_gitignore()

        self.version = CACHE_VERSION
        self._locks: dict[str, Lock] = {}

    def _create_gitignore(self) -> None:
        """Create .gitignore file in cache directory to exclude it from git"""

        gitignore_path = self.cache_dir / GITIGNORE_FILENAME
        if not gitignore_path.exists():
            try:
                gitignore_content = "# PbtEval cache directory\n*\n"
                gitignore_path.write_text(gitignore_content, encoding="utf-8")
                logger.debug(f"Created .gitignore in {self.cache_dir}")
            except Exception as e:
                logger.warning(f"Failed to create .gitignore in {self.cache_dir}: {e}")

    def _get_lock(self, cache_file_path: Path) -> Lock:
        """Get or create a lock for a specific cache file"""
        lock_key = str(cache_file_path)
        if lock_key not in self._locks:
            self._locks[lock_key] = Lock()
        return self._locks[lock_key]

    def get_file_hash(self, file_path: Path) -> str:
        """
        Get hash of file content

        Args:
            file_path: Path to the file

        Returns:
            SHA256 hash of file content
        """
        if not file_path.exists():
            return ""
        try:
            content = file_path.read_text(encoding="utf-8")
            return hashlib.sha256(content.encode("utf-8")).hexdigest()
        except Exception as e:
            logger.warning(f"Failed to read file {file_path}: {e}")
            return ""

    def _get_model_from_path(self, test_file_path: Path) -> str:
        """Extract model name from test file path"""
        # Expected path structure: output/{test_type}/{provider}/{model}/...
        path_parts = test_file_path.parts

        # Find the test_type index
        test_type_index = -1
        for i, part in enumerate(path_parts):
            if part in ["ebt", "pbt"]:
                test_type_index = i
                break

        if test_type_index == -1 or test_type_index >= len(path_parts) - 2:
            return "unknown"

        # Extract provider/model from path
        remaining_parts = path_parts[test_type_index + 1 :]

        if len(remaining_parts) >= 3:
            # Format: output/{test_type}/{provider}/{model}/...
            provider = remaining_parts[0]
            model = remaining_parts[1]
            return f"{provider}/{model}"

        return "unknown"

    def _get_cache_file_path(self, model: str, test_type: str) -> Path:
        """Get cache file path for specific model and test type"""
        test_type_dir = self.cache_dir / test_type.lower()
        test_type_dir.mkdir(exist_ok=True)

        # Expected provider/model format (e.g., "openai/gpt-4o-mini")
        provider, model_name = model.split("/", 1)
        model_dir = test_type_dir / provider / model_name

        model_dir.mkdir(parents=True, exist_ok=True)
        return model_dir / CACHE_FILENAME

    def _load_cache_data(self, cache_file_path: Path) -> CacheData:
        """Load cache data from file"""
        if not cache_file_path.exists():
            return {"version": self.version, "entries": {}}

        try:
            with cache_file_path.open("r", encoding="utf-8") as f:
                data: CacheData = json.load(f)

            # Check version compatibility
            if data.get("version") != self.version:
                logger.debug(
                    f"Cache version mismatch in {cache_file_path.name}, resetting cache"
                )
                return {"version": self.version, "entries": {}}

            # Ensure proper structure
            if not isinstance(data.get("entries"), dict):
                return {"version": self.version, "entries": {}}

            return data
        except (json.JSONDecodeError, KeyError) as e:
            logger.debug(f"Invalid cache file {cache_file_path.name}: {e}")
            return {"version": self.version, "entries": {}}

    def _save_cache_data(self, cache_file_path: Path, cache_data: CacheData) -> None:
        """Save cache data to file"""
        try:
            with cache_file_path.open("w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Failed to save cache data to {cache_file_path}: {e}")

    def get_cache_key(
        self, test_file_path: Path, source_code: str, test_type: str
    ) -> str:
        """
        Generate cache key from test file path, source code, and test type

        Args:
            test_file_path: Path to the test file
            source_code: Source code content
            test_type: Type of test (EBT or PBT)

        Returns:
            SHA256 hash as cache key
        """
        normalized_path = str(test_file_path.resolve())
        combined = f"{test_type}:{normalized_path}:{source_code}"
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()

    def get_cached_result_with_validation(
        self, test_file_path: Path, source_code: str, test_type: str
    ) -> tuple[bool, str | None, float | None] | None:
        """
        Get cached result with file modification validation

        Args:
            test_file_path: Path to the test file
            source_code: Source code content
            test_type: Type of test (EBT or PBT)

        Returns:
            Tuple of (result, error_info, execution_time) if valid, None if cache miss or invalid
        """
        model = self._get_model_from_path(test_file_path)
        cache_file_path = self._get_cache_file_path(model, test_type)
        cache_key = self.get_cache_key(test_file_path, source_code, test_type)

        with self._get_lock(cache_file_path):
            cache_data = self._load_cache_data(cache_file_path)
            entries = cache_data.get("entries", {})

            # Ensure entries is a dict
            if not isinstance(entries, dict):
                return None

            if cache_key not in entries:
                return None

            entry = entries[cache_key]
            # Ensure entry is a dict
            if not isinstance(entry, dict):
                return None

            stored_file_hash = entry.get("file_hash", "")
            current_file_hash = self.get_file_hash(test_file_path)

            # Check if file has been modified
            if stored_file_hash != current_file_hash:
                logger.debug(
                    f"File {test_file_path.name} has been modified, invalidating cache"
                )
                # Remove invalid entry
                del entries[cache_key]
                self._save_cache_data(cache_file_path, cache_data)
                return None

            logger.debug(f"Cache hit for {test_type} {test_file_path.name}")
            result = entry.get("result")
            error_info = entry.get("error_info")
            execution_time = entry.get("execution_time")
            # Ensure error_info is str or None
            if error_info is not None and not isinstance(error_info, str):
                error_info = str(error_info)
            # Ensure execution_time is float or None
            if execution_time is not None and not isinstance(
                execution_time, int | float
            ):
                execution_time = None
            if isinstance(result, bool | int | str):
                return (bool(result), error_info, execution_time)
            else:
                return (False, error_info, execution_time)

    def cache_result_with_metadata(
        self,
        test_file_path: Path,
        source_code: str,
        test_type: str,
        result: bool,
        error_info: str | None = None,
        execution_time: float | None = None,
    ) -> None:
        """
        Cache test result with file metadata

        Args:
            test_file_path: Path to the test file
            source_code: Source code content
            test_type: Type of test (EBT or PBT)
            result: Test execution result
            error_info: Error information if test failed
            execution_time: Execution time in seconds
        """
        model = self._get_model_from_path(test_file_path)
        cache_file_path = self._get_cache_file_path(model, test_type)
        cache_key = self.get_cache_key(test_file_path, source_code, test_type)

        entry_data: CacheEntry = {
            "result": result,
            "timestamp": time.time(),
            "file_path": str(test_file_path.resolve()),
            "file_hash": self.get_file_hash(test_file_path),
            "test_type": test_type,
            "error_info": error_info,
            "execution_time": execution_time,
        }

        with self._get_lock(cache_file_path):
            cache_data = self._load_cache_data(cache_file_path)
            entries = cache_data.get("entries", {})

            # Ensure entries is a dict
            if not isinstance(entries, dict):
                entries = {}
                cache_data["entries"] = entries

            entries[cache_key] = entry_data
            self._save_cache_data(cache_file_path, cache_data)

        logger.debug(f"Cached {test_type} result for {test_file_path.name}")

    def clear_filtered_cache(
        self,
        model: str | None = None,
        test_type: str | None = None,
        task_id: str | None = None,
    ) -> int:
        """
        Clear cache entries based on filter criteria

        Args:
            model: Model name (e.g., "anthropic/claude-sonnet-4")
            test_type: Test type ("ebt" or "pbt")
            task_id: Task ID (e.g., "HumanEval/55")

        Returns:
            Number of cleared cache entries
        """
        cleared_count = 0

        # Search through all cache files
        for test_type_dir in self.cache_dir.iterdir():
            if not test_type_dir.is_dir():
                continue

            # Filter by test type if specified
            if test_type and test_type_dir.name.lower() != test_type.lower():
                continue

            # Walk through provider directories
            for provider_dir in test_type_dir.iterdir():
                if not provider_dir.is_dir():
                    continue

                # Walk through model directories
                for model_dir in provider_dir.iterdir():
                    if not model_dir.is_dir():
                        continue

                    # Filter by model if specified
                    if model:
                        current_model = f"{provider_dir.name}/{model_dir.name}"
                        # Normalize both model names by converting hyphens to underscores for comparison
                        normalized_current = current_model.replace("-", "_")
                        normalized_input = model.replace("-", "_")
                        if normalized_current != normalized_input:
                            continue

                    cache_file_path = model_dir / "cache.json"
                    if not cache_file_path.exists():
                        continue

                    with self._get_lock(cache_file_path):
                        cache_data = self._load_cache_data(cache_file_path)
                        entries = cache_data.get("entries", {})

                        # Ensure entries is a dict
                        if not isinstance(entries, dict):
                            continue

                        # Find and remove entries matching the criteria
                        keys_to_remove = []
                        for key, entry in entries.items():
                            if not isinstance(entry, dict):
                                continue

                            # Filter by task_id if specified
                            if task_id:
                                file_path = entry.get("file_path", "")
                                if isinstance(file_path, str):
                                    # Extract task ID from file path
                                    # Format: .../HumanEval_55.txt -> HumanEval/55
                                    file_name = Path(file_path).stem
                                    if "_" in file_name:
                                        extracted_task_id = file_name.replace("_", "/")
                                        if extracted_task_id != task_id:
                                            continue
                                    else:
                                        continue
                                else:
                                    continue

                            keys_to_remove.append(key)

                        for key in keys_to_remove:
                            entry = entries[key]
                            del entries[key]
                            cleared_count += 1
                            if isinstance(entry, dict):
                                file_path = entry.get("file_path", "unknown")
                                logger.debug(f"Cleared cache for {file_path}")

                        if keys_to_remove:
                            self._save_cache_data(cache_file_path, cache_data)

        return cleared_count

    def clear_all_cache(self) -> int:
        """
        Clear all cache entries

        Returns:
            Number of cleared cache entries
        """
        cleared_count = 0

        # Remove all cache files
        for test_type_dir in self.cache_dir.iterdir():
            if not test_type_dir.is_dir():
                continue

            # Walk through provider directories
            for provider_dir in test_type_dir.iterdir():
                if not provider_dir.is_dir():
                    continue

                # Walk through model directories
                for model_dir in provider_dir.iterdir():
                    if not model_dir.is_dir():
                        continue

                    cache_file_path = model_dir / "cache.json"
                    if cache_file_path.exists():
                        with self._get_lock(cache_file_path):
                            cache_data = self._load_cache_data(cache_file_path)
                            entries_count = len(cache_data.get("entries", {}))
                            cleared_count += entries_count
                            cache_file_path.unlink()

        logger.info(f"Cleared {cleared_count} cache entries")
        return cleared_count

    def get_cache_stats(self) -> dict[str, int | float]:
        """
        Get cache statistics

        Returns:
            Dictionary containing cache statistics
        """
        if not self.cache_dir.exists():
            return {
                "total_files": 0,
                "total_entries": 0,
                "total_size_bytes": 0,
                "total_size_kb": 0,
                "ebt_count": 0,
                "pbt_count": 0,
            }

        total_files = 0
        total_entries = 0
        total_size = 0
        ebt_count = 0
        pbt_count = 0

        # Count cache files and entries
        for test_type_dir in self.cache_dir.iterdir():
            if not test_type_dir.is_dir():
                continue

            test_type = test_type_dir.name.upper()

            # Walk through provider directories
            for provider_dir in test_type_dir.iterdir():
                if not provider_dir.is_dir():
                    continue

                # Walk through model directories
                for model_dir in provider_dir.iterdir():
                    if not model_dir.is_dir():
                        continue

                    cache_file_path = model_dir / "cache.json"
                    if cache_file_path.exists():
                        total_files += 1
                        total_size += cache_file_path.stat().st_size

                        cache_data = self._load_cache_data(cache_file_path)
                        entries = cache_data.get("entries", {})
                        entries_count = len(entries)
                        total_entries += entries_count

                        if test_type == "EBT":
                            ebt_count += entries_count
                        elif test_type == "PBT":
                            pbt_count += entries_count

        return {
            "total_files": total_files,
            "total_entries": total_entries,
            "total_size_bytes": total_size,
            "total_size_kb": total_size / 1024,
            "ebt_count": ebt_count,
            "pbt_count": pbt_count,
        }


def handle_clear_cache_command(
    target: str = "all",
    model: str | None = None,
    test_type: str | None = None,
    task_id: str | None = None,
) -> None:
    """Handle clear cache command with all business logic

    Args:
        target: Target to clear ('all' or 'filtered')
        model: Model name filter (e.g., "anthropic/claude-sonnet-4")
        test_type: Test type filter ("ebt" or "pbt")
        task_id: Task ID filter (e.g., "HumanEval/55")

    Raises:
        Exception: If cache clearing fails
    """
    cache = TestResultCache()

    if target == "all":
        count = cache.clear_all_cache()
        print(f"Cleared {count} cache entries")
    else:
        # Filtered clear
        count = cache.clear_filtered_cache(
            model=model,
            test_type=test_type,
            task_id=task_id,
        )

        # Build descriptive message
        filters = []
        if model:
            filters.append(f"model={model}")
        if test_type:
            filters.append(f"type={test_type}")
        if task_id:
            filters.append(f"task={task_id}")

        if filters:
            filter_desc = " (" + ", ".join(filters) + ")"
        else:
            filter_desc = ""

        print(f"Cleared {count} cache entries{filter_desc}")


def handle_cache_stats_command() -> None:
    """Handle cache stats command with all business logic

    Raises:
        Exception: If getting cache stats fails
    """
    cache = TestResultCache()
    stats = cache.get_cache_stats()

    print("Cache Statistics:")
    print(f"  Total files: {stats['total_files']}")
    print(f"  Total size: {stats['total_size_kb']:.2f} KB")
    print(f"  EBT cache entries: {stats['ebt_count']}")
    print(f"  PBT cache entries: {stats['pbt_count']}")

    if stats["total_files"] == 0:
        print("  No cache files found")
