"""Tests for the puzzle engine: generation, validation, registry."""

from __future__ import annotations

import pytest

from ai_captcha.engine.registry import all_types, discover, get_generator, pick_puzzle_types


@pytest.fixture(scope="module", autouse=True)
def _discover():
    discover()


def test_all_types_present():
    types = all_types()
    assert "text_reasoning" in types
    assert "code_execution" in types
    assert "pattern_match" in types
    assert "cipher" in types
    assert "visual_grid" in types
    assert "rapid_trivia" in types
    assert "steganography" in types
    assert "logic_truth_table" in types
    assert "anagram" in types
    assert "sequence_words" in types


@pytest.mark.parametrize("ptype", ["text_reasoning", "code_execution", "pattern_match", "cipher", "visual_grid", "rapid_trivia", "steganography", "logic_truth_table", "anagram", "sequence_words"])
def test_generate_and_validate(ptype):
    gen = get_generator(ptype)
    puzzle = gen.generate("easy")
    assert puzzle.question
    assert puzzle.answer
    # Correct answer validates.
    assert gen.validate(puzzle, puzzle.answer)
    # Wrong answer does not.
    assert not gen.validate(puzzle, "definitely-not-the-answer-xyz")


def test_pick_puzzle_types_respects_tier():
    types = pick_puzzle_types("easy", 5)
    assert len(types) == 5
    for t in types:
        assert t in all_types()


def test_unknown_type_raises():
    with pytest.raises(KeyError):
        get_generator("does_not_exist")
