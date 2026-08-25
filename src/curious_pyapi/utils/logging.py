"""Logging utilities."""

import logging


def get_logger(name: str) -> logging.Logger:
    """Get Logger object."""
    return logging.getLogger(name)
