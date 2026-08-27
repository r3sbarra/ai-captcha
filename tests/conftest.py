"""Pytest fixtures for AI CAPTCHA tests."""

from __future__ import annotations

import pytest

from ai_captcha import create_app


@pytest.fixture()
def app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "TOKEN_SECRET": "test-secret-0123456789abcdef0123456789",
        }
    )
    yield app


@pytest.fixture()
def client(app):
    return app.test_client()
