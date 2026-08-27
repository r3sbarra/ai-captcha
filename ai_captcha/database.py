"""SQLAlchemy setup.

The app works standalone (own SQLite DB) or embedded in an existing Flask
project (shares the host app's SQLAlchemy instance). ``init_db`` is idempotent
and safe to call multiple times.
"""

from __future__ import annotations

import os
from pathlib import Path

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def init_db(app: Flask) -> None:
    """Bind SQLAlchemy to ``app`` and create tables if they don't exist.

    Safe to call more than once. When embedding, call this after
    ``app.config`` is fully populated.
    """
    db.init_app(app)
    with app.app_context():
        # Ensure the SQLite instance directory exists before creating tables.
        uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
        if uri.startswith("sqlite:///"):
            db_path = uri.replace("sqlite:///", "", 1)
            if db_path and db_path != ":memory:":
                Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        db.create_all()
