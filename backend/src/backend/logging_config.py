"""Application logging configuration."""

from __future__ import annotations

import logging

LOGGER_NAME = "backend"
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


def configure_logging(level: str) -> None:
    """Configure one non-duplicating handler for all backend loggers."""

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level.upper())
    logger.propagate = False

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logger.addHandler(handler)

    for handler in logger.handlers:
        handler.setLevel(level.upper())
