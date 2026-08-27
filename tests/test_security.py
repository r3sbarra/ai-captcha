"""Tests for the security hardening: cache, secret guard, rate limiting,
replay protection, and security headers."""

from __future__ import annotations

import pytest
from flask import Flask, jsonify

from ai_captcha import create_app, init_app
from ai_captcha.decorators import ai_captcha_required
from ai_captcha.utils.cache import FileCache, MemoryCache, get_cache
from ai_captcha.utils.security import check_secrets, consume_jti
from ai_captcha.utils.tokens import sign_token, verify_token

SECRET = "test-secret-0123456789abcdef0123456789abcdef"


# --- Secret guard -----------------------------------------------------------

def test_check_secrets_raises_on_default():
    """Default secret + default mode=error must raise."""
    with pytest.raises(RuntimeError):
        create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
                "SECRET_MODE": "error",
                "TOKEN_SECRET": "token-signing-secret",
            }
        )


def test_check_secrets_short_secret_raises():
    with pytest.raises(RuntimeError):
        create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
                "SECRET_MODE": "error",
                "TOKEN_SECRET": "short",
            }
        )


def test_check_secrets_off_mode_allows_default():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SECRET_MODE": "off",
        }
    )
    assert app.config["TOKEN_SECRET"] == "token-signing-secret"


def test_check_secrets_warn_mode_does_not_raise():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SECRET_MODE": "warn",
        }
    )
    assert app.config["TOKEN_SECRET"] == "token-signing-secret"


# --- Cache backends ---------------------------------------------------------

def test_memory_cache_basic():
    c = MemoryCache()
    assert c.get("k") is None
    c.set("k", "v")
    assert c.get("k") == "v"
    assert c.incr("ctr") == 1
    assert c.incr("ctr") == 2
    c.delete("k")
    assert c.get("k") is None


def test_memory_cache_ttl_expires():
    c = MemoryCache()
    c.set("tmp", "x", ttl_seconds=0)  # immediate expiry
    assert c.get("tmp") is None


def test_file_cache_roundtrip(tmp_path):
    c = FileCache(directory=str(tmp_path))
    c.set("a", {"n": 1})
    assert c.get("a") == {"n": 1}
    assert c.incr("b") == 1
    assert c.incr("b") == 2
    assert c.get("b") == 2
    c.delete("a")
    assert c.get("a") is None


def test_get_cache_defaults_to_memory():
    app = create_app(
        {"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", "TOKEN_SECRET": SECRET}
    )
    assert isinstance(get_cache(app), MemoryCache)


def test_get_cache_external_instance_used():
    custom = MemoryCache()
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "TOKEN_SECRET": SECRET,
            "CACHE_BACKEND": custom,
        }
    )
    assert get_cache(app) is custom


def test_get_cache_file_backend(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "TOKEN_SECRET": SECRET,
            "CACHE_BACKEND": FileCache(directory=str(tmp_path)),
        }
    )
    assert isinstance(get_cache(app), FileCache)


def test_get_cache_import_path_backend():
    # A dotted "pkg.mod:Class" path resolves to a cache instance.
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "TOKEN_SECRET": SECRET,
            "CACHE_BACKEND": "ai_captcha.utils.cache:MemoryCache",
        }
    )
    assert isinstance(get_cache(app), MemoryCache)


# --- Rate limiting ----------------------------------------------------------

def test_rate_limit_start_blocks_over_limit():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "TOKEN_SECRET": SECRET,
            "RATE_LIMIT_START_PER_MIN": 2,
        }
    )
    c = app.test_client()
    assert c.post("/api/start", json={"tier": "easy"}).status_code == 201
    assert c.post("/api/start", json={"tier": "easy"}).status_code == 201
    r = c.post("/api/start", json={"tier": "easy"})
    assert r.status_code == 429
    assert r.get_json()["error"] == "rate_limited"


def test_rate_limit_disabled_when_zero():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "TOKEN_SECRET": SECRET,
            "RATE_LIMIT_START_PER_MIN": 0,
        }
    )
    c = app.test_client()
    for _ in range(5):
        assert c.post("/api/start", json={"tier": "easy"}).status_code == 201


# --- Replay protection ------------------------------------------------------

def test_consume_jti_blocks_replay():
    app = create_app(
        {"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", "TOKEN_SECRET": SECRET}
    )
    with app.app_context():
        payload = {"jti": "abc123"}
        assert consume_jti(payload, ttl_seconds=60) is True  # first use allowed
        assert consume_jti(payload, ttl_seconds=60) is False  # replay blocked


def test_token_replay_rejected_via_decorator():
    app = Flask(__name__)
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        TOKEN_SECRET=SECRET,
        TOKEN_REPLAY_PROTECTION=True,
    )
    init_app(app)

    @app.route("/p")
    @ai_captcha_required
    def p():
        return jsonify({"ok": True})

    token = sign_token(
        {"session_id": "s", "tier": "hard", "model": "m", "solved": 5, "total": 5}, SECRET
    )
    c = app.test_client()
    assert c.get("/p", headers={"X-AI-CAPTCHA-TOKEN": token}).status_code == 200
    # Same token replayed → rejected.
    assert c.get("/p", headers={"X-AI-CAPTCHA-TOKEN": token}).status_code == 401


def test_token_replay_allowed_when_disabled():
    app = Flask(__name__)
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        TOKEN_SECRET=SECRET,
        TOKEN_REPLAY_PROTECTION=False,
    )
    init_app(app)

    @app.route("/p")
    @ai_captcha_required
    def p():
        return jsonify({"ok": True})

    token = sign_token(
        {"session_id": "s", "tier": "hard", "model": "m", "solved": 5, "total": 5}, SECRET
    )
    c = app.test_client()
    assert c.get("/p", headers={"X-AI-CAPTCHA-TOKEN": token}).status_code == 200
    assert c.get("/p", headers={"X-AI-CAPTCHA-TOKEN": token}).status_code == 200


def test_sign_token_includes_jti():
    t = sign_token({"a": 1}, SECRET)
    assert verify_token(t, SECRET)["jti"]


# --- Security headers -------------------------------------------------------

def test_security_headers_present(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"
    assert "Content-Security-Policy" in r.headers
    assert r.headers.get("Referrer-Policy") == "no-referrer"
