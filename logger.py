"""Logging setup.

Console: warnings and errors only, or everything with ``-v``.
File:    full detail with timestamps in ``<folder>/.sfm/sfm.log`` (rotating),
         written only by commands that change files (organize, undo).
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from .config import LOG_FILE_NAME

LOGGER_NAME = "smart_file_manager"


def setup_logging(log_dir: Optional[Path] = None, verbose: bool = False) -> logging.Logger:
    """Configure the package logger. Safe to call more than once."""
    close_logging()
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    console = logging.StreamHandler()
    console.setLevel(logging.INFO if verbose else logging.WARNING)
    console.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logger.addHandler(console)

    if log_dir is not None:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_dir / LOG_FILE_NAME, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
        )
        logger.addHandler(file_handler)

    return logger


def close_logging() -> None:
    """Close and remove handlers so files are released (important in tests)."""
    logger = logging.getLogger(LOGGER_NAME)
    for handler in list(logger.handlers):
        handler.close()
        logger.removeHandler(handler)
