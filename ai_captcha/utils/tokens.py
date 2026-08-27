"""JWT signing and verification for verification tokens."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import jwt


def sign_token(
    payload: dict,
    secret: str,
    ttl_hours: int = 24,
    issuer: str = "ai-captcha",
    with_jti: bool = True,
) -> str:
    """Sign a verification token.

    Adds ``iat``, ``exp``, ``iss`` and (unless ``with_jti=False``) a unique
    ``jti`` for replay protection. ``secret`` is required — never call without
    the signing secret.
    """
    now = datetime.now(timezone.utc)
    body = {
        **payload,
        "iat": now,
        "exp": now + timedelta(hours=ttl_hours),
        "iss": issuer,
    }
    if with_jti:
        body["jti"] = uuid.uuid4().hex
    return jwt.encode(body, secret, algorithm="HS256")


def verify_token(token: str, secret: str, issuer: str = "ai-captcha") -> dict | None:
    try:
        return jwt.decode(token, secret, algorithms=["HS256"], issuer=issuer)
    except jwt.InvalidTokenError:
        return None
