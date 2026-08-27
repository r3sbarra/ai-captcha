"""Server-authoritative timer logic.

The client receives ``started_at`` and ``time_limit_total`` and displays a
cosmetic countdown, but the server re-checks elapsed time on every request.
This prevents client-side tampering.
"""

from __future__ import annotations

from datetime import datetime, timezone


def remaining_seconds(started_at: datetime | None, time_limit_total: int) -> int:
    if started_at is None:
        return time_limit_total
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)
    elapsed = (datetime.now(timezone.utc) - started_at).total_seconds()
    return max(0, int(time_limit_total - elapsed))


def is_expired(started_at: datetime | None, time_limit_total: int) -> bool:
    return remaining_seconds(started_at, time_limit_total) <= 0
