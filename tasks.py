"""Scheduled task for AppManager cron — hourly cleanup of old sessions."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


def cleanup_sessions() -> None:
    """Purge challenge sessions completed more than 24h ago."""
    print(f"[AI-CAPTCHA CRON] Cleaning up sessions at {datetime.now(timezone.utc).isoformat()}")

    try:
        from ai_captcha.database import db
        from ai_captcha.models import ChallengeSession

        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        old = ChallengeSession.query.filter(
            ChallengeSession.completed_at < cutoff
        ).all()
        for s in old:
            db.session.delete(s)
        db.session.commit()
        print(f"[AI-CAPTCHA CRON] Purged {len(old)} old sessions.")

        try:
            from appmanager.bridge import report_event

            report_event("ai-captcha", "cron_cleanup", {"purged": len(old)})
        except ImportError:
            pass
    except Exception as e:  # noqa: BLE001
        print(f"[AI-CAPTCHA CRON ERROR] {e}")
