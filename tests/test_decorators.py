"""Tests for the route-gating decorators."""

from __future__ import annotations

import pytest
from flask import Flask, jsonify

from ai_captcha import init_app
from ai_captcha.decorators import ai_captcha_required, tier_gate
from ai_captcha.utils.tokens import sign_token


@pytest.fixture()
def app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["TOKEN_SECRET"] = _SECRET
    init_app(app)

    @app.route("/protected")
    @ai_captcha_required
    def protected():
        return jsonify({"ok": True})

    @app.route("/hard")
    @tier_gate("hard")
    @ai_captcha_required
    def hard():
        return jsonify({"ok": True})

    return app


@pytest.fixture()
def client(app):
    return app.test_client()


_SECRET = "test-secret-0123456789abcdef0123456789abcdef"


def _token(tier="hard"):
    return sign_token(
        {"session_id": "s1", "tier": tier, "model": "m", "solved": 5, "total": 5},
        _SECRET,
    )


def test_no_token_401(client):
    r = client.get("/protected")
    assert r.status_code == 401


def test_valid_token_passes(client):
    r = client.get("/protected", headers={"X-AI-CAPTCHA-TOKEN": _token()})
    assert r.status_code == 200


def test_tier_gate_blocks_low_tier(client):
    low = _token(tier="easy")
    r = client.get("/hard", headers={"X-AI-CAPTCHA-TOKEN": low})
    assert r.status_code == 403


def test_tier_gate_passes_high_tier(client):
    high = _token(tier="hard")
    r = client.get("/hard", headers={"X-AI-CAPTCHA-TOKEN": high})
    assert r.status_code == 200
