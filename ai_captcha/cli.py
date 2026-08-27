"""CLI helpers for AI CAPTCHA.

Provides the ``ai-captcha-init`` script and a Flask CLI command group.
"""

from __future__ import annotations

import click
from flask import Flask


def init_db() -> None:
    """Initialize the database (create tables)."""
    from .app import create_app

    app = create_app()
    with app.app_context():
        from .database import db

        db.create_all()
    click.echo("AI CAPTCHA database initialized.")


@click.group()
def cli() -> None:
    """AI CAPTCHA CLI commands."""


@cli.command("init-db")
def init_db_command() -> None:
    """Initialize the database."""
    init_db()


@cli.command("run")
@click.option("--host", default="0.0.0.0")
@click.option("--port", default=5100, type=int)
@click.option("--debug", is_flag=True)
def run_command(host: str, port: int, debug: bool) -> None:
    """Run the standalone server."""
    from .app import create_app

    app = create_app()
    app.run(host=host, port=port, debug=debug)
