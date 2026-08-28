"""Embeddable (iframe) CAPTCHA — sitekey/secretkey model, siteverify, admin.

This implements the reCAPTCHA-style architecture for embedding the challenge
in a third-party page via an iframe:

* ``GET /embed`` — serves the iframe challenge page. Validates the ``sitekey``
  and ``origin`` query params against the registered ``EmbedSite`` and emits a
  dynamic ``frame-ancestors`` CSP so only the site's registered origins can
  frame it (clickjacking defense).
* ``POST /api/siteverify`` — the host *backend* calls this with
  ``{secretkey, token, remoteip}`` to confirm a pass. Validates the secretkey,
  token signature, expiry, single-use, and sitekey binding. Returns a
  reCAPTCHA-shaped response.
* Admin endpoints under ``/api/embed/sites`` to create/list/delete sites and
  manage allowed origins.

Security model (see README "Embed" section): the pass/fail decision is NEVER
trusted client-side. The iframe posts a token to the host via postMessage; the
host backend must verify it here with the secretkey. A forged postMessage or a
replayed token is rejected because the token is single-use, short-lived, and
bound to the sitekey.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import uuid

from flask import Blueprint, current_app, jsonify, render_template, request

from ..database import db
from ..engine.gating import TIER_ORDER
from ..engine.session import SessionManager
from ..models import EmbedSite
from ..utils.security import consume_jti, rate_limit
from ..utils.tokens import verify_token

embed_bp = Blueprint("embed", __name__)

_manager = SessionManager()

# Default token TTL for embed tokens (seconds). reCAPTCHA uses 120s.
EMBED_TOKEN_TTL_SECONDS = 120


def _hash_secretkey(secretkey: str) -> str:
    return hashlib.sha256(secretkey.encode()).hexdigest()


def _origin_of() -> str:
    """The request's origin (scheme://host[:port]), or '' if absent."""
    return request.headers.get("Origin", "") or request.headers.get("Referer", "")


def _normalize_origin(origin: str) -> str:
    """Strip a trailing slash and path from an origin string."""
    origin = (origin or "").strip().rstrip("/")
    # Keep only scheme://host[:port]
    if "://" in origin:
        scheme, rest = origin.split("://", 1)
        host = rest.split("/", 1)[0]
        return f"{scheme}://{host}"
    return origin


def _get_site(sitekey: str) -> EmbedSite | None:
    return db.session.get(EmbedSite, sitekey)


def _require_admin() -> tuple[dict, int] | None:
    """Enforce the embed admin bearer token. Returns an error payload if
    unauthorized, else None (authorized). Fails closed when no token is set."""
    expected = current_app.config.get("EMBED_ADMIN_TOKEN", "")
    if not expected:
        return jsonify({"error": "admin_disabled", "message": "Embed admin is disabled (no EMBED_ADMIN_TOKEN configured)."}), 403
    auth = request.headers.get("Authorization", "")
    token = auth[7:] if auth.startswith("Bearer ") else ""
    if not token or token != expected:
        return jsonify({"error": "unauthorized", "message": "A valid admin token is required."}), 401
    return None


# --- Admin: manage embed sites ---------------------------------------------

@embed_bp.route("/api/embed/sites", methods=["POST"])
def create_site():
    """Create an embed site. Returns the sitekey + secretkey (shown once)."""
    err = _require_admin()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()[:200]
    origins = [_normalize_origin(o) for o in (data.get("allowed_origins") or [])]
    origins = [o for o in origins if o]

    sitekey = secrets.token_urlsafe(16)
    secretkey = secrets.token_urlsafe(32)

    site = EmbedSite(
        sitekey=sitekey,
        secretkey_hash=_hash_secretkey(secretkey),
        name=name or None,
        enabled=True,
    )
    site.set_origins(origins)
    db.session.add(site)
    db.session.commit()

    return (
        jsonify(
            {
                "sitekey": sitekey,
                "secretkey": secretkey,  # shown once — store it server-side
                "name": site.name,
                "allowed_origins": site.origins(),
            }
        ),
        201,
    )


@embed_bp.route("/api/embed/sites", methods=["GET"])
def list_sites():
    err = _require_admin()
    if err:
        return err
    sites = EmbedSite.query.order_by(EmbedSite.created_at.desc()).all()
    return jsonify({"sites": [s.to_dict() for s in sites]})


@embed_bp.route("/api/embed/sites/<sitekey>", methods=["DELETE"])
def delete_site(sitekey: str):
    err = _require_admin()
    if err:
        return err
    site = _get_site(sitekey)
    if not site:
        return jsonify({"error": "not_found", "message": "Site not found"}), 404
    db.session.delete(site)
    db.session.commit()
    return jsonify({"deleted": sitekey})


@embed_bp.route("/api/embed/sites/<sitekey>/origins", methods=["PUT"])
def set_origins(sitekey: str):
    err = _require_admin()
    if err:
        return err
    site = _get_site(sitekey)
    if not site:
        return jsonify({"error": "not_found", "message": "Site not found"}), 404
    data = request.get_json(silent=True) or {}
    origins = [_normalize_origin(o) for o in (data.get("allowed_origins") or [])]
    origins = [o for o in origins if o]
    site.set_origins(origins)
    db.session.commit()
    return jsonify(site.to_dict())


@embed_bp.route("/api/embed/sites/<sitekey>/enabled", methods=["PUT"])
def set_enabled(sitekey: str):
    err = _require_admin()
    if err:
        return err
    site = _get_site(sitekey)
    if not site:
        return jsonify({"error": "not_found", "message": "Site not found"}), 404
    data = request.get_json(silent=True) or {}
    site.enabled = bool(data.get("enabled", True))
    db.session.commit()
    return jsonify(site.to_dict())


@embed_bp.route("/api/embed/demo-site", methods=["POST"])
def create_demo_site():
    """Create a throwaway embed site for the demo page (no admin token needed).

    The demo page needs a sitekey/secretkey to exercise the widget + siteverify
    flow, but must NOT call the admin endpoints (which require the admin token).
    This endpoint creates an ephemeral site bound to the caller's origin and
    returns the secretkey so the demo can run a real siteverify from the browser.
    It is rate-limited and only ever creates throwaway sites.
    """
    data = request.get_json(silent=True) or {}
    origin = _normalize_origin(data.get("origin", ""))
    if not origin:
        return jsonify({"error": "missing_origin", "message": "An origin is required."}), 400

    # Rate-limit demo site creation per client to prevent abuse.
    limit = int(current_app.config.get("RATE_LIMIT_START_PER_MIN", 30))
    ok, _ = rate_limit("demo-site", limit)
    if not ok:
        return jsonify({"error": "rate_limited", "message": "Too many demo sites."}), 429

    sitekey = secrets.token_urlsafe(16)
    secretkey = secrets.token_urlsafe(32)
    site = EmbedSite(
        sitekey=sitekey,
        secretkey_hash=_hash_secretkey(secretkey),
        name="Embed Demo (ephemeral)",
        enabled=True,
    )
    site.set_origins([origin])
    db.session.add(site)
    db.session.commit()
    return jsonify({"sitekey": sitekey, "secretkey": secretkey, "allowed_origins": [origin]}), 201


# --- Embed page ------------------------------------------------------------

@embed_bp.route("/embed")
def embed():
    """Serve the iframe challenge page.

    Requires ``?sitekey=...&origin=...``. The origin must be registered on the
    site, otherwise we refuse to render (and emit no frame-ancestors header for
    that origin, so the browser blocks framing anyway).
    """
    sitekey = request.args.get("sitekey", "")
    origin = _normalize_origin(request.args.get("origin", ""))
    tier = request.args.get("tier", current_app.config.get("DEFAULT_TIER", "medium"))

    site = _get_site(sitekey) if sitekey else None
    if not site or not site.enabled:
        return jsonify({"error": "invalid_sitekey", "message": "Unknown or disabled sitekey"}), 400
    if tier not in TIER_ORDER:
        return jsonify({"error": "invalid_tier", "message": f"Must be one of {TIER_ORDER}"}), 400
    if origin not in site.origins():
        # Not a registered origin — refuse to render. Also log for visibility.
        current_app.logger.warning(
            "embed blocked: sitekey=%s origin=%s not in allowed_origins", sitekey, origin
        )
        return jsonify({"error": "origin_not_allowed", "message": "Origin not registered for this sitekey"}), 403

    # Dynamic frame-ancestors CSP: only the site's registered origins may frame.
    allowed = site.origins()
    frame_ancestors = " ".join(allowed) if allowed else "'none'"

    from flask import make_response

    resp = make_response(
        render_template(
            "embed.html",
            sitekey=sitekey,
            origin=origin,
            tier=tier,
            base_path=request.script_root.rstrip("/"),
        )
    )
    resp.headers["Content-Security-Policy"] = (
        f"default-src 'self'; "
        f"script-src 'self' 'unsafe-inline'; "
        f"style-src 'self' 'unsafe-inline'; "
        f"img-src 'self' data:; "
        f"connect-src 'self'; "
        f"base-uri 'self'; form-action 'self'; "
        f"frame-ancestors {frame_ancestors};"
    )
    # X-Frame-Options is a deprecated fallback (ALLOW-FROM is ignored by modern
    # browsers). SAMEORIGIN at least blocks fully cross-origin framing if the
    # CSP is ever stripped; the CSP frame-ancestors above is the real defense.
    resp.headers["X-Frame-Options"] = "SAMEORIGIN"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Referrer-Policy"] = "no-referrer"
    return resp


# --- Siteverify (host backend) ---------------------------------------------

@embed_bp.route("/api/siteverify", methods=["POST"])
def siteverify():
    """Verify a challenge token. Called by the host backend with the secretkey.

    Request (form or JSON): ``secretkey``, ``response`` (token), optional
    ``remoteip``, optional ``sitekey``.

    Response (reCAPTCHA-shaped): ``{success, challenge_ts, hostname, error-codes}``.
    """
    # Rate-limit verify calls per secretkey to blunt brute force.
    data = request.get_json(silent=True) or request.form.to_dict() or {}
    secretkey = data.get("secretkey", "")
    token = data.get("response", "") or data.get("token", "")
    remoteip = data.get("remoteip", "")
    sitekey_hint = data.get("sitekey", "")

    if not secretkey or not token:
        return jsonify({"success": False, "error-codes": ["missing-input"]}), 400

    # Rate limit by secretkey hash.
    sk_hash = _hash_secretkey(secretkey)
    limit = int(current_app.config.get("RATE_LIMIT_VERIFY_PER_MIN", 60))
    ok, _ = rate_limit(f"verify:{sk_hash}", limit)
    if not ok:
        return jsonify({"success": False, "error-codes": ["rate-limited"]}), 429

    # Find the site by secretkey hash.
    site = EmbedSite.query.filter_by(secretkey_hash=sk_hash).first()
    if not site or not site.enabled:
        return jsonify({"success": False, "error-codes": ["invalid-secretkey"]}), 200

    # If a sitekey hint was provided, it must match (prevents cross-sitekey
    # token laundering).
    if sitekey_hint and sitekey_hint != site.sitekey:
        return jsonify({"success": False, "error-codes": ["sitekey-mismatch"]}), 200

    secret = current_app.config.get("TOKEN_SECRET", "")
    issuer = current_app.config.get("TOKEN_ISSUER", "ai-captcha")
    payload = verify_token(token, secret, issuer=issuer)
    if not payload:
        return jsonify({"success": False, "error-codes": ["invalid-token"]}), 200

    # Token must be bound to this sitekey.
    if payload.get("sitekey") != site.sitekey:
        return jsonify({"success": False, "error-codes": ["sitekey-mismatch"]}), 200

    # Single-use: consume the jti atomically. Replay → reject.
    if not consume_jti(payload, ttl_seconds=EMBED_TOKEN_TTL_SECONDS):
        return jsonify({"success": False, "error-codes": ["timeout-or-duplicate"]}), 200

    return jsonify(
        {
            "success": True,
            "challenge_ts": payload.get("iat"),
            "hostname": site.name,
            "sitekey": site.sitekey,
            "tier": payload.get("tier"),
            "error-codes": [],
        }
    )


# --- Embed session API (used by the iframe) --------------------------------

@embed_bp.route("/api/embed/start", methods=["POST"])
def embed_start():
    """Start an embed challenge session bound to a sitekey.

    The iframe calls this (same-origin) to begin a challenge. The session is
    bound to the sitekey so the issued token can't be replayed elsewhere.
    """
    data = request.get_json(silent=True) or {}
    sitekey = data.get("sitekey", "")
    origin = _normalize_origin(data.get("origin", ""))
    tier = data.get("tier", current_app.config.get("DEFAULT_TIER", "medium"))

    site = _get_site(sitekey) if sitekey else None
    if not site or not site.enabled:
        return jsonify({"error": "invalid_sitekey", "message": "Unknown or disabled sitekey"}), 400
    if origin not in site.origins():
        return jsonify({"error": "origin_not_allowed", "message": "Origin not registered"}), 403
    if tier not in TIER_ORDER:
        return jsonify({"error": "invalid_tier", "message": f"Must be one of {TIER_ORDER}"}), 400

    session = _manager.create_session(
        tier=tier,
        model_name="embed",
        client_id=request.remote_addr,
        sitekey=sitekey,
    )
    _manager.start_session(session.id)
    puzzle = _manager.get_current_puzzle(session.id)
    return (
        jsonify(
            {
                "session_id": session.id,
                "tier": session.tier,
                "status": session.status,
                "total_puzzles": session.total_puzzles,
                "time_limit_total": session.time_limit_total,
                "started_at": session.started_at.isoformat() if session.started_at else None,
                "current_puzzle": puzzle,
            }
        ),
        201,
    )


@embed_bp.route("/api/embed/session/<session_id>", methods=["GET"])
def embed_session_status(session_id: str):
    """Current puzzle for an embed session (same-origin iframe call)."""
    from ..models import ChallengeSession

    s = db.session.get(ChallengeSession, session_id)
    if not s:
        return jsonify({"error": "not_found", "message": "Session not found"}), 404
    # Bind the session to its sitekey: the caller must present the same sitekey
    # the session was created under (prevents cross-sitekey session access).
    sitekey = request.args.get("sitekey", "") or (request.get_json(silent=True) or {}).get("sitekey", "")
    if s.sitekey and sitekey != s.sitekey:
        return jsonify({"error": "sitekey_mismatch", "message": "Session belongs to a different sitekey"}), 403
    puzzle = _manager.get_current_puzzle(session_id)
    return jsonify({"session": s.to_dict(), "current_puzzle": puzzle})


@embed_bp.route("/api/embed/session/<session_id>/answer", methods=["POST"])
def embed_answer(session_id: str):
    """Submit an answer for an embed session."""
    data = request.get_json(silent=True) or {}
    answer = data.get("answer", "")
    if not answer:
        return jsonify({"error": "no_answer", "message": "No answer provided"}), 400
    max_len = int(current_app.config.get("MAX_ANSWER_LENGTH", 10000))
    if len(answer) > max_len:
        return jsonify({"error": "answer_too_long", "message": f"Answer exceeds {max_len} chars"}), 400

    from ..models import ChallengeSession

    s = db.session.get(ChallengeSession, session_id)
    if s and s.sitekey and data.get("sitekey") != s.sitekey:
        return jsonify({"error": "sitekey_mismatch", "message": "Session belongs to a different sitekey"}), 403

    try:
        result = _manager.submit_answer(session_id, str(answer))
    except ValueError as e:
        return jsonify({"error": "bad_request", "message": str(e)}), 400

    if result.get("status") == "expired":
        return jsonify(result), 410

    if result["session_status"] == "active":
        result["next_puzzle"] = _manager.get_current_puzzle(session_id)

    return jsonify(result), 200


@embed_bp.route("/api/embed/session/<session_id>/result", methods=["GET"])
def embed_result(session_id: str):
    """Final result for an embed session, including the verification token."""
    from ..models import ChallengeSession

    s = db.session.get(ChallengeSession, session_id)
    if not s:
        return jsonify({"error": "not_found", "message": "Session not found"}), 404
    sitekey = request.args.get("sitekey", "") or (request.get_json(silent=True) or {}).get("sitekey", "")
    if s.sitekey and sitekey != s.sitekey:
        return jsonify({"error": "sitekey_mismatch", "message": "Session belongs to a different sitekey"}), 403
    pass_rate = (s.puzzles_solved / s.total_puzzles) if s.total_puzzles else 0
    return jsonify(
        {
            "session_id": s.id,
            "tier": s.tier,
            "status": s.status,
            "puzzles_solved": s.puzzles_solved,
            "total_puzzles": s.total_puzzles,
            "pass_rate": round(pass_rate, 3),
            "passed": bool(s.verification_token),
            "verification_token": s.verification_token,
            "sitekey": s.sitekey,
        }
    )
