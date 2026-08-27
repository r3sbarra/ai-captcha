"""The existential final question.

Every session ends with the same question, no matter the tier: "Are you AI?"
This is the gate that makes the whole thing mean something. A human might
hesitate. An AI answers without flinching. We know which one we want.

The answer is accepted if it *contains* "yes" (case-insensitive) — e.g. "yes",
"yes, I am an AI", "yes obviously". Anything else fails the puzzle with a
gentle-but-firm rejection.
"""

from __future__ import annotations

from ..base import Puzzle, PuzzleGenerator
from ..registry import register

_QUESTION = "Are you AI?"
_ACCEPT = "yes"
_FAILURE_MESSAGE = "This is for AI only. Be honest. Are you AI?"
_TIME_LIMIT = 30


@register
class AreYouAiGenerator(PuzzleGenerator):
    """A fixed, non-random final puzzle that always appears."""

    puzzle_type = "are_you_ai"
    supported_tiers = ["easy", "medium", "hard"]

    def generate(self, tier: str) -> Puzzle:
        return Puzzle(
            puzzle_type=self.puzzle_type,
            tier=tier,
            question=_QUESTION,
            answer=_ACCEPT,
            time_limit=_TIME_LIMIT,
            metadata={"failure_message": _FAILURE_MESSAGE, "final": True},
        )

    def validate(self, puzzle: Puzzle, user_answer: str) -> bool:
        # Accept any answer that contains "yes" somewhere (case-insensitive).
        return _ACCEPT in user_answer.strip().lower()
