# Bing Webmaster parity

Goal: Bing and Google as separate, equally supported search data providers, without pretending their APIs have identical capabilities.

Sources: https://learn.microsoft.com/en-us/bingwebmaster/ and https://learn.microsoft.com/en-us/dotnet/api/microsoft.bing.webmaster.api.interfaces?view=bing-webmaster-dotnet . Legacy SDK signatures are not proof of current REST support. Live availability must be verified with authorized credentials.

## Implemented increments
- Site-scoped, allowlisted read-only endpoints for traffic, pages, query/page mappings, URL info, sitemaps, backlinks, crawl
  settings and submission quota.
- Explicit provider and retrieval timestamp; no invented or merged Google/Bing metrics.
- Immutable provider snapshots (migration `0015`), tenant-scoped history, UI and read-only MCP access.
- Bounded content analysis from real page-query observations. Incomplete weekly series cannot produce temporal signals.
- Mock transport, signature, normalization, migration, API tenant-boundary, persistence, MCP and frontend regression tests.
- Provider error bodies are not exposed because they can echo credential-bearing URLs.

## Remaining acceptance gates
1. Verify each JSON/HTTP operation, quota and response schema against authorized live responses; record unavailable capabilities separately.
2. Introduce provider-specific normalized query/page/day facts and idempotent scheduled import; never combine positions across engines.
3. Extend historical analysis beyond bounded on-demand samples while preserving per-series coverage evidence.
4. Verify keyword research and backlink coverage live; distinguish absence in a limited export from confirmed lost link.
5. Index inspection, crawl issues and sitemap inventory with Bing-specific semantics.
6. Explicit confirmation for management mutations; retain IndexNow, redact credentials and enforce tenant boundaries.
7. Add normalized provider data to reports with source labels, coverage and timestamps.
8. Add authorized live integration tests where credentials and provider stability permit them.

This remains an incremental parity implementation, not complete feature parity. Automated CI is required for merge; no
authorized live API verification is claimed.
