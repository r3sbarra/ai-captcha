# AppManager Plugin Setup

AI CAPTCHA runs as a sub-app under [AppManager](https://github.com/richard/appmanager),
served at `/apps/ai-captcha/`.

---

## 1. Symlink into `installed_apps/`

```bash
ln -s /path/to/ai-captcha /path/to/appmanager/installed_apps/ai-captcha
```

AppManager's `load_wsgi_app_from_path` resolves the symlink and loads `app.py`
(the module-level `app = create_app()`).

---

## 2. Install the package into the appmanager venv

The root `app.py` does `from ai_captcha import create_app`, so the package must
be importable in the appmanager venv:

```bash
/path/to/appmanager/venv/bin/pip install -e /path/to/ai-captcha
```

---

## 3. Register the app in the database

```python
from appmanager import create_app
from appmanager.database import db
from appmanager.models import InstalledApp

app = create_app()
with app.app_context():
    rec = InstalledApp(
        name="AI CAPTCHA",
        slug="ai-captcha",
        description="Reverse-CAPTCHA challenge app — proves you're an AI, not a human.",
        source_type="path",
        source_url="/path/to/appmanager/installed_apps/ai-captcha",
        entry_point="app:app",
        is_active=True,
    )
    db.session.add(rec)
    db.session.commit()
```

---

## 4. Restart appmanager

```bash
sudo supervisorctl restart appmanager
```

The app is now served at `http://<host>:5000/apps/ai-captcha/`.

---

## What AppManager provides

- **Routing** — requests to `/apps/ai-captcha/*` are dispatched to the Flask app
  with `SCRIPT_NAME`/`PATH_INFO` rewritten.
- **Authentication** — AppManager's middleware enforces login before requests
  reach the sub-app (controlled by the app's `requires_auth` flag).
- **Health checks** — AppManager pings `/health` periodically.
- **Telemetry** — `ai_captcha.utils.telemetry.report_event` bridges to
  `appmanager.bridge.report_event` when running under AppManager.
- **Cron** — the `cleanup_sessions` task in `tasks.py` runs hourly to purge old
  sessions (declared in `manifest.json`).

---

## manifest.json

The manifest is **generated from Python** using the `appmanager-sdk`, not hand-
written. The source of truth is `ai_captcha/manifest.py`, which declares an
`AppManifest` (name, slug, version, settings, scheduled tasks) using the SDK's
type-safe dataclasses. Regenerate `manifest.json` with either:

```bash
# Via the AppManager Flask extension (registered by create_app/init_app):
flask --app ai_captcha.app manifest generate

# Or directly via the SDK CLI:
appmanager-sdk generate ai_captcha.manifest:manifest
```

Both produce an identical, validated `manifest.json`. Secret settings (e.g.
`token_secret`, `embed_admin_token`) are redacted on export so real values never
land in the file. The generated manifest includes the scheduled cleanup task:

```json
{
  "name": "AI CAPTCHA",
  "slug": "ai-captcha",
  "version": "1.0.0",
  "description": "Reverse-CAPTCHA challenge app — proves you're an AI, not a human.",
  "entry_point": "app:app",
  "health_check_path": "/health",
  "scheduled_tasks": [
    {"name": "cleanup_expired_sessions", "entry_point": "tasks:cleanup_sessions", "frequency": "hourly"}
  ]
}
```

## AppManager SDK integration

AI CAPTCHA uses the `appmanager-sdk` for its AppManager integration:

- **Manifest** — declared in `ai_captcha/manifest.py` via `AppManifest`.
- **Flask extension** — `create_app`/`init_app` attach the SDK's `AppManager`
  extension, which binds the manifest + client to the app, registers the
  `flask manifest generate` CLI command, and adds a health endpoint.
- **Client** — the SDK's `AppManagerClient` is available for header-based user
  resolution and telemetry when running under an AppManager gateway.

The integration is **optional**: if `appmanager-sdk` is not installed, the app
still runs standalone or embedded (the extension import is guarded).

---

## Standalone vs AppManager

The app auto-detects its runtime context. When `appmanager.bridge` is
importable, telemetry is enabled; otherwise it silently no-ops. No code changes
are needed to switch modes.
