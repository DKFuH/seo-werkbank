# Changelog

All notable changes are recorded here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project
uses [Semantic Versioning](https://semver.org/).

## [Unreleased] - SEO-Werkbank

### Changed (crawl numbering)
- Crawls are numbered per project: "Crawl 1" to "Crawl n" for each website (competitor crawls separately), instead of
  the global database id. The number is gap-free after a deletion; the internal id stays in URLs and as a tooltip.
  Exports and the PDF report use the run number in file name and header.

### Added (GEO)
- robots.txt AI signals: detection of the Cloudflare-managed section that blocks AI crawlers (`geo_cloudflare_ai_block`)
  and of `Content-Signal` lines with `search=no` or `ai-input=no` (`geo_content_signal_restrictive`; `ai-train=no` is
  not flagged). Crawler-specific meta tags / X-Robots-Tag and `noai`/`noimageai` (`geo_ai_meta_restricted`).
- llms.txt checked for the llmstxt.org structure (H1, `>` summary, `##` sections, link list; `geo_llms_incomplete`) and
  `/llms-full.txt`. New **llms.txt draft** from the last crawl (`GET /sites/{id}/geo/llms-txt-draft`, card on the GEO page).
- GEO check group **Integrität** and five crawl audit rules: `geo_snippet_limited` (nosnippet, max-snippet below 50,
  data-nosnippet on half the text), `geo_hidden_instructions` (LLM instructions in comments, attributes or hidden
  text, invisible control characters), `geo_schema_not_visible` (headline, product name, price or FAQ question only in
  JSON-LD), `geo_date_inconsistent` (future dates, dateModified before datePublished, visible date over 30 days off),
  `geo_brand_inconsistent` (start page: brand name missing from title/Open Graph or differing from og:site_name).
- **CDN bot access** (`POST /sites/{id}/geo/bot-access`): requests a page of the own site with a browser and with
  eleven AI crawler user agents and reports blocks, challenge pages and diverging responses. On demand only.
- AI crawler list: Applebot (now a search crawler that must not be blocked), DuckAssistBot, Amazonbot.

### Fixed (GEO)
- A `Content-Signal` line in robots.txt (added by Cloudflare on many sites) was reported as an unknown directive and
  raised the robots.txt syntax rule.
- GEO integrity checks decode HTML as UTF-8 before parsing; lxml otherwise reads pages without a charset declaration
  as Latin-1.

### Changed
- **Navigation** grouped by the question a user brings: Analyse, Sichtbarkeit, Content, Conversion, Maßnahmen (plus Übersicht and
  System). Groups collapse; the group of the open page is always expanded and highlighted, other open groups are remembered per
  browser. All 36 screens stay reachable.
- **Dashboard** starts with four area cards for the selected site: technical SEO (last crawl), Google search (GSC clicks and
  impressions with change vs. the previous period), AI mentions (manual samples, own-URL citations) and open SEO work items.
  Each card shows only values its API returns and labels their source; without data it links to the setup. The technical charts
  follow below, the site list only appears with more than one site.

### Added
- **Audit rule `template_content`** (medium): pages that share at least half of their 5-word sequences with another indexable
  page, typical for template pages with swapped city or product names. Site-wide blocks that appear on many pages are ignored.
- **Keyword mapping vs. Search Console**: each mapped keyword shows the page Google actually shows for it (most impressions in the
  last 90 days of query+page data) and flags a mismatch with the intended page.

Evidence-first planning and review modules. All of them store manually entered or imported records, scope every route to the
signed-in user's site, and label their results as observations rather than measured rankings or causal effects.
- **Content refresh** (`/content-refresh`): GSC query+URL pairs grouped per page, striking-distance and low-CTR prompts, lexical
  check against the crawled headings ([docs](docs/CONTENT_REFRESH.md)).
- **Opportunity value** (`/opportunity-value`): user-defined lead, close-rate and margin assumptions as scenarios
  ([docs](docs/OPPORTUNITY_VALUE.md)).
- **SEO work items** (`/seo-work`): manual workflow for content, reviews, publications, local tasks and competitor observations, with
  dated GSC baseline/follow-up snapshots for content items ([docs](docs/SEO_WORKFLOW.md)).
- **Internal link context**: `GET /crawls/{id}/link-opportunities/context` shows a real source-text passage and an anchor candidate for
  existing link opportunities.
- **AI visibility observations** (`/ai-visibility`): manual samples of brand mentions and cited URLs ([docs](docs/AI_VISIBILITY.md)).
- **Competitor topic radar** (`/competitor-radar`): word pairs from competitor titles/H1s missing from the own crawl.
- **Local SEO action plan and publication evidence** (`/seo-evidence`) ([docs](docs/LOCAL_EVIDENCE.md)).
- **Content proposals** (`/content-proposals`): draft, diff, separate approval and manual "published" marker
  ([docs](docs/CONTENT_PROPOSALS.md)).
- **Rank tracker** (`/rank-tracking`): explicit targets with provenance-labelled observations ([docs](docs/RANK_TRACKING.md)).
- **SEO research** (`/research`), **quality & CRO** (`/research-quality`), **change timeline, SERP features, indexing and GEO
  citations** (`/research-monitoring`), **conversion & trust** (`/conversion-trust`) ([docs](docs/SEO_RESEARCH.md),
  [quality](docs/RESEARCH_QUALITY.md), [monitoring](docs/RESEARCH_MONITORING.md), [conversion](docs/CONVERSION_TRUST.md)).
- Alembic migrations `0002`–`0006`; they run automatically on start-up.

### Fixed
- Timestamps entered with a UTC offset (AI observations, rank observations, research records) were stored with the offset cut off
  instead of being converted to UTC.
- Rank capture did not recognise the own site when the provider returned `example.de` for a site saved as `www.example.de` (or the
  other way round).
- A GSC follow-up snapshot for a page without recent impressions reused the baseline's old window; the window now ends at the newest
  day of the whole site dataset.
- The change timeline issued one database query per event and rank target (up to 60,000 per request); it now uses one query.

## [0.1.0] - Unreleased

First development release.

### Security
Result of the pre-release security review (details: `docs/SECURITY_REVIEW.md`).
- JavaScript rendering: every browser request is vetted and performed with redirects disabled; WebSockets blocked; frame URLs re-checked;
  Chromium sandbox on by default (`SEO_RENDER_SANDBOX`).
- Local Lighthouse: administrator-only, one run at a time, final URL re-checked, errors no longer echoed.
- `robots.txt` rules and crawl filters use a linear-time matcher instead of regular expressions (a hostile `robots.txt` or pattern could
  freeze the server).
- Request-body size limit enforced before bodies are read; overall deadline and minimum transfer rate per fetch; per-account job cap;
  links-per-page cap; hostile HTML parsed off the event loop.
- Search Console OAuth: `state` is single-use and bound to the signed-in account; the code is exchanged by the app with the user's token.
- Accounts: registration closed after the first account by default; atomic first-admin creation; per-account login lockout; password
  change invalidates older sessions; trusted-proxy aware rate limiting (`SEO_TRUSTED_PROXIES`); secret key file created owner-only.
- Web: Permissions-Policy, COOP/CORP, HSTS over HTTPS, `Cache-Control: no-store` on the API, narrow CSP for the API docs, only `http(s)`
  links are clickable; static-file requests are vetted before touching the filesystem (UNC path leak on Windows).
- SSRF guard: deprecated IPv6 ranges refused; startup failure instead of a silently inactive guard.
- Dependencies: Vite 6, Vitest 4, React Router 7 (8 npm advisories, 2 critical, resolved); GitHub Actions pinned by SHA; Dependabot and a
  scheduled security workflow added; Docker Compose binds to `127.0.0.1`, drops capabilities and sets `no-new-privileges`.

### Fixed
- Crawls could lose up to 40 pages from their totals when the last database batch was still being written as the crawl finished
  (found by CI as an occasional 460-of-500 failure on slower disks).
- `docker compose up -d` failed on a fresh checkout because the optional PostgreSQL service required a password even when it was not
  started. PostgreSQL is now an optional override file, `docker-compose.postgres.yml`, and CI smoke-tests both variants.

### Changed
- The product is named **OpenSEOSuite** (README, UI, licence holder, API title).
- **Crawl include/exclude patterns are no longer regular expressions.** They are plain text with `*` wildcards and optional `^` / `$`
  anchors (for example `/blog/*`, `?sort=`, `.pdf$`).
- `SEO_ALLOW_REGISTRATION` now defaults to `false` (the first account can always be created).
- Docker Compose publishes the port on `127.0.0.1` by default (`SEO_BIND=0.0.0.0` to expose it).
- `/api/auth/password` returns a fresh token; older tokens stop working.
- `/api/gsc/callback` now redirects into the app; the exchange happens at `POST /api/gsc/exchange`.

### Added (documentation)
- README banner, badges, 23 screenshots from a real instance (`scripts/capture_screenshots.py`), comparison table and security section.

### Added
- **Crawler**: asyncio crawler with RFC 9309 robots.txt handling, sitemap discovery (index, gzip, text), depth/URL limits, per-host
  throttling with crawl-delay, retries honouring Retry-After, include/exclude patterns, optional subdomains, external-link and image
  checks, optional Playwright rendering, cancellation.
- **Audit**: 95 rules across availability, redirects, links, indexability, content, URL, security, images, mobile, HTML, social,
  structured data, international and sitemap categories; page and site scores; crawl comparison.
- **Site analysis**: internal PageRank, click depth, orphan detection, exact and near-duplicate content (SimHash), canonical and
  hreflang cross-checks, sitemap consistency.
- **Modules**: internal linking (with link graph and link opportunities), sitemap manager and generator, schema validator and
  generator, PageSpeed Insights + local Lighthouse, international SEO, local SEO, keyword research (suggestions, intent, clustering,
  page mapping, cannibalisation, Keyword Planner import), SERP analysis (SearXNG, Google CSE, Brave, manual), content optimizer,
  competitor comparison, backlink import and verification, Search Console (OAuth and CSV), monitoring with alerts, optional AI layer
  (Ollama or OpenAI-compatible).
- **Reports**: PDF audit report, PDF competitor report, XLSX workbooks, CSV, JSON, generated XML sitemap.
- **Platform**: FastAPI REST API with OpenAPI docs, SQLite/PostgreSQL via SQLAlchemy and Alembic migrations, in-process job runner and
  scheduler, React/TypeScript dashboard with light and dark themes.
- **Security**: connection-level SSRF guard, Argon2id passwords, JWT auth, per-user data isolation, rate limiting, security headers,
  upload restrictions, formula-injection-safe exports.
- **Tooling**: 221 backend tests including an end-to-end audit of a deliberately flawed test website, frontend tests, CI workflow,
  Dockerfile and Compose file.
