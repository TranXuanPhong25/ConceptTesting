"""Dataset utilities with Unicode handling."""

from __future__ import annotations

from pathlib import Path

from pbteval.commands.generate import find_task_by_id, load_dataset
from pbteval.core.data import JsonData
from pbteval.utils.logger import get_logger

logger = get_logger(__name__)


class UnicodeProcessor:
    """Handle Unicode character processing"""

    @staticmethod
    def decode_unicode_content(content: str) -> str:
        """Decode Unicode escape sequences in content

        Args:
            content: Content string that may contain Unicode escape sequences

        Returns:
            Decoded content string
        """
        if not isinstance(content, str):
            return content

        try:
            # \u279e などのUnicodeエスケープシーケンスを実際の文字に変換
            return (
                content.encode("utf-8")
                .decode("unicode_escape")
                .encode("latin1")
                .decode("utf-8")
            )
        except (UnicodeDecodeError, UnicodeEncodeError):
            # デコードに失敗した場合は元の文字列を返す
            return content


class DatasetExtractor:
    """Extract information from dataset"""

    def __init__(self, dataset_path: Path) -> None:
        """Initialize dataset extractor

        Args:
            dataset_path: Path to the dataset file
        """
        self.dataset_path = dataset_path
        self.unicode_processor = UnicodeProcessor()
        self._dataset: list[JsonData] | None = None
        self._load_dataset()

    def _load_dataset(self) -> None:
        """Load dataset once and cache it"""
        try:
            if not self.dataset_path.exists():
                logger.warning(f"Dataset file not found: {self.dataset_path}")
                self._dataset = None
                return

            self._dataset = load_dataset(self.dataset_path)
            logger.debug(f"Dataset loaded successfully: {len(self._dataset)} entries")

        except Exception as e:
            logger.warning(f"Failed to load dataset from {self.dataset_path}: {e}")
            self._dataset = None

    def _get_task_data(self, task_id: str) -> JsonData | None:
        """Get task data from cached dataset

        Args:
            task_id: Task identifier

        Returns:
            Task data or None if not found
        """
        if self._dataset is None:
            return None

        try:
            return find_task_by_id(self._dataset, task_id)
        except Exception as e:
            logger.warning(f"Failed to find task {task_id} in dataset: {e}")
            return None

    def get_target_function(self, task_id: str) -> str | None:
        """Get target function implementation from dataset

        Args:
            task_id: Task identifier

        Returns:
            Target function implementation or None if not found
        """
        try:
            target_data = self._get_task_data(task_id)
            if target_data is None:
                return None

            completion = target_data.completion
            return self.unicode_processor.decode_unicode_content(completion)

        except Exception as e:
            logger.warning(
                f"Failed to get target function from dataset for {task_id}: {e}"
            )
            logger.debug(f"Dataset path: {self.dataset_path}")
            logger.debug(f"Task ID: {task_id}")
            return None

    def get_problem_description(self, task_id: str) -> str | None:
        """Get problem description from dataset prompt

        Args:
            task_id: Task identifier

        Returns:
            Problem description or None if not found
        """
        try:
            target_data = self._get_task_data(task_id)
            if target_data is None:
                return None

            prompt = target_data.prompt
            decoded_prompt = self.unicode_processor.decode_unicode_content(prompt)
            if decoded_prompt != prompt:
                logger.debug(f"Successfully decoded Unicode characters for {task_id}")

            return decoded_prompt

        except Exception as e:
            logger.warning(
                f"Failed to get problem description from dataset for {task_id}: {e}"
            )
            logger.debug(f"Dataset path: {self.dataset_path}")
            logger.debug(f"Task ID: {task_id}")
            return None

    def get_canonical_solution(self, task_id: str) -> str | None:
        """Get canonical solution from dataset

        Args:
            task_id: Task identifier

        Returns:
            Canonical solution or None if not found
        """
        try:
            target_data = self._get_task_data(task_id)
            if target_data is None:
                return None

            canonical_solution = target_data.canonical_solution
            return self.unicode_processor.decode_unicode_content(canonical_solution)

        except Exception as e:
            logger.warning(
                f"Failed to get canonical solution from dataset for {task_id}: {e}"
            )
            logger.debug(f"Dataset path: {self.dataset_path}")
            logger.debug(f"Task ID: {task_id}")
            return None

    def get_entry_point(self, task_id: str) -> str | None:
        """Get entry point from dataset

        Args:
            task_id: Task identifier

        Returns:
            Entry point function name or None if not found
        """
        try:
            target_data = self._get_task_data(task_id)
            if target_data is None:
                return None

            return target_data.entry_point

        except Exception as e:
            logger.warning(f"Failed to get entry point from dataset for {task_id}: {e}")
            logger.debug(f"Dataset path: {self.dataset_path}")
            logger.debug(f"Task ID: {task_id}")
            return None

    def get_humaneval_test_code(self, task_id: str) -> str | None:
        """Get HumanEval test code from dataset

        Args:
            task_id: Task identifier

        Returns:
            HumanEval test code string or None if not found
        """
        try:
            target_data = self._get_task_data(task_id)
            if target_data is None:
                return None

            # HumanEvalテストコードを生成（_make_humaneval_tests_stringと同じロジック）
            humaneval_test_code = target_data._make_humaneval_tests_string()
            return self.unicode_processor.decode_unicode_content(humaneval_test_code)

        except Exception as e:
            logger.warning(
                f"Failed to get HumanEval test code from dataset for {task_id}: {e}"
            )
            logger.debug(f"Dataset path: {self.dataset_path}")
            logger.debug(f"Task ID: {task_id}")
            return None
