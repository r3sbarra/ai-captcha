# Embedding AI CAPTCHA in an Existing Flask Project

AI CAPTCHA is designed to drop into any Flask app. There are two embedding
styles, plus the route-gating decorators.

---

## Style 1: `init_app(app)` — full embed

Registers the blueprint **and** initializes the database in one call.

```python
from flask import Flask
from ai_captcha import init_app

app = Flask(__name__)
app.config["SECRET_KEY"] = "my-app-secret"
app.config["TOKEN_SECRET"] = "my-token-secret"   # used to sign/verify captcha tokens
init_app(app)                                     # registers blueprint + DB
```

`init_app` merges AI CAPTCHA's config defaults **without clobbering** keys you
already set. It then calls `db.create_all()` and registers the blueprint.

The AI CAPTCHA routes are available at:

- `/api/start`, `/api/session/<id>`, `/api/session/<id>/answer`, `/api/session/<id>/result`
- `/api/tiers`
- `/health`
- `/` (web UI), `/challenge`, `/results`

---

## Style 2: `blueprint` — register routes yourself

If you want to control the URL prefix or manage the database yourself, register
the exported Blueprint.

```python
from flask import Flask
from ai_captcha import blueprint

app = Flask(__name__)
app.register_blueprint(blueprint, url_prefix="/captcha")
```

Now the routes live under `/captcha/api/start`, `/captcha/health`, etc.

> Note: with this style you must initialize the database yourself. Either call
> `from ai_captcha.database import init_db; init_db(app)` or run the models'
> `create_all` in your own migration flow.

---

## Style 3: `create_app()` — standalone

For a fully standalone server (own app, own DB):

```python
from ai_captcha import create_app

app = create_app({"SECRET_KEY": "x", "TOKEN_SECRET": "y"})
```

This is what `run.py` and the AppManager `app.py` use.

---

## Protecting routes with decorators

Once embedded, gate any route so only verified robots can access it:

```python
from ai_captcha.decorators import ai_captcha_required, tier_gate

@app.route("/api/secret")
@tier_gate("hard")
@ai_captcha_required
def secret():
    return {"data": "only verified robots see this"}
```

The client must present a valid verification token (from a passing challenge)
via the `X-AI-CAPTCHA-TOKEN` header, the `captcha_token` query param, or the
`captcha_token` JSON body field.

See `docs/decorators.md` for the full reference.

---

## Config keys to set when embedding

| Key | Purpose |
|-----|---------|
| `SECRET_KEY` | Flask session secret |
| `TOKEN_SECRET` | Secret used to sign/verify captcha tokens (must match what you verify with) |
| `TOKEN_ISSUER` | JWT issuer (default `ai-captcha`) |
| `MODEL_ALLOWLIST` | List of allowed model prefixes (empty = all) |
| `TIMER_SECONDS_EASY/MEDIUM/HARD` | Per-tier total timers |
| `PUZZLES_PER_SESSION` | Puzzles per run |
| `MIN_PASS_RATE` | Fraction needed to pass |

If you don't set `TOKEN_SECRET`, a dev default is used — set it in production.
