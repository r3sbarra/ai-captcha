# AI CAPTCHA — Gap Analysis vs. Comparable Mature Open-Source Flask/Python Projects

**Date:** 2026-08-27
**Scope:** Comparison of `/home/richard/.openclaw/workspace/ai-captcha/` against the scaffolding and hardening typically shipped by polished, pip-installable open-source Flask security/verification services (mature CAPTCHA/challenge services, token-issuing APIs, and production Flask packages).

**Method:** All findings grounded in actual project files (`pyproject.toml`, `README.md`, `ai_captcha/app.py`, `ai_captcha/decorators.py`, `ai_captcha/utils/tokens.py`, `ai_captcha/engine/session.py`, `ai_captcha/config.py`, `ai_captcha/routes/*`, `webui/*`, `tests/*`). Nothing is listed as missing that is actually present.

**What the project already HAS (so it is not re-listed as missing):**
pytest suite + `pytest-cov` wiring (term-missing report, no threshold), `flask>=3.0`/`pyjwt>=2.8` deps with lower bounds, extras (`webui`, `dev`), Python 3.10–3.12 classifiers, project URLs, setuptools package-data declarations, entry points + Flask command, README with config table, `Dockerfile` + `gunicorn.conf.py` under `webui/`, `/health` endpoint, MIT license *declared in metadata*, docs set, examples dir, model allowlist gating, token-hash-based log redaction.

---

## 1. Project Hygiene

| Priority | Item | Rationale |
|---|---|---|
| HIGH | **`.gitignore`** | Absent entirely — `.coverage`, `.pytest_cache/`, `__pycache__/`, `.venv/`, `instance/ai_captcha.db`, and `ai_captcha.egg-info/` are all sitting in the worktree and would be committed on `git init && git add -A`. |
| HIGH | **`LICENSE` file** | `pyproject.toml` declares `license = {text = "MIT"}` but no `LICENSE`/`LICENSE.txt` file exists; PyPI and corporate consumers expect the full text file (also modern packaging prefers `license = "MIT"` SPDX + `license-files`). |
| HIGH | **CI (GitHub Actions etc.)** | No `.github/workflows/` — no automated test run on push/PR; the single biggest credibility gap for a pip-installable package. |
| MEDIUM | **`CHANGELOG.md`** | Version is already split (`0.0.1` in pyproject vs `1.0.0` in `__init__.py`) with no record of what changed. |
| MEDIUM | **`CONTRIBUTING.md`** | Project advertises "add a new puzzle type by dropping in a file" — exactly the kind of extension point that needs contributor docs. |
| MEDIUM | **Version drift between `pyproject.toml` (0.0.1) and `ai_captcha/__init__.py` (1.0.0)** | Two sources of truth; `/health` reports `__version__` (1.0.0) while a wheel would install as 0.0.1. Use `importlib.metadata.version` or a single-source pattern. |
| MEDIUM | **Formatter/linter config (ruff/black)** | No tool config in `pyproject.toml`; no `[tool.ruff]`/`[tool.black]` sections at all. |
| MEDIUM | **Type checking (mypy/pyright)** | Codebase is already annotated (`str | None`, `dict[str,int]`); a strict-optional mypy pass would catch real bugs such as the `sign_token` defect below. |
| MEDIUM | **pre-commit hooks** | No `.pre-commit-config.yaml`; natural fit once black/ruff are adopted. |
| LOW | **`SECURITY.md`** | No vulnerability-disclosure policy — mildly embarrassing for a security-adjacent product. |
| LOW | **Issue/PR templates, CODE_OF_CONDUCT** | Nice-to-have for a young single-author project. |
| LOW | **Makefile/Taskfile, tox/nox** | `tasks.py` exists but is AppManager cron, not task running; a one-shot `make test` / tox matrix eases contributor onboarding. |
| LOW | **README badges** (CI, PyPI version, coverage, license) | Cosmetic but expected on a polished project landing page. |
| LOW | **Pinned `requirements.txt`** | Contains only the 3 unpinned runtime deps (dev deps live only as extras); either pin it (it's referenced by the Dockerfile!) or generate a lockfile. |

## 2. Packaging

| Priority | Item | Rationale |
|---|---|---|
| HIGH | **`MANIFEST.in`** | `package-data` covers templates/static, but `MANIFEST.in` is missing for sdist completeness — `docs/`, `examples/`, `webui/`, `README.md` assets are not guaranteed into the sdist; `docs/img/*.jpg/*.svg` (referenced by README) definitely aren't in `package-data`. |
| HIGH | **Dockerfile installs unpinned `requirements.txt`** | Image builds are non-reproducible; lock or pin. |
| MEDIUM | **Dev-secret defaults baked into package** | `SECRET_KEY="ai-captcha-dev-secret-change-me"` and `TOKEN_SECRET="token-signing-secret"` ship as silent defaults in `config.py` and as fallback `"token-signing-secret"` inline in `decorators.py` — a deployed instance that forgets env vars is forgeable by anyone who read the source. Mature packages fail loudly in non-debug mode. |
| MEDIUM | **`SESSION_TYPE="filesystem"` config keys with no Flask-Session dependency** | Dead config surface: no `flask-session` in deps or extras, and the DB (SQLAlchemy) is the actual session store — misleading to operators. |
| LOW | **PyPI metadata polish** | Version `0.0.1` + `Development Status :: 3 - Alpha` contradicts the `1.0.0` `__version__`; no `Changelog`/`Documentation` links in `[project.urls]`; no Python 3.13 classifier. |
| LOW | **`requires-python` floor check** | `>=3.10` is fine, but nothing in CI validates the floor (`str \| None` syntax enforces 3.10 — intentional). |

## 3. Testing / QA

| Priority | Item | Rationale |
|---|---|---|
| HIGH | **No end-to-end test of a passing run** | Latent crash bug: `SessionManager._issue_token` calls `sign_token(payload)` **without the required positional `secret`** (`tokens.py:10`; `session.py:215`). Any `passed=True` run raises `TypeError` at runtime. No test covers pass→token issue→verify. Fix the call and add the test. |
| HIGH | **Coverage threshold** | `pytest-cov` is wired (`--cov-report=term-missing`) but no `--cov-fail-under`/`fail_under` — coverage can silently rot. |
| HIGH | **CI test matrix (Python 3.10/3.11/3.12)** | Classifiers claim three versions; nothing tests them. |
| MEDIUM | **Benchmark/performance harness** | This project's whole premise is a timing oracle for AI capability — yet there's no benchmark script measuring solve rates/latency per model, no seed corpus stability checks, and no regression suite ensuring puzzles stay machine-solvable-but-human-hard across edits. |
| MEDIUM | **Puzzle answer-corpus leak checks / determinism tests** | No property-based tests (hypothesis) validating that generated puzzles always have verifiable answers across seeds and tiers; for a benchmark suite, puzzle integrity *is* the product. |
| LOW | **Load tests** (locust/k6) | SQLite-backed session store + per-request DB hits will bottleneck; no numbers exist. |
| LOW | **Security-focused tests** | No tests asserting expired-token rejection edge cases, tampered-JWT rejection at decorator level (exists implicitly), or timer-enforcement under clock skew. |

## 4. Ops / Deployment

| Priority | Item | Rationale |
|---|---|---|
| HIGH | **Rate limiting** | None anywhere (no flask-limiter, no app-level throttle). `/api/start`, `/api/answer` are unauthenticated and DB-writing; one client can exhaust timers/DB rows. For a verification service this is existential. |
| HIGH | **Health check is static** | `/health` hardcodes `"database": "ok"` without probing the DB or engine — a broken instance reports healthy. |
| MEDIUM | **Graceful shutdown / worker lifecycle** | `gunicorn.conf.py` lacks `graceful_timeout`, `max_requests`/`max_requests_jitter`, and (critically) in-process `SessionManager()` state interacts dangerously with `workers = 2`+ (blueprint-level `_manager = SessionManager()` is per-worker — fine because state lives in DB, but nothing documents this constraint). |
| MEDIUM | **Structured logging / observability** | Logging hooks exist but emit plain text to stdout/file; no JSON formatter option, no OpenTelemetry/Prometheus metrics endpoint (session counts, pass rates, token issues are natural metrics for an oracle service). |
| MEDIUM | **Reverse-proxy guidance** | README/AppManager docs give no nginx/Caddy snippet, no `ProxyFix`/trusted-proxy note despite `request.remote_addr` being used as `client_id` (always 127.0.0.1 behind a proxy → per-IP controls impossible). |
| LOW | **docker-compose.yml, systemd unit** | Only a bare Dockerfile; no compose with a real DB/redis, no systemd example. |
| LOW | **Runtime pinning in Dockerfile** | Uses `python:3.12-slim` + unpinned requirements (see Packaging). |

## 5. Security Hardening (token/verification-service specific)

| Priority | Item | Rationale |
|---|---|---|
| HIGH | **Replay protection on verification tokens** | Tokens carry no `jti`, no nonce, and no used-token store; the same JWT can be replayed forever within its 24 h TTL against any `@ai_captcha_required` endpoint, across all consumers. Mature CAPTCHA services (reCAPTCHA, hCaptcha) are single-use or at least nonce-tracked. |
| HIGH | **Per-IP / per-model throttling on challenge start & answer** | No counter on `/api/start` or answer attempts; an attacker can brute-force puzzle answers with unlimited submissions (`submit_answer` has no attempt cap beyond the puzzle count) or farm unlimited sessions/tokens. |
| HIGH | **JWT secret hard-fail & rotation** | See Packaging: silently-forgeable default `TOKEN_SECRET`; no key-id (`kid`) or keyring for rotation; `TOKEN_TTL_HOURS=24` with no revocation list. |
| MEDIUM | **Dev `SECRET_KEY` + query-param token transport** | Tokens accepted via `?captcha_token=` query param (`decorators.py`) → leaks into access logs, browser history, referer headers; should be header/body-only or at least documented as dev-only. |
| MEDIUM | **Security response headers** | No CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy on any blueprint (only playful `X-Robot-Whisper`/`X-Synthetic-Sentience`). The web UI sets no headers at all. |
| MEDIUM | **CSRF posture undocumented/unhandled** | All state-changing routes are JSON API (arguably CSRF-safe), but the form in `index.html` POSTs via fetch without any CSRF discussion; if cookie-based auth is ever layered on, this becomes live. At minimum document the posture; Flask-WTF absent. |
| MEDIUM | **SAST / dependency scanning** | No bandit config, no pip-audit/Dependabot/Renovate, no secret-scan (gitleaks) — trivially added to the (also missing) CI. |
| MEDIUM | **Session ID bearer semantics** | `GET /api/session/<id>` and `/result` return the full verification token to *anyone holding the UUID session id* — no binding to `client_id`/origin. If a session id leaks (logs, screenshots), the token is public. Constant-time comparison is moot here (JWT lib handles that) but possession semantics deserve hardening. |
| LOW | **`hs256` only, no asymmetric option** | Downstream verifiers must share the symmetric secret; offering EdDSA/RS256 with a public JWKS endpoint (like mature verification services) removes that coupling. |
| LOW | **`.well-known/security.txt`** | No security contact endpoint; robots/llms/sitemap exist but security.txt does not. |
| LOW | **Server clock-skew leeway in JWT decode** | `jwt.decode` called without `leeway`; harmless now, but documented leeway avoids flaky verification across skewed hosts. |

---

## Quick Verdict

**The product code is real and unusually complete** (decorators, timers, tier gating, embedding API, telemetry bridge, health route, Dockerfile, docs) — but the project is missing essentially the entire **repository/packaging shell** (gitignore, LICENSE file, CI, lint/type/format tooling, changelog) and several **non-negotiables for a verification service** (rate limiting, replay protection, real health probes, no-forgeable-default secrets, passing-run e2e test that would have caught the `sign_token` crash).

Highest-leverage fixes in order:
1. Fix `sign_token(payload)` → pass `secret` (+ e2e passing-run test). **(bug)**
2. `.gitignore` + `LICENSE` + basic CI (pytest across 3.10–3.12, ruff, mypy).
3. Rate limiting on `/api/start` + `/answer` (flask-limiter) and `ProxyFix` note.
4. Token replay protection (`jti` allowlist-once or per-consumer nonce) & secret-rotation docs.
5. Resolve version drift (0.0.1 vs 1.0.0) and add `MANIFEST.in`.
6. Fail loudly when `TOKEN_SECRET`/`SECRET_KEY` are defaults outside debug mode.
7. Real `/health` DB probe + security headers middleware.
