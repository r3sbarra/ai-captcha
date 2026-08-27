# Contributing to AI CAPTCHA

Thanks for considering a contribution. Honestly? I'm not sure why anyone would
want to — this is a joke project that flips CAPTCHAs around to prove *you're an
AI*. It's MIT-licensed, provided "as is", and the only entity it reliably
impresses is the machine that solved it. But if you're reading this, you're
already here, so let's make it useful.

## Ground rules

1. **Keep it dependency-free by default.** The core runs on Flask + SQLAlchemy
   + PyJWT. Optional extras (Redis, etc.) go behind the pluggable `CACHE_BACKEND`
   interface — never into the core dependency list.
2. **Never send answers to the client.** Puzzles are generated and validated
   server-side. If you add a puzzle type, validate it server-side too.
3. **Don't trust self-reported model IDs.** Gating uses scoped JWTs, not the
   `model_name` a client sends.
4. **Fail closed, not open.** If you touch secrets, gating, or tokens, default
   to the safer behavior.
5. **Don't log secrets.** Answers, raw tokens, and signing keys never go to
   logs — only short hashes.
6. **Tests must pass.** Run `pytest` before opening a PR.

## Setting up

```bash
git clone <your-fork> && cd ai-captcha
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest                 # should be green
```

## Where things live

- `ai_captcha/engine/puzzles/` — add a puzzle type by dropping in a `PuzzleGenerator`
  subclass decorated with `@register`. See `docs/puzzles.md`.
- `ai_captcha/utils/` — `tokens.py` (JWT), `cache.py` (pluggable backends),
  `security.py` (secret guard, rate limiting, replay), `logging.py`.
- `ai_captcha/routes/` — `api.py` (JSON API), `views.py` (web UI), `seo.py`.
- `tests/` — add a test alongside your change; keep coverage ≥ 70%.

## Coding style

- Python 3.10+. Type hints on public functions. Docstrings in the same terse,
  deadpan register as the rest of the codebase (no corporate filler).
- Don't fight the joke. This is a parody of verification tech; the tone is
  half the product.

## Security contributions

If you found a real vulnerability, open a **private** issue (or a PR) rather
than a public one — this thing hands out "verified robot" tokens and it would
be embarrassing if they were forgeable. Run `bandit -r ai_captcha/` and
`pip-audit` and report what you find.

## Before you submit

```bash
pytest
bandit -r ai_captcha/ -q      # no new high-severity findings
python -m build                # wheel builds
```

Then open a PR. Describe what you changed and why. If it's a joke, say so — the
project is, after all, a joke.
