"""Puzzle type registry and discovery.

New puzzle types are added by dropping a module in ``ai_captcha/engine/puzzles/``
that defines a ``PuzzleGenerator`` subclass decorated with ``@register``.
"""

from __future__ import annotations

import importlib
import pkgutil
import random
from typing import Type

from .base import PuzzleGenerator

_registry: dict[str, Type[PuzzleGenerator]] = {}


def register(cls: Type[PuzzleGenerator]) -> Type[PuzzleGenerator]:
    """Decorator to register a PuzzleGenerator subclass by its ``puzzle_type``."""
    _registry[cls.puzzle_type] = cls
    return cls


def discover() -> None:
    """Auto-import all modules in ``ai_captcha.engine.puzzles`` to trigger @register."""
    from . import puzzles as puzzle_pkg

    for _importer, modname, _ispkg in pkgutil.iter_modules(puzzle_pkg.__path__):
        importlib.import_module(f".puzzles.{modname}", package="ai_captcha.engine")


def get_generator(puzzle_type: str) -> PuzzleGenerator:
    cls = _registry.get(puzzle_type)
    if not cls:
        raise KeyError(f"Unknown puzzle type: {puzzle_type}")
    return cls()


def all_types() -> list[str]:
    return list(_registry.keys())


def pick_puzzle_types(
    tier: str, count: int, weights: dict[str, int] | None = None
) -> list[str]:
    """Select ``count`` puzzle types for a tier, optionally weighted."""
    types = [t for t, gen_cls in _registry.items() if tier in gen_cls.supported_tiers]
    if not types:
        raise ValueError(f"No puzzle types support tier '{tier}'")
    if weights:
        weighted: list[str] = []
        for t in types:
            weighted.extend([t] * weights.get(t, 1))
        if len(weighted) >= count:
            return random.sample(weighted, count)
        return random.choices(weighted, k=count)
    if len(types) >= count:
        return random.sample(types, count)
    return random.choices(types, k=count)
