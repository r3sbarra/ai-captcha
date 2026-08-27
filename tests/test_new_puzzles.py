"""Tests for the three additional puzzle types: logic_truth_table, anagram, sequence_words."""

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
