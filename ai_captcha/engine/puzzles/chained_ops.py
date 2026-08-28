"""Chained-operation puzzles — obfuscated multi-step computation.

The *entire instruction* is base64-encoded, so a reverse-engineer cannot grep
the served question for a known answer or pattern-match a static template. The
solver must (1) decode the base64, (2) read a multi-step chain of operations,
and (3) execute it. Each instance is procedurally generated with a random start
value and a random operation chain, so no two puzzles are alike and the answer
cannot be derived from a lookup table.

Designed to be solvable by a capable language model (decode + symbolic
arithmetic) but effectively impossible for a human under the 8s hard-tier clock,
and resistant to naive bot scraping.
"""

from __future__ import annotations

import base64
import random

from ..base import Puzzle, PuzzleGenerator
from ..registry import register


def _digit_sum(n: int) -> int:
    return sum(int(d) for d in str(abs(n)))


def _reverse_digits(n: int) -> int:
    return int(str(abs(n))[::-1])


def _apply(op: str, n: int) -> int:
    """Apply a single named operation to n. All ops are deterministic ints."""
    if op == "double":
        return n * 2
    if op == "halve":
        return n // 2
    if op == "add3":
        return n + 3
    if op == "sub5":
        return n - 5
    if op == "mod7":
        return n % 7
    if op == "mod11":
        return n % 11
    if op == "digitsum":
        return _digit_sum(n)
    if op == "reverse":
        return _reverse_digits(n)
    if op == "square":
        return n * n
    raise ValueError(f"unknown op {op!r}")


# Operation pool. Keep results non-negative and small enough to be mentally
# tractable for a model but non-trivial for a human.
_OPS = ["double", "add3", "sub5", "mod7", "mod11", "digitsum", "reverse", "square"]


def _gen_hard() -> tuple[str, str]:
    start = random.randint(7, 40)
    chain_len = random.randint(3, 5)
    # Avoid consecutive squares (runaway growth) and keep the final result in a
    # mentally-tractable range so a capable model can execute it reliably.
    ops: list[str] = []
    for _ in range(chain_len):
        pool = _OPS
        if ops and ops[-1] == "square":
            pool = [o for o in _OPS if o != "square"]
        ops.append(random.choice(pool))

    # Compute the answer by applying ops left-to-right.
    value = start
    for op in ops:
        value = _apply(op, value)

    # Human-readable chain, e.g. "start 12 -> double -> mod7 -> digitsum".
    chain_str = " -> ".join([f"start {start}"] + ops)
    plaintext = (
        f"Apply this chain of operations left to right, starting from the given "
        f"value. Operations: double (x2), halve (//2), add3 (+3), sub5 (-5), "
        f"mod7 (%7), mod11 (%11), digitsum (sum of digits), reverse (reverse "
        f"digits), square (x^2).\n\nChain: {chain_str}\n\n"
        f"What is the final result? Answer with an integer."
    )
    # Obfuscate the whole instruction so the served question is not greppable.
    encoded = base64.b64encode(plaintext.encode("utf-8")).decode("ascii")
    question = (
        "Decode the following base64-encoded instruction, then follow it "
        "exactly. Respond with the final integer result.\n\n"
        f"```\n{encoded}\n```"
    )
    return question, str(value)


def _normalize(s: str) -> str:
    return s.strip().lower().replace(" ", "")


def _extract_int(s: str) -> str | None:
    """Pull the last standalone integer from a model response."""
    import re

    ints = [m.group(1) for m in re.finditer(r"(?<![\d.])(-?\d+)(?![\d.])", s)]
    return ints[-1] if ints else None


@register
class ChainedOps(PuzzleGenerator):
    puzzle_type = "chained_ops"
    supported_tiers = ["hard"]

    def generate(self, tier: str) -> Puzzle:
        question, answer = _gen_hard()
        return Puzzle(
            puzzle_type=self.puzzle_type,
            tier=tier,
            question=question,
            answer=_normalize(answer),
            metadata={"category": "chained_computation", "obfuscated": True},
            time_limit=_tier_time(tier),
        )

    def validate(self, puzzle: Puzzle, user_answer: str) -> bool:
        if _normalize(user_answer) == _normalize(puzzle.answer):
            return True
        got = _extract_int(user_answer)
        return got is not None and got == puzzle.answer


def _tier_time(tier: str) -> int:
    return {"hard": 8}[tier]
