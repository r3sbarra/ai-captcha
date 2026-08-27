"""Security helpers: secret guard, security headers, rate limiting, replay protection.

These are wired into the app factory (secret guard, headers) and used by the
API routes (rate limiting) and token issuance/verification (replay protection).
All are built on the pluggable cache (see ``utils/cache.py``) so they work
with any backend — memory, file, Redis, Memcached, etc.
"""

from __future__ import annotations

import time

from flask import current_app, jsonify, request

from .cache import get_cache, make_key

# Secrets that, if left as defaults, mean tokens can be forged by anyone who
# reads the source. These are the published dev defaults.
_INSECURE_SECRETS = {"token-signing-secret", "ai-captcha-dev-secret-change-me"}
_MIN_SECRET_LEN = 32  # RFC 7518 §3.2: HMAC keys should be >= 256 bits.


def check_secrets(app) -> None:
    """Validate token secrets at startup.

    * If ``SECRET_MODE == \"error\"`` (default) and the secret is the default or
      too short, raise — fail closed rather than ship forgeable tokens.
    * If ``SECRET_MODE == \"warn\"``, log a loud warning instead.
    * If ``SECRET_MODE == \"off\"``, do nothing (dev only).
    """
    mode = str(app.config.get("SECRET_MODE", "error")).lower()
    if mode == "off":
        return

    problems = []
    secret = app.config.get("TOKEN_SECRET", "")
    if secret in _INSECURE_SECRETS:
        problems.append("TOKEN_SECRET is still the published default (forgeable tokens)")
    if len(secret) < _MIN_SECRET_LEN:
        problems.append(
            f"TOKEN_SECRET is {len(secret)} chars (< {_MIN_SECRET_LEN} min; RFC 7518)"
        )

    if not problems:
        return

    msg = "AI CAPTCHA security check failed: " + "; ".join(problems) + (
        ". Set AIC_TOKEN_SECRET to a strong, random value (>= 32 chars) in production."
    )
    if mode == "warn":
        import logging

        logging.getLogger("ai_captcha").warning(msg)
        return
    raise RuntimeError(msg)


def apply_security_headers(response) -> None:
    """Attach baseline security headers when ``SECURITY_HEADERS`` is enabled."""
    if not current_app.config.get("SECURITY_HEADERS", True):
        return
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    # The UI ships its JS as inline <script> blocks and inline style=""
    # attributes (base.html + every template), so a strict CSP that omits
    # 'unsafe-inline' for script-src/style-src BREAKS the app: the modal's
    # inline style="display:none" gets dropped (modal stuck open) and the
    # inline handlers never attach (can't close it).
    # We keep the useful hard restrictions (self-only origins, no remote
    # scripts, no data:/blob: script sources, frame-ancestors none).
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "base-uri 'self'; form-action 'self'; frame-ancestors 'none';",
    )
    if current_app.config.get("SESSION_COOKIE_SECURE", False):
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response


def client_key() -> str:
    """A stable per-client identifier for rate limiting.

    Prefers a forwarded client id when behind a trusted proxy (set
    ``TRUST_PROXY_HEADERS`` + ``TRUSTED_PROXY_COUNT`` or a ProxyFix-style
    config). Falls back to ``request.remote_addr``.
    """
    from .proxy import get_client_ip

    return get_client_ip()


def rate_limit(scope: str, limit: int, window_seconds: int = 60) -> tuple[bool, int]:
    """Enforce a sliding-ish window limit for ``scope``.

    Returns ``(allowed, current_count)``. ``allowed`` is False (and the caller
    should return 429) when the current count exceeds ``limit``. ``limit`` of
    0 or None disables the check (always allowed).
    """
    if not limit:
        return True, 0
    cache = get_cache(current_app)
    key = make_key(["rl", scope, client_key()])
    count = cache.incr(key, delta=1, ttl_seconds=window_seconds)
    return count <= limit, count


def check_rate_limits() -> dict | None:
    """Enforce the configured per-route rate limits.

    Returns an error payload dict if a limit is exceeded, else None.
    Called at the top of each rate-limited route.
    """
    path = request.path
    if path.endswith("/start"):
        limit = current_app.config.get("RATE_LIMIT_START_PER_MIN", 30)
        ok, _ = rate_limit("start", int(limit or 0))
        if not ok:
            return _rate_error("start", limit)
    elif "/answer" in path:
        limit = current_app.config.get("RATE_LIMIT_ANSWER_PER_MIN", 120)
        ok, _ = rate_limit("answer", int(limit or 0))
        if not ok:
            return _rate_error("answer", limit)

    global_limit = int(current_app.config.get("RATE_LIMIT_GLOBAL_PER_MIN", 0) or 0)
    if global_limit:
        ok, _ = rate_limit("global", global_limit)
        if not ok:
            return _rate_error("global", global_limit)
    return None


def _rate_error(scope: str, limit: int) -> dict:
    return jsonify(
        {
            "error": "rate_limited",
            "message": f"Too many requests ({scope} limit {limit}/min reached).",
        }
    )


# --- Replay protection ------------------------------------------------------

def consume_jti(token_payload: dict, ttl_seconds: int | None = None) -> bool:
    """Mark a token's ``jti`` as consumed. Returns True if newly consumed
    (allowed), False if already seen (replay → reject)."""
    jti = token_payload.get("jti")
    if not jti:
        return True  # no jti → no replay protection for this token
    cache = get_cache(current_app)
    key = make_key(["jti", jti])
    if ttl_seconds is None:
        ttl_seconds = current_app.config.get("TOKEN_TTL_HOURS", 24) * 3600
    seen = cache.get(key)
    if seen is not None:
        return False
    cache.set(key, True, ttl_seconds=ttl_seconds)
    return True


def _replay_error() -> tuple[dict, int]:
    return (
        jsonify(
            {
                "error": "token_replayed",
                "message": "This verification token has already been used.",
            }
        ),
        401,
    )
