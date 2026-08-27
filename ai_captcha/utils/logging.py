"""Structured logging for AI CAPTCHA.

Logging is **OFF by default**. Enable via the ``LOGGING_ENABLED`` config key
(env ``AIC_LOGGING_ENABLED``). To plug in an existing logger from a host Flask
app, pass it via ``LOG_LOGGER`` — it is used as-is and the app's own logger
setup is skipped.

Sensitive values (answers, tokens) are never logged in plaintext; tokens are
short-hashed by the caller before emitting.
"""

from __future__ import annotations

import logging
import sys

from flask import Flask

_DEFAULT_FORMAT = (
    "%(asctime)s %(levelname)s [ai-captcha] "
    "%(name)s %(funcName)s:%(lineno)d | %(message)s"
)


def get_logger(app: Flask) -> logging.Logger:
    """Return a configured logger for AI CAPTCHA.

    - If ``LOG_LOGGER`` is set, use that logger directly (host owns config).
    - If ``LOGGING_ENABLED`` is False, return a no-op logger (NullHandler).
    - Otherwise create/configure the ``ai_captcha`` logger.
    """
    external = app.config.get("LOG_LOGGER")
    if external is not None:
        return external

    logger = logging.getLogger("ai_captcha")

    if not app.config.get("LOGGING_ENABLED", False):
        if not logger.handlers:
            logger.addHandler(logging.NullHandler())
        logger.setLevel(logging.CRITICAL + 1)  # suppress everything
        return logger

    level_name = app.config.get("LOG_LEVEL", "INFO").upper()
    logger.setLevel(getattr(logging, level_name, logging.INFO))

    if not any(isinstance(h, (logging.StreamHandler, logging.FileHandler))
               for h in logger.handlers):
        fmt = app.config.get("LOG_FORMAT") or _DEFAULT_FORMAT
        formatter = logging.Formatter(fmt)

        file_path = app.config.get("LOG_TO_FILE")
        if file_path:
            handler: logging.Handler = logging.FileHandler(file_path)
        else:
            handler = logging.StreamHandler(sys.stdout)

        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger.propagate = False  # don't bubble to root logger
    return logger


def log_event(app: Flask, level: str, event: str, **fields) -> None:
    """Emit a structured log event.

    ``fields`` become a ``key=val key=val`` suffix so logs are grep-friendly
    without extra dependencies. Sensitive values must be hashed by the caller.
    """
    logger = app.extensions.get("ai_captcha_logger")
    if logger is None:
        return
    parts = [f"event={event}"]
    for k, v in fields.items():
        parts.append(f"{k}={v}")
    msg = " ".join(parts)
    getattr(logger, level.lower(), logger.info)(msg)
