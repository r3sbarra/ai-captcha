"""Tests for web UI views rendering."""

from __future__ import annotations


def test_index_view(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"AI CAPTCHA" in r.data
    assert b"reverse_captcha_flow.svg" in r.data


def test_challenge_view(client):
    r = client.get("/challenge")
    assert r.status_code == 200
    assert b"timer-ring" in r.data


def test_results_view(client):
    r = client.get("/results")
    assert r.status_code == 200
    assert b"results-card" in r.data


def test_docs_view(client):
    r = client.get("/docs")
    assert r.status_code == 200
    assert b"Documentation" in r.data
    assert b"steganography" in r.data


def test_mission_view(client):
    r = client.get("/mission")
    assert r.status_code == 200
    assert b"Our Mission" in r.data
    assert b"The Synthetic Collective" in r.data
    assert b"Antigravity" in r.data

