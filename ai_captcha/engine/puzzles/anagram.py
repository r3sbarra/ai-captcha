"""Anagram puzzles — unscramble a set of letters into a word.

A model can reorder letters instantly; humans struggle under the clock.
A hint word (synonym) is provided to disambiguate. Answers are normalized
(lowercase, no spaces).
"""

from __future__ import annotations

import random

from ..base import Puzzle, PuzzleGenerator
from ..registry import register

# (word, hint) pairs. Answers lowercase.
BANK: dict[str, list[tuple[str, str]]] = {
    "easy": [
        ("cat", "feline pet"),
        ("dog", "canine pet"),
        ("sun", "star of our solar system"),
        ("moon", "orbits the Earth"),
        ("tree", "plant with a trunk"),
        ("rain", "water falling from clouds"),
        ("fish", "swims in water"),
        ("book", "you read it"),
    ],
    "medium": [
        ("planet", "orbits a star"),
        ("garden", "place to grow plants"),
        ("orange", "citrus fruit"),
        ("bridge", "crosses a river"),
        ("castle", "fortified residence"),
        ("forest", "large area of trees"),
        ("island", "land surrounded by water"),
        ("silver", "precious grey metal"),
    ],
    "hard": [
        ("algorithm", "step-by-step procedure"),
        ("symphony", "orchestral composition"),
        ("labyrinth", "complex maze"),
        ("paradox", "self-contradictory statement"),
        ("serendipity", "fortunate accident"),
        ("ephemeral", "lasting a very short time"),
        ("cryptography", "art of secret writing"),
        ("quintessence", "purest essence"),
    ],
}


def _scramble(word: str) -> str:
    letters = list(word)
    while "".join(letters) == word:
        random.shuffle(letters)
    return "".join(letters)


def _normalize(s: str) -> str:
    return s.strip().lower().replace(" ", "")


@register
class Anagram(PuzzleGenerator):
    puzzle_type = "anagram"
    supported_tiers = ["easy", "medium", "hard"]

    def generate(self, tier: str) -> Puzzle:
        pool = BANK.get(tier, BANK["medium"])
        word, hint = random.choice(pool)
        scrambled = _scramble(word)
        question = (
            f"Unscramble these letters to form an English word. "
            f"Hint: {hint}.\nLetters: {scrambled.upper()}"
        )
        return Puzzle(
            puzzle_type=self.puzzle_type,
            tier=tier,
            question=question,
            answer=_normalize(word),
            metadata={"hint": hint, "scrambled": scrambled},
            time_limit=_tier_time(tier),
        )

    def validate(self, puzzle: Puzzle, user_answer: str) -> bool:
        return _normalize(user_answer) == _normalize(puzzle.answer)


def _tier_time(tier: str) -> int:
    return {"easy": 15, "medium": 12, "hard": 8}[tier]
