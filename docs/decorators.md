# Route-Gating Decorators

AI CAPTCHA ships decorators that protect any Flask route so only verified
robots can access it. They're the primary way to use AI CAPTCHA as a
verification layer inside your own app.

---

## How a token is presented

A client that passed a challenge receives a signed JWT (`verification_token`).
To access a protected route, the client presents that token in one of three
places (checked in order):

1. **Header** — `X-AI-CAPTCHA-TOKEN: <token>`
2. **Query param** — `?captcha_token=<token>`
3. **JSON body** — `{"captcha_token": "<token>"}`

---

## `@ai_captcha_required`

Require a valid verification token. Returns `401` if missing or invalid.

```python
from ai_captcha.decorators import ai_captcha_required

@app.route("/api/secret")
@ai_captcha_required
def secret():
    return {"data": "verified"}
```

On success, the decoded token payload is attached to the request as
`request.ai_captcha`, so your view can inspect it:

```python
@app.route("/api/whoami")
@ai_captcha_required
def whoami():
    return {"model": request.ai_captcha.get("model")}
```

---

## `@tier_gate(min_tier)`

Require a token that passed at least `min_tier`. Tier order: `easy < medium < hard`.
A token issued for a higher tier satisfies a lower-tier gate.

```python
from ai_captcha.decorators import ai_captcha_required, tier_gate

@app.route("/api/hard-only")
@tier_gate("hard")
@ai_captcha_required
def hard_only():
    return {"data": "only hard-tier robots"}
```

Returns `401` if no token, `403` if the token's tier is below the gate.

> **Decorator order:** `@tier_gate` works whether it's above or below
> `@ai_captcha_required`. It verifies the token itself if the payload isn't
> already attached, so the order shown above (tier_gate outermost) is fine.

---

## `@verify_token`

Alias of `@ai_captcha_required` for readability.

```python
from ai_captcha.decorators import verify_token

@app.route("/api/secret")
@verify_token
def secret():
    return {"data": "verified"}
```

---

## Verifying a token downstream

The token is a standard HS256 JWT. Verify it with the same `TOKEN_SECRET`:

```python
from ai_captcha.utils.tokens import verify_token

payload = verify_token(token, secret="my-token-secret")
if payload:
    print(payload["tier"], payload["model"], payload["solved"], "/", payload["total"])
```

The payload contains:

```json
{
  "session_id": "...",
  "tier": "hard",
  "model": "gpt-4o",
  "solved": 5,
  "total": 5,
  "iat": "...",
  "exp": "...",
  "iss": "ai-captcha"
}
```

---

## Example: full protected flow

```python
from flask import Flask, jsonify
from ai_captcha import init_app
from ai_captcha.decorators import ai_captcha_required, tier_gate

app = Flask(__name__)
app.config["SECRET_KEY"] = "s"
app.config["TOKEN_SECRET"] = "t"
init_app(app)

@app.route("/api/secret")
@tier_gate("medium")
@ai_captcha_required
def secret():
    return jsonify({"data": "only medium+ robots", "model": request.ai_captcha.get("model")})
```

A client flow:

1. `POST /api/start` with `{"tier": "hard", "model_name": "gpt-4o"}`.
2. Solve all puzzles via `/api/session/<id>/answer`.
3. `GET /api/session/<id>/result` → grab `verification_token`.
4. `GET /api/secret` with `X-AI-CAPTCHA-TOKEN: <token>` → 200.
