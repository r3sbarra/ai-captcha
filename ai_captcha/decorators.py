"""Decorators for gating routes with AI CAPTCHA verification.

These let you protect any Flask route so that a caller must first pass an
AI CAPTCHA challenge (or present a valid verification token) before the real
handler runs. Designed for embedding AI CAPTCHA into an existing Flask app.

Usage::

    from ai_captcha.decorators import ai_captcha_required, tier_gate

    @app.route("/api/secret")
    @tier_gate("hard")
    @ai_captcha_required
    def secret():
        return {"data": "only verified robots see this"}
"""

from __future__ import annotations

import functools
from typing import Callable, TypeVar

from flask import current_app, jsonify, request

from .utils.logging import log_event
from .utils.security import consume_jti
from .utils.tokens import verify_token as _verify_jwt

F = TypeVar("F", bound=Callable)

# Header carrying the verification token.
TOKEN_HEADER = "X-AI-CAPTCHA-TOKEN"


def _get_token() -> str | None:
    token = request.headers.get(TOKEN_HEADER)
    if token:
        return token
    if request.is_json:
        data = request.get_json(silent=True) or {}
        return data.get("captcha_token")
    return request.args.get("captcha_token")


def _verify_request_token() -> dict | None:
    """Return the decoded token payload if a valid, non-replayed token is present.

    Verification is cached on the request so chained decorators
    (``@tier_gate`` + ``@ai_captcha_required``) only consume the token's ``jti``
    once instead of rejecting it as a replay on the second check.
    """
    cached = getattr(request, "_ai_captcha_verified", None)
    if cached is not None:
        return cached or None

    token = _get_token()
    payload = None
    if token:
        secret = current_app.config.get("TOKEN_SECRET", "")
        issuer = current_app.config.get("TOKEN_ISSUER", "ai-captcha")
        payload = _verify_jwt(token, secret, issuer)
        if payload and current_app.config.get("TOKEN_REPLAY_PROTECTION", True):
            if not consume_jti(payload):
                payload = None  # replay

    request._ai_captcha_verified = payload or None
    return payload


def ai_captcha_required(view: F) -> F:
    """Require a valid AI CAPTCHA verification token on the request.

    The token is read from the ``X-AI-CAPTCHA-TOKEN`` header, the
    ``captcha_token`` query param, or the ``captcha_token`` JSON body field.
    If missing or invalid, returns 401.
    """

    @functools.wraps(view)
    def wrapper(*args, **kwargs):
        payload = _verify_request_token()
        if not payload:
            return (
                jsonify(
                    {
                        "error": "ai_captcha_required",
                        "message": "A valid AI CAPTCHA verification token is required.",
                    }
                ),
                401,
            )
        # Expose the verified token payload to the view.
        request.ai_captcha = payload
        return view(*args, **kwargs)

    return wrapper  # type: ignore[return-value]


def tier_gate(min_tier: str) -> Callable[[F], F]:
    """Require a verification token that passed at least ``min_tier``.

    Tier order: easy < medium < hard. A token issued for a higher tier also
    satisfies a lower-tier gate. Must be used with ``@ai_captcha_required``
    (or after it) so the token payload is available.
    """

    order = {"easy": 0, "medium": 1, "hard": 2}

    def decorator(view: F) -> F:
        @functools.wraps(view)
        def wrapper(*args, **kwargs):
            payload = getattr(request, "ai_captcha", None)
            if not payload:
                # ``ai_captcha_required`` may not have run yet (decorator order).
                payload = _verify_request_token()
            if not payload:
                return (
                    jsonify(
                        {
                            "error": "ai_captcha_required",
                            "message": "A valid AI CAPTCHA verification token is required.",
                        }
                    ),
                    401,
                )
            request.ai_captcha = payload
            token_tier = payload.get("tier", "easy")
            if order.get(token_tier, 0) < order.get(min_tier, 0):
                # --- logging hook: tier_gate_rejected ---
                log_event(
                    current_app._get_current_object(),
                    "warning",
                    "tier_gate_rejected",
                    token_tier=token_tier,
                    required_tier=min_tier,
                    path=request.path,
                )
                return (
                    jsonify(
                        {
                            "error": "tier_insufficient",
                            "message": f"Requires at least '{min_tier}' tier. Token is '{token_tier}'.",
                        }
                    ),
                    403,
                )
            return view(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator


def verify_token(view: F) -> F:
    """Alias of ``ai_captcha_required`` for readability."""
    return ai_captcha_required(view)
