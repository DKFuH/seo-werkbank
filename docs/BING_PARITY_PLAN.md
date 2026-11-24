# Bing Webmaster parity

Goal: Bing and Google as separate, equally supported search data providers, without pretending their APIs have identical capabilities.

Sources: https://learn.microsoft.com/en-us/bingwebmaster/ and https://learn.microsoft.com/en-us/dotnet/api/microsoft.bing.webmaster.api.interfaces?view=bing-webmaster-dotnet . Legacy SDK signatures are not proof of current REST support. Live availability must be verified with authorized credentials.

## First increment
- Site-scoped read-only endpoint for traffic, pages, query-page mapping, URL info and sitemaps.
- Explicit provider and retrieval timestamp; no invented metrics.
- Mock transport and input validation tests. Live calls not verified.

## Remaining acceptance gates
1. Verify each REST operation, parameters, quota and response schema against current documentation and authorized live responses; record unavailable capabilities separately.
2. Introduce provider-specific normalized query/page/day facts, site/property mapping, migrations and idempotent import; never combine positions across engines.
3. Reuse content gap, decay, overlap and trend algorithms with provider selection.
4. Verify keyword research and backlinks operations, implement provider adapters and historical snapshots; distinguish absence in a limited export from confirmed lost link.
5. Index inspection, crawl issues and sitemap inventory with Bing-specific semantics.
6. Explicit confirmation for management mutations; retain IndexNow, redact credentials and enforce tenant boundaries.
7. UI, reports and MCP with source labels, coverage and timestamps.
8. Regression, migration, security and integration tests; update handbook and API reference.

This draft is an initial increment, not completed feature parity. No live API test or CI success is claimed.
