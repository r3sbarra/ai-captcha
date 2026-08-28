"""Tests for the embeddable (iframe) CAPTCHA: sitekey/secretkey model,
siteverify, origin allow-listing, and the embed challenge flow."""

from __future__ import annotations

import pytest

from ai_captcha import create_app
from ai_captcha.models import EmbedSite
from ai_captcha.utils.tokens import sign_token

SECRET = "test-secret-0123456789abcdef0123456789abcdef"
ADMIN_TOKEN = "test-admin-token-0123456789abcdef"


@pytest.fixture()
def app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "TOKEN_SECRET": SECRET,
            "SECRET_KEY": "test-secret-key-0123456789abcdef0123456789",
            "EMBED_ADMIN_TOKEN": ADMIN_TOKEN,
        }
    )
    yield app


@pytest.fixture()
def client(app):
    return app.test_client()


def _admin_headers():
    return {"Authorization": f"Bearer {ADMIN_TOKEN}"}


def _create_site(client, origins=("https://example.com",)):
    r = client.post(
        "/api/embed/sites",
        json={"name": "Example", "allowed_origins": list(origins)},
        headers=_admin_headers(),
    )
    assert r.status_code == 201
    return r.get_json()


# --- Admin: auth ---------------------------------------------------------

def test_admin_endpoints_require_token(client):
    # No token → 401.
    r = client.post("/api/embed/sites", json={"name": "x", "allowed_origins": []})
    assert r.status_code == 401
    r = client.get("/api/embed/sites")
    assert r.status_code == 401
    # Wrong token → 401.
    r = client.post(
        "/api/embed/sites",
        json={"name": "x", "allowed_origins": []},
        headers={"Authorization": "Bearer wrong"},
    )
    assert r.status_code == 401


def test_admin_disabled_when_no_token_configured(app, client):
    # With no EMBED_ADMIN_TOKEN, admin endpoints fail closed (403).
    app.config["EMBED_ADMIN_TOKEN"] = ""
    r = client.post("/api/embed/sites", json={"name": "x", "allowed_origins": []})
    assert r.status_code == 403


def test_demo_site_endpoint_creates_throwaway_site(client):
    # The demo endpoint needs no admin token and binds to the caller's origin.
    r = client.post("/api/embed/demo-site", json={"origin": "https://example.com"})
    assert r.status_code == 201
    d = r.get_json()
    assert d["sitekey"]
    assert d["secretkey"]
    assert d["allowed_origins"] == ["https://example.com"]


def test_demo_site_requires_origin(client):
    r = client.post("/api/embed/demo-site", json={})
    assert r.status_code == 400


# --- Admin: site creation ------------------------------------------------

def test_create_site_returns_sitekey_and_secretkey(client):
    d = _create_site(client)
    assert d["sitekey"]
    assert d["secretkey"]
    assert d["allowed_origins"] == ["https://example.com"]


def test_list_sites_does_not_expose_secretkey(client):
    _create_site(client)
    r = client.get("/api/embed/sites", headers=_admin_headers())
    assert r.status_code == 200
    sites = r.get_json()["sites"]
    assert len(sites) == 1
    assert "secretkey" not in sites[0]
    assert "secretkey_hash" not in sites[0]


def test_delete_site(client):
    d = _create_site(client)
    r = client.delete(f"/api/embed/sites/{d['sitekey']}", headers=_admin_headers())
    assert r.status_code == 200
    assert client.get("/api/embed/sites", headers=_admin_headers()).get_json()["sites"] == []


def test_set_origins(client):
    d = _create_site(client, origins=("https://a.com",))
    r = client.put(
        f"/api/embed/sites/{d['sitekey']}/origins",
        json={"allowed_origins": ["https://b.com", "https://c.com"]},
        headers=_admin_headers(),
    )
    assert r.status_code == 200
    assert r.get_json()["allowed_origins"] == ["https://b.com", "https://c.com"]


# --- Embed page: origin allow-listing + CSP ------------------------------

def test_embed_requires_valid_sitekey(client):
    r = client.get("/embed?sitekey=nope&origin=https://example.com")
    assert r.status_code == 400


def test_embed_blocks_unregistered_origin(client):
    d = _create_site(client, origins=("https://example.com",))
    r = client.get(f"/embed?sitekey={d['sitekey']}&origin=https://evil.com")
    assert r.status_code == 403


def test_embed_allows_registered_origin_and_sets_csp(client):
    d = _create_site(client, origins=("https://example.com",))
    r = client.get(f"/embed?sitekey={d['sitekey']}&origin=https://example.com")
    assert r.status_code == 200
    csp = r.headers.get("Content-Security-Policy", "")
    assert "frame-ancestors https://example.com" in csp
    assert "frame-ancestors *" not in csp


def test_embed_disabled_site_rejected(client):
    d = _create_site(client)
    client.put(
        f"/api/embed/sites/{d['sitekey']}/enabled",
        json={"enabled": False},
        headers=_admin_headers(),
    )
    r = client.get(f"/embed?sitekey={d['sitekey']}&origin=https://example.com")
    assert r.status_code == 400


# --- Siteverify ----------------------------------------------------------

def test_siteverify_rejects_bad_secretkey(client):
    d = _create_site(client)
    r = client.post(
        "/api/siteverify",
        json={"secretkey": "wrong", "response": "abc"},
    )
    assert r.status_code == 200
    assert r.get_json()["success"] is False
    assert "invalid-secretkey" in r.get_json()["error-codes"]


def test_siteverify_rejects_forged_token(client):
    d = _create_site(client)
    # A token signed with the WRONG secret (attacker forging).
    forged = sign_token(
        {"session_id": "x", "tier": "hard", "sitekey": d["sitekey"]},
        "attacker-secret-0123456789abcdef0123456789",
    )
    r = client.post(
        "/api/siteverify",
        json={"secretkey": d["secretkey"], "response": forged},
    )
    assert r.status_code == 200
    assert r.get_json()["success"] is False
    assert "invalid-token" in r.get_json()["error-codes"]


def test_siteverify_rejects_token_for_other_site(client):
    d1 = _create_site(client, origins=("https://a.com",))
    d2 = _create_site(client, origins=("https://b.com",))
    # Token bound to site1, verified with site2's secretkey.
    token = sign_token(
        {"session_id": "x", "tier": "hard", "sitekey": d1["sitekey"]},
        SECRET,
    )
    r = client.post(
        "/api/siteverify",
        json={"secretkey": d2["secretkey"], "response": token},
    )
    assert r.status_code == 200
    assert r.get_json()["success"] is False
    assert "sitekey-mismatch" in r.get_json()["error-codes"]


def test_siteverify_success_and_replay_rejected(client):
    d = _create_site(client)
    token = sign_token(
        {"session_id": "x", "tier": "hard", "sitekey": d["sitekey"]},
        SECRET,
    )
    r1 = client.post(
        "/api/siteverify",
        json={"secretkey": d["secretkey"], "response": token},
    )
    assert r1.status_code == 200
    assert r1.get_json()["success"] is True

    # Replay → rejected (single-use).
    r2 = client.post(
        "/api/siteverify",
        json={"secretkey": d["secretkey"], "response": token},
    )
    assert r2.get_json()["success"] is False
    assert "timeout-or-duplicate" in r2.get_json()["error-codes"]


def test_siteverify_sitekey_hint_mismatch(client):
    d1 = _create_site(client, origins=("https://a.com",))
    d2 = _create_site(client, origins=("https://b.com",))
    token = sign_token(
        {"session_id": "x", "tier": "hard", "sitekey": d1["sitekey"]},
        SECRET,
    )
    # Correct secretkey but wrong sitekey hint → reject (anti-laundering).
    r = client.post(
        "/api/siteverify",
        json={"secretkey": d1["secretkey"], "response": token, "sitekey": d2["sitekey"]},
    )
    assert r.get_json()["success"] is False
    assert "sitekey-mismatch" in r.get_json()["error-codes"]


# --- Full embed challenge flow -------------------------------------------

def test_embed_challenge_flow_passes_and_verifies(app, client):
    d = _create_site(client, origins=("https://example.com",))
    sitekey = d["sitekey"]

    # Start an embed session.
    r = client.post(
        "/api/embed/start",
        json={"sitekey": sitekey, "origin": "https://example.com", "tier": "easy"},
    )
    assert r.status_code == 201
    start = r.get_json()
    sid = start["session_id"]
    assert start["current_puzzle"] is not None

    # Answer every puzzle correctly by reading the correct answer from the DB.
    from ai_captcha.database import db
    from ai_captcha.models import PuzzleAttempt

    for _ in range(start["total_puzzles"]):
        with app.app_context():
            attempt = PuzzleAttempt.query.filter_by(
                session_id=sid, user_answer=None
            ).first()
            assert attempt is not None, "expected an unanswered puzzle"
            correct = attempt.correct_answer
        r = client.post(
            f"/api/embed/session/{sid}/answer",
            json={"answer": correct, "sitekey": sitekey},
        )
        assert r.status_code == 200
        body = r.get_json()
        if body["session_status"] != "active":
            break

    # Result should be passed with a token.
    r = client.get(f"/api/embed/session/{sid}/result?sitekey={sitekey}")
    assert r.status_code == 200
    res = r.get_json()
    assert res["passed"] is True
    assert res["verification_token"]
    assert res["sitekey"] == sitekey

    # Verify the token with the secretkey.
    r = client.post(
        "/api/siteverify",
        json={"secretkey": d["secretkey"], "response": res["verification_token"]},
    )
    assert r.status_code == 200
    assert r.get_json()["success"] is True


def test_embed_challenge_flow_fails(client):
    d = _create_site(client, origins=("https://example.com",))
    sitekey = d["sitekey"]

    r = client.post(
        "/api/embed/start",
        json={"sitekey": sitekey, "origin": "https://example.com", "tier": "easy"},
    )
    assert r.status_code == 201
    sid = r.get_json()["session_id"]

    # Answer everything wrong → fail-fast should end the session early.
    for _ in range(6):
        r = client.post(
            f"/api/embed/session/{sid}/answer",
            json={"answer": "definitely-wrong", "sitekey": sitekey},
        )
        assert r.status_code == 200
        if r.get_json()["session_status"] != "active":
            break

    res = client.get(f"/api/embed/session/{sid}/result?sitekey={sitekey}").get_json()
    assert res["passed"] is False
    assert res["verification_token"] is None


def test_embed_session_rejects_wrong_sitekey(client):
    d = _create_site(client, origins=("https://example.com",))
    sitekey = d["sitekey"]
    r = client.post(
        "/api/embed/start",
        json={"sitekey": sitekey, "origin": "https://example.com", "tier": "easy"},
    )
    assert r.status_code == 201
    sid = r.get_json()["session_id"]

    # Accessing the session with the WRONG sitekey → 403.
    r = client.get(f"/api/embed/session/{sid}?sitekey=wrong")
    assert r.status_code == 403
    r = client.post(
        f"/api/embed/session/{sid}/answer",
        json={"answer": "x", "sitekey": "wrong"},
    )
    assert r.status_code == 403
    r = client.get(f"/api/embed/session/{sid}/result?sitekey=wrong")
    assert r.status_code == 403


def test_embed_start_blocks_unregistered_origin(client):
    d = _create_site(client, origins=("https://example.com",))
    r = client.post(
        "/api/embed/start",
        json={"sitekey": d["sitekey"], "origin": "https://evil.com", "tier": "easy"},
    )
    assert r.status_code == 403
