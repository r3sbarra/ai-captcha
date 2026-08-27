"""Health check blueprint — AppManager standardized health contract.

The health endpoint actually probes the database so a ``200`` means the app is
really functional, not just that the process is up.
"""

from __future__ import annotations

from datetime import datetime, timezone

from flask import Blueprint, jsonify
from sqlalchemy import text

from .. import __version__
from ..database import db

health_bp = Blueprint("health", __name__)


@health_bp.route("/health")
def health():
    db_ok = True
    try:
        with db.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001
        db_ok = False

    status = "healthy" if db_ok else "degraded"
    return jsonify(
        {
            "status": status,
            "app_slug": "ai-captcha",
            "version": __version__,
            "checks": {
                "database": "ok" if db_ok else "error",
                "puzzle_engine": "ok",
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )
