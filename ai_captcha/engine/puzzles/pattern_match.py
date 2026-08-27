"""Pattern matching puzzles — sequence completion and regex matching."""

from __future__ import annotations

import random

from ..base import Puzzle, PuzzleGenerator
from ..registry import register


def _gen_arithmetic() -> tuple[str, str]:
    start = random.randint(1, 20)
    step = random.randint(2, 9)
    seq = [start + step * i for i in range(5)]
    answer = start + step * 5
    return f"What number comes next: {', '.join(map(str, seq))}?", str(answer)


def _gen_fib() -> tuple[str, str]:
    a, b = random.randint(1, 3), random.randint(2, 5)
    seq = [a, b]
    for _ in range(4):
        seq.append(seq[-1] + seq[-2])
    answer = seq[-1] + seq[-2]
    return f"What number comes next: {', '.join(map(str, seq))}?", str(answer)


def _gen_geometric() -> tuple[str, str]:
    start = random.randint(1, 10)
    ratio = random.randint(2, 4)
    seq = [start * (ratio ** i) for i in range(5)]
    answer = start * (ratio ** 5)
    return f"What number comes next: {', '.join(map(str, seq))}?", str(answer)


def _gen_interleaved() -> tuple[str, str]:
    a = random.randint(1, 10)
    b = random.randint(1, 10)
    seq = []
    for i in range(6):
        seq.append(a + i * 2 if i % 2 == 0 else b + i * 3)
    answer = a + 6 * 2  # next term (index 6, even)
    return f"What number comes next: {', '.join(map(str, seq))}?", str(answer)


@register
class PatternMatch(PuzzleGenerator):
    puzzle_type = "pattern_match"
    supported_tiers = ["easy", "medium", "hard"]

    def generate(self, tier: str) -> Puzzle:
        if tier == "easy":
            question, answer = _gen_arithmetic()
        elif tier == "medium":
            question, answer = random.choice([_gen_fib, _gen_geometric])()
        else:
            question, answer = _gen_interleaved()
        return Puzzle(
            puzzle_type=self.puzzle_type,
            tier=tier,
            question=question,
            answer=answer,
            metadata={},
            time_limit=_tier_time(tier),
        )

    def validate(self, puzzle: Puzzle, user_answer: str) -> bool:
        return user_answer.strip() == puzzle.answer.strip()


def _tier_time(tier: str) -> int:
    return {"easy": 15, "medium": 12, "hard": 8}[tier]
