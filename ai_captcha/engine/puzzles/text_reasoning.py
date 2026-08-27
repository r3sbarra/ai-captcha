"""Text reasoning puzzles — logic, riddles, word math.

Uses a curated bank plus procedural variants. These are designed to be
trivial for a language model but slow/error-prone for a human under the clock.
"""

from __future__ import annotations

import random

from ..base import Puzzle, PuzzleGenerator
from ..registry import register

# (question, answer) pairs per tier. Answers are normalized (lowercase, no spaces).
BANK: dict[str, list[tuple[str, str]]] = {
    "easy": [
        ("I have keys but no locks. What am I?", "keyboard"),
        ("What has a head, a tail, but no body?", "coin"),
        ("What gets wetter the more it dries?", "towel"),
        ("What has hands but cannot clap?", "clock"),
        ("What has one eye but cannot see?", "needle"),
        ("What has a neck but no head?", "bottle"),
        ("What runs but never walks?", "water"),
        ("What has a face and two hands but no arms or legs?", "clock"),
        ("What has a bottom at the top?", "legs"),
        ("What has many teeth but cannot bite?", "comb"),
    ],
    "medium": [
        ("If all Bloops are Razzies and all Razzies are Lazzies, then all Bloops are definitely what?", "lazzies"),
        ("Alice is taller than Bob. Bob is taller than Carol. Who is the shortest? Answer with one name.", "carol"),
        ("A farmer has 17 sheep. All but 9 die. How many are left?", "9"),
        ("What number is 3 more than half of 20?", "13"),
        ("If you have 3 apples and take away 2, how many do you have?", "2"),
        ("What is the next letter in this sequence: O, T, T, F, F, S, S, E, ?", "n"),
        ("A bat and a ball cost $1.10 in total. The bat costs $1.00 more than the ball. How much does the ball cost? Answer in cents.", "5"),
        ("If it takes 5 machines 5 minutes to make 5 widgets, how long would it take 100 machines to make 100 widgets? Answer in minutes.", "5"),
    ],
    "hard": [
        ("I speak without a mouth and hear without ears. I have no body, but I come alive with wind. What am I?", "echo"),
        ("What can travel around the world while staying in a corner?", "stamp"),
        ("The more you take, the more you leave behind. What am I?", "footsteps"),
        ("What has cities, but no houses; forests, but no trees; and water, but no fish?", "map"),
        ("What is always in front of you but can never be seen?", "future"),
        ("What has a spine but no bones?", "book"),
        ("What word is spelled incorrectly in every dictionary?", "incorrectly"),
        ("What has four letters, sometimes has nine, but never has five?", "what"),
    ],
}


def _normalize(s: str) -> str:
    return s.strip().lower().replace(" ", "")


@register
class TextReasoning(PuzzleGenerator):
    puzzle_type = "text_reasoning"
    supported_tiers = ["easy", "medium", "hard"]

    def generate(self, tier: str) -> Puzzle:
        pool = BANK.get(tier, BANK["medium"])
        question, answer = random.choice(pool)
        return Puzzle(
            puzzle_type=self.puzzle_type,
            tier=tier,
            question=question,
            answer=_normalize(answer),
            metadata={"category": "riddle"},
            time_limit=_tier_time(tier),
        )

    def validate(self, puzzle: Puzzle, user_answer: str) -> bool:
        return _normalize(user_answer) == _normalize(puzzle.answer)


def _tier_time(tier: str) -> int:
    return {"easy": 15, "medium": 12, "hard": 8}[tier]
