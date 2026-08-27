"""Logic truth-table puzzles — evaluate a boolean expression.

Trivial for a model that can reason symbolically; error-prone for a human
under the clock. Answers are normalized to 'true' / 'false'.
"""

from __future__ import annotations

import random

from ..base import Puzzle, PuzzleGenerator
from ..registry import register


def _eval(expr: str) -> str:
    """Safely evaluate a boolean expression built from literals and operators."""
    # Only allow a constrained grammar (no arbitrary exec).
    allowed = {"True", "False", "and", "or", "not", "(", ")", " "}
    for ch in expr:
        if ch not in allowed and not (ch.isalnum()):
            raise ValueError(f"disallowed char {ch!r} in {expr!r}")
    for tok in expr.replace("(", " ").replace(")", " ").split():
        if tok not in ("True", "False", "and", "or", "not"):
            raise ValueError(f"disallowed token {tok!r} in {expr!r}")
    return str(eval(expr, {"__builtins__": {}}, {}))  # noqa: S307


def _gen_easy() -> tuple[str, str]:
    a, b = random.choice([True, False]), random.choice([True, False])
    op = random.choice(["and", "or"])
    expr = f"{a} {op} {b}"
    return f"Evaluate this boolean expression. Answer 'true' or 'false':\n`{expr}`", _eval(expr)


def _gen_medium() -> tuple[str, str]:
    a, b, c = (random.choice([True, False]) for _ in range(3))
    ops = random.choice(["and", "or"])
    second = random.choice(["and", "or"])
    expr = f"({a} {ops} {b}) {second} {c}"
    return f"Evaluate this boolean expression. Answer 'true' or 'false':\n`{expr}`", _eval(expr)


def _gen_hard() -> tuple[str, str]:
    a, b = random.choice([True, False]), random.choice([True, False])
    # Mix of not/and/or and parentheses.
    templates = [
        f"not ({a} and {b})",
        f"(not {a}) or ({b} and {not a})",
        f"({a} or not {b}) and (not {a} or {b})",
    ]
    expr = random.choice(templates)
    return f"Evaluate this boolean expression. Answer 'true' or 'false':\n`{expr}`", _eval(expr)


def _normalize(s: str) -> str:
    return s.strip().lower()


@register
class LogicTruthTable(PuzzleGenerator):
    puzzle_type = "logic_truth_table"
    supported_tiers = ["easy", "medium", "hard"]

    def generate(self, tier: str) -> Puzzle:
        if tier == "easy":
            question, answer = _gen_easy()
        elif tier == "medium":
            question, answer = _gen_medium()
        else:
            question, answer = _gen_hard()
        return Puzzle(
            puzzle_type=self.puzzle_type,
            tier=tier,
            question=question,
            answer=_normalize(answer),
            metadata={"category": "logic"},
            time_limit=_tier_time(tier),
        )

    def validate(self, puzzle: Puzzle, user_answer: str) -> bool:
        return _normalize(user_answer) == _normalize(puzzle.answer)


def _tier_time(tier: str) -> int:
    return {"easy": 15, "medium": 12, "hard": 8}[tier]
