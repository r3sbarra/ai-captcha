"""Word-sequence puzzles — find the next item in a letter/word pattern.

Letter-position arithmetic (A, C, F, J → +2,+3,+4 → next is O) is trivial for
a model but slow for a human under the clock. Answers are single letters or
words, normalized.
"""

from __future__ import annotations

import random
import string

from ..base import Puzzle, PuzzleGenerator
from ..registry import register

LETTERS = string.ascii_uppercase


def _gen_letter_arithmetic() -> tuple[str, str]:
    start = random.randint(0, 20)
    step = random.randint(1, 5)
    count = 4
    idx = [(start + step * i) % 26 for i in range(count)]
    seq = "".join(LETTERS[i] for i in idx)
    nxt = LETTERS[(start + step * count) % 26]
    return f"What letter comes next in this sequence: {', '.join(seq)}?", nxt


def _gen_letter_gaps() -> tuple[str, str]:
    """Sequence with growing gaps: +1, +2, +3, ..."""
    start = random.randint(0, 18)
    idx = start
    seq = []
    for gap in range(1, 5):
        idx = (idx + gap) % 26
        seq.append(LETTERS[idx])
    nxt = LETTERS[(idx + 5) % 26]
    return f"What letter comes next in this sequence: {', '.join(seq)}?", nxt


def _gen_word_sequence() -> tuple[str, str]:
    """Simple word patterns: two, four, six → eight (evens)."""
    pairs = [
        (["one", "two", "three"], "four"),
        (["two", "four", "six"], "eight"),
        (["five", "ten", "fifteen"], "twenty"),
        (["red", "green", "blue"], "yellow"),
        (["monday", "tuesday", "wednesday"], "thursday"),
        (["january", "february", "march"], "april"),
        (["spring", "summer", "autumn"], "winter"),
    ]
    seq, nxt = random.choice(pairs)
    return f"What comes next in this sequence: {', '.join(seq)}?", nxt


def _normalize(s: str) -> str:
    return s.strip().lower().replace(" ", "")


@register
class SequenceWords(PuzzleGenerator):
    puzzle_type = "sequence_words"
    supported_tiers = ["easy", "medium", "hard"]

    def generate(self, tier: str) -> Puzzle:
        if tier == "easy":
            question, answer = _gen_word_sequence()
        elif tier == "medium":
            question, answer = _gen_letter_arithmetic()
        else:
            question, answer = _gen_letter_gaps()
        return Puzzle(
            puzzle_type=self.puzzle_type,
            tier=tier,
            question=question,
            answer=_normalize(answer),
            metadata={"category": "sequence"},
            time_limit=_tier_time(tier),
        )

    def validate(self, puzzle: Puzzle, user_answer: str) -> bool:
        return _normalize(user_answer) == _normalize(puzzle.answer)


def _tier_time(tier: str) -> int:
    return {"easy": 15, "medium": 12, "hard": 8}[tier]
