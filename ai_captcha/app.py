"""Flask app factory and embeddable API.

Three ways to use AI CAPTCHA:

1. **Standalone** — ``flask --app ai_captcha.app run`` or ``python run.py``.
2. **AppManager plugin** — symlink into ``installed_apps/``; the root ``app.py``
   exposes ``app = create_app()``.
3. **Embedded in an existing Flask project** — either call ``init_app(app)`` to
   register the blueprint + DB, or ``app.register_blueprint(blueprint)`` and
   manage the DB yourself.
"""

from __future__ import annotations

from typing import Any

from flask import Flask

from .config import Config
from .database import init_db
from .manifest import manifest as appmanager_manifest
from .routes.api import api_bp
from .routes.embed import embed_bp
from .routes.health import health_bp
from .routes.seo import seo_bp
from .routes.views import views_bp
from .utils.cache import get_cache
from .utils.logging import get_logger
from .utils.security import apply_security_headers, check_secrets

# AppManager SDK Flask extension. Binds the manifest + client to the app and
# registers a ``flask manifest generate`` CLI command. Imported lazily so the
# package still works if appmanager-sdk is not installed (standalone/embedded).
try:
    from appmanager_sdk.flask import AppManager as _AppManager
except ImportError:  # pragma: no cover - appmanager-sdk optional
    _AppManager = None

# A single Blueprint that bundles all AI CAPTCHA routes. Register it on any
# Flask app to embed the challenge system under a URL prefix of your choice.
blueprint = views_bp
blueprint.register_blueprint(api_bp, url_prefix="/api")
blueprint.register_blueprint(embed_bp)
blueprint.register_blueprint(health_bp)
blueprint.register_blueprint(seo_bp)


def _register_appmanager(app: Flask) -> None:
    """Attach the AppManager SDK manifest + client to ``app`` (if available).

    Registers the ``flask manifest generate`` CLI command and a health endpoint
    (only if the app doesn't already define one). No-op when appmanager-sdk is
    not installed, so standalone/embedded use is unaffected.
    """
    if _AppManager is None:
        return
    # The SDK's AppManager extension binds the manifest and client. We pass the
    # manifest explicitly so ``flask manifest generate`` and the generator can
    # discover it from the app object.
    _AppManager(app, manifest=appmanager_manifest)


def create_app(config: dict[str, Any] | None = None) -> Flask:
    """Create a standalone AI CAPTCHA Flask app.

    ``config`` may be a dict of overrides applied on top of the defaults.
    """
    app = Flask(__name__)
    app.config.from_object(Config)
    if config:
        app.config.from_mapping(config)
    check_secrets(app)
    init_db(app)
    app.extensions["ai_captcha_logger"] = get_logger(app)
    get_cache(app)  # init the cache backend up front
    app.register_blueprint(blueprint)
    _register_context(app)
    _register_security_headers(app)
    _register_appmanager(app)
    return app


def _register_context(app: Flask) -> None:
    """Expose the app's URL prefix so client JS works under any mount point.

    Standalone: ``base_path == ""``. Under AppManager (SCRIPT_NAME set to
    ``/apps/ai-captcha``): ``base_path == "/apps/ai-captcha"``.
    """

    @app.context_processor
    def inject_base_path():
        from flask import request

        script_name = request.script_root if request else ""
        return {"base_path": script_name.rstrip("/")}

    @app.context_processor
    def inject_benchmark_labels():
        from . import benchmark_results

        return {
            "bench_labels": benchmark_results.PUZZLE_LABELS,
            "model_labels": benchmark_results.MODEL_LABELS,
        }


def _register_security_headers(app: Flask) -> None:
    """Attach baseline security headers to every response when enabled."""
    if not app.config.get("SECURITY_HEADERS", True):
        return

    @app.after_request
    def _headers(response):
        return apply_security_headers(response)


def init_app(app: Flask, config: dict[str, Any] | None = None) -> Flask:
    """Embed AI CAPTCHA into an existing Flask app.

    Merges AI CAPTCHA config defaults (without clobbering existing keys),
    initializes the DB, and registers the blueprint. Returns the app.
    """
    # Only set keys the host app hasn't already configured.
    for key, value in Config.__dict__.items():
        if key.isupper() and key not in app.config:
            app.config[key] = value
    if config:
        app.config.from_mapping(config)
    check_secrets(app)
    init_db(app)
    app.extensions["ai_captcha_logger"] = get_logger(app)
    get_cache(app)
    app.register_blueprint(blueprint)
    _register_context(app)
    _register_security_headers(app)
    _register_appmanager(app)
    return app


# Standalone instance for `flask --app ai_captcha.app run` and AppManager `app:app`.
# The singleton defaults to warn-mode (non-fatal) so the package imports and runs
# out-of-the-box in dev; production deployments should set a strong AIC_TOKEN_SECRET
# (>= 32 chars) and/or AIC_SECRET_MODE=error via `create_app`/`init_app` config.
import os as _os

if _os.getenv("AIC_SECRET_MODE", "") == "":
    # Only default the singleton to warn if the user hasn't explicitly chosen a mode.
    app = create_app({"SECRET_MODE": "warn"})
else:
    app = create_app()


def run_standalone() -> None:
    """CLI entrypoint: ``ai-captcha``."""
    import argparse

    parser = argparse.ArgumentParser(description="AI CAPTCHA — reverse-CAPTCHA challenge app.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5100)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    run_standalone()
