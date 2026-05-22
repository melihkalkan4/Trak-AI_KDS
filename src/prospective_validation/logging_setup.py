"""
Loguru configuration for the FLOV module.

A single call to ``configure_logging()`` is idempotent: re-importing or
re-invoking will not duplicate sinks. We rotate at 100 MB and retain 90 days
of compressed history per the user's audit-trail requirements.
"""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger

from . import config

_CONFIGURED = False


def configure_logging(verbose: bool = True) -> None:
    """Install rotating file sink + stderr sink. Safe to call repeatedly."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    config.ensure_runtime_dirs()

    logger.remove()  # drop default stderr handler so we control format
    logger.add(
        sys.stderr,
        level="INFO" if verbose else "WARNING",
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> "
            "<level>{level: <8}</level> "
            "<cyan>{name}:{function}:{line}</cyan> "
            "<level>{message}</level>"
        ),
        backtrace=False,
        diagnose=False,
    )
    logger.add(
        config.LOG_FILE,
        level="DEBUG",
        rotation=config.LOG_ROTATION,
        retention=config.LOG_RETENTION,
        compression="zip",
        encoding="utf-8",
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
            "{name}:{function}:{line} | {message}"
        ),
        enqueue=True,        # multi-process safe
    )
    _CONFIGURED = True
    logger.debug("Loguru configured: file={}, rotation={}",
                 Path(config.LOG_FILE), config.LOG_ROTATION)


__all__ = ["configure_logging", "logger"]
