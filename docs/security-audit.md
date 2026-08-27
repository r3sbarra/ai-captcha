# AI CAPTCHA — Security Audit Findings

Date: 2026-08-27. Performed by main (Ai) with bandit 1.9.4 SAST + pip-audit + manual review.

## Tooling used
- `bandit -r ai_captcha/` (SAST) — 42 findings, breakdown below.
- `pip-audit` — only flags the dev `pip 24.0` package itself, NOT any app runtime dep.
- Manual review of tokens.py, decorators.py, api.py, config.py, engine, views.py.

---

## CRITICAL

### C1 — Forgeable verification tokens via hardcoded default secret (PROVEN exploitable)
- `config.py:48` — `TOKEN_SECRET: str = os.getenv("AIC_TOKEN_SECRET", "token-signing-secret")`
- `config.py:26` — `SECRET_KEY` defaults to `"ai-captcha-dev-secret-change-me"`.
- The running AppManager instance has **no** `AIC_TOKEN_SECRET` / `AIC_SECRET_KEY` env set
  (verified: no AIC_* vars in the running process environ).
- **Proof:** I minted a hard-tier JWT (`tier=hard, solved=5, total=5`) signed with the default
  secret and the app's own `verify_token()` accepted it. Any attacker who reads the source
  (it's a public pip package) can forge tokens that bypass `ai_captcha_required` and `tier_gate("hard")`.
- **Fix:** fail-closed — refuse to start (or log a loud warning) when secrets equal the defaults;
  require env-provided secrets in production/AppManager. Generate strong secrets at install.

## HIGH

### H1 — Default token secret is too short (20 bytes < 32)
- pyjwt emits `InsecureKeyLengthWarning` (RFC 7518 §3.2 requires ≥256-bit HMAC keys).
- Same root cause as C1: the default `"token-signing-secret"` is 20 bytes.
- Fix alongside C1: enforce ≥32-byte secrets.

### H2 — No rate limiting anywhere
- No throttle/limit on `/api/start`, `/api/session/<id>/answer`, `/api/session/<id>/result`.
- As a benchmark oracle this is trivially spammable: an attacker can brute-force answers,
  exhaust server CPU with puzzle generation, or DoS via mass session creation.
- `bandit B311` also flags `random` (non-crypto) for puzzle gen — acceptable for a benchmark,
  but combined with no rate limit, answer-guessing at scale is feasible.
- **Fix:** per-IP + per-session rate limiting on the API blueprint (simple token bucket, stdlib
  or flask-limiter). Note: the 410-expiry path and server-authoritative timer already limit
  brute-force *per session*, but nothing stops creating many sessions.

## MEDIUM

### M1 — No security headers
- Only `after_request` in api.py injects the robot easter-egg headers; no
  `X-Content-Type-Options: nosniff`, `X-Frame-Options`, `Content-Security-Policy`,
  `Referrer-Policy`, or `Strict-Transport-Security`.
- **Fix:** add an after_request hook (or AppManager middleware) emitting a baseline header set.

### M2 — No CSRF protection on the web form
- `index.html` posts JSON to `/api/start`. No cookies are used for auth in the standalone flow,
  so the practical CSRF surface is low, but if the app is ever embedded where it *does* share
  cookies, the JSON POST lacks CSRF tokens.
- **Fix:** document the risk; optionally add Flask-WTF / CSRFProtect when embedding with cookies.

### M3 — Verification tokens have no nonce/revocation (`jti`)
- `tokens.py` issues `iat`/`exp`/`iss` but no `jti` (unique id), so a leaked token is valid for
  the full 24h TTL with no way to revoke.
- **Fix:** add a `jti` claim + optional server-side denylist for revocation; document the
  trade-off (stateless HMAC vs revocability).

### M4 — `exec` in code_execution puzzle (sandbox is not a real boundary)
- `code_execution.py:24` runs `exec(code, {"__builtins__": {}}, {})`.
- **Currently SAFE** because input is always server-generated (`_gen_easy/medium/hard`); client
  answer strings never reach `exec`. The `{"__builtins__": {}}` sandbox is escapable via object
  introspection, so it is a mitigation, not a boundary.
- **Fix:** keep a hard invariant that `_run()` only ever receives internally-generated code; add
  a comment + test asserting no client input flows into `exec`. Do not document the sandbox as secure.

## LOW

### L1 — `pip 24.0` in dev venv has known vulns
- pip-audit flags 7 CVEs in pip 24.0 (fix: ≥26.x). Dev-only, not shipped. Upgrade the venv pip.

### L2 — `B105` false positives
- Whisper text containing the word "password" and the header name `X-AI-CAPTCHA-TOKEN` flagged.
  Not real hardcoded credentials.

### L3 — `B104` bind 0.0.0.0 (intentional)
- `app.py`/`cli.py` default `--host 0.0.0.0` for AppManager/LAN. Intentional; ensure a reverse
  proxy or firewall guards it. Not a code defect.

### L4 — Non-constant-time answer comparison
- `base.py` and puzzle `validate()` use `==` for answers. Answers are short server-side strings,
  not remote secrets, so timing attacks aren't meaningful here. Low priority; could switch to
  `hmac.compare_digest` for hygiene.

---

## Verdict
The project is **sound by design** for a benchmark oracle (server-authoritative timers, answers
never sent to client, opaque pass/fail, no self-reported model IDs, signed tokens, tier gating).
The one genuinely critical, **proven-exploitable** issue is C1 (forgeable tokens from the
default secret in the live AppManager deploy). Fix C1 (+ H1) first — it's a one-line fail-closed
guard plus real secrets in the deploy env. H2 (rate limiting) is the next most impactful.
