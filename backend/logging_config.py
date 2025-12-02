"""Central logging configuration for Keihitsu backend."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

DATA_LOG_DIR = Path(__file__).resolve().parent.parent / "data" / "logs"
DATA_LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = DATA_LOG_DIR / "keihitsu.log"


def configure_logging(level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger("keihitsu")
    logger.setLevel(level)

    if not any(isinstance(h, RotatingFileHandler) for h in logger.handlers):
        handler = RotatingFileHandler(LOG_PATH, maxBytes=2_000_000, backupCount=3)
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
        stream = logging.StreamHandler()
        stream.setLevel(level)
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
        )
        stream.setFormatter(formatter)
        logger.addHandler(stream)

    return logger
