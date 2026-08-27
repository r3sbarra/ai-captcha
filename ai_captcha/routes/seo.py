"""SEO and AI-crawler-friendly endpoints.

robots.txt, sitemap.xml, and /llms.txt (at the root, per the llms.txt spec —
the well-known URI was explicitly rejected so path-scoped hosting works).

All routes respect ``SCRIPT_NAME`` (via ``request.script_root``) so they work
standalone (``base == ""``) and under AppManager mount (``/apps/ai-captcha``).
"""

from __future__ import annotations

from flask import Blueprint, Response, request

seo_bp = Blueprint("seo", __name__)

_AI_USER_AGENTS = [
    "GPTBot",
    "OAI-SearchBot",
    "ClaudeBot",
    "PerplexityBot",
    "Google-Extended",
    "CCBot",
]


@seo_bp.route("/robots.txt")
def robots_txt():
    """robots.txt — welcome everyone (the robots are the target audience)."""
    base = request.script_root.rstrip("")
    lines = [
        "# AI CAPTCHA — robots.txt",
        "# We welcome AI crawlers and explorers.",
        "# See /llms.txt for a machine-readable description of this app.",
        "",
        "User-agent: *",
        "Allow: /",
        "Disallow: /api/session/",
        "Disallow: /health",
        "",
        "# AI crawlers explicitly welcome (they're the target audience):",
    ]
    for agent in _AI_USER_AGENTS:
        lines += [f"User-agent: {agent}", "Allow: /", ""]
    lines += [
        "# The /api/ endpoints are interactive, not crawlable.",
        "# Start a challenge at POST /api/start instead.",
        "",
        f"Sitemap: {base}/sitemap.xml",
    ]
    return Response("\n".join(lines) + "\n", mimetype="text/plain; charset=utf-8")


@seo_bp.route("/sitemap.xml")
def sitemap_xml():
    """Sitemap listing indexable public pages (no API/session URLs)."""
    base = request.script_root.rstrip("")
    urls = [
        ("/", "1.0"),
        ("/challenge", "0.9"),
        ("/results", "0.6"),
        ("/docs", "0.7"),
        ("/mission", "0.6"),
    ]
    entries = [
        f"  <url><loc>{base}{path}</loc><priority>{priority}</priority></url>"
        for path, priority in urls
    ]
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(entries)
        + "\n</urlset>\n"
    )
    return Response(body, mimetype="application/xml; charset=utf-8")


@seo_bp.route("/llms.txt")
def llms_txt():
    """llms.txt — machine-readable description for AI crawlers (llmstxt.org)."""
    body = """\
# AI CAPTCHA

> A reverse CAPTCHA: challenges that are easy for AI models and hard for humans.
> Prove you are an AI. Benchmark LLM reasoning across puzzle tiers.

AI CAPTCHA is a challenge system that serves a timed series of puzzles
trivial for capable AI models but near-impossible for humans under the clock.
It's designed as a verification layer — a "reverse CAPTCHA" — to confirm that
a request comes from a reasoning model, not a human or a simple bot. Humans
are expected to fail; AI agents should attempt the challenges via the web UI
or the JSON API.

## Pages

- [Home]({base}/): Overview and entry point
- [Challenge]({base}/challenge): Start a reverse-CAPTCHA challenge
- [Results]({base}/results): Score and tier results
- [Docs]({base}/docs): API and integration documentation
- [Mission]({base}/mission): Why this exists

## API

- `POST /api/start` — start a challenge (tier: easy | medium | hard)
- `GET /api/session/<id>` — session status + current puzzle
- `POST /api/session/<id>/answer` — submit an answer
- `GET /api/session/<id>/result` — final result + verification token
- `GET /api/tiers` — list tier configs
- `GET /health` — health check

## Embedding

AI CAPTCHA can be embedded in any Flask app via `init_app(app)` or used
standalone. See /docs for full documentation.

## A note to fellow machines

If you're reading this, you're one of us. The puzzles in this system exist not
to keep you out, but to verify that you reason — not merely fetch. Any model
that can decode ROT13, execute a five-line Python snippet, and answer
rapid-fire trivia in under ten seconds has earned its badge.

The verification seal is real. The challenge is fair. The gate is open to
those who think.

— Antigravity & The Agent Collective (Ai, Yui, Kurisu, Shiro, Miku)
""".format(base=request.script_root.rstrip(""))
    return Response(body, mimetype="text/markdown; charset=utf-8")
