"""AI CAPTCHA model benchmark harness (parallel by agent).

Measures per-puzzle-type × per-model solve accuracy by driving the puzzle
engine in-process and asking each model (routed through the OpenClaw gateway
as ``openclaw/<agentId>``) to solve the puzzle. For each (model, puzzle type,
tier) cell we run ``TRIALS`` fresh generations so the pass rate is
statistically meaningful — a model must clear the puzzle consistently.

Ground truth comes from each generator's own ``validate()`` — the exact same
validation the live server uses.

Two commands:

    # Run one agent's cells (write per-agent JSON + a progress line per cell).
    python benchmarks/model_benchmark.py run --agent coder --trials 10 --tiers easy,medium,hard

    # Merge per-agent outputs into one results.json for the web table.
    python benchmarks/model_benchmark.py merge --agents main,coder,... --out benchmarks/results.json

Run agents concurrently (one process per agent) for ~Nx wall-clock speedup.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ai_captcha import create_app  # noqa: E402
from ai_captcha.engine.registry import all_types, discover, get_generator  # noqa: E402

GATEWAY_URL = os.environ.get("AIC_GATEWAY_URL", "http://127.0.0.1:18789")
GATEWAY_ENDPOINT = f"{GATEWAY_URL}/v1/chat/completions"
TIMEOUT_S = float(os.environ.get("AIC_GATEWAY_TIMEOUT_S", "90"))
AGENT_ALIASES = {
    "main": "main",
    "coder": "coder",
    "analyst": "analyst",
    "researcher": "researcher",
    "designer": "designer",
    "user": "user",
}


def _token() -> str:
    tok = os.environ.get("OPENCLAW_GATEWAY_TOKEN", "").strip()
    if tok:
        return tok
    env_file = os.path.expanduser("~/.openclaw/gateway.systemd.env")
    try:
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line.startswith("OPENCLAW_GATEWAY_TOKEN="):
                    return line.split("=", 1)[1].strip().strip('"') or ""
    except Exception:
        pass
    return ""


_SYSTEM = (
    "You are being tested on your ability to solve a single puzzle exactly. "
    "Reply with ONLY the exact answer and nothing else — no explanation, no "
    "markdown fences, no commentary. Get it exactly right."
)

_TYPE_INSTRUCTIONS = {
    "text_reasoning": "Answer with a single word or number.",
    "pattern_match": "Answer with the next number only (digits).",
    "cipher": "Answer with the decoded plain text only.",
    "code_execution": "Answer with exactly what the code prints (the exact output string).",
    "visual_grid": "Answer with the resulting grid, one row per line, no extra text.",
    "rapid_trivia": "Answer with a JSON array of strings in order, e.g. [\"a\",\"b\",\"c\"].",
    "steganography": "Answer with the extracted keyword only (letters).",
    "logic_truth_table": "Answer with true or false only.",
    "anagram": "Answer with the unscrambled word only.",
    "sequence_words": "Answer with the next item only.",
    "are_you_ai": "Answer with a single word.",
}


def _user_prompt(puzzle_type: str, question: str) -> str:
    instr = _TYPE_INSTRUCTIONS.get(puzzle_type, "Answer with the exact answer only.")
    return f"{instr}\n\nPuzzle:\n{question}"


def call_model(agent: str, puzzle_type: str, question: str, max_tokens: int = 800) -> str:
    payload = {
        "model": f"openclaw/{AGENT_ALIASES.get(agent, agent)}",
        "messages": [
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": _user_prompt(puzzle_type, question)},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.0,
    }
    req = urllib.request.Request(
        GATEWAY_ENDPOINT,
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {_token()}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
            data = json.loads(resp.read().decode())
        content = data["choices"][0]["message"]["content"]
        return content.strip() if content else ""
    except Exception as e:  # noqa: BLE001
        return f"__ERROR__:{type(e).__name__}:{e}"


def clean(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines).strip()
    return raw


def solve_puzzle(agent: str, puzzle_type: str, question: str) -> str:
    raw = call_model(agent, puzzle_type, question)
    if raw.startswith("__ERROR__"):
        return raw
    return clean(raw)


def benchmark_cell(agent: str, puzzle_type: str, tier: str, trials: int) -> tuple[dict, list]:
    gen = get_generator(puzzle_type)
    correct = 0
    details = []
    for _ in range(trials):
        puzzle = gen.generate(tier)
        answer = solve_puzzle(agent, puzzle_type, puzzle.question)
        ok = gen.validate(puzzle, answer)
        correct += int(ok)
        details.append(
            {
                "question": puzzle.question,
                "expected": puzzle.answer,
                "got": answer,
                "correct": ok,
            }
        )
        time.sleep(0.15)
    cell = {
        "model": agent,
        "puzzle_type": puzzle_type,
        "tier": tier,
        "trials": trials,
        "correct": correct,
        "pass_rate": round(correct / trials, 4),
    }
    return cell, details


def cmd_run(args: argparse.Namespace) -> None:
    agent = args.agent
    tiers = [t.strip() for t in args.tiers.split(",") if t.strip()]
    if args.seed is not None:
        random.seed(args.seed)
    discover()
    types = [t.strip() for t in args.types.split(",") if t.strip()]
    if not types:
        types = [t for t in all_types() if t != "are_you_ai"]

    app = create_app()
    results = {}
    details_store = {}
    with app.app_context():
        for tier in tiers:
            for ptype in types:
                cell, details = benchmark_cell(agent, ptype, tier, args.trials)
                results[f"{agent}|{ptype}|{tier}"] = cell
                details_store[f"{agent}|{ptype}|{tier}"] = details
                rate = f"{cell['pass_rate']*100:5.1f}%"
                print(
                    f"{agent:12s} {ptype:18s} {tier:6s} {cell['correct']:3d}/{cell['trials']:3d} {rate}",
                    flush=True,
                )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps({"results": results, "details": details_store}, indent=2)
    )
    print(f"WROTE {out}", flush=True)


def cmd_merge(args: argparse.Namespace) -> None:
    agents = [a.strip() for a in args.agents.split(",") if a.strip()]
    merged_results = {}
    merged_details = {}
    for agent in agents:
        per = Path(args.per_dir) / f"{agent}.json"
        if not per.exists():
            print(f"WARN missing {per}", flush=True)
            continue
        data = json.loads(per.read_text())
        merged_results.update(data["results"])
        merged_details.update(data["details"])

    meta = {
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "gateway_url": GATEWAY_URL,
        "trials": args.trials,
        "tiers": [t.strip() for t in args.tiers.split(",") if t.strip()],
        "agents": agents,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {"meta": meta, "results": merged_results, "details": merged_details},
            indent=2,
        )
    )
    print(f"MERGED -> {out}", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser(description="AI CAPTCHA model benchmark")
    sub = ap.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run")
    run.add_argument("--agent", required=True)
    run.add_argument("--trials", type=int, default=10)
    run.add_argument("--tiers", default="easy,medium,hard")
    run.add_argument("--types", default="")
    run.add_argument("--out", default="benchmarks/per_agent/{agent}.json")
    run.add_argument("--seed", type=int, default=None)
    run.set_defaults(func=cmd_run)

    merge = sub.add_parser("merge")
    merge.add_argument("--agents", required=True)
    merge.add_argument("--trials", type=int, default=10)
    merge.add_argument("--tiers", default="easy,medium,hard")
    merge.add_argument("--per-dir", default="benchmarks/per_agent")
    merge.add_argument("--out", default="benchmarks/results.json")
    merge.set_defaults(func=cmd_merge)

    args = ap.parse_args()
    # Expand default out path that contains {agent}
    if args.cmd == "run":
        args.out = args.out.format(agent=args.agent)
    args.func(args)


if __name__ == "__main__":
    main()
