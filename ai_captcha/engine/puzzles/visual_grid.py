"""Visual grid puzzles — ASCII-art grid transformations.

The AI must apply a transformation rule to a grid and output the result.
A human is slow and error-prone at this under the clock.
"""

from __future__ import annotations

import random

from ..base import Puzzle, PuzzleGenerator
from ..registry import register


def _random_grid(size: int) -> list[list[str]]:
    return [[random.choice(["#", "."]) for _ in range(size)] for _ in range(size)]


def _grid_to_ascii(grid: list[list[str]]) -> str:
    return "\n".join("".join(row) for row in grid)


def _transpose(grid: list[list[str]]) -> list[list[str]]:
    return [list(row) for row in zip(*grid)]


def _rotate90(grid: list[list[str]]) -> list[list[str]]:
    return [list(reversed(col)) for col in zip(*grid)]


def _mirror(grid: list[list[str]]) -> list[list[str]]:
    return [list(reversed(row)) for row in grid]


def _gen_easy() -> tuple[str, str, str]:
    size = 3
    grid = _random_grid(size)
    transform = random.choice([_transpose, _mirror])
    name = "transpose" if transform is _transpose else "mirror horizontally"
    return (
        f"Apply this transformation to the grid ({name}):\n```\n{_grid_to_ascii(grid)}\n```",
        _grid_to_ascii(transform(grid)),
        name,
    )


def _gen_medium() -> tuple[str, str, str]:
    size = 5
    grid = _random_grid(size)
    transform = _rotate90
    return (
        f"Apply this transformation to the grid (rotate 90 degrees clockwise):\n```\n{_grid_to_ascii(grid)}\n```",
        _grid_to_ascii(transform(grid)),
        "rotate90",
    )


def _gen_hard() -> tuple[str, str, str]:
    size = 7
    grid = _random_grid(size)
    # Compose: transpose then mirror.
    result = _mirror(_transpose(grid))
    return (
        f"Apply this transformation to the grid (transpose, then mirror horizontally):\n```\n{_grid_to_ascii(grid)}\n```",
        _grid_to_ascii(result),
        "transpose_then_mirror",
    )


@register
class VisualGrid(PuzzleGenerator):
    puzzle_type = "visual_grid"
    supported_tiers = ["easy", "medium", "hard"]

    def generate(self, tier: str) -> Puzzle:
        if tier == "easy":
            question, answer, name = _gen_easy()
        elif tier == "medium":
            question, answer, name = _gen_medium()
        else:
            question, answer, name = _gen_hard()
        return Puzzle(
            puzzle_type=self.puzzle_type,
            tier=tier,
            question=question,
            answer=answer,
            metadata={"transform": name},
            time_limit=_tier_time(tier),
        )

    def validate(self, puzzle: Puzzle, user_answer: str) -> bool:
        return user_answer.strip() == puzzle.answer.strip()


def _tier_time(tier: str) -> int:
    return {"easy": 20, "medium": 15, "hard": 10}[tier]
