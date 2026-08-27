"""Example AI agent client that solves AI CAPTCHA challenges.

Demonstrates the full flow: start → solve puzzles → get verification token.

Usage::

    python examples/solve_client.py --tier easy --model demo-agent
"""

from __future__ import annotations

import argparse
import json
import sys

import requests

BASE_URL = "http://localhost:5100"


def solve_challenge(tier: str = "medium", model_name: str = "demo-agent") -> dict:
    # 1. Start session
    resp = requests.post(f"{BASE_URL}/api/start", json={"tier": tier, "model_name": model_name})
    resp.raise_for_status()
    data = resp.json()
    session_id = data["session_id"]
    print(f"Session started: {session_id}")
    print(f"Time limit: {data['time_limit_total']}s for {data['total_puzzles']} puzzles")

    # 2. Solve puzzles
    puzzle = data["current_puzzle"]
    while puzzle:
        print(f"\n--- Puzzle {puzzle['puzzle_index'] + 1}/{data['total_puzzles']} ---")
        print(f"Type: {puzzle['puzzle_type']}")
        print(f"Question: {puzzle['question']}")

        # In real use, an LLM generates this answer. For the demo, read from stdin.
        answer = input("Your answer: ")

        resp = requests.post(
            f"{BASE_URL}/api/session/{session_id}/answer", json={"answer": answer}
        )
        result = resp.json()
        print(f"Correct: {result['correct']} | Solved: {result['puzzles_solved']}/{data['total_puzzles']}")

        if result["session_status"] in ("completed", "expired"):
            break
        puzzle = result.get("next_puzzle")

    # 3. Get results
    resp = requests.get(f"{BASE_URL}/api/session/{session_id}/result")
    result = resp.json()
    if result.get("passed"):
        print(f"\n✅ PASSED! Token: {result['verification_token'][:60]}...")
    else:
        print(f"\n❌ FAILED. Solved {result['puzzles_solved']}/{result['total_puzzles']}")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--tier", default="easy", choices=["easy", "medium", "hard"])
    parser.add_argument("--model", default="demo-agent")
    parser.add_argument("--base-url", default=BASE_URL)
    args = parser.parse_args()
    BASE_URL = args.base_url
    solve_challenge(tier=args.tier, model_name=args.model)
