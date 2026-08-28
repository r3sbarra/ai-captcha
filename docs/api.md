# AI CAPTCHA — JSON API Reference

Base URL: `/api` (standalone) or `/apps/ai-captcha/api` (under AppManager).

All request/response bodies are JSON.

---

## `GET /api/tiers`

List available difficulty tiers and their configs.

**Response 200**

```json
{
  "easy":   {"timer_seconds": 30, "puzzles_per_session": 5, "min_pass_rate": 0.8},
  "medium": {"timer_seconds": 20, "puzzles_per_session": 5, "min_pass_rate": 0.8},
  "hard":   {"timer_seconds": 10, "puzzles_per_session": 5, "min_pass_rate": 0.8}
}
```

---

## `POST /api/start`

Create and start a challenge session.

**Request body**

```json
{
  "tier": "easy",            // easy | medium | hard (default: medium)
  "model_name": "gpt-4o"     // optional; gated by MODEL_ALLOWLIST if set
}
```

**Response 201**

```json
{
  "session_id": "9121b756-...",
  "tier": "easy",
  "status": "active",
  "total_puzzles": 5,
  "time_limit_total": 30,
  "started_at": "2026-08-27T20:36:26.226129",
  "current_puzzle": {
    "attempt_id": "712bda7e-...",
    "puzzle_index": 0,
    "puzzle_type": "cipher",
    "question": "Decode this ROT13 string: 'uryyb jbeyq'",
    "time_limit": 15
  }
}
```

**Errors**

- `400 invalid_tier` — tier not in easy/medium/hard.
- `403 model_not_allowed` — model not on the allowlist.

---

## `GET /api/session/<session_id>`

Get session status and the current puzzle.

**Response 200**

```json
{
  "session": {
    "id": "9121b756-...",
    "tier": "easy",
    "status": "active",
    "model_name": "gpt-4o",
    "total_puzzles": 5,
    "puzzles_solved": 1,
    "puzzles_attempted": 1,
    "current_puzzle_index": 1,
    "time_limit_total": 30,
    "started_at": "...",
    "completed_at": null
  },
  "current_puzzle": {
    "attempt_id": "8ab67eba-...",
    "puzzle_index": 1,
    "puzzle_type": "rapid_trivia",
    "question": "Answer these 3 questions...",
    "time_limit": 20
  }
}
```

When the session is complete/expired, `current_puzzle` is `null`.

---

## `POST /api/session/<session_id>/answer`

Submit an answer for the current puzzle.

**Request body**

```json
{ "answer": "hello world" }
```

**Response 200**

```json
{
  "correct": true,
  "puzzles_solved": 1,
  "puzzles_remaining": 4,
  "session_status": "active",
  "next_puzzle": { "...": "..." }
}
```

`next_puzzle` is present only while the session is still active.

**Errors**

- `400 no_answer` — empty answer.
- `400 bad_request` — no active puzzle to answer.
- `410` — session time expired.

---

## `GET /api/session/<session_id>/result`

Get the final result and, if passed, the verification token.

**Response 200**

```json
{
  "session_id": "9121b756-...",
  "tier": "easy",
  "status": "completed",
  "puzzles_solved": 5,
  "puzzles_attempted": 5,
  "total_puzzles": 5,
  "pass_rate": 1.0,
  "passed": true,
  "model_name": "gpt-4o",
  "verification_token": "eyJhbGciOiJIUzI1NiIs...",
  "completed_at": "2026-08-27T20:36:30Z"
}
```

`passed` is `true` when the pass rate meets the tier threshold. The
`verification_token` is a signed JWT (see `docs/decorators.md` for how to
verify it downstream).

---

## `GET /health`

AppManager standardized health contract.

**Response 200**

```json
{
  "status": "healthy",
  "app_slug": "ai-captcha",
  "version": "1.0.0",
  "checks": {"database": "ok", "puzzle_engine": "ok"},
  "timestamp": "2026-08-27T20:36:26Z"
}
```

---

# Embed (iframe widget) API

The reCAPTCHA-style embed endpoints. Base URL is the same (`/api` standalone,
`/apps/ai-captcha/api` under AppManager). The admin endpoints require the
`EMBED_ADMIN_TOKEN` bearer token; the session endpoints are called same-origin
by the iframe.

## `GET /embed`

Serve the iframe challenge page. Requires `?sitekey=…&origin=…` (and optional
`?tier=`). The origin must be registered on the site, otherwise the page
refuses to render and emits no `frame-ancestors` header for that origin.

**Errors**

- `400 invalid_sitekey` — unknown or disabled sitekey.
- `400 invalid_tier` — tier not in easy/medium/hard.
- `403 origin_not_allowed` — origin not registered for this sitekey.

## `POST /api/siteverify`

Verify a challenge token. Called by the host **backend** with the secretkey.

**Request (form or JSON)**

```json
{
  "secretkey": "YOUR_SECRETKEY",
  "response": "<token>",
  "remoteip": "1.2.3.4",
  "sitekey": "optional-hint"
}
```

**Response 200** (reCAPTCHA-shaped)

```json
{
  "success": true,
  "challenge_ts": 1724877386,
  "hostname": "My Site",
  "sitekey": "...",
  "tier": "medium",
  "error-codes": []
}
```

**Errors / failure codes** (`success: false` with `error-codes`)

- `missing-input` — no secretkey or token.
- `rate-limited` — per-secretkey rate limit hit (`429`).
- `invalid-secretkey` — unknown or disabled secretkey.
- `sitekey-mismatch` — token bound to a different sitekey.
- `invalid-token` — bad signature / expired.
- `timeout-or-duplicate` — token replayed (single-use `jti` consumed).

## Admin endpoints (require `Authorization: Bearer $EMBED_ADMIN_TOKEN`)

### `POST /api/embed/sites`

Create an embed site. Returns the `sitekey` + `secretkey` (shown once).

**Request**

```json
{ "name": "My Site", "allowed_origins": ["https://example.com"] }
```

**Response 201**

```json
{ "sitekey": "...", "secretkey": "...", "name": "My Site", "allowed_origins": ["https://example.com"] }
```

### `GET /api/embed/sites`

List all embed sites.

### `DELETE /api/embed/sites/<sitekey>`

Delete a site. **Response 200** `{ "deleted": "<sitekey>" }`.

### `PUT /api/embed/sites/<sitekey>/origins`

Set allowed origins. **Request** `{ "allowed_origins": ["https://example.com"] }`.

### `PUT /api/embed/sites/<sitekey>/enabled`

Enable/disable a site. **Request** `{ "enabled": true }`.

### `POST /api/embed/demo-site`

Create a throwaway demo site (no admin token needed; rate-limited).
**Request** `{ "origin": "https://example.com" }`.

## Embed session API (same-origin, used by the iframe)

### `POST /api/embed/start`

Start an embed challenge bound to a sitekey.

**Request** `{ "sitekey": "...", "origin": "https://example.com", "tier": "medium" }`

**Response 201** — same shape as `POST /api/start` (session + current puzzle).

### `GET /api/embed/session/<id>`

Current puzzle for an embed session. Pass `?sitekey=` to bind.

### `POST /api/embed/session/<id>/answer`

Submit an answer. **Request** `{ "answer": "...", "sitekey": "..." }`.

### `GET /api/embed/session/<id>/result`

Final result + verification token. Pass `?sitekey=` to bind.
