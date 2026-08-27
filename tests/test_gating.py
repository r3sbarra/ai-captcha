"""Tests for complexity gating and model allowlist."""

from __future__ import annotations

from ai_captcha.engine.gating import check_model_allowed, get_tier_config


def test_empty_allowlist_allows_all():
    assert check_model_allowed("anything", []) is True
    assert check_model_allowed("", []) is True


def test_prefix_matching():
    allowlist = ["gpt-4", "claude-3"]
    assert check_model_allowed("gpt-4o", allowlist) is True
    assert check_model_allowed("gpt-4-turbo", allowlist) is True
    assert check_model_allowed("claude-3-opus", allowlist) is True
    assert check_model_allowed("llama-2-7b", allowlist) is False


def test_tier_config():
    cfg = get_tier_config("hard")
    assert cfg.timer_seconds == 10
    assert cfg.puzzles_per_session == 5
    assert cfg.min_pass_rate == 0.8


def test_unknown_tier_raises():
    import pytest

    with pytest.raises(ValueError):
        get_tier_config("impossible")
