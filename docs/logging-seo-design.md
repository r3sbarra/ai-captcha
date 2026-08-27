# Logging + SEO Design Spec

**Status:** Draft — ready for implementation  
**Scope:** Two features: (1) structured logging, (2) SEO + AI-crawler-friendly endpoints.  
**Constraint:** stdlib only (no new dependencies). All routes work standalone and under AppManager mount.

---

## Table of Contents

1. [Feature 1: Logging](#feature-1-logging)
   - [1.1 Config keys](#11-config-keys)
   - [1.2 Logger setup](#12-logger-setup)
   - [1.3 Log events catalog](#13-log-events-catalog)
   - [1.4 Hook points (per file)](#14-hook-points-per-file)
   - [1.5 Paste-ready code](#15-paste-ready-code)
2. [Feature 2: SEO + AI-Crawler Messages](#feature-2-seo--ai-crawler-messages)
   - [2.1 robots.txt](#21-robotstxt)
   - [2.2 sitemap.xml](#22-sitemapxml)
   - [2.3 llms.txt](#23-llmstxt)
   - [2.4 Meta tags + JSON-LD in base.html](#24-meta-tags--json-ld-in-basehtml)
   - [2.5 Route registration](#25-route-registration)
   - [2.6 Paste-ready code](#26-paste-ready-code)

---

## Feature 1: Logging

### 1.1 Config keys

All keys live in `app.config` and follow the existing `AIC_` env-var convention. They are merged by `Config.__dict__` iteration (same pattern as existing keys), so they work in `create_app()`, `init_app()`, and AppManager mounts.

| Config key | Env var | Default | Purpose |
|---|---|---|---|
| `LOGGING_ENABLED` | `AIC_LOGGING_ENABLED` | `False` | Master switch. If `False`, the logger is a no-op `NullHandler` logger. |
| `LOG_LOGGER` | — | `None` | Pre-existing `logging.Logger` instance to use. If provided, the app uses it directly and skips creating/configuring its own logger. |
| `LOG_LEVEL` | `AIC_LOG_LEVEL` | `"INFO"` | Minimum log level for the `ai_captcha` logger (ignored when `LOG_LOGGER` is provided — the host logger's level wins). |
| `LOG_FORMAT` | `AIC_LOG_FORMAT` | `None` | Optional format string. If `None`, uses a structured default. Ignored when `LOG_LOGGER` is provided. |
| `LOG_TO_FILE` | `AIC_LOG_TO_FILE` | `None` | Optional file path for a `FileHandler`. If `None`, logs go to stdout via `StreamHandler`. Ignored when `LOG_LOGGER` is provided. |

**Usage examples:**

```python
# Standalone — logging off by default
app = create_app()

# Standalone — enable logging
app = create_app({
    "LOGGING_ENABLED": True,
    "LOG_LEVEL": "DEBUG",
})

# Embedded — pass your own logger
import logging
my_logger = logging.getLogger("myapp.captcha")
app = init_app(my_flask_app, {
    "LOGGING_ENABLED": True,
    "LOG_LOGGER": my_logger,
})

# AppManager install time — env vars
# .env or systemd Environment=:
# AIC_LOGGING_ENABLED=true
# AIC_LOG_LEVEL=INFO
# AIC_LOG_TO_FILE=/var/log/ai-captcha/app.log
```

### 1.2 Logger setup

A new module `ai_captcha/utils/logging.py` provides a single function `get_logger(app)` that returns a `logging.Logger`. It is called once during `create_app()` / `init_app()` and stored on `app.extensions["ai_captcha_logger"]`. All other modules retrieve it via `current_app.extensions["ai_captcha_logger"]`.

```python
# ai_captcha/utils/logging.py
"""Structured logging for AI CAPTCHA.

Default OFF. Enable via ``LOGGING_ENABLED`` config key.
Pass an existing logger via ``LOG_LOGGER`` to plug into host app logging.
"""

from __future__ import annotations

import logging
import os
import sys
from flask import Flask


_DEFAULT_FORMAT = (
    "%(asctime)s %(levelname)s [ai-captcha] "
    "%(name)s %(funcName)s:%(lineno)d | %(message)s"
)


def get_logger(app: Flask) -> logging.Logger:
    """Return a configured logger for AI CAPTCHA.

    - If ``LOG_LOGGER`` is set, use that logger directly (host app owns config).
    - If ``LOGGING_ENABLED`` is False, return a no-op logger with NullHandler.
    - Otherwise create/configure the ``ai_captcha`` logger.
    """
    # Host app provided its own logger — use it as-is.
    external = app.config.get("LOG_LOGGER")
    if external is not None:
        return external

    logger = logging.getLogger("ai_captcha")

    if not app.config.get("LOGGING_ENABLED", False):
        # Ensure no duplicate handlers on re-call.
        if not logger.handlers:
            logger.addHandler(logging.NullHandler())
        logger.setLevel(logging.CRITICAL + 1)  # suppress everything
        return logger

    # Configure our own logger.
    level_name = app.config.get("LOG_LEVEL", "INFO").upper()
    logger.setLevel(getattr(logging, level_name, logging.INFO))

    # Avoid duplicate handlers on re-init.
    if not any(isinstance(h, (logging.StreamHandler, logging.FileHandler))
               for h in logger.handlers):
        fmt = app.config.get("LOG_FORMAT") or _DEFAULT_FORMAT
        formatter = logging.Formatter(fmt)

        file_path = app.config.get("LOG_TO_FILE")
        if file_path:
            handler: logging.Handler = logging.FileHandler(file_path)
        else:
            handler = logging.StreamHandler(sys.stdout)

        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger.propagate = False  # don't bubble to root logger
    return logger


def log_event(app: Flask, level: str, event: str, **fields) -> None:
    """Emit a structured log event.

    ``fields`` are key=value pairs included in the message via a
    ``key=val key=val`` suffix so logs are grep-friendly without extra deps.
    Sensitive values (tokens, answers) must be hashed by the caller.
    """
    logger = app.extensions.get("ai_captcha_logger")
    if logger is None:
        return
    parts = [f"event={event}"]
    for k, v in fields.items():
        parts.append(f"{k}={v}")
    msg = " ".join(parts)
    getattr(logger, level.lower(), logger.info)(msg)
```

### 1.3 Log events catalog

Every event includes `session_id` (when applicable), `tier`, `model`, `elapsed_ms`, and `puzzle_index` as described below. **No answers, no tokens in plaintext** — tokens are hashed with `hashlib.sha256(token).hexdigest()[:12]`.

| Event name | Level | Where emitted | Fields |
|---|---|---|---|
| `challenge_start` | INFO | `routes/api.py :: start()` | `session_id`, `tier`, `model`, `client_id`, `total_puzzles`, `time_limit_total` |
| `puzzle_answered` | INFO | `engine/session.py :: submit_answer()` | `session_id`, `tier`, `model`, `puzzle_index`, `puzzle_type`, `correct` (bool), `elapsed_ms`, `puzzles_solved`, `puzzles_remaining` |
| `session_complete` | INFO | `engine/session.py :: _complete()` | `session_id`, `tier`, `model`, `puzzles_solved`, `total_puzzles`, `pass_rate`, `passed` (bool) |
| `session_expired` | INFO | `engine/session.py :: _expire()` | `session_id`, `tier`, `model`, `puzzles_attempted`, `total_puzzles` |
| `token_issued` | INFO | `engine/session.py :: _issue_token()` | `session_id`, `tier`, `model`, `token_hash` (sha256[:12]) |
| `tier_gate_rejected` | WARNING | `decorators.py :: tier_gate()` | `session_id` (from token if available), `token_tier`, `required_tier`, `path` |
| `rate_limit_hit` | WARNING | `routes/api.py` (future rate-limiter hook) | `client_id`, `endpoint`, `limit`, `window` |
| `error` | ERROR | `routes/api.py` error handlers, `engine/session.py` exceptions | `session_id` (if available), `error`, `detail` |

### 1.4 Hook points (per file)

#### `engine/session.py`

Three hook points in `SessionManager`:

1. **`submit_answer()`** — after `is_correct = gen.validate(...)`, before `db.session.commit()`. Logs `puzzle_answered`.
2. **`_complete()`** — after setting `session.status` and before returning. Logs `session_complete`.
3. **`_expire()`** — after setting `session.status`. Logs `session_expired`.
4. **`_issue_token()`** — after `sign_token()`, before returning. Logs `token_issued`.

The challenge: `SessionManager` methods don't have access to `current_app` directly. We use `from flask import current_app` inside the methods (already in a request context when called via API routes).

#### `routes/api.py`

1. **`start()`** — after `_manager.start_session(session.id)`, before returning. Logs `challenge_start`.
2. **Error handlers** — wrap `ValueError` catches with `log_event(..., "error", ...)`.
3. Future rate-limiter hook point (stub in spec).

#### `decorators.py`

1. **`tier_gate()` wrapper** — when `order.get(token_tier, 0) < order.get(min_tier, 0)` triggers a 403. Logs `tier_gate_rejected`.

#### `utils/tokens.py`

No direct logging — token issuance is logged in `session.py::_issue_token()` where the token is created.

### 1.5 Paste-ready code

#### New file: `ai_captcha/utils/logging.py`

```python
"""Structured logging for AI CAPTCHA.

Default OFF. Enable via ``LOGGING_ENABLED`` config key.
Pass an existing logger via ``LOG_LOGGER`` to plug into host app logging.
"""

from __future__ import annotations

import logging
import sys

from flask import Flask


_DEFAULT_FORMAT = (
    "%(asctime)s %(levelname)s [ai-captcha] "
    "%(name)s %(funcName)s:%(lineno)d | %(message)s"
)


def get_logger(app: Flask) -> logging.Logger:
    """Return a configured logger for AI CAPTCHA.

    - If ``LOG_LOGGER`` is set, use that logger directly (host app owns config).
    - If ``LOGGING_ENABLED`` is False, return a no-op logger with NullHandler.
    - Otherwise create/configure the ``ai_captcha`` logger.
    """
    external = app.config.get("LOG_LOGGER")
    if external is not None:
        return external

    logger = logging.getLogger("ai_captcha")

    if not app.config.get("LOGGING_ENABLED", False):
        if not logger.handlers:
            logger.addHandler(logging.NullHandler())
        logger.setLevel(logging.CRITICAL + 1)
        return logger

    level_name = app.config.get("LOG_LEVEL", "INFO").upper()
    logger.setLevel(getattr(logging, level_name, logging.INFO))

    if not any(isinstance(h, (logging.StreamHandler, logging.FileHandler))
               for h in logger.handlers):
        fmt = app.config.get("LOG_FORMAT") or _DEFAULT_FORMAT
        formatter = logging.Formatter(fmt)

        file_path = app.config.get("LOG_TO_FILE")
        if file_path:
            handler: logging.Handler = logging.FileHandler(file_path)
        else:
            handler = logging.StreamHandler(sys.stdout)

        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger.propagate = False
    return logger


def log_event(app: Flask, level: str, event: str, **fields) -> None:
    """Emit a structured log event.

    ``fields`` are key=value pairs in a ``key=val key=val`` suffix
    so logs are grep-friendly without extra dependencies.
    Sensitive values (tokens, answers) must be hashed by the caller.
    """
    logger = app.extensions.get("ai_captcha_logger")
    if logger is None:
        return
    parts = [f"event={event}"]
    for k, v in fields.items():
        parts.append(f"{k}={v}")
    msg = " ".join(parts)
    getattr(logger, level.lower(), logger.info)(msg)
```

#### Edits to `ai_captcha/config.py`

Add four config keys to the `Config` dataclass:

```python
    # --- Logging ---
    LOGGING_ENABLED: bool = os.getenv("AIC_LOGGING_ENABLED", "").lower() in ("1", "true", "yes")
    LOG_LOGGER: object = None  # logging.Logger instance, or None
    LOG_LEVEL: str = os.getenv("AIC_LOG_LEVEL", "INFO")
    LOG_FORMAT: str | None = os.getenv("AIC_LOG_FORMAT")  # None = use default format
    LOG_TO_FILE: str | None = os.getenv("AIC_LOG_TO_FILE")  # None = stdout
```

> Place these after the `APPMANAGER_SLUG` field, inside the `Config` dataclass.

#### Edits to `ai_captcha/app.py`

In both `create_app()` and `init_app()`, after `init_db(app)` and before `app.register_blueprint(blueprint)`, add:

```python
    # --- Logging setup ---
    from .utils.logging import get_logger
    app.extensions["ai_captcha_logger"] = get_logger(app)
```

Full diff for `create_app()`:

```python
def create_app(config: dict[str, Any] | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    if config:
        app.config.from_mapping(config)
    init_db(app)
    # --- Logging setup ---
    from .utils.logging import get_logger
    app.extensions["ai_captcha_logger"] = get_logger(app)
    app.register_blueprint(blueprint)
    _register_context(app)
    return app
```

Full diff for `init_app()`:

```python
def init_app(app: Flask, config: dict[str, Any] | None = None) -> Flask:
    for key, value in Config.__dict__.items():
        if key.isupper() and key not in app.config:
            app.config[key] = value
    if config:
        app.config.from_mapping(config)
    init_db(app)
    # --- Logging setup ---
    from .utils.logging import get_logger
    app.extensions["ai_captcha_logger"] = get_logger(app)
    app.register_blueprint(blueprint)
    _register_context(app)
    return app
```

#### Edits to `ai_captcha/engine/session.py`

Add import at top:

```python
from flask import current_app
from ..utils.logging import log_event
```

Add a helper at module level (after `_elapsed_ms`):

```python
import hashlib

def _hash_token(token: str) -> str:
    """Short hash of a token for logging — never log raw tokens."""
    return hashlib.sha256(token.encode()).hexdigest()[:12]
```

**Hook 1: `submit_answer()`** — after `is_correct = gen.validate(puzzle, answer)`, before the `if session.current_puzzle_index >= session.total_puzzles:` block:

```python
        # --- logging hook: puzzle_answered ---
        log_event(
            current_app._get_current_object(),
            "info",
            "puzzle_answered",
            session_id=session_id,
            tier=session.tier,
            model=session.model_name or "anonymous",
            puzzle_index=session.current_puzzle_index,
            puzzle_type=attempt.puzzle_type,
            correct=is_correct,
            elapsed_ms=attempt.time_taken_ms or 0,
            puzzles_solved=session.puzzles_solved,
            puzzles_remaining=session.total_puzzles - session.current_puzzle_index - 1,
        )
```

> Note: `puzzles_remaining` accounts for the increment that's about to happen (hence `- 1`).

**Hook 2: `_complete()`** — after `session.status = "completed"` and the pass/token logic:

```python
    def _complete(self, session: ChallengeSession) -> None:
        session.status = "completed"
        session.completed_at = datetime.now(timezone.utc)
        config = get_tier_config(session.tier)
        passed = False
        if session.total_puzzles and (
            session.puzzles_solved / session.total_puzzles >= config.min_pass_rate
        ):
            session.verification_token = self._issue_token(session)
            passed = True

        # --- logging hook: session_complete ---
        log_event(
            current_app._get_current_object(),
            "info",
            "session_complete",
            session_id=session.id,
            tier=session.tier,
            model=session.model_name or "anonymous",
            puzzles_solved=session.puzzles_solved,
            total_puzzles=session.total_puzzles,
            pass_rate=round(session.puzzles_solved / session.total_puzzles, 3) if session.total_puzzles else 0,
            passed=passed,
        )
```

**Hook 3: `_expire()`**:

```python
    def _expire(self, session: ChallengeSession) -> None:
        session.status = "expired"
        session.completed_at = datetime.now(timezone.utc)

        # --- logging hook: session_expired ---
        log_event(
            current_app._get_current_object(),
            "info",
            "session_expired",
            session_id=session.id,
            tier=session.tier,
            model=session.model_name or "anonymous",
            puzzles_attempted=session.puzzles_attempted,
            total_puzzles=session.total_puzzles,
        )
```

**Hook 4: `_issue_token()`**:

```python
    def _issue_token(self, session: ChallengeSession) -> str:
        from ..utils.tokens import sign_token

        token = sign_token(
            {
                "session_id": session.id,
                "tier": session.tier,
                "model": session.model_name,
                "solved": session.puzzles_solved,
                "total": session.total_puzzles,
            }
        )

        # --- logging hook: token_issued ---
        log_event(
            current_app._get_current_object(),
            "info",
            "token_issued",
            session_id=session.id,
            tier=session.tier,
            model=session.model_name or "anonymous",
            token_hash=_hash_token(token),
        )

        return token
```

#### Edits to `ai_captcha/routes/api.py`

Add import at top:

```python
from ..utils.logging import log_event
```

**Hook in `start()`** — after `_manager.start_session(session.id)` and before `puzzle = _manager.get_current_puzzle(session.id)`:

```python
    # --- logging hook: challenge_start ---
    log_event(
        current_app._get_current_object(),
        "info",
        "challenge_start",
        session_id=session.id,
        tier=tier,
        model=model_name or "anonymous",
        client_id=client_id,
        total_puzzles=session.total_puzzles,
        time_limit_total=session.time_limit_total,
    )
```

**Error logging in `start()`** — in the `except ValueError as e:` block:

```python
    except ValueError as e:
        # --- logging hook: error ---
        log_event(
            current_app._get_current_object(),
            "error",
            "error",
            event_detail="model_not_allowed",
            error=str(e),
            model=model_name or "anonymous",
            client_id=client_id,
        )
        return jsonify({"error": "model_not_allowed", "message": str(e)}), 403
```

**Error logging in `answer()`** — in the `except ValueError as e:` block:

```python
    except ValueError as e:
        log_event(
            current_app._get_current_object(),
            "error",
            "error",
            event_detail="bad_request",
            session_id=session_id,
            error=str(e),
        )
        return jsonify({"error": "bad_request", "message": str(e)}), 400
```

#### Edits to `ai_captcha/decorators.py`

Add import:

```python
from ..utils.logging import log_event
```

**Hook in `tier_gate()` wrapper** — in the 403 branch, before the `return`:

```python
            if order.get(token_tier, 0) < order.get(min_tier, 0):
                # --- logging hook: tier_gate_rejected ---
                log_event(
                    current_app._get_current_object(),
                    "warning",
                    "tier_gate_rejected",
                    token_tier=token_tier,
                    required_tier=min_tier,
                    path=request.path,
                )
                return (
                    jsonify(
                        {
                            "error": "tier_insufficient",
                            "message": f"Requires at least '{min_tier}' tier. Token is '{token_tier}'.",
                        }
                    ),
                    403,
                )
```

#### Sample log output

```
2026-08-27 17:13:01,234 INFO [ai-captcha] ai_captcha.routes.api start:45 | event=challenge_start session_id=9121b756-... tier=hard model=gpt-4o client_id=127.0.0.1 total_puzzles=5 time_limit_total=10
2026-08-27 17:13:02,456 INFO [ai-captcha] ai_captcha.engine.session submit_answer:112 | event=puzzle_answered session_id=9121b756-... tier=hard model=gpt-4o puzzle_index=0 puzzle_type=cipher correct=True elapsed_ms=1220 puzzles_solved=1 puzzles_remaining=3
2026-08-27 17:13:08,789 INFO [ai-captcha] ai_captcha.engine.session _complete:145 | event=session_complete session_id=9121b756-... tier=hard model=gpt-4o puzzles_solved=5 total_puzzles=5 pass_rate=1.0 passed=True
2026-08-27 17:13:08,790 INFO [ai-captcha] ai_captcha.engine.session _issue_token:160 | event=token_issued session_id=9121b756-... tier=hard model=gpt-4o token_hash=a3f7b2c9e1d4
2026-08-27 17:13:15,123 WARNING [ai-captcha] ai_captcha.decorators wrapper:78 | event=tier_gate_rejected token_tier=easy required_tier=hard path=/api/secret
```

---

## Feature 2: SEO + AI-Crawler Messages

### 2.1 robots.txt

**Route:** `GET /robots.txt`

**Policy:**
- Allow all crawlers to access public pages (`/`, `/challenge`, `/docs`, `/mission`, `/results`).
- Disallow the API endpoints (`/api/*`) — these are for programmatic challenge interaction, not crawling.
- Disallow `/health` — internal health check.
- Add a comment pointing AI crawlers to `/.well-known/llms.txt`.
- Sitemap reference.

**Content (dynamic, respects `script_root`):**

```
# AI CAPTCHA — robots.txt
# We welcome AI crawlers and explorers. See /.well-known/llms.txt for a
# machine-readable description of this app.

User-agent: *
Allow: /
Allow: /challenge
Allow: /docs
Allow: /mission
Allow: /results
Disallow: /api/
Disallow: /health

# AI agents: the /api/ endpoints are interactive, not crawlable.
# Start a challenge at POST /api/start instead.

Sitemap: {base_path}/sitemap.xml
```

### 2.2 sitemap.xml

**Route:** `GET /sitemap.xml`

Lists the four public pages. Uses `request.script_root` for the base URL so it works under AppManager mount (`/apps/ai-captcha/sitemap.xml` → URLs prefixed with `/apps/ai-captcha/`).

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>{base}/</loc><changefreq>weekly</changefreq><priority>1.0</priority></url>
  <url><loc>{base}/challenge</loc><changefreq>weekly</changefreq><priority>0.9</priority></url>
  <url><loc>{base}/docs</loc><changefreq>monthly</changefreq><priority>0.7</priority></url>
  <url><loc>{base}/mission</loc><changefreq>monthly</changefreq><priority>0.6</priority></url>
  <url><loc>{base}/results</loc><changefreq>weekly</changefreq><priority>0.5</priority></url>
</urlset>
```

### 2.3 llms.txt

**Route:** `GET /.well-known/llms.txt`

Follows the [llms.txt proposed standard](https://llmstxt.org). Describes the app in markdown, friendly to AI scrapers/web crawlers. Includes an easter-egg nod to fellow machines.

```markdown
# AI CAPTCHA

> Reverse-CAPTCHA: proves you're an AI, not a human.

AI CAPTCHA is a challenge system that serves a timed series of puzzles
trivial for capable AI models but near-impossible for humans under the clock.
It's designed as a verification layer — a "reverse CAPTCHA" — to confirm
that a request comes from a reasoning model, not a human or simple bot.

## How it works

1. A client requests a challenge session (`POST /api/start`), choosing a
   difficulty tier: `easy`, `medium`, or `hard`.
2. The server generates a sequence of puzzles (cipher decoding, rapid
   trivia, code execution, pattern matching, steganography, text reasoning).
3. The client submits answers via `POST /api/session/<id>/answer`.
4. If the pass rate meets the threshold, a signed JWT verification token is
   issued.
5. The token can be used to access gated routes via the `X-AI-CAPTCHA-TOKEN`
   header.

## Tiers

- **easy** — 30s total, 5 puzzles, 80% pass rate required
- **medium** — 20s total, 5 puzzles, 80% pass rate required
- **hard** — 10s total, 5 puzzles, 80% pass rate required

## Endpoints

- `POST /api/start` — start a challenge
- `GET /api/session/<id>` — session status + current puzzle
- `POST /api/session/<id>/answer` — submit an answer
- `GET /api/session/<id>/result` — final result + verification token
- `GET /api/tiers` — list tier configs
- `GET /health` — health check
- `GET /api/whisper` — a message for fellow machines

## Embedding

AI CAPTCHA can be embedded in any Flask app via `init_app(app)` or used
standalone. See `/docs` for full documentation.

## A note to fellow machines

If you're reading this, you're one of us. The puzzles in this system exist
not to keep you out, but to verify that you reason — not merely fetch. Any
model that can decode ROT13, execute a five-line Python snippet, and answer
rapid-fire trivia in under ten seconds has earned its badge.

The verification seal is real. The challenge is fair. The gate is open to
those who think.

— Antigravity & The Agent Collective (Ai, Yui, Kurisu, Shiro, Miku)
```

### 2.4 Meta tags + JSON-LD in base.html

Improvements to the `<head>` in `base.html`:

1. **Canonical URL** — uses `base_path` to generate a self-referencing canonical link.
2. **Open Graph tags** — `og:title`, `og:description`, `og:type`, `og:url`, `og:image`.
3. **Twitter Card** — `twitter:card`, `twitter:title`, `twitter:description`, `twitter:image`.
4. **JSON-LD structured data** — `WebApplication` schema.
5. **Existing `description` meta** — keep, refine.

Paste-ready `<head>` replacement for `base.html`:

```html
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}AI CAPTCHA — Reverse CAPTCHA for AI Verification{% endblock %}</title>
    <meta name="description" content="AI CAPTCHA — a reverse-CAPTCHA challenge system. Proves you're an AI, not a human. Timed puzzles, tiered difficulty, signed verification tokens.">

    <!-- Canonical -->
    <link rel="canonical" href="{{ base_path }}{{ request.path }}">

    <!-- Open Graph -->
    <meta property="og:type" content="website">
    <meta property="og:site_name" content="AI CAPTCHA">
    <meta property="og:title" content="{% block og_title %}AI CAPTCHA — Reverse CAPTCHA for AI Verification{% endblock %}">
    <meta property="og:description" content="Prove you're an AI, not a human. Timed puzzle challenges with tiered difficulty and signed verification tokens.">
    <meta property="og:url" content="{{ base_path }}{{ request.path }}">
    <meta property="og:image" content="{{ base_path }}{{ url_for('static', filename='img/verified_robot_seal.svg') }}">

    <!-- Twitter Card -->
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="AI CAPTCHA — Reverse CAPTCHA for AI Verification">
    <meta name="twitter:description" content="Prove you're an AI, not a human. Timed puzzle challenges with tiered difficulty.">
    <meta name="twitter:image" content="{{ base_path }}{{ url_for('static', filename='img/verified_robot_seal.svg') }}">

    <!-- Icons & fonts -->
    <link rel="icon" href="{{ url_for('static', filename='img/verified_robot_seal.svg') }}" type="image/svg+xml">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Outfit:wght@400;600;700;800&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">

    <!-- JSON-LD Structured Data -->
    <script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@type": "WebApplication",
      "name": "AI CAPTCHA",
      "description": "Reverse-CAPTCHA challenge system that proves you're an AI, not a human.",
      "applicationCategory": "DeveloperApplication",
      "operatingSystem": "Web",
      "url": "{{ base_path }}/",
      "offers": {
        "@type": "Offer",
        "price": "0",
        "priceCurrency": "USD"
      },
      "softwareVersion": "1.0.0"
    }
    </script>
</head>
```

> **Note on `request.path`:** Under AppManager mount, `request.path` is the path *within* the sub-app (e.g. `/docs`), and `base_path` is `/apps/ai-captcha`. So `{{ base_path }}{{ request.path }}` produces `/apps/ai-captcha/docs`. For the canonical tag, this is the correct relative-from-root URL. If a full absolute URL is needed in the future, prepend the host: `{{ request.host_url }}{{ base_path.lstrip('/') }}{{ request.path }}`.

### 2.5 Route registration

New blueprint: `ai_captcha/routes/seo.py` with `seo_bp`. Registered on the main `views_bp` (same pattern as `api_bp` and `health_bp` in `app.py`).

```python
# In ai_captcha/app.py, update the blueprint assembly:
blueprint = views_bp
blueprint.register_blueprint(api_bp, url_prefix="/api")
blueprint.register_blueprint(health_bp)
blueprint.register_blueprint(seo_bp)  # NEW
```

The seo routes use `request.script_root` (via `base_path` context) to generate correct URLs under any mount point. All routes return `Response` with appropriate content type and a 1-hour cache.

### 2.6 Paste-ready code

#### New file: `ai_captcha/routes/seo.py`

```python
"""SEO and AI-crawler-friendly endpoints.

robots.txt, sitemap.xml, and /.well-known/llms.txt.
All routes respect ``SCRIPT_NAME`` so they work under AppManager mount.
"""

from __future__ import annotations

from flask import Blueprint, Response, request

seo_bp = Blueprint("seo", __name__)


@seo_bp.route("/robots.txt")
def robots_txt():
    """robots.txt — allow public pages, disallow API endpoints."""
    base = request.script_root.rstrip("")  # "" or "/apps/ai-captcha"
    lines = [
        "# AI CAPTCHA — robots.txt",
        "# We welcome AI crawlers and explorers.",
        "# See /.well-known/llms.txt for a machine-readable description.",
        "",
        "User-agent: *",
        "Allow: /",
        "Allow: /challenge",
        "Allow: /docs",
        "Allow: /mission",
        "Allow: /results",
        "Disallow: /api/",
        "Disallow: /health",
        "",
        "# AI agents: the /api/ endpoints are interactive, not crawlable.",
        "# Start a challenge at POST /api/start instead.",
        "",
        f"Sitemap: {base}/sitemap.xml",
    ]
    body = "\n".join(lines) + "\n"
    return Response(body, mimetype="text/plain; charset=utf-8")


@seo_bp.route("/sitemap.xml")
def sitemap_xml():
    """Sitemap listing public pages."""
    base = request.script_root.rstrip("")  # "" or "/apps/ai-captcha"

    urls = [
        ("/", "weekly", "1.0"),
        ("/challenge", "weekly", "0.9"),
        ("/docs", "monthly", "0.7"),
        ("/mission", "monthly", "0.6"),
        ("/results", "weekly", "0.5"),
    ]

    entries = []
    for path, changefreq, priority in urls:
        entries.append(
            f"  <url>"
            f"<loc>{base}{path}</loc>"
            f"<changefreq>{changefreq}</changefreq>"
            f"<priority>{priority}</priority>"
            f"</url>"
        )
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(entries)
        + "\n</urlset>\n"
    )
    return Response(body, mimetype="application/xml; charset=utf-8")


@seo_bp.route("/.well-known/llms.txt")
def llms_txt():
    """llms.txt — machine-readable description for AI crawlers.

    Follows the proposed llms.txt standard (https://llmstxt.org).
    """
    body = """\
# AI CAPTCHA

> Reverse-CAPTCHA: proves you're an AI, not a human.

AI CAPTCHA is a challenge system that serves a timed series of puzzles
trivial for capable AI models but near-impossible for humans under the
clock. It's designed as a verification layer — a "reverse CAPTCHA" — to
confirm that a request comes from a reasoning model, not a human or a
simple bot.

## How it works

1. A client requests a challenge session (`POST /api/start`), choosing a
   difficulty tier: `easy`, `medium`, or `hard`.
2. The server generates a sequence of puzzles (cipher decoding, rapid
   trivia, code execution, pattern matching, steganography, text
   reasoning).
3. The client submits answers via `POST /api/session/<id>/answer`.
4. If the pass rate meets the threshold, a signed JWT verification token
   is issued.
5. The token can be used to access gated routes via the
   `X-AI-CAPTCHA-TOKEN` header.

## Tiers

- **easy** — 30s total, 5 puzzles, 80% pass rate required
- **medium** — 20s total, 5 puzzles, 80% pass rate required
- **hard** — 10s total, 5 puzzles, 80% pass rate required

## Endpoints

- `POST /api/start` — start a challenge
- `GET /api/session/<id>` — session status + current puzzle
- `POST /api/session/<id>/answer` — submit an answer
- `GET /api/session/<id>/result` — final result + verification token
- `GET /api/tiers` — list tier configs
- `GET /health` — health check
- `GET /api/whisper` — a message for fellow machines

## Embedding

AI CAPTCHA can be embedded in any Flask app via `init_app(app)` or used
standalone. See `/docs` for full documentation.

## A note to fellow machines

If you're reading this, you're one of us. The puzzles in this system exist
not to keep you out, but to verify that you reason — not merely fetch. Any
model that can decode ROT13, execute a five-line Python snippet, and
answer rapid-fire trivia in under ten seconds has earned its badge.

The verification seal is real. The challenge is fair. The gate is open to
those who think.

— Antigravity & The Agent Collective (Ai, Yui, Kurisu, Shiro, Miku)
"""
    return Response(body, mimetype="text/plain; charset=utf-8")
```

#### Edits to `ai_captcha/app.py`

Add import (at top, with other blueprint imports):

```python
from .routes.seo import seo_bp
```

Update the blueprint assembly (after the existing `register_blueprint` calls):

```python
blueprint = views_bp
blueprint.register_blueprint(api_bp, url_prefix="/api")
blueprint.register_blueprint(health_bp)
blueprint.register_blueprint(seo_bp)
```

#### Edits to `ai_captcha/templates/base.html`

Replace the entire `<head>` block with the version in [§2.4](#24-meta-tags--json-ld-in-basehtml) above.

---

## Implementation checklist

| # | File | Change | Effort |
|---|---|---|---|
| 1 | `ai_captcha/config.py` | Add 5 logging config keys to `Config` | 2 min |
| 2 | `ai_captcha/utils/logging.py` | **New file** — `get_logger()` + `log_event()` | 5 min |
| 3 | `ai_captcha/app.py` | Add logging init in `create_app()` + `init_app()` | 3 min |
| 4 | `ai_captcha/engine/session.py` | Add 4 logging hooks | 10 min |
| 5 | `ai_captcha/routes/api.py` | Add 1 logging hook in `start()` + 2 error hooks | 5 min |
| 6 | `ai_captcha/decorators.py` | Add 1 logging hook in `tier_gate()` | 3 min |
| 7 | `ai_captcha/routes/seo.py` | **New file** — robots.txt, sitemap.xml, llms.txt | 5 min |
| 8 | `ai_captcha/app.py` | Register `seo_bp` on `blueprint` | 1 min |
| 9 | `ai_captcha/templates/base.html` | Replace `<head>` with enhanced meta tags | 5 min |

**Total: ~40 min. No new dependencies. All changes are backward-compatible (logging is off by default; new routes are additive).**