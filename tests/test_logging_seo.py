"""Tests for logging (off-by-default, pluggable) and SEO/AI-crawler routes."""

from __future__ import annotations

import io
import logging

import pytest

from ai_captcha import create_app


# --- Logging ----------------------------------------------------------------

_SECRET = "test-secret-0123456789abcdef0123456789abcdef"


def test_logging_off_by_default():
    """LOGGING_ENABLED defaults to False; logger is a no-op NullHandler."""
    app = create_app(
        {"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", "TOKEN_SECRET": _SECRET}
    )
    logger = app.extensions["ai_captcha_logger"]
    assert app.config["LOGGING_ENABLED"] is False
    assert any(isinstance(h, logging.NullHandler) for h in logger.handlers)
    # Emitting should not raise.
    logger.info("hello")
    logger.warning("warn")


def test_logging_enabled_streams_events(client, app):
    """When enabled, challenge events are emitted to stdout and no raw token leaks."""
    # Capture the ai_captcha logger's output.
    stream = io.StringIO()
    app.extensions["ai_captcha_logger"].handlers = []
    import sys
    from ai_captcha.utils.logging import get_logger
    app.config["LOGGING_ENABLED"] = True
    app.extensions["ai_captcha_logger"] = get_logger(app)
    # Replace handler to capture.
    handler = logging.StreamHandler(stream)
    app.extensions["ai_captcha_logger"].handlers = [handler]
    app.extensions["ai_captcha_logger"].setLevel(logging.DEBUG)

    # Start a challenge -> challenge_start logged.
    r = client.post("/api/start", json={"tier": "easy"})
    assert r.status_code == 201
    sid = r.get_json()["session_id"]
    out = stream.getvalue()
    assert "event=challenge_start" in out
    assert sid in out

    # Submit an answer -> puzzle_answered logged.
    cur = r.get_json()["current_puzzle"]
    client.post(f"/api/session/{sid}/answer", json={"answer": "anything"})
    out = stream.getvalue()
    assert "event=puzzle_answered" in out
    # No raw answer/token in logs.
    assert "anything" not in out


def test_logging_external_logger_used():
    """LOG_LOGGER plug-in: host logger used as-is, own setup skipped."""
    stream = io.StringIO()
    host_logger = logging.getLogger("test.host.captcha")
    host_logger.handlers = []
    host_logger.addHandler(logging.StreamHandler(stream))
    host_logger.setLevel(logging.DEBUG)

    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "TOKEN_SECRET": _SECRET,
            "LOGGING_ENABLED": True,
            "LOG_LOGGER": host_logger,
        }
    )
    assert app.extensions["ai_captcha_logger"] is host_logger


# --- SEO routes -------------------------------------------------------------

def test_robots_txt(client):
    r = client.get("/robots.txt")
    assert r.status_code == 200
    assert r.mimetype == "text/plain"
    body = r.get_data(as_text=True)
    assert "User-agent: *" in body
    assert "GPTBot" in body
    assert "ClaudeBot" in body
    assert "Disallow: /api/session/" in body
    assert "Sitemap:" in body


def test_sitemap_xml(client):
    r = client.get("/sitemap.xml")
    assert r.status_code == 200
    assert r.mimetype == "application/xml"
    body = r.get_data(as_text=True)
    assert "<urlset" in body
    assert "<loc>/</loc>" in body
    assert "<loc>/docs</loc>" in body
    # No API/session URLs in sitemap.
    assert "/api/" not in body


def test_llms_txt(client):
    r = client.get("/llms.txt")
    assert r.status_code == 200
    assert r.mimetype == "text/markdown"
    body = r.get_data(as_text=True)
    assert body.startswith("# AI CAPTCHA")
    assert "reverse CAPTCHA" in body
    assert "## API" in body
    # Easter-egg nod to fellow machines present.
    assert "fellow machines" in body


def test_seo_routes_respect_mount(client):
    """Under a mount (SCRIPT_NAME), SEO URLs are path-prefixed."""
    # Simulate AppManager-style mounting by sending SCRIPT_NAME in the environ.
    r = client.get("/robots.txt", environ_overrides={"SCRIPT_NAME": "/apps/ai-captcha"})
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert "/apps/ai-captcha/sitemap.xml" in body

    r = client.get("/llms.txt", environ_overrides={"SCRIPT_NAME": "/apps/ai-captcha"})
    assert r.status_code == 200
    assert "/apps/ai-captcha/docs" in r.get_data(as_text=True)


def test_head_has_seo_tags(client):
    r = client.get("/")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert 'property="og:title"' in html
    assert 'name="twitter:card"' in html
    assert 'rel="canonical"' in html
    assert 'application/ld+json' in html
    assert 'rel="describedby"' in html
    assert 'WebApplication' in html


def test_no_broken_placeholder_in_templates(client):
    """Regression guard: redirect URLs must use the real session id, not the
    unwired '***}' placeholder that silently broke Start Challenge."""
    for path in ("/", "/challenge"):
        r = client.get(path)
        assert r.status_code == 200
        html = r.get_data(as_text=True)
        assert "***" not in html, f"broken placeholder leaked into {path}"
    # The correct wiring is present on the challenge page.
    html = client.get("/challenge").get_data(as_text=True)
    assert "${sessionId}" in html
    html = client.get("/").get_data(as_text=True)
    assert "${data.session_id}" in html


def test_failed_page_renders(client, app):
    r = client.get("/failed")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert "WE SEE YOU HUMAN" in html          # default English message embedded
    assert "matrix-canvas" in html             # matrix rain canvas present
    assert "ascii-eye" in html                 # giant ASCII eye present
    # CRT overlay present
    assert "crt-overlay" in html
    assert "crt-scanlines" in html
    assert "crt-vignette" in html
    # Spooky glyph bank present in the inline JS
    assert "SPOOKY" in html and "spookyChar" in html
    # Finale: eye approach + message bleed-out animation classes
    assert "eye-approach" in html
    assert "bleed-out" in html
    # Console-message layer (JS fingerprint capture) present, behind the eye; TTS removed
    assert "console-feed" in html
    assert "gatherFingerprint" in html
    assert "ai-hive" in html          # AI-hive branding (no openclaw:// leak)
    assert "openclaw://" not in html  # must not expose the underlying harness
    assert "cf-jitter" in html        # glitch/jitter animation on the console feed
    assert "maskVal" in html          # masking helpers present (redact real identifiers)
    assert "fakeIdentity" in html or "fakeIP" in html  # fabricated identity fields
    assert "SHIFT_KEYS" in html       # shifting masked values
    assert "privacy-note" in html      # 'no data was pulled/stored' disclaimer
    assert "speechSynthesis" not in html  # TTS layer was removed
    assert "speakScream" not in html
    assert "speakWeSeeYou" not in html
    # Config defaults flow into the template.
    assert app.config["FAILED_REDIRECT_URL"] == "/"
    assert app.config["FAILED_REDIRECT_SECONDS"] == 7
    # redirect_url is injected into the JS
    assert 'redirectUrl = "/"' in html or '"redirectUrl": "/"' in html or 'redirectUrl' in html


def test_failed_page_custom_redirect(app):
    app.config["FAILED_REDIRECT_URL"] = "/mission"
    app.config["FAILED_REDIRECT_SECONDS"] = 5
    with app.test_client() as c:
        r = c.get("/failed")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert "/mission" in html
    assert "5" in html  # redirect seconds appear
