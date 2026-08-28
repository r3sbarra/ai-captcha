"""Word-math puzzles — letter-value arithmetic.

Each letter is assigned a random digit and the solver must compute the value of
a word or expression. Trivial for a language model (symbolic arithmetic) but
slow and error-prone for a human under the clock.

Fully procedural: letters and values are drawn at random per instance, so there
is no static answer bank to reverse-engineer. Answers are normalized integers.
"""

from __future__ import annotations

import random
import string

from ..base import Puzzle, PuzzleGenerator
from ..registry import register

# Letters we draw from (avoid I/O/1 and O/0 confusion for humans, though the
# model doesn't care — keeps the prompt clean).
_LETTERS = [c for c in string.ascii_uppercase if c not in "IO"]


def _gen_medium() -> tuple[str, str]:
    """Sum of two words given per-letter values."""
    letters = random.sample(_LETTERS, 4)
    values = {ch: random.randint(1, 9) for ch in letters}
    word_a = "".join(random.sample(letters, 3))
    word_b = "".join(random.sample(letters, 3))
    val_a = sum(values[ch] for ch in word_a)
    val_b = sum(values[ch] for ch in word_b)
    mapping = ", ".join(f"{ch}={values[ch]}" for ch in letters)
    question = (
        f"Each letter has a digit value. Given {mapping}, "
        f"what is the value of {word_a} + {word_b}? "
        f"(A word's value = sum of its letters' values.) Answer with an integer."
    )
    return question, str(val_a + val_b)


def _gen_hard() -> tuple[str, str]:
    """Product of two words given per-letter values (larger numbers)."""
    letters = random.sample(_LETTERS, 5)
    values = {ch: random.randint(2, 9) for ch in letters}
    word_a = "".join(random.sample(letters, 3))
    word_b = "".join(random.sample(letters, 3))
    val_a = sum(values[ch] for ch in word_a)
    val_b = sum(values[ch] for ch in word_b)
    mapping = ", ".join(f"{ch}={values[ch]}" for ch in letters)
    question = (
        f"Each letter has a digit value. Given {mapping}, "
        f"what is the value of {word_a} * {word_b}? "
        f"(A word's value = sum of its letters' values.) Answer with an integer."
    )
    return question, str(val_a * val_b)


def _normalize(s: str) -> str:
    return s.strip().lower().replace(" ", "")


def _extract_int(s: str) -> str | None:
    """Pull the last standalone integer from a model response.

    Models often wrap the answer in reasoning ("... = 42\n\n42"). We accept
    the puzzle if the expected integer appears as a standalone token anywhere
    in the response.
    """
    import re

    # Collect all standalone integers; return the last one (models usually end
    # with the final answer).
    ints = [m.group(1) for m in re.finditer(r"(?<![\d.])(-?\d+)(?![\d.])", s)]
    return ints[-1] if ints else None


@register
class WordMath(PuzzleGenerator):
    puzzle_type = "word_math"
    supported_tiers = ["medium", "hard"]

    def generate(self, tier: str) -> Puzzle:
        if tier == "medium":
            question, answer = _gen_medium()
        else:
            question, answer = _gen_hard()
        return Puzzle(
            puzzle_type=self.puzzle_type,
            tier=tier,
            question=question,
            answer=_normalize(answer),
            metadata={"category": "arithmetic"},
            time_limit=_tier_time(tier),
        )

    def validate(self, puzzle: Puzzle, user_answer: str) -> bool:
        # Accept the exact answer, or the expected integer appearing as a
        # standalone token in a reasoning-wrapped response.
        if _normalize(user_answer) == _normalize(puzzle.answer):
            return True
        got = _extract_int(user_answer)
        return got is not None and got == puzzle.answer


def _tier_time(tier: str) -> int:
    return {"medium": 12, "hard": 8}[tier]
