"""Puzzle engine — decoupled from Flask (pure Python, independently testable)."""

from .base import Puzzle, PuzzleGenerator
from .registry import (
    register,
    discover,
    get_generator,
    all_types,
    pick_puzzle_types,
)

__all__ = [
    "Puzzle",
    "PuzzleGenerator",
    "register",
    "discover",
    "get_generator",
    "all_types",
    "pick_puzzle_types",
]
