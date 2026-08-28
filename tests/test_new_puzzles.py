"""Tests for the additional puzzle types: logic_truth_table, anagram, sequence_words, word_math, chained_ops."""

from __future__ import annotations

import pytest

from ai_captcha.engine.registry import discover, get_generator

pytestmark = pytest.mark.usefixtures("discover")


@pytest.fixture(scope="module")
def discover():
    from ai_captcha.engine.registry import discover

    discover()


@pytest.mark.parametrize("ptype", ["logic_truth_table", "anagram", "sequence_words"])
@pytest.mark.parametrize("tier", ["easy", "medium", "hard"])
def test_new_types_generate_and_validate(ptype, tier):
    gen = get_generator(ptype)
    puzzle = gen.generate(tier)
    assert puzzle.question
    assert puzzle.answer
    assert tier in gen.supported_tiers
    assert gen.validate(puzzle, puzzle.answer)
    assert not gen.validate(puzzle, "zz-definitely-wrong-answer")


def test_logic_truth_table_answers_are_booleans():
    gen = get_generator("logic_truth_table")
    for tier in ("easy", "medium", "hard"):
        p = gen.generate(tier)
        assert p.answer in ("true", "false")


def test_anagram_answers_are_words_without_spaces():
    gen = get_generator("anagram")
    for tier in ("easy", "medium", "hard"):
        p = gen.generate(tier)
        assert p.answer.isalpha()
        assert len(p.answer) >= 3


def test_sequence_words_always_has_an_answer():
    gen = get_generator("sequence_words")
    for tier in ("easy", "medium", "hard"):
        p = gen.generate(tier)
        assert p.answer


# --- word_math (medium/hard) ---


@pytest.mark.parametrize("tier", ["medium", "hard"])
def test_word_math_generate_and_validate(tier):
    gen = get_generator("word_math")
    p = gen.generate(tier)
    assert p.question
    assert p.answer.isdigit()
    assert gen.validate(p, p.answer)
    assert not gen.validate(p, "zz-definitely-wrong-answer")


def test_word_math_answers_are_integers():
    gen = get_generator("word_math")
    for tier in ("medium", "hard"):
        p = gen.generate(tier)
        assert p.answer.isdigit()
        assert int(p.answer) >= 0


def test_word_math_is_dynamic():
    """No static answer bank: repeated generation yields varied questions."""
    gen = get_generator("word_math")
    questions = {gen.generate("medium").question for _ in range(20)}
    assert len(questions) > 1


# --- chained_ops (hard, obfuscated) ---


def test_chained_ops_generate_and_validate():
    gen = get_generator("chained_ops")
    p = gen.generate("hard")
    assert p.question
    assert p.answer.isdigit()
    assert gen.validate(p, p.answer)
    assert not gen.validate(p, "zz-definitely-wrong-answer")


def test_chained_ops_question_is_obfuscated():
    """The served question must be base64-encoded (not greppable plaintext)."""
    import base64

    gen = get_generator("chained_ops")
    p = gen.generate("hard")
    # Extract the base64 blob between the code fences.
    lines = p.question.splitlines()
    in_fence = False
    blob_parts = []
    for l in lines:
        if l.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            blob_parts.append(l.strip())
    blob = "".join(blob_parts)
    # The blob must decode to valid UTF-8 and contain the chain instruction.
    decoded = base64.b64decode(blob).decode("utf-8")
    assert "Chain:" in decoded
    assert "start" in decoded


def test_chained_ops_is_dynamic():
    """High entropy: repeated generation yields varied encoded questions."""
    gen = get_generator("chained_ops")
    questions = {gen.generate("hard").question for _ in range(20)}
    assert len(questions) > 1
