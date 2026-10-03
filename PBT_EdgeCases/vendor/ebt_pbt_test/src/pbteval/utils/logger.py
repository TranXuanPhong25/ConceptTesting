"""Logging configuration for pbteval package."""

import logging
import os
import sys

from dotenv import load_dotenv


def setup_logger(
    name: str = "pbteval", level: int | None = None, debug: bool = False
) -> logging.Logger:
    """
    Set up and configure logger for the pbteval package.

    Args:
        name: Logger name
        level: Logging level (overrides environment variables)
        debug: Enable debug mode (overrides level)

    Returns:
        Configured logger instance
    """
    # Load environment variables from .env file
    load_dotenv()

    # Determine log level with priority: debug flag > level param > env var > default
    if debug:
        log_level = logging.DEBUG
    elif level is not None:
        log_level = level
    else:
        # Check environment variables (loaded from .env)
        env_level = os.getenv("PBTEVAL_LOG_LEVEL", "INFO").upper()
        env_debug = os.getenv("PBTEVAL_DEBUG", "").lower() in ("1", "true", "yes")

        if env_debug:
            log_level = logging.DEBUG
        else:
            log_level = getattr(logging, env_level, logging.INFO)

    # Configure basic logging if not already configured
    if not logging.getLogger().handlers:
        # More detailed format for debug mode
        if log_level == logging.DEBUG:
            format_str = "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
        else:
            format_str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

        logging.basicConfig(
            level=log_level,
            format=format_str,
            datefmt="%Y-%m-%d %H:%M:%S",
            stream=sys.stderr,
        )

    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    # Increase httpx log level (only show WARNING level and above)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    return logger


def get_logger(name: str = "pbteval") -> logging.Logger:
    """
    Get logger instance for the given name.

    Args:
        name: Logger name

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
