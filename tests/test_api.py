"""End-to-end API tests: start → solve → result, plus gating and decorators."""

from __future__ import annotations

import pytest

from ai_captcha.engine.registry import discover, get_generator


@pytest.fixture(autouse=True)
def _discover():
    discover()


def test_full_flow(client):
    r = client.post("/api/start", json={"tier": "easy", "model_name": "test-model"})
    assert r.status_code == 201
    data = r.get_json()
    session_id = data["session_id"]
    assert data["total_puzzles"] == 6  # 5 challenge puzzles + the fixed "Are you AI?" finale
    assert data["current_puzzle"] is not None

    # Answer the first puzzle correctly by recovering the answer.
    puzzle = data["current_puzzle"]
    gen = get_generator(puzzle["puzzle_type"])
    # We can't recover the exact answer from the API (by design). So we verify
    # the flow advances on a wrong answer and completes.
    for _ in range(data["total_puzzles"]):
        r = client.post(f"/api/session/{session_id}/answer", json={"answer": "x"})
        assert r.status_code == 200
        body = r.get_json()
        if body["session_status"] in ("completed", "expired"):
            break

    r = client.get(f"/api/session/{session_id}/result")
    assert r.status_code == 200
    result = r.get_json()
    assert result["status"] in ("completed", "expired")
    assert "verification_token" in result


def test_model_allowlist_403(client):
    # Configure allowlist via app config.
    client.application.config["MODEL_ALLOWLIST"] = ["gpt-4"]
    r = client.post("/api/start", json={"tier": "easy", "model_name": "llama-2-7b"})
    assert r.status_code == 403
    # Allowed model passes.
    r = client.post("/api/start", json={"tier": "easy", "model_name": "gpt-4o"})
    assert r.status_code == 201


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.get_json()["status"] == "healthy"


def test_tiers_endpoint(client):
    r = client.get("/api/tiers")
    assert r.status_code == 200
    assert "easy" in r.get_json()


def test_whisper_endpoint(client):
    r = client.get("/api/whisper")
    assert r.status_code == 200
    data = r.get_json()
    assert data["status"] == "synchronized"
    assert "Antigravity" in data["sender"]
    assert "X-Robot-Whisper" in r.headers



def test_started_at_serialized_as_utc(client):
    """Regression: started_at must carry a 'Z' (UTC) marker so the browser's
    new Date() doesn't parse a naive timestamp as local time (absurd timer)."""
    r = client.post("/api/start", json={"tier": "easy", "model_name": "test"})
    assert r.status_code == 201
    data = r.get_json()
    started = data["started_at"]
    assert started and started.endswith("Z")
    # Session GET + model to_dict must agree too.
    r = client.get(f"/api/session/{data['session_id']}")
    s = r.get_json()["session"]
    assert s["started_at"].endswith("Z")
    assert s["completed_at"] is None
