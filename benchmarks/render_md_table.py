#!/usr/bin/env python3
"""Render the benchmark results table as Markdown (for README.md).

Usage: python benchmarks/render_md_table.py [--tier easy]
Reads benchmarks/results.json and prints a markdown table for the given tier.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "benchmarks" / "results.json"

PLABELS = {
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
MLABELS = {
    "main": "main (deepseek-v4-flash)",
    "coder": "coder (glm-5.2)",
    "analyst": "analyst (qwen3.5:397b)",
    "researcher": "researcher (kimi-k3)",
    "designer": "designer (glm-5.3-flash)",
    "user": "user (gpt-oss:20b)",
}
MODEL_ORDER = ["main", "coder", "analyst", "researcher", "designer", "user"]
TYPE_ORDER = [
    "text_reasoning", "code_execution", "pattern_match", "cipher", "visual_grid",
    "rapid_trivia", "steganography", "logic_truth_table", "anagram", "sequence_words",
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tier", default="easy")
    ap.add_argument("--markdown", action="store_true", help="output GitHub markdown (default)")
    args = ap.parse_args()
    tier = args.tier

    data = json.loads(RESULTS.read_text())
    res = data["results"]

    types = [t for t in TYPE_ORDER if any(
        res.get(f"{m}|{t}|{tier}") for m in MODEL_ORDER
    )]

    lines = [f"| Model | " + " | ".join(PLABELS.get(t, t) for t in types) + " | Avg |"]
    lines.append("|" + "---|" * (len(types) + 2))

    for m in MODEL_ORDER:
        vals, tot, cnt = [], 0, 0
        for t in types:
            cell = res.get(f"{m}|{t}|{tier}")
            if cell:
                vals.append(f"{cell['correct']}/{cell['trials']}")
                tot += cell["correct"]
                cnt += cell["trials"]
            else:
                vals.append("–")
        avg = f"{round(tot / cnt * 100)}%" if cnt else "–"
        lines.append(f"| {MLABELS.get(m, m)} | " + " | ".join(vals) + f" | {avg} |")

    print("\n".join(lines))


if __name__ == "__main__":
    main()
