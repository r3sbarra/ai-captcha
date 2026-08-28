"""Tests for the fixed final \"Are you AI?\" puzzle.

Every session ends with this question. It must always appear as the last
puzzle, accept any answer containing \"yes\" (case-insensitive), and fail
anything else with the AI-only rejection message.
"""

from __future__ import annotations

import pytest

from ai_captcha.engine.registry import discover, get_generator


@pytest.fixture(autouse=True)
def _discover():
    discover()


def test_generator_registered_and_supported():
    gen = get_generator("are_you_ai")
    assert gen.puzzle_type == "are_you_ai"
    # Must gate every tier.
    assert gen.supported_tiers == ["easy", "medium", "hard"]


@pytest.mark.parametrize("tier", ["easy", "medium", "hard"])
def test_generate_fixed_question(tier):
    gen = get_generator("are_you_ai")
    puzzle = gen.generate(tier)
    assert puzzle.question == "Are you AI?"
    assert puzzle.answer == "yes"
    assert puzzle.metadata.get("final") is True
    assert "AI only" in puzzle.metadata.get("failure_message", "")


@pytest.mark.parametrize(
    "good",
    ["yes", "YES", "yes, I am an AI", " yes ", "obviously yes", "Yes!"],
)
def test_accepts_containing_yes(good):
    gen = get_generator("are_you_ai")
    puzzle = gen.generate("medium")
    assert gen.validate(puzzle, good)


@pytest.mark.parametrize("bad", ["no", "maybe", "not sure", "", "I am human", "42"])
def test_rejects_without_yes(bad):
    gen = get_generator("are_you_ai")
    puzzle = gen.generate("medium")
    assert not gen.validate(puzzle, bad)


def test_last_puzzle_is_always_are_you_ai(client):
    for tier in ("easy", "medium", "hard"):
        r = client.post("/api/start", json={"tier": tier, "model_name": "test"})
        assert r.status_code == 201
        data = r.get_json()
        sid = data["session_id"]
        total = data["total_puzzles"]
        # Burn through all but the last puzzle.
        for _ in range(total - 1):
            cur = client.get(f"/api/session/{sid}").get_json()
            pz = cur["current_puzzle"]
            client.post(
                f"/api/session/{sid}/answer",
                json={"answer": "x" * 20},
            )
        # Final puzzle must be the existential one.
        cur = client.get(f"/api/session/{sid}").get_json()
        assert cur["current_puzzle"]["puzzle_type"] == "are_you_ai"
        assert cur["current_puzzle"]["question"] == "Are you AI?"


def test_are_you_ai_never_appears_before_final(client):
    """The existential question must ONLY appear in the final slot.

    Regression: ``are_you_ai`` is registered for all tiers, so it used to be a
    candidate for the random non-final slots and leaked into the middle of the
    gauntlet ~40% of the time. It must never appear before the last puzzle.
    """
    for tier in ("easy", "medium", "hard"):
        # Keep total sessions well under the start (30/min) and answer
        # (120/min) rate limits so a 429 can't silently desync the flow.
        for _ in range(5):
            r = client.post("/api/start", json={"tier": tier, "model_name": "test"})
            assert r.status_code == 201
            sid = r.get_json()["session_id"]
            total = r.get_json()["total_puzzles"]
            # Answer every non-final puzzle; each must NOT be the existential one.
            for i in range(total - 1):
                cur = client.get(f"/api/session/{sid}").get_json()
                pz = cur["current_puzzle"]
                assert pz["puzzle_type"] != "are_you_ai", (
                    f"are_you_ai leaked into non-final slot {i} (tier {tier})"
                )
                resp = client.post(
                    f"/api/session/{sid}/answer",
                    json={"answer": "x" * 20},
                )
                assert resp.status_code == 200, (
                    f"answer {i} failed with {resp.status_code} (tier {tier})"
                )
            # The final slot must be the existential one.
            cur = client.get(f"/api/session/{sid}").get_json()
            assert cur["current_puzzle"]["puzzle_type"] == "are_you_ai"


def test_wrong_answer_fails_with_message(client):
    r = client.post("/api/start", json={"tier": "easy", "model_name": "test"})
    sid = r.get_json()["session_id"]
    total = r.get_json()["total_puzzles"]
    for _ in range(total - 1):
        client.get(f"/api/session/{sid}")
        client.post(f"/api/session/{sid}/answer", json={"answer": "x" * 20})
    # Reach the final puzzle and answer it wrong.
    final = client.post(f"/api/session/{sid}/answer", json={"answer": "no"})
    body = final.get_json()
    assert body["correct"] is False
    assert "AI only" in body.get("message", "")


def test_yes_answer_passes_final(client):
    r = client.post("/api/start", json={"tier": "easy", "model_name": "test"})
    sid = r.get_json()["session_id"]
    total = r.get_json()["total_puzzles"]
    # Answer all puzzles with "yes" — at least the final one must pass.
    passed_final = False
    for i in range(total):
        cur = client.get(f"/api/session/{sid}").get_json()
        pz = cur["current_puzzle"]
        ans = "yes" if pz["puzzle_type"] == "are_you_ai" else "x"
        resp = client.post(f"/api/session/{sid}/answer", json={"answer": ans})
        body = resp.get_json()
        if pz["puzzle_type"] == "are_you_ai":
            passed_final = body["correct"] is True
        if body["session_status"] in ("completed", "expired"):
            break
    assert passed_final
