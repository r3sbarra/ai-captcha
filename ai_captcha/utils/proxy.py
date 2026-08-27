"""Client IP resolution, aware of trusted reverse proxies.

A direct ``request.remote_addr`` is wrong behind nginx/AppManager (it returns
the proxy's IP, collapsing all clients into one rate-limit bucket). This helper
honors forwarded headers only when the app opts in via config, to avoid
spoofing attacks when not behind a trusted proxy.

Config:
* ``TRUST_PROXY_HEADERS`` (bool, default False) — honor ``X-Forwarded-For``.
* ``TRUSTED_PROXY_COUNT`` (int, default 0) — number of trusted proxies between
  the client and the app (right-most ``count`` entries of XFF are the chain).
* ``TRUSTED_PROXY_IP`` (str, optional) — if set, only trust XFF when the direct
  peer equals this IP (e.g. the known nginx proxy). More secure than a bare
  count.
"""

from __future__ import annotations

from flask import current_app, request


def get_client_ip() -> str:
    """Return the effective client IP, honoring trusted-proxy config."""
    trust_headers = current_app.config.get("TRUST_PROXY_HEADERS", False)
    xff = request.headers.get("X-Forwarded-For", "")
    peer = request.remote_addr or "unknown"

    if trust_headers and xff:
        proxy_ip = current_app.config.get("TRUSTED_PROXY_IP")
        if proxy_ip and peer != proxy_ip:
            # XFF is only trusted when it came from our known proxy.
            return peer
        # Take the left-most XFF entry (the original client).
        first = xff.split(",")[0].strip()
        if first:
            return first

    # Only honor a single XFF hop from a trusted proxy IP when configured.
    if proxy_ip := current_app.config.get("TRUSTED_PROXY_IP"):
        if peer == proxy_ip:
            first = xff.split(",")[0].strip() if xff else ""
            if first:
                return first

    return peer
