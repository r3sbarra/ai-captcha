"""Complexity tier config and model allowlist gating."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TierConfig:
    name: str
    timer_seconds: int
    puzzles_per_session: int
    min_pass_rate: float


# Defaults. Overridable at runtime via app.config (see get_tier_config).
TIERS: dict[str, TierConfig] = {
    "easy": TierConfig("easy", 30, 5, 0.80),
    "medium": TierConfig("medium", 20, 5, 0.80),
    "hard": TierConfig("hard", 10, 5, 0.80),
}

TIER_ORDER = ["easy", "medium", "hard"]


def get_tier_config(tier: str) -> TierConfig:
    if tier not in TIERS:
        raise ValueError(f"Unknown tier: {tier}. Must be one of {list(TIERS.keys())}")
    return TIERS[tier]


def check_model_allowed(model_name: str, allowlist: list[str] | None = None) -> bool:
    """Check a model name against an allowlist.

    Empty allowlist = all models allowed. Supports prefix matching:
    ``gpt-4`` matches ``gpt-4``, ``gpt-4o``, ``gpt-4-turbo``, etc.
    """
    if not model_name:
        return True  # anonymous play allowed by default
    allowlist = allowlist or []
    if not allowlist:
        return True
    for allowed in allowlist:
        if model_name == allowed or model_name.startswith(allowed):
            return True
    return False
