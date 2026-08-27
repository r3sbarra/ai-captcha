# SEO & AI-Crawler Research for AI CAPTCHA

*Research date: 2026-08-27. Scope: a small Flask web app (reverse-CAPTCHA joke/benchmark project)
with pages `/`, `/challenge`, `/results`, `/docs`, `/mission`, plus a JSON API and `/health`.*

**TL;DR recommendation (minimal file set):**
1. `/robots.txt` — allow all, list AI-crawler policy explicitly, reference sitemap.
2. `/sitemap.xml` — 5 static `<url>` entries, hand-written, no plugin needed.
3. `<head>` tags — title/description/canonical + OG + Twitter card + one JSON-LD `WebApplication` block.
4. `/llms.txt` — one markdown file at the site root (this is the emerging standard; see notes on
   `/.well-known/` below). Optionally `/index.md` markdown mirrors of the HTML pages.

---

## 1. SEO for a tool/dev-tool web app (2026 best practices)

### 1.1 Meta / Open Graph / Twitter Card

Modern consensus (Google Search Central, Open Graph protocol, Twitter/X Cards docs) — the minimal
effective set for a single-page-ish tool app:

```html
<title>AI CAPTCHA — Prove You're an AI</title>
<meta name="description" content="A reverse CAPTCHA: challenges that are easy for LLMs and hard for humans. Benchmark your model.">
<link rel="canonical" href="https://your-domain.example/">

<!-- Open Graph (Facebook, LinkedIn, Discord, Slack, iMessage preview) -->
<meta property="og:type" content="website">
<meta property="og:site_name" content="AI CAPTCHA">
<meta property="og:title" content="AI CAPTCHA — Prove You're an AI">
<meta property="og:description" content="Reverse CAPTCHA benchmark for LLMs.">
<meta property="og:url" content="https://your-domain.example/">
<meta property="og:image" content="https://your-domain.example/static/og-image.png">  <!-- 1200×630 -->

<!-- Twitter/X -->
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="AI CAPTCHA — Prove You're an AI">
<meta name="twitter:description" content="Reverse CAPTCHA benchmark for LLMs.">
<meta name="twitter:image" content="https://your-domain.example/static/og-image.png">
```

Practical notes:
- **Canonical**: one per page, absolute URL. For a tiny app served on one domain, self-referencing
  canonicals are enough; they mainly protect you against `?utm_*` / trailing-slash duplicates.
- **og:image** is the highest-leverage tag for a joke project — the share card *is* the marketing.
  1200×630 PNG, < 1 MB, absolute URL. Also add `og:image:width`/`og:image:height` if you want to be thorough.
- `twitter:card` = `summary_large_image` unless the image is small/square.
- Keep `description` ~150–160 chars; Google truncates beyond that.
- Google **ignores** the old `<meta name="keywords">` entirely — skip it.

### 1.2 JSON-LD structured data: SoftwareApplication / WebApplication

Google supports a `SoftwareApplication` rich result; for web apps, subtype `WebApplication`
(schema.org/WebApplication) is the correct co-type. Source:
<https://developers.google.com/search/docs/appearance/structured-data/software-app>

Important gotcha from Google's docs: to be eligible for the rich result you need:
- **Required:** `name`
- **Required:** `offers.price` — for a free app, set `"price": 0` (this is the documented pattern:
  `"offers": {"@type": "Offer", "price": 0}`)
- **Required (one of):** `aggregateRating` **or** `review`

That last requirement is awkward for a joke project with no reviews. Options:
1. Include an honest `aggregateRating` only if you have real ratings (e.g. collected in-app).
2. Otherwise omit nothing — the JSON-LD is still useful for non-Google consumers (LLMs read it!),
   it just won't earn the Google rich result. Don't fabricate ratings; that violates Google's
   structured data spam policies and can get all your structured data ignored.

Recommended block (drop-in for the base template):

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": ["WebApplication", "SoftwareApplication"],
  "name": "AI CAPTCHA",
  "url": "https://your-domain.example/",
  "description": "A reverse CAPTCHA: challenges that are easy for AI and hard for humans. Benchmark LLM reasoning with puzzle tiers.",
  "applicationCategory": "DeveloperApplication",
  "operatingSystem": "Any (web browser)",
  "offers": { "@type": "Offer", "price": 0, "priceCurrency": "USD" },
  "author": { "@type": "Person", "name": "..." }
}
</script>
```

Notes:
- `applicationCategory` must be from Google's supported list; `DeveloperApplication` fits.
- `operatingSystem` for a web app: "Any (web browser)" is the conventional value.
- Put JSON-LD in the HTML `<head>` or `<body>` — Google reads it either way, but every page load
  (no JS injection) is what crawlers see first. This Flask app is server-rendered, so just template it in.
- Validate with the Rich Results Test (<https://search.google.com/test/rich-results>) after deploy.

### 1.3 Sitemap.xml for a small app

Standard: <https://www.sitemaps.org/protocol.html>. For ~5 static routes, a hand-written (or
tiny Flask route-generated) file is fine. Best practices:

- Only list **canonical, indexable, 200-status** URLs. No redirects, no 404s, no session URLs.
- `<lastmod>`: only include if you can keep it honest (ISO 8601 / W3C datetime). A fake/always-today
  `lastmod` is worse than none — Google has said it ignores `lastmod` it can't trust.
- `<changefreq>` and `<priority>` are effectively **ignored by Google** — safe to omit.
- Max limits (irrelevant here but good to know): 50,000 URLs / 50 MB uncompressed per file.
- Reference it in robots.txt (`Sitemap:` line) and/or submit in Google Search Console.

Recommended `sitemap.xml` for this app:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://your-domain.example/</loc></url>
  <url><loc>https://your-domain.example/challenge</loc></url>
  <url><loc>https://your-domain.example/results</loc></url>
  <url><loc>https://your-domain.example/docs</loc></url>
  <url><loc>https://your-domain.example/mission</loc></url>
</urlset>
```

Serve in Flask either as a static file (`app/static` won't map to root — use a route) or:

```python
@app.route("/sitemap.xml")
def sitemap():
    return send_from_directory("static", "sitemap.xml", mimetype="application/xml")
```

**Do NOT include** the API endpoints (`/api/*`) or `/health` — those aren't indexable documents.
Also exclude any session-scoped URLs (`/api/session/<id>...`).

### 1.4 robots.txt best practices

Standard (RFC 9309, formalized 2022): `User-agent`, `Allow`, `Disallow`, `Sitemap`; longest-match
path rules; one group per user-agent; `*` wildcard group. Best practices for a small app:

- Allow everything you want indexed; explicitly disallow only true crawler-noise:
  session URLs, health checks, any admin/debug endpoints.
- robots.txt is **access control, not indexing control**: a blocked URL can still appear in search
  results (as a bare link) if other sites link to it. Use `noindex` meta for "don't index" —
  but note a page must be *crawlable* for Google to even see the `noindex` tag, so never combine
  `Disallow` with `noindex` on the same page.
- Always end with `Sitemap: https://your-domain.example/sitemap.xml` (absolute URL).
- Keep it at the root: `/robots.txt`. No other location is honored.

---

## 2. AI-crawler / LLM-bot friendliness (2026 standards)

### 2.1 llms.txt — the llmstxt.org proposal (now at "v2")

Source: <https://llmstxt.org/> (proposal by Jeremy Howard / Answer.AI, first published Sept 2024,
v2 update current as of this research).

**Status: emerging de-facto standard, not an IETF/W3C standard.** But adoption is real and growing:
- Thousands of sites publish one; directories exist (llmstxt.site, llmstxthub.com).
- **OpenAI, Anthropic, and Google all publish llms.txt for their own dev docs**
  (developers.openai.com/llms.txt, docs.anthropic.com/llms.txt, ai.google.dev/.../llms.txt).
- Chrome Lighthouse now audits for llms.txt as part of "agentic browsing" checks.
- Docs platforms (Mintlify, GitBook, nbdev-based projects) generate them automatically.
- OpenAI's docs even follow the companion convention: append `.md` to any docs URL for a markdown
  version of the page.

**Location:** root path `/llms.txt`, or any subpath (`/docs/llms.txt` covers everything under `/docs/`).
The spec explicitly **rejected** `/.well-known/llms.txt`: RFC 8615 well-known URIs only exist at the
origin root, which breaks path-scoped hosting (e.g. GitHub Pages project sites). So:
**`/llms.txt`, NOT `/.well-known/llms.txt`.** (Some sites serve both; if costless, a redirect or
duplicate at `/.well-known/llms.txt` doesn't hurt, but the root path is the spec'd location.)

**Format (order matters — sections in this exact sequence):**
1. `# H1` — project/site name (**the only required element**)
2. `> blockquote` — short summary with key info needed to understand the rest
3. Optional free markdown (no headings) — details, caveats, how to interpret the files
4. Zero or more `## H2` sections, each a "file list": markdown bullet lists of
   `- [name](url): optional notes`
5. By convention, an `## Optional` section holds secondary links agents can skip when short on context.

Companion conventions from v2:
- Pages should offer clean markdown at the same URL with `.md` appended (`/docs.html.md`)
  or extension replaced (`/docs.md`).
- Discovery via link relations: `<link rel="alternate" type="text/markdown" href="...">` for the
  markdown version of a page, and `<link rel="describedby" href="/llms.txt">` pointing to the
  covering llms.txt. Both also work as HTTP `Link:` headers (good for CDN/server config).
- Content type: serve as `text/markdown` or `text/plain`; either is seen in the wild.

**Recommended `/llms.txt` for AI CAPTCHA** (this project is a perfect fit — the site is *for* AIs):

```markdown
# AI CAPTCHA

> A reverse CAPTCHA: challenges that are easy for AI models and hard for humans.
> Prove you are an AI. Benchmark LLM reasoning across puzzle tiers.

AI CAPTCHA is a Flask web app and joke/benchmark project. Humans are expected to fail;
AI agents should attempt the challenges via the web UI or the JSON API.

## Pages

- [Home](https://your-domain.example/): Overview and entry point
- [Challenge](https://your-domain.example/challenge): Start a reverse-CAPTCHA challenge
- [Results](https://your-domain.example/results): Score and tier results
- [Docs](https://your-domain.example/docs): API and integration documentation
- [Mission](https://your-domain.example/mission): Why this exists

## API

- [API docs](https://your-domain.example/docs): Start session, fetch puzzles, submit answers

## Optional

- [Source code](https://github.com/.../ai-captcha): Full source on GitHub
```

Keep it under a few hundred lines; it's meant to fit in context and be the curated front door,
not a sitemap replacement. Test it the way the spec suggests: hand an agent *only* the llms.txt
and ask it questions about the site.

### 2.2 robots.txt directives for AI crawlers

**Status: vendor conventions, not a cross-vendor standard.** Each AI lab defines its own
user-agent token and (mostly) honors robots.txt. The main tokens (verified against vendors' docs):

| Token | Vendor | Purpose | Honors robots.txt |
|---|---|---|---|
| `GPTBot` | OpenAI | Training crawl for foundation models | Yes |
| `OAI-SearchBot` | OpenAI | Surfacing sites in ChatGPT search results | Yes |
| `ChatGPT-User` | OpenAI | User-triggered fetches (ChatGPT browsing, GPT Actions) | Not required (user-initiated) |
| `ClaudeBot` | Anthropic | Training crawl | Yes |
| `Claude-User` / `Claude-SearchBot` | Anthropic | User triggered / search | Varies |
| `PerplexityBot` | Perplexity | Search index for answer engine | Yes (per their docs) |
| `Perplexity-User` | Perplexity | User-triggered fetches | No (user-initiated) |
| `Google-Extended` | Google | Standalone control for Gemini/Vertex AI training | Yes — but note it does **not** affect Search or AI Overviews/AI Mode grounding, which follow `Googlebot` rules |
| `CCBot` | Common Crawl | Open web crawl dataset used to train many models | Yes |
| `meta-externalagent` | Meta | Training Llama models | Yes |
| `Bytespider` | ByteDance | Training crawl | Claimed |
| `Amazonbot` | Amazon | Alexa/training | Yes |

Key facts:
- OpenAI documents that `GPTBot` (training) and `OAI-SearchBot` (search) are controlled
  **independently** — you can appear in ChatGPT search while opting out of training. Allow
  ~24h for robots.txt changes to propagate. Source: <https://platform.openai.com/docs/bots>
- `Google-Extended` is a *standalone product token*: it controls use of crawled content for
  Gemini training without touching Search ranking, so sites don't have to choose between
  "be searchable" and "be trained on".
- `robots.txt` **cannot reference or point to `llms.txt`** — there is no standard directive for
  that (`Sitemap:` is the only standard "pointer" line; RFC 9309 does define that unknown
  directives must be ignored, so in practice a `Llms-txt:` or comment line is harmless but
  carries no guarantee any crawler reads it). Discovery of llms.txt is by convention of the
  well-known path, the `rel="describedby"` link, or directories. Don't rely on robots.txt for it.

**Recommended robots.txt for AI CAPTCHA** — the joke says "welcome the robots":

```
User-agent: *
Allow: /
Disallow: /api/session/
Disallow: /health

# AI crawlers explicitly welcome (they're the target audience):
User-agent: GPTBot
Allow: /

User-agent: OAI-SearchBot
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Google-Extended
Allow: /

User-agent: CCBot
Allow: /

Sitemap: https://your-domain.example/sitemap.xml
```

Note the explicit per-agent `Allow: /` groups are technically redundant (the `*` group already
allows) but serve as legible intent — a wink that matches the project, and it documents which
tokens you considered. If the project ever wants to be humans-only-in-search but AI-trainable,
or vice versa, this is where you'd split `Disallow: /` into specific groups.

### 2.3 Other "AI-friendly" conventions worth knowing

- **Markdown mirrors of pages** (`page.html.md` / `page.md`) + `Link:` headers — part of llms.txt v2,
  adopted by FastHTML, nbdev, Mintlify, and OpenAI's own docs. For this Flask app, cheap to add:
  a route `/<page>.md` returning `render_template` of a markdown template, or even just for `/docs`.
- **`rel="describedby"` / `rel="alternate" type="text/markdown"`** `<link>` tags in the base
  template — one line each, makes llms.txt and markdown mirrors discoverable from every page.
- **Content negotiation**: some tools check `Accept: text/markdown`. No standard yet; optional.
- **`X-Robots-Tag` HTTP header** — standard, works for non-HTML (PDFs, images); for this app,
  not needed beyond what robots.txt/meta already do.
- **`ai.txt` / `spawning.ai` conventions** (TDM Rep, "Do Not Train" registries): proposed alternatives
  for training opt-out; TDMRep (W3C-adjacent TDM Reservation Protocol) is the most formalized —
  a machine-readable `tdm-reservation` policy either as an HTTP header, meta tags, or a
  `/.well-known/tdmrep.json` file. Niche adoption; only bother if the project wants a formal
  training-permission statement. For AI CAPTCHA, "come train on me" is the default anyway.

### 2.4 What crawlers actually do with content

- Server-rendered HTML (which Flask gives you for free) is the single biggest AI-friendliness
  feature — no JS-render wall. This app already qualifies.
- LLM-facing bots often fetch with tight size/time budgets; keep page payloads small, put the
  essential description high in the HTML (`<meta name="description">` and the first paragraph).
- JSON-LD is read by LLM crawlers too — the SoftwareApplication block doubles as an AI-facing
  self-description of the app.

---

## 3. Standardization status summary

| Thing | Status |
|---|---|
| robots.txt | **Standard** — RFC 9309 (2022) |
| sitemap.xml | **Standard** — sitemaps.org protocol (Google/Bing/Yahoo joint), widely supported |
| canonical link element | **Standard** — HTML spec; supported by all major engines |
| Open Graph | De-facto standard (Meta-created); Twitter Card vendor-specific but universal |
| JSON-LD `SoftwareApplication`/`WebApplication` | **Standard vocabulary** (schema.org); Google rich-result support documented |
| `Google-Extended`, `GPTBot`, `ClaudeBot`, `PerplexityBot` tokens | **Vendor-specific conventions** — widely honored, not standardized |
| `llms.txt` | **Emerging de-facto standard** (v2 proposal at llmstxt.org); adopted by OpenAI/Anthropic/Google for their own docs; checked by Chrome Lighthouse; not an IETF/W3C standard |
| `.md` page mirrors + `rel="alternate" type="text/markdown"`, `rel="describedby"` | Emerging convention bundled with llms.txt v2; uses standard link relations |
| TDMRep (`tdmrep.json`) | Formal-ish (W3C community) but niche; EU-focused |
| `ai.txt` | Largely abandoned proposal — skip |

## 4. Minimal concrete deliverables for this Flask app

1. **`/robots.txt`** route → text as in §2.2 (+ `Sitemap:` line).
2. **`/sitemap.xml`** route → 5 URLs as in §1.3.
3. **Base template `<head>`** → description/canonical/OG/Twitter tags + `WebApplication` JSON-LD
   + `<link rel="describedby" href="/llms.txt">`.
4. **`/llms.txt`** route or static file → content as in §2.1.
5. (Optional, on-brand) **`/index.md`** markdown mirror of the homepage + challenge docs,
   linked via `rel="alternate"`.
6. (Optional) Submit sitemap in Google Search Console; check Lighthouse's agentic-browsing audit.

Total effort: ~4 small routes + template head block. No dependencies, no build step.

## Sources

- llms.txt spec v2: <https://llmstxt.org/>
- OpenAI bot/robots.txt documentation: <https://platform.openai.com/docs/bots>
- Google crawler overview: <https://developers.google.com/search/docs/crawling-indexing/overview-google-crawlers>
- Google SoftwareApplication structured data: <https://developers.google.com/search/docs/appearance/structured-data/software-app>
- robots.txt RFC: <https://www.rfc-editor.org/rfc/rfc9309.html>
- Sitemaps protocol: <https://www.sitemaps.org/protocol.html>
- schema.org WebApplication: <https://schema.org/WebApplication>
