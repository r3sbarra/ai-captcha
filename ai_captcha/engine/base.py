"""Base classes for the puzzle engine."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Puzzle:
    """A single generated puzzle instance."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    puzzle_type: str = ""
    tier: str = "medium"
    question: str = ""
    answer: str = ""
    metadata: dict = field(default_factory=dict)
    time_limit: int = 20  # seconds for this single puzzle

    def validate(self, user_answer: str) -> bool:
        """Default validation: case-insensitive, whitespace-trimmed equality."""
        return user_answer.strip().lower() == self.answer.strip().lower()


class PuzzleGenerator(ABC):
    """Base class for puzzle generators. Subclass, set metadata, and register."""

    puzzle_type: str = "base"
    supported_tiers: list[str] = ["easy", "medium", "hard"]

    @abstractmethod
    def generate(self, tier: str) -> Puzzle:
        """Generate a single puzzle for the given tier."""
        ...

    def validate(self, puzzle: Puzzle, user_answer: str) -> bool:
        """Validate a user answer against a puzzle. Override for fuzzy logic."""
        return puzzle.validate(user_answer)
