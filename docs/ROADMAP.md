# Roadmap

Ordered by expected value to users. Items move to `CHANGELOG.md` when shipped. See `../PROJECT_STATUS.md` for what is verified today.

## Next (0.2)

- Expand Chromium/Playwright CI coverage and add a dedicated local Lighthouse integration test.
- Verify Search Console OAuth and URL Inspection against a real authorized Google Cloud project and property.
- Notifications for alerts: e-mail (SMTP) and generic webhook (Slack/Discord compatible).
- Batch page-speed testing for the top pages of a crawl, with site-level Core Web Vitals summary.
- Verify encryption and key rotation of stored integration secrets on real migrations and recovery.
- Validate SERP-overlap clustering against a configured provider and document ranking-source limitations.
- Refresh README screenshots/demo for Redirects, Logs/404 and Schema-Management; manually test these new workflows.

## Later

- Advanced log-analysis adapters: arbitrary Nginx `log_format`, JSON access logs, independently verified crawler signatures and configurable retention. Current support is Common/Combined + up to two trailing quoted fields; 64 KiB/line.
- Google Analytics 4 integration; validate Bing Webmaster Tools/IndexNow with a live authorized account (both are already implemented).
- Image audit by downloading headers of all images (dimensions, format, compression potential).
- Soft-404 detection, pagination-sequence checks, `srcset`/CSS-background link extraction, AMP checks.
- Rendering-based mobile checks (tap targets, font sizes) through Playwright.
- Language-aware readability (formulas for German, Spanish, French ...) and multilingual stop words.
- Embedding-based topic clustering through the optional local AI provider.
- Teams/workspaces with shared sites and roles; API tokens for automation; audit log.
- Queue backend option (Redis/RQ or Dramatiq) and multi-process crawling for very large sites.
- White-label PDF reports (logo, colours), scheduled report delivery.
- Plugin interface for custom audit rules.

## Delivered (PRs #41–#45, 23 November 2026)

- Redirect proposal, simulation, approval and Apache/Nginx/CSV draft export; database uniqueness per site/source (migrations `0010`, `0013`).
- Privacy-reduced access-log and 404 monitoring with bounded import, crash recovery, API tests and redirect proposal handoff (migration `0011`).
- Crawl-based schema templates and JSON-LD draft approval with separately HTML-escaped embedding output (migration `0012`).
- CI on Linux, Windows and macOS plus frontend, security and Docker smoke testing. Manual production verification remains outstanding.

## Research

- An open backlink dataset derived from Common Crawl's published web-graph files (host-level first). This needs significant storage and
  batch processing and would ship as a separate optional importer rather than inside the app.
- Google Trends without an official API: revisit if a permitted access route appears.

## Out of scope

- Scraping Google/Bing result pages, proxy rotation, captcha solving.
- Estimating search volumes or traffic without a data source.
- Link-building automation.
