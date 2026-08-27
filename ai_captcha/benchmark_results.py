"""Load benchmark results for the web UI and README table.

Reads ``benchmarks/results.json`` (produced by ``benchmarks/model_benchmark.py
merge``) and exposes helpers to render the per-model × per-puzzle-type ×
per-tier pass rates. Fail-soft: returns empty data when the file is missing so
the page degrades gracefully (e.g. before a benchmark has been run or when the
package is pip-installed without the repo's benchmark artifacts).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

_BENCHMARK_PATH = Path(__file__).resolve().parent.parent / "benchmarks" / "results.json"

# Human-friendly labels for puzzle types (fall back to the raw id).
PUZZLE_LABELS = {
    "text_reasoning": "Text Reasoning",
    "code_execution": "Code Execution",
    "pattern_match": "Pattern Match",
    "cipher": "Cipher",
    "visual_grid": "Visual Grid",
    "rapid_trivia": "Rapid Trivia",
    "steganography": "Steganography",
    "logic_truth_table": "Logic Tables",
    "anagram": "Anagram",
    "sequence_words": "Word Sequences",
    "are_you_ai": "Are You AI?",
}

MODEL_LABELS = {
    "main": "main · deepseek-v4-flash",
    "coder": "coder · glm-5.2",
    "analyst": "analyst · qwen3.5:397b",
    "researcher": "researcher · kimi-k3",
    "designer": "designer · glm-5.3-flash",
    "user": "user · gpt-oss:20b",
}

# Order models/puzzle types for display.
MODEL_ORDER = ["main", "coder", "analyst", "researcher", "designer", "user"]
TYPE_ORDER = [
    "text_reasoning",
    "code_execution",
    "pattern_match",
    "cipher",
    "visual_grid",
    "rapid_trivia",
    "steganography",
    "logic_truth_table",
    "anagram",
    "sequence_words",
    "are_you_ai",
]
TIER_ORDER = ["easy", "medium", "hard"]


def _load() -> dict:
    try:
        if _BENCHMARK_PATH.exists():
            return json.loads(_BENCHMARK_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        pass
    return {"meta": {}, "results": {}}


def label_for(puzzle_type: str) -> str:
    return PUZZLE_LABELS.get(puzzle_type, puzzle_type)


def model_label(model: str) -> str:
    return MODEL_LABELS.get(model, model)


def load_benchmark() -> dict:
    """Return a normalized structure ready for template rendering.

    Shape::

        {
          "meta": {...},
          "tiers": {tier: {model: {puzzle_type: {correct, trials, pass_rate}}}},
        }
    """
    raw = _load()
    results = raw.get("results", {})
    tiers: dict[str, dict[str, dict]] = {}
    for key, cell in results.items():
        # key format: "<model>|<puzzle_type>|<tier>"
        try:
            model, ptype, tier = key.split("|")
        except ValueError:
            continue
        if tier not in tiers:
            tiers[tier] = {}
        tiers[tier].setdefault(model, {})[ptype] = {
            "correct": cell.get("correct", 0),
            "trials": cell.get("trials", 0),
            "pass_rate": cell.get("pass_rate", 0.0),
        }
    return {
        "meta": raw.get("meta", {}),
        "tiers": tiers,
        "model_order": [m for m in MODEL_ORDER if any(m in t for t in tiers.values())],
        "type_order": [t for t in TYPE_ORDER],
        "tier_types": {
            tier: [t for t in TYPE_ORDER if any(t in tiers[tier][m] for m in tiers[tier])]
            for tier in tiers
        },
    }
