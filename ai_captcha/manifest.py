"""AppManager manifest for AI CAPTCHA, defined via the ``appmanager-sdk``.

This is the single source of truth for how AI CAPTCHA registers with an
AppManager host. It is declared in Python using the SDK's type-safe
:class:`appmanager_sdk.AppManifest` dataclass, then exported to ``manifest.json``
via either:

* ``flask manifest generate`` (the ``AppManager`` extension registers this CLI
  command on the app), or
* ``appmanager-sdk generate ai_captcha.manifest:manifest``.

The manifest is attached to the Flask app by :func:`ai_captcha.app.create_app`
and :func:`ai_captcha.app.init_app` through the ``AppManager`` extension, so the
generator can discover it from the app object as well.
"""

from __future__ import annotations

from appmanager_sdk import AppManifest, ScheduledTask, Setting

# Keep in sync with ``ai_captcha.__version__``.
__version__ = "1.0.0"

# The scheduled cleanup task declared in ``tasks.py``. AppManager's cron runner
# invokes ``tasks:cleanup_sessions`` hourly to purge expired challenge sessions.
_CLEANUP_TASK = ScheduledTask(
    name="cleanup_expired_sessions",
    entry_point="tasks:cleanup_sessions",
    frequency="hourly",
)

# Settings surfaced in the AppManager admin UI. These mirror the environment
# variables in ``ai_captcha/config.py`` so an operator can configure the app
# without touching the environment. Secret defaults are redacted on export.
_SETTINGS = [
    Setting(
        key="token_secret",
        type="string",
        label="Token Signing Secret",
        default="",
        description="Secret used to sign verification tokens (>= 32 chars in production).",
        is_secret=True,
    ),
    Setting(
        key="default_tier",
        type="string",
        label="Default Difficulty Tier",
        default="medium",
        description="easy | medium | hard",
    ),
    Setting(
        key="puzzles_per_session",
        type="integer",
        label="Puzzles per Session",
        default=5,
        description="Number of puzzles in a challenge session.",
    ),
    Setting(
        key="min_pass_rate",
        type="float",
        label="Minimum Pass Rate",
        default=0.8,
        description="Fraction of puzzles that must be correct to pass.",
    ),
    Setting(
        key="rate_limit_start_per_min",
        type="integer",
        label="Start Rate Limit (per min)",
        default=30,
        description="Per-client limit on challenge-start requests.",
    ),
    Setting(
        key="rate_limit_answer_per_min",
        type="integer",
        label="Answer Rate Limit (per min)",
        default=120,
        description="Per-client limit on answer submissions.",
    ),
    Setting(
        key="token_replay_protection",
        type="boolean",
        label="Token Replay Protection",
        default=True,
        description="Reject replayed verification tokens (single-use).",
    ),
    Setting(
        key="security_headers",
        type="boolean",
        label="Security Headers",
        default=True,
        description="Apply baseline security headers to every response.",
    ),
    Setting(
        key="embed_admin_token",
        type="string",
        label="Embed Admin Token",
        default="",
        description="Bearer token for the embed site admin API. Empty disables admin.",
        is_secret=True,
    ),
]

manifest = AppManifest(
    name="AI CAPTCHA",
    slug="ai-captcha",
    version=__version__,
    description=(
        "Reverse-CAPTCHA challenge app — proves you're an AI, not a human. "
        "Timed puzzle series with complexity gating. Standalone, AppManager "
        "plugin, or embeddable in any Flask project."
    ),
    author="Richard",
    entry_point="app:app",
    health_check_path="/health",
    app_type="standalone",
    has_web_ui=True,
    requires_auth=True,
    settings=_SETTINGS,
    scheduled_tasks=[_CLEANUP_TASK],
    ui_slots=["dashboard_widget"],
)

__all__ = ["manifest", "__version__"]
