"""Configuration for AI CAPTCHA.

All settings are overridable via environment variables or by setting keys on
``app.config`` when embedding the app in an existing Flask project.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Default instance dir lives next to the package (works standalone + embedded).
_DEFAULT_INSTANCE = Path(__file__).resolve().parent.parent / "instance"


def _env_list(name: str) -> list[str]:
    raw = os.getenv(name, "")
    return [p.strip() for p in raw.split(",") if p.strip()]


@dataclass
class Config:
    """Default configuration. Merge into an app via ``app.config.from_object``."""

    SECRET_KEY: str = os.getenv("AIC_SECRET_KEY", "ai-captcha-dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI: str = os.getenv(
        "AIC_DATABASE_URL", f"sqlite:///{_DEFAULT_INSTANCE / 'ai_captcha.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False

    # --- Challenge defaults ---
    DEFAULT_TIER: str = "medium"  # easy | medium | hard
    PUZZLES_PER_SESSION: int = 5
    MIN_PASS_RATE: float = 0.8  # fraction of puzzles that must be correct

    # Per-tier total timers (seconds)
    TIMER_SECONDS_EASY: int = 30
    TIMER_SECONDS_MEDIUM: int = 20
    TIMER_SECONDS_HARD: int = 10

    # --- Gating ---
    # Comma-separated model name prefixes. Empty = all models allowed.
    # Prefix matching: "gpt-4" matches "gpt-4", "gpt-4o", "gpt-4-turbo", ...
    MODEL_ALLOWLIST: list[str] = field(default_factory=lambda: _env_list("AIC_MODEL_ALLOWLIST"))

    # --- Token signing ---
    TOKEN_SECRET: str = os.getenv("AIC_TOKEN_SECRET", "token-signing-secret")
    TOKEN_TTL_HOURS: int = 24
    TOKEN_ISSUER: str = "ai-captcha"
    # Refuse to start (or warn) when the token secret is the publicly-known
    # default. Set to "error" to hard-fail, "warn" to log a loud warning, or
    # "off" to allow the default (not recommended outside dev).
    SECRET_MODE: str = os.getenv("AIC_SECRET_MODE", "error")

    # --- Caching ---
    # "memory" (default), "file", an import path "pkg.mod:Class", a cache
    # instance, or a callable returning a cache instance. Used for rate
    # limiting and token replay protection.
    CACHE_BACKEND: Any = os.getenv("AIC_CACHE_BACKEND", "memory")
    CACHE_DIR: str | None = os.getenv("AIC_CACHE_DIR")  # used by the file backend

    # --- Rate limiting ---
    # Per-client (IP / agent id) limits on the public API. 0 or None = off.
    RATE_LIMIT_START_PER_MIN: int = int(os.getenv("AIC_RATE_LIMIT_START_PER_MIN", "30"))
    RATE_LIMIT_ANSWER_PER_MIN: int = int(os.getenv("AIC_RATE_LIMIT_ANSWER_PER_MIN", "120"))
    RATE_LIMIT_GLOBAL_PER_MIN: int = int(os.getenv("AIC_RATE_LIMIT_GLOBAL_PER_MIN", "0"))  # 0=off
    # Per-secretkey limit on /api/siteverify calls (blunts brute force).
    RATE_LIMIT_VERIFY_PER_MIN: int = int(os.getenv("AIC_RATE_LIMIT_VERIFY_PER_MIN", "60"))

    # --- Embeddable (iframe) CAPTCHA ---
    # Max length of an answer submission (defense against oversized payloads).
    MAX_ANSWER_LENGTH: int = int(os.getenv("AIC_MAX_ANSWER_LENGTH", "10000"))
    # Bearer token for the embed site admin API. Empty = admin disabled (fail closed).
    EMBED_ADMIN_TOKEN: str = os.getenv("AIC_EMBED_ADMIN_TOKEN", "")

    # --- Replay protection ---
    # When enabled, each issued token gets a unique ``jti`` and consumed jtis
    # are recorded (until token expiry) so a token can't be replayed.
    TOKEN_REPLAY_PROTECTION: bool = (
        os.getenv("AIC_TOKEN_REPLAY_PROTECTION", "true").lower() in ("1", "true", "yes")
    )

    # --- Security headers ---
    # Applied to every response when enabled.
    SECURITY_HEADERS: bool = os.getenv("AIC_SECURITY_HEADERS", "true").lower() in ("1", "true", "yes")

    # --- Failed / rejection page ---
    # After a failed session is shown, auto-redirect here (a route or URL).
    FAILED_REDIRECT_URL: str = os.getenv("AIC_FAILED_REDIRECT_URL", "/")
    # Seconds the failed page lingers before redirecting.
    FAILED_REDIRECT_SECONDS: float = float(os.getenv("AIC_FAILED_REDIRECT_SECONDS", "7"))

    # --- Session storage ---
    SESSION_TYPE: str = "filesystem"  # or "redis" for production
    SESSION_FILE_DIR: str = str(_DEFAULT_INSTANCE / "sessions")

    # --- AppManager integration ---
    # When running under AppManager, set this to the slug so the app can
    # detect its runtime context and enable telemetry bridging.
    APPMANAGER_SLUG: str = os.getenv("APPMANAGER_SLUG", "")

    # --- Logging ---
    # Logging is OFF by default. Enable via LOGGING_ENABLED (or env
    # AIC_LOGGING_ENABLED). Pass LOG_LOGGER to plug in an existing logger.
    LOGGING_ENABLED: bool = os.getenv("AIC_LOGGING_ENABLED", "").lower() in ("1", "true", "yes")
    LOG_LOGGER: object = None  # logging.Logger instance, or None to use own
    LOG_LEVEL: str = os.getenv("AIC_LOG_LEVEL", "INFO")
    LOG_FORMAT: str | None = os.getenv("AIC_LOG_FORMAT")  # None = default format
    LOG_TO_FILE: str | None = os.getenv("AIC_LOG_TO_FILE")  # None = stdout


def get_tier_timers(config) -> dict[str, int]:
    """Return {tier: total_seconds} from an app config object."""
    return {
        "easy": config.get("TIMER_SECONDS_EASY", 30),
        "medium": config.get("TIMER_SECONDS_MEDIUM", 20),
        "hard": config.get("TIMER_SECONDS_HARD", 10),
    }
