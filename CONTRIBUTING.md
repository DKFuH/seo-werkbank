# Contributing

Thanks for considering a contribution. This project values accuracy and maintainability over feature count.
Contributions in German or English are welcome (issues, comments and pull requests).

## Where to start

- Look for issues labelled [`good first issue`](https://github.com/DKFuH/seo-werkbank/labels/good%20first%20issue) or
  [`help wanted`](https://github.com/DKFuH/seo-werkbank/labels/help%20wanted), or pick an item from `docs/ROADMAP.md`.
- Comment on the issue that you take it, so nobody works on it twice. For anything larger than a small fix, open an issue or
  a [discussion](https://github.com/DKFuH/seo-werkbank/discussions) first and agree on the approach before you write code.
- Questions are welcome in discussions. There are no bad questions about the codebase.

## Ground rules

1. **No fabricated data.** A feature must show measured data, a clearly labelled estimate with its method, imported data, or nothing.
2. **No placeholders.** Do not merge buttons that do nothing, endpoints that return canned responses, or empty modules. If something
   cannot be finished, leave it out and add it to `docs/ROADMAP.md`.
3. **Respect third-party terms.** No scraping of search-result pages; prefer official APIs; keep robots.txt compliance on by default.
4. **Licences.** Only add dependencies under MIT/BSD/Apache-2.0/ISC (or similar permissive) licences. Never copy code from GPL/AGPL or
   unlicensed projects. Record new dependencies in `docs/THIRD_PARTY_LICENSES.md`.
5. **Security.** Any code that fetches a user-supplied URL must go through `app.crawler.fetcher.Fetcher` (or `checked_url` +
   `Fetcher`) so SSRF protections apply.

## Development setup

```bash
cd backend
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest -q
ruff check app tests

cd ../frontend
npm install
npm run typecheck && npm test
npm run dev
```

On Windows, run the frontend tests from PowerShell with a `C:\` path, not from Git Bash: Vitest fails on the drive letter otherwise.
The same checks run in CI (`.github/workflows/ci.yml`), so a green local run is a good predictor.

## Workflow

1. Fork the repository and branch from `main`. Name the branch by intent: `feat/...`, `fix/...`, `docs/...`.
2. Make small, focused commits. Prefix messages with `feat:`, `fix:`, `docs:`, `test:` or `refactor:` and explain the *why*.
3. Open a pull request against `main`. A draft PR is fine for early feedback.
4. A maintainer reviews, usually within a few days. Please answer review comments by pushing further commits; the PR is merged
   with a merge commit once CI is green.

Language: user-facing texts in the app are German; code, identifiers and commit messages are English; documentation is German
or English.

AI-assisted contributions are fine. You are responsible for the result: understand the change, run the checks, and make sure no
data or behaviour is invented.

## Project layout

```
backend/app/
  api/            REST routers (auth, sites, crawls, tools, integrations)
  audit/          rule catalogue, page checks, site-wide analysis, schema + hreflang validation
  crawler/        fetcher (SSRF-safe), robots, sitemaps, HTML parser, crawl engine, optional renderer
  keywords/ serp/ content/   research modules
  integrations/   PageSpeed, Search Console, AI providers
  services/       backlinks, competitors, monitoring, settings store
  reports/        CSV/XLSX/PDF builders
  security/       auth, SSRF guard, rate limiting
backend/tests/    unit, security and end-to-end tests + the flawed fixture website
frontend/src/     components/ (UI kit, layout), lib/ (API client, context), pages/
```

## Adding a feature area

A new area (page, API, data) usually touches the same places. Use an existing one such as `api/redirects.py` as a template.

1. Router in `backend/app/api/<name>.py`; register it in the import block and the router tuple in `backend/app/main.py`.
2. Models in `backend/app/models.py` and a numbered Alembic migration (`backend/alembic/versions/00NN_*.py`, `down_revision`
   is the previous one). A migration that could fail on existing data must check first and explain what to do, not delete silently.
3. Every site-scoped endpoint resolves the site with `get_site_for` and has a test for the tenant boundary.
4. Page in `frontend/src/pages/`, route in `frontend/src/App.tsx`, entry in `frontend/src/components/Layout.tsx`.
5. A guide in `docs/` and an entry in `CHANGELOG.md`; list limitations in `KNOWN_LIMITATIONS.md`.

## Adding an audit rule

1. Add an entry to `backend/app/audit/rules.py` (id, title, severity, category, description, fix) **and** put the id in exactly one
   provenance set there (`TECHNICAL_REQUIREMENT_IDS`, `GOOGLE_RECOMMENDATION_IDS` or `SEO_HEURISTIC_IDS`; `geo_*` rules are
   classified automatically). A test fails otherwise. Do not present a heuristic as a search-engine requirement; see
   `docs/AUDIT_PROVENANCE.md`.
   A Bing or Brave mapping in `backend/app/audit/engine_guidance.py` needs the guideline section and either a verbatim quote or an explicit
   `topic` entry. Never copy Google statements to Bing or Brave, and never use blog posts as the source (see `docs/SEARCH_ENGINE_RULES.md`).
2. Emit it from `audit/page_checks.py` (needs one page) or `audit/analysis.py` (needs the whole crawl).
3. Add a page that triggers it to `backend/tests/fixture_site.py` and list it in `EXPECTED` in `tests/test_api.py`; add a healthy page
   to `NOT_EXPECTED` if false positives are plausible.

## Database changes

Change the models, then generate a migration and review it:

```bash
cd backend
alembic revision --autogenerate -m "describe the change"
pytest tests/test_api.py::test_migrations_are_current
```

## Pull requests

- Keep PRs focused; include tests for new behaviour and update docs (`README.md`, `KNOWN_LIMITATIONS.md`, `CHANGELOG.md`).
- CI must pass: ruff, pytest, TypeScript type-check, frontend tests and build.
- Describe how you verified the change. "It renders" is not verification.

## Reporting bugs

Open an issue with the version, steps to reproduce, expected and actual behaviour. For crawler issues include the crawl settings and,
if possible, a public URL that reproduces the problem. For security issues follow `SECURITY.md`.
