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

---

## Style 4: iframe embed widget (reCAPTCHA-style)

For third-party pages that can't run your Flask app, AI CAPTCHA ships a
**drop-in iframe widget** modeled on reCAPTCHA's sitekey/secretkey model. The
host page frames a challenge widget; on a pass the widget posts a token to the
host via `postMessage`; the host **backend** then confirms it with the secretkey.
The pass/fail decision is **never** trusted client-side.

### Flow

1. **Create an embed site** (admin API, requires `EMBED_ADMIN_TOKEN`):

   ```bash
   curl -X POST http://localhost:5100/api/embed/sites \
     -H "Authorization: Bearer $EMBED_ADMIN_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"name":"My Site","allowed_origins":["https://example.com"]}'
   ```

   Returns `{sitekey, secretkey, allowed_origins}`. The `secretkey` is shown
   **once** — store it server-side. The `sitekey` is public.

2. **Drop the widget into your page** (host-side helper `embed.js`):

   ```html
   <div class="ai-captcha" data-sitekey="YOUR_SITEKEY"
        data-callback="onCaptchaPass" data-error-callback="onCaptchaError"></div>
   <script src="https://YOUR_HOST/apps/ai-captcha/static/js/embed.js" async defer></script>
   ```

   `embed.js` creates the iframe (`GET /embed?sitekey=…&origin=…`), listens for
   `postMessage` (strict origin + source checks), and on a pass stores the token
   in a hidden `ai-captcha-response` input and calls your `data-callback` with it.

3. **Verify server-side** (the security-critical step):

   ```bash
   curl -X POST http://localhost:5100/api/siteverify \
     -H "Content-Type: application/json" \
     -d '{"secretkey":"YOUR_SECRETKEY","response":"<token>","remoteip":"1.2.3.4"}'
   ```

   Returns a reCAPTCHA-shaped `{success, challenge_ts, hostname, error-codes}`.
   Never grant access based on the client-side token alone.

### Security model

- **Single-use tokens** — each token carries a `jti` that is consumed on
  verification; a replayed token is rejected (`timeout-or-duplicate`).
- **Short-lived** — embed tokens expire after 120s (`EMBED_TOKEN_TTL_SECONDS`).
- **Sitekey-bound** — a token is bound to the sitekey it was issued under;
  cross-sitekey laundering is rejected (`sitekey-mismatch`).
- **Clickjacking defense** — `GET /embed` validates the `origin` against the
  site's registered origins and emits a dynamic `frame-ancestors` CSP so only
  those origins can frame it.
- **Brute-force blunted** — `/api/siteverify` is rate-limited per secretkey
  (`RATE_LIMIT_VERIFY_PER_MIN`, default 60/min).

### Admin endpoints (require `EMBED_ADMIN_TOKEN`)

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/embed/sites` | Create a site (returns sitekey + secretkey once) |
| `GET` | `/api/embed/sites` | List sites |
| `DELETE` | `/api/embed/sites/<sitekey>` | Delete a site |
| `PUT` | `/api/embed/sites/<sitekey>/origins` | Set allowed origins |
| `PUT` | `/api/embed/sites/<sitekey>/enabled` | Enable/disable a site |
| `POST` | `/api/embed/demo-site` | Create a throwaway demo site (no admin token; rate-limited) |

### Embed session API (used by the iframe, same-origin)

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/embed/start` | Start an embed challenge bound to a sitekey |
| `GET` | `/api/embed/session/<id>` | Current puzzle for an embed session |
| `POST` | `/api/embed/session/<id>/answer` | Submit an answer |
| `GET` | `/api/embed/session/<id>/result` | Final result + verification token |

### Config keys for the embed widget

| Key | Default | Purpose |
|-----|---------|---------|
| `EMBED_ADMIN_TOKEN` | `""` | Bearer token for the admin API (empty = admin disabled, fail closed) |
| `RATE_LIMIT_VERIFY_PER_MIN` | `60` | Per-secretkey limit on `/api/siteverify` |
| `MAX_ANSWER_LENGTH` | `10000` | Max answer length |
| `EMBED_TOKEN_TTL_SECONDS` | `120` | Embed token lifetime (module constant) |

A live demo is served at `/embed-demo` (or `/apps/ai-captcha/embed-demo` under
AppManager). See `docs/api.md` for the full endpoint reference.
