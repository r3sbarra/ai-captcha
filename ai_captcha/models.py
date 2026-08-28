"""Database models for AI CAPTCHA challenge sessions and puzzle attempts."""

from __future__ import annotations

from datetime import datetime, timezone

from .database import db


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def to_utc_iso(dt: datetime | None) -> str | None:
    """Serialize a datetime as an unambiguous UTC ISO-8601 string.

    SQLite stores datetimes naively (tzinfo dropped), so naive values are
    treated as UTC here and emitted with a trailing ``Z``. Without this,
    the browser's ``new Date()`` would parse a bare ``2026-..T..`` as LOCAL
    time, skewing client-side countdowns by the UTC offset (the absurd-timer
    bug).
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class ChallengeSession(db.Model):
    __tablename__ = "challenge_sessions"

    id = db.Column(db.String(36), primary_key=True)  # UUID
    tier = db.Column(db.String(20), nullable=False)  # easy/medium/hard
    status = db.Column(db.String(20), default="created", nullable=False)
    # created, active, completed, expired, failed

    model_name = db.Column(db.String(100), nullable=True)  # AI model identifier
    client_id = db.Column(db.String(255), nullable=True)  # IP or agent identifier
    # When created via the embeddable (iframe) flow, the sitekey this session is
    # bound to. Used to prevent cross-sitekey token/session laundering.
    sitekey = db.Column(db.String(64), nullable=True)

    total_puzzles = db.Column(db.Integer, default=5)
    puzzles_solved = db.Column(db.Integer, default=0)
    puzzles_attempted = db.Column(db.Integer, default=0)
    current_puzzle_index = db.Column(db.Integer, default=0)

    time_limit_total = db.Column(db.Integer, nullable=False)  # total seconds
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)

    # Signed token issued on success
    verification_token = db.Column(db.String(500), nullable=True)

    attempts = db.relationship(
        "PuzzleAttempt",
        backref="session",
        cascade="all, delete-orphan",
        order_by="PuzzleAttempt.puzzle_index",
    )

    def is_expired(self) -> bool:
        if not self.started_at or self.status != "active":
            return False
        elapsed = (datetime.now(timezone.utc) - self.started_at).total_seconds()
        return elapsed > self.time_limit_total

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tier": self.tier,
            "status": self.status,
            "model_name": self.model_name,
            "total_puzzles": self.total_puzzles,
            "puzzles_solved": self.puzzles_solved,
            "puzzles_attempted": self.puzzles_attempted,
            "current_puzzle_index": self.current_puzzle_index,
            "time_limit_total": self.time_limit_total,
            "started_at": to_utc_iso(self.started_at),
            "completed_at": to_utc_iso(self.completed_at),
        }


class EmbedSite(db.Model):
    """A registered embeddable (iframe) CAPTCHA site.

    Mirrors the reCAPTCHA model: a ``sitekey`` (public, used by the iframe) and a
    ``secretkey`` (private, used by the host backend to verify tokens). Only the
    SHA-256 hash of the secretkey is stored; the raw value is shown once at
    creation. ``allowed_origins`` controls which origins may frame the challenge
    (clickjacking defense via a dynamic ``frame-ancestors`` CSP).
    """

    __tablename__ = "embed_sites"

    sitekey = db.Column(db.String(64), primary_key=True)
    secretkey_hash = db.Column(db.String(64), nullable=False, unique=True)
    name = db.Column(db.String(200), nullable=True)
    enabled = db.Column(db.Boolean, default=True, nullable=False)
    allowed_origins = db.Column(db.Text, nullable=False, default="")  # newline-separated
    created_at = db.Column(db.DateTime, default=_utcnow, nullable=False)

    def set_origins(self, origins: list[str]) -> None:
        """Store the allowed origins as a newline-separated list."""
        self.allowed_origins = "\n".join(origins)

    def origins(self) -> list[str]:
        """Return the allowed origins as a list."""
        return [o for o in (self.allowed_origins or "").split("\n") if o]

    def to_dict(self) -> dict:
        """Public view — never exposes the secretkey or its hash."""
        return {
            "sitekey": self.sitekey,
            "name": self.name,
            "enabled": self.enabled,
            "allowed_origins": self.origins(),
            "created_at": to_utc_iso(self.created_at),
        }


class PuzzleAttempt(db.Model):
    __tablename__ = "puzzle_attempts"

    id = db.Column(db.String(36), primary_key=True)
    session_id = db.Column(
        db.String(36), db.ForeignKey("challenge_sessions.id"), nullable=False
    )
    puzzle_index = db.Column(db.Integer, nullable=False)
    puzzle_type = db.Column(db.String(50), nullable=False)
    tier = db.Column(db.String(20), nullable=False)
    question = db.Column(db.Text, nullable=False)
    correct_answer = db.Column(db.Text, nullable=True)  # audit only, never sent to client
    user_answer = db.Column(db.Text, nullable=True)
    is_correct = db.Column(db.Boolean, default=False)
    time_taken_ms = db.Column(db.Integer, nullable=True)
    time_limit = db.Column(db.Integer, nullable=True)  # per-puzzle seconds
    created_at = db.Column(db.DateTime, default=_utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "puzzle_index": self.puzzle_index,
            "puzzle_type": self.puzzle_type,
            "tier": self.tier,
            "question": self.question,
            "is_correct": self.is_correct,
            "time_taken_ms": self.time_taken_ms,
            "time_limit": self.time_limit,
        }
