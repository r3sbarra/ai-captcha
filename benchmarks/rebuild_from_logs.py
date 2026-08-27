#!/usr/bin/env python3
"""Rebuild benchmarks/results.json from the agent run logs.

Each agent writes a line per finished cell of the form::

    <agent> <puzzle_type> <tier> <correct>/<trials> <rate>%

(and optionally a final `WROTE <path>`). This reconstructs the results dict
from whatever cells completed before the run was stopped, then writes a merged
results.json suitable for the web table and README.

Usage: python benchmarks/rebuild_from_logs.py
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOGS = ROOT / "benchmarks" / "logs"
OUT = ROOT / "benchmarks" / "results.json"

LINE_RE = re.compile(
    r"^(?P<agent>\S+)\s+(?P<ptype>\S+)\s+(?P<tier>\S+)\s+"
    r"(?P<correct>\d+)/\s*(?P<trials>\d+)\s+[\d.]+%$"
)


def main() -> None:
    results = {}
    agents = []
    meta_trials = None
    for log in sorted(LOGS.glob("*.log")):
        agent = log.stem
        for line in log.read_text().splitlines():
            m = LINE_RE.match(line.strip())
            if not m:
                continue
            agents.append(agent)
            key = f"{m.group('agent')}|{m.group('ptype')}|{m.group('tier')}"
            correct = int(m.group("correct"))
            trials = int(m.group("trials"))
            if meta_trials is None:
                meta_trials = trials
            results[key] = {
                "model": m.group("agent"),
                "puzzle_type": m.group("ptype"),
                "tier": m.group("tier"),
                "trials": trials,
                "correct": correct,
                "pass_rate": round(correct / trials, 4),
            }

    agents = sorted(set(agents))
    tiers = sorted({k.split("|")[2] for k in results})
    payload = {
        "meta": {
            "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "gateway_url": "http://127.0.0.1:18789",
            "trials": meta_trials or 10,
            "tiers": tiers,
            "agents": agents,
            "note": "Partial run — rebuilt from agent logs.",
        },
        "results": results,
        "details": {},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2))
    print(f"Rebuilt {OUT} with {len(results)} cells across agents {agents} tiers {tiers}")


if __name__ == "__main__":
    main()
