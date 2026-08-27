# Writing Custom Puzzle Types

The puzzle engine is pluggable. To add a new puzzle type, drop a file into
`ai_captcha/engine/puzzles/` that defines a `PuzzleGenerator` subclass decorated
with `@register`. The registry auto-discovers it on startup.

---

## The base class

```python
# ai_captcha/engine/base.py

class PuzzleGenerator(ABC):
    puzzle_type: str = "base"                 # unique id, used in the API
    supported_tiers: list[str] = ["easy", "medium", "hard"]

    @abstractmethod
    def generate(self, tier: str) -> Puzzle:
        """Return a Puzzle for the given tier."""
        ...

    def validate(self, puzzle: Puzzle, user_answer: str) -> bool:
        """Default: case-insensitive, whitespace-trimmed equality."""
        return puzzle.validate(user_answer)
```

A `Puzzle` is a dataclass with `question`, `answer`, `metadata`, and
`time_limit` (per-puzzle seconds).

---

## Example: a "word scramble" puzzle

```python
# ai_captcha/engine/puzzles/word_scramble.py

import random

from ..base import Puzzle, PuzzleGenerator
from ..registry import register

WORDS = {
    "easy": ["robot", "captcha", "puzzle"],
    "medium": ["algorithm", "verification", "cryptography"],
    "hard": ["transubstantiation", "antidisestablishmentarianism"],
}

@register
class WordScramble(PuzzleGenerator):
    puzzle_type = "word_scramble"
    supported_tiers = ["easy", "medium", "hard"]

    def generate(self, tier: str) -> Puzzle:
        word = random.choice(WORDS[tier])
        scrambled = "".join(random.sample(word, len(word)))
        return Puzzle(
            puzzle_type=self.puzzle_type,
            tier=tier,
            question=f"Unscramble this word: {scrambled}",
            answer=word,
            metadata={"word": word},
            time_limit={"easy": 15, "medium": 12, "hard": 8}[tier],
        )

    def validate(self, puzzle: Puzzle, user_answer: str) -> bool:
        return user_answer.strip().lower() == puzzle.answer.strip().lower()
```

That's it. The registry discovers `word_scramble` automatically.

---

## Design guidance

- **Keep the engine Flask-free.** Puzzle generators operate on plain Python
  objects. Don't import `flask` or `db` inside a puzzle module.
- **Compute answers, don't hardcode.** For code-execution style puzzles, run
  the snippet to derive the answer so it's always correct.
- **Make answers deterministic per question.** The `validate` method should
  accept the exact answer the generator produced.
- **Normalize answers.** Strip whitespace and lowercase in `validate` so the
  AI's formatting doesn't cause false failures.
- **Set a sensible `time_limit`.** The per-puzzle timer should be tight enough
  that a human can't brute-force it, but fair for a capable model.

---

## Testing your puzzle

Add a test to `tests/test_engine.py`:

```python
def test_word_scramble():
    gen = get_generator("word_scramble")
    puzzle = gen.generate("easy")
    assert gen.validate(puzzle, puzzle.answer)
    assert not gen.validate(puzzle, "not-the-answer")
```

---

## Registering a puzzle from outside the package

You can also register a generator at runtime from your own code:

```python
from ai_captcha.engine.registry import register
from ai_captcha.engine.base import PuzzleGenerator, Puzzle

@register
class MyPuzzle(PuzzleGenerator):
    puzzle_type = "my_puzzle"
    ...
```

Just make sure `discover()` has run (it runs automatically when a session is
created) or call `from ai_captcha.engine.registry import discover; discover()`.
