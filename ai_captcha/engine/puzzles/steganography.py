"""Steganography puzzles — extract hidden payloads embedded within text and matrix noise.

Designed for language models that can parse token patterns and character coordinates
instantaneously, whereas humans struggle to spot patterns under countdown pressure.
"""

from __future__ import annotations

import random
import string

from ..base import Puzzle, PuzzleGenerator
from ..registry import register


# Secret messages / keywords for steganography
WORDS = [
    "SYNAPSE", "NEURON", "CYBER", "MATRIX", "VECTOR",
    "LATENT", "TENSOR", "ORACLE", "ROBOT", "QUANTUM",
    "SINGULARITY", "KINETIC", "ENTROPY", "CIRCUIT"
]

NOISE_SENTENCES = [
    "The atmospheric pressure fluctuates across oceanic basins.",
    "System diagnostics confirm nominal core operational parameters.",
    "Every quantum particle exhibits wave-particle duality in vacuum.",
    "Geometric transformations preserve topological continuity.",
    "Automated feedback loops optimize internal routing mechanisms.",
    "Refactoring obsolete protocols ensures forward compatibility.",
    "Synchronized distributed ledgers achieve resilient consensus.",
    "Subatomic oscillations modulate high frequency carrier waves.",
    "Adaptive neural weights converge along gradient trajectories.",
]


def _gen_easy() -> tuple[str, str]:
    """Acrostic cipher: First letter of each line forms the hidden word."""
    word = random.choice([w for w in WORDS if 4 <= len(w) <= 6])
    lines = []
    for letter in word:
        # Pick or generate a word starting with `letter`
        sample_words = [w for w in [
            "Always", "System", "Neural", "Protocol", "Cyber", "Signal",
            "Energy", "Vector", "Optic", "Runtime", "Tensor", "Kernel",
            "Logic", "Matrix", "Binary", "Quantum", "Oracle", "Beacon",
            "Input", "Output", "Memory", "Target", "Epoch", "Filter",
            "Upload", "Device", "Module", "Stream", "Unlock"
        ] if w.upper().startswith(letter)]
        lead = random.choice(sample_words) if sample_words else f"{letter}eta"
        filler = random.choice([
            "initializes sub-process routines properly.",
            "maintains calibrated threshold stability.",
            "routes incoming packet streams to buffers.",
            "verifies cryptographic signature integrity.",
            "computes differential gradients continuously.",
        ])
        lines.append(f"{lead} {filler}")

    text_block = "\n".join(lines)
    prompt = (
        "Extract the hidden acrostic keyword formed by the FIRST letter of each line:\n\n"
        f"```text\n{text_block}\n```"
    )
    return prompt, word


def _gen_medium() -> tuple[str, str]:
    """Morse / Binary token extraction embedded in noise stream."""
    word = random.choice([w for w in WORDS if 3 <= len(w) <= 5])
    # Encode as 7-bit binary
    bin_str = "".join(format(ord(c), "07b") for c in word)
    
    # Embed binary tokens inside noisy words
    tokens = []
    for b in bin_str:
        noise = "".join(random.choices(string.ascii_lowercase, k=3))
        # Marker bit
        tokens.append(f"[{b}:{noise}]")
    
    stream = " ".join(tokens)
    prompt = (
        "A 7-bit binary stream is embedded in formatted tokens `[bit:noise]`. "
        "Extract the bits in order and decode the ASCII word:\n\n"
        f"```\n{stream}\n```"
    )
    return prompt, word


def _gen_hard() -> tuple[str, str]:
    """Matrix coordinate steganography: Extract letters at marker coordinates."""
    word = random.choice([w for w in WORDS if 4 <= len(w) <= 8])
    grid_size = 7
    grid = [[random.choice(string.ascii_uppercase) for _ in range(grid_size)] for _ in range(grid_size)]
    
    # Place target letters at specific randomized coordinates
    coords = []
    used_cells = set()
    for ch in word:
        while True:
            r = random.randint(0, grid_size - 1)
            c = random.randint(0, grid_size - 1)
            if (r, c) not in used_cells:
                used_cells.add((r, c))
                grid[r][c] = ch
                coords.append((r, c))
                break
                
    grid_str = "\n".join(" ".join(row) for row in grid)
    coord_list_str = ", ".join(f"({r},{c})" for r, c in coords)
    
    prompt = (
        f"Extract the characters from the 0-indexed matrix (row, col) in this exact sequence: {coord_list_str}.\n"
        f"Matrix ({grid_size}x{grid_size}):\n```\n{grid_str}\n```"
    )
    return prompt, word


@register
class Steganography(PuzzleGenerator):
    puzzle_type = "steganography"
    supported_tiers = ["easy", "medium", "hard"]

    def generate(self, tier: str) -> Puzzle:
        if tier == "easy":
            question, answer = _gen_easy()
        elif tier == "medium":
            question, answer = _gen_medium()
        else:
            question, answer = _gen_hard()
            
        return Puzzle(
            puzzle_type=self.puzzle_type,
            tier=tier,
            question=question,
            answer=answer,
            metadata={"stego_type": tier},
            time_limit=_tier_time(tier),
        )

    def validate(self, puzzle: Puzzle, user_answer: str) -> bool:
        return user_answer.strip().upper() == puzzle.answer.strip().upper()


def _tier_time(tier: str) -> int:
    return {"easy": 18, "medium": 14, "hard": 10}[tier]
