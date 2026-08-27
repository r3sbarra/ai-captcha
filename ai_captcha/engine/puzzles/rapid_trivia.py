"""Rapid-fire trivia puzzles — multiple questions in a single puzzle.

Tests both knowledge and speed. The answer is a JSON array of answers.
"""

from __future__ import annotations

import json
import random

from ..base import Puzzle, PuzzleGenerator
from ..registry import register

# (question, answer) pairs. Answers normalized (lowercase).
TRIVIA: dict[str, list[tuple[str, str]]] = {
    "easy": [
        ("What is the capital of France?", "paris"),
        ("How many continents are there?", "7"),
        ("What is 2 + 2?", "4"),
        ("What color is the sky on a clear day?", "blue"),
        ("How many legs does a spider have?", "8"),
        ("What is the largest planet in our solar system?", "jupiter"),
        ("What gas do plants absorb from the air?", "carbon dioxide"),
        ("How many days are in a leap year?", "366"),
    ],
    "medium": [
        ("What is the chemical symbol for gold?", "au"),
        ("Who painted the Mona Lisa?", "leonardo da vinci"),
        ("What is the square root of 144?", "12"),
        ("What year did World War II end?", "1945"),
        ("What is the fastest land animal?", "cheetah"),
        ("How many bones are in the adult human body?", "206"),
        ("What is the currency of Japan?", "yen"),
        ("What is the largest ocean?", "pacific"),
    ],
    "hard": [
        ("What is the only even prime number?", "2"),
        ("What is the smallest prime number greater than 100?", "101"),
        ("What is the atomic number of carbon?", "6"),
        ("What is the capital of Australia?", "canberra"),
        ("What is the derivative of x^2?", "2x"),
        ("What is the value of pi to 3 decimal places?", "3.142"),
        ("What is the longest river in the world?", "nile"),
        ("What is the hardest natural substance?", "diamond"),
    ],
}


def _normalize(s: str) -> str:
    return s.strip().lower().replace(" ", "")


@register
class RapidTrivia(PuzzleGenerator):
    puzzle_type = "rapid_trivia"
    supported_tiers = ["easy", "medium", "hard"]

    def generate(self, tier: str) -> Puzzle:
        count = {"easy": 3, "medium": 5, "hard": 7}[tier]
        pool = TRIVIA.get(tier, TRIVIA["medium"])
        items = random.sample(pool, min(count, len(pool)))
        questions = [q for q, _ in items]
        answers = [_normalize(a) for _, a in items]

        question = (
            f"Answer these {len(questions)} questions. Respond with a JSON array "
            f"of answers in order, e.g. [\"a\",\"b\",\"c\"]:\n"
            + "\n".join(f"{i+1}. {q}" for i, q in enumerate(questions))
        )
        return Puzzle(
            puzzle_type=self.puzzle_type,
            tier=tier,
            question=question,
            answer=json.dumps(answers),
            metadata={"answers": answers},
            time_limit=_tier_time(tier),
        )

    def validate(self, puzzle: Puzzle, user_answer: str) -> bool:
        try:
            given = json.loads(user_answer)
            expected = json.loads(puzzle.answer)
        except (json.JSONDecodeError, TypeError):
            return False
        if not isinstance(given, list) or len(given) != len(expected):
            return False
        return all(_normalize(str(g)) == _normalize(str(e)) for g, e in zip(given, expected))


def _tier_time(tier: str) -> int:
    return {"easy": 20, "medium": 15, "hard": 10}[tier]
