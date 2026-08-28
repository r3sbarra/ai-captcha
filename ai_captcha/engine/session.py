"""Challenge session state machine and manager."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone

from flask import current_app

from ..database import db
from ..models import ChallengeSession, PuzzleAttempt
from ..utils.logging import log_event
from .base import Puzzle
from .gating import check_model_allowed, get_tier_config
from .registry import discover, get_generator, pick_puzzle_types
from .timer import is_expired


def _hash_token(token: str) -> str:
    """Short hash of a token for logging — never log raw tokens."""
    return hashlib.sha256(token.encode()).hexdigest()[:12]


def _elapsed_ms(started_at) -> int:
    """Milliseconds elapsed since ``started_at``, tolerant of naive/aware mix."""
    now = datetime.now(timezone.utc)
    if started_at is None:
        return 0
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)
    return int((now - started_at).total_seconds() * 1000)


class SessionManager:
    """Creates, advances, and completes challenge sessions."""

    def __init__(self) -> None:
        discover()  # auto-register all puzzle generators

    # --- creation ---

    def create_session(
        self,
        tier: str = "medium",
        model_name: str | None = None,
        client_id: str | None = None,
        allowlist: list[str] | None = None,
        sitekey: str | None = None,
    ) -> ChallengeSession:
        config = get_tier_config(tier)
        if model_name and not check_model_allowed(model_name, allowlist):
            raise ValueError(f"Model '{model_name}' is not on the allowlist.")

        session = ChallengeSession(
            id=str(uuid.uuid4()),
            tier=tier,
            model_name=model_name,
            client_id=client_id,
            sitekey=sitekey,
            # +1 reserves the final slot for the fixed "Are you AI?" puzzle.
            total_puzzles=config.puzzles_per_session + 1,
            time_limit_total=config.timer_seconds,
        )
        db.session.add(session)
        db.session.commit()
        return session

    def start_session(self, session_id: str) -> ChallengeSession:
        session = db.session.get(ChallengeSession, session_id)
        if not session or session.status != "created":
            raise ValueError("Session not found or already started.")
        session.status = "active"
        session.started_at = datetime.now(timezone.utc)
        db.session.commit()
        return session

    # --- puzzle flow ---

    def get_current_puzzle(self, session_id: str) -> dict | None:
        session = db.session.get(ChallengeSession, session_id)
        if not session or session.status != "active":
            return None
        if is_expired(session.started_at, session.time_limit_total):
            self._expire(session)
            return None
        if session.current_puzzle_index >= session.total_puzzles:
            self._complete(session)
            return None

        existing = PuzzleAttempt.query.filter_by(
            session_id=session_id, puzzle_index=session.current_puzzle_index
        ).first()
        if existing and not existing.user_answer:
            return self._puzzle_to_dict(existing)

        # Generate a fresh puzzle for this slot.
        # The final slot is always the fixed "Are you AI?" question.
        if session.current_puzzle_index == session.total_puzzles - 1:
            ptype = "are_you_ai"
        else:
            # Never let the existential question leak into a non-final slot.
            # Filter it out of the picked pool; re-pick to fill any gap left by
            # the filter so the list always has enough entries.
            puzzle_types = pick_puzzle_types(
                session.tier, session.total_puzzles - 1
            )
            puzzle_types = [t for t in puzzle_types if t != "are_you_ai"]
            while len(puzzle_types) < session.total_puzzles - 1:
                puzzle_types += [
                    t for t in pick_puzzle_types(session.tier, 1)
                    if t != "are_you_ai"
                ]
            ptype = puzzle_types[session.current_puzzle_index]
        gen = get_generator(ptype)
        puzzle = gen.generate(session.tier)

        attempt = PuzzleAttempt(
            id=str(uuid.uuid4()),
            session_id=session_id,
            puzzle_index=session.current_puzzle_index,
            puzzle_type=ptype,
            tier=session.tier,
            question=puzzle.question,
            correct_answer=puzzle.answer,
            time_limit=puzzle.time_limit,
        )
        db.session.add(attempt)
        db.session.commit()
        return self._puzzle_to_dict(attempt)

    def submit_answer(self, session_id: str, answer: str) -> dict:
        session = db.session.get(ChallengeSession, session_id)
        if not session or session.status != "active":
            raise ValueError("Session not active.")
        if is_expired(session.started_at, session.time_limit_total):
            self._expire(session)
            return {"status": "expired", "result": None}

        attempt = PuzzleAttempt.query.filter_by(
            session_id=session_id, puzzle_index=session.current_puzzle_index
        ).first()
        if not attempt or attempt.user_answer:
            raise ValueError("No active puzzle to answer.")

        gen = get_generator(attempt.puzzle_type)
        puzzle = Puzzle(question=attempt.question, answer=attempt.correct_answer)
        is_correct = gen.validate(puzzle, answer)

        attempt.user_answer = answer
        attempt.is_correct = is_correct
        attempt.time_taken_ms = int(
            _elapsed_ms(attempt.created_at)
        )
        session.puzzles_attempted += 1
        if is_correct:
            session.puzzles_solved += 1
        session.current_puzzle_index += 1

        # --- logging hook: puzzle_answered ---
        log_event(
            current_app._get_current_object(),
            "info",
            "puzzle_answered",
            session_id=session_id,
            tier=session.tier,
            model=session.model_name or "anonymous",
            puzzle_index=attempt.puzzle_index,
            puzzle_type=attempt.puzzle_type,
            correct=is_correct,
            elapsed_ms=attempt.time_taken_ms or 0,
            puzzles_solved=session.puzzles_solved,
            puzzles_remaining=session.total_puzzles - session.current_puzzle_index,
        )

        if session.current_puzzle_index >= session.total_puzzles:
            self._complete(session)

        db.session.commit()

        response: dict = {
            "correct": is_correct,
            "puzzles_solved": session.puzzles_solved,
            "puzzles_remaining": session.total_puzzles - session.current_puzzle_index,
            "session_status": session.status,
        }
        # Surface the existential rejection when the final question is answered wrong.
        if attempt.puzzle_type == "are_you_ai" and not is_correct:
            response["message"] = puzzle.metadata.get(
                "failure_message", "This is for AI only."
            )

        return response

    # --- completion ---

    def _complete(self, session: ChallengeSession) -> None:
        session.status = "completed"
        session.completed_at = datetime.now(timezone.utc)
        config = get_tier_config(session.tier)
        passed = bool(session.total_puzzles and (
            session.puzzles_solved / session.total_puzzles >= config.min_pass_rate
        ))
        if passed:
            session.verification_token = self._issue_token(session)

        # --- logging hook: session_complete ---
        log_event(
            current_app._get_current_object(),
            "info",
            "session_complete",
            session_id=session.id,
            tier=session.tier,
            model=session.model_name or "anonymous",
            puzzles_solved=session.puzzles_solved,
            total_puzzles=session.total_puzzles,
            pass_rate=round(session.puzzles_solved / session.total_puzzles, 3) if session.total_puzzles else 0,
            passed=passed,
        )

    def _expire(self, session: ChallengeSession) -> None:
        session.status = "expired"
        session.completed_at = datetime.now(timezone.utc)

        # --- logging hook: session_expired ---
        log_event(
            current_app._get_current_object(),
            "info",
            "session_expired",
            session_id=session.id,
            tier=session.tier,
            model=session.model_name or "anonymous",
            puzzles_attempted=session.puzzles_attempted,
            total_puzzles=session.total_puzzles,
        )

    def _issue_token(self, session: ChallengeSession) -> str:
        from flask import current_app as _app

        from ..utils.tokens import sign_token

        secret = _app.config.get("TOKEN_SECRET", "")
        ttl = int(_app.config.get("TOKEN_TTL_HOURS", 24))
        issuer = _app.config.get("TOKEN_ISSUER", "ai-captcha")

        token = sign_token(
            {
                "session_id": session.id,
                "tier": session.tier,
                "model": session.model_name,
                "solved": session.puzzles_solved,
                "total": session.total_puzzles,
                "sitekey": session.sitekey,
            },
            secret=secret,
            ttl_hours=ttl,
            issuer=issuer,
        )

        # --- logging hook: token_issued ---
        log_event(
            current_app._get_current_object(),
            "info",
            "token_issued",
            session_id=session.id,
            tier=session.tier,
            model=session.model_name or "anonymous",
            token_hash=_hash_token(token),
        )

        return token

    @staticmethod
    def _puzzle_to_dict(attempt: PuzzleAttempt) -> dict:
        return {
            "attempt_id": attempt.id,
            "puzzle_index": attempt.puzzle_index,
            "puzzle_type": attempt.puzzle_type,
            "question": attempt.question,
            "time_limit": attempt.time_limit,
        }
