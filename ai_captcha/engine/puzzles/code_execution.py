"""Code execution puzzles — "what does this code print?".

The generator runs the snippet to compute the correct answer, so puzzles are
always correct. The AI must mentally execute the code; a human is slow and
error-prone under the clock.
"""

from __future__ import annotations

import random

from ..base import Puzzle, PuzzleGenerator
from ..registry import register


def _run(code: str) -> str:
    """Execute a snippet and return its printed output (or error)."""
    import io
    import contextlib

    buf = io.StringIO()
    # Allow `print` (and the minimal builtins the snippets use) while still
    # sandboxing against imports/os side effects.
    _builtins = {"print": print, "range": range, "len": len, "True": True, "False": False,
                 "None": None, "list": list, "dict": dict, "int": int, "str": str}
    try:
        with contextlib.redirect_stdout(buf):
            exec(code, {"__builtins__": _builtins}, {})
        return buf.getvalue().strip()
    except Exception as e:  # noqa: BLE001
        return f"Error: {type(e).__name__}"


def _gen_easy() -> tuple[str, str]:
    a = random.randint(1, 9)
    b = random.randint(1, 9)
    op = random.choice(["+", "-", "*"])
    code = f"print({a} {op} {b})"
    return code, _run(code)


def _gen_medium() -> tuple[str, str]:
    n = random.randint(3, 6)
    start = random.randint(1, 5)
    step = random.randint(2, 5)
    code = (
        f"total = 0\n"
        f"for i in range({start}, {start + n * step}, {step}):\n"
        f"    total += i\n"
        f"print(total)"
    )
    return code, _run(code)


def _gen_hard() -> tuple[str, str]:
    # Mutable-default-argument gotcha: the default list persists across calls.
    code = (
        "def add(x, bucket=[]):\n"
        "    bucket.append(x)\n"
        "    return bucket\n"
        "print(len(add(1)), len(add(2)), len(add(3)))"
    )
    return code, _run(code)


@register
class CodeExecution(PuzzleGenerator):
    puzzle_type = "code_execution"
    supported_tiers = ["easy", "medium", "hard"]

    def generate(self, tier: str) -> Puzzle:
        if tier == "easy":
            code, answer = _gen_easy()
        elif tier == "medium":
            code, answer = _gen_medium()
        else:
            code, answer = _gen_hard()
        return Puzzle(
            puzzle_type=self.puzzle_type,
            tier=tier,
            question=f"What does this Python code print?\n```python\n{code}\n```",
            answer=answer,
            metadata={"code": code},
            time_limit=_tier_time(tier),
        )

    def validate(self, puzzle: Puzzle, user_answer: str) -> bool:
        return user_answer.strip() == puzzle.answer.strip()


def _tier_time(tier: str) -> int:
    return {"easy": 15, "medium": 12, "hard": 8}[tier]
