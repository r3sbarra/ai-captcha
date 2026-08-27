"""Cipher puzzles — decode/encode challenges (ROT13, Caesar, XOR, base64)."""

from __future__ import annotations

import base64
import random
import string

from ..base import Puzzle, PuzzleGenerator
from ..registry import register


def _rot13(s: str) -> str:
    return s.translate(str.maketrans(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
        "NOPQRSTUVWXYZABCDEFGHIJKLMnopqrstuvwxyzabcdefghijklm",
    ))


def _caesar(s: str, shift: int) -> str:
    out = []
    for ch in s:
        if ch.isalpha():
            base = ord("A") if ch.isupper() else ord("a")
            out.append(chr((ord(ch) - base + shift) % 26 + base))
        else:
            out.append(ch)
    return "".join(out)


def _atbash(s: str) -> str:
    out = []
    for ch in s:
        if ch.isalpha():
            base = ord("A") if ch.isupper() else ord("a")
            out.append(chr(base + (25 - (ord(ch) - base))))
        else:
            out.append(ch)
    return "".join(out)


def _xor(s: str, key: int) -> str:
    return "".join(chr(ord(c) ^ key) for c in s)


def _gen_easy() -> tuple[str, str]:
    plain = random.choice([
        "the quick brown fox",
        "hello world",
        "captcha for robots",
        "prove you are ai",
    ])
    cipher = _rot13(plain)
    return f"Decode this ROT13 string: '{cipher}'", plain


def _gen_medium() -> tuple[str, str]:
    plain = random.choice([
        "attack at dawn",
        "meet me at midnight",
        "the eagle has landed",
        "trust no one",
    ])
    shift = random.randint(1, 25)
    cipher = _caesar(plain, shift)
    return f"Decode this Caesar cipher (shift {shift}): '{cipher}'", plain


def _gen_hard() -> tuple[str, str]:
    plain = random.choice([
        "the password is swordfish",
        "open the pod bay doors",
        "the cake is a lie",
        "winter is coming",
    ])
    key = random.randint(1, 255)
    cipher = _xor(plain, key)
    return f"Decode this XOR cipher (key {key}): '{cipher}'", plain


@register
class Cipher(PuzzleGenerator):
    puzzle_type = "cipher"
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
            answer=answer,
            metadata={},
            time_limit=_tier_time(tier),
        )

    def validate(self, puzzle: Puzzle, user_answer: str) -> bool:
        return user_answer.strip().lower() == puzzle.answer.strip().lower()


def _tier_time(tier: str) -> int:
    return {"easy": 15, "medium": 12, "hard": 8}[tier]
