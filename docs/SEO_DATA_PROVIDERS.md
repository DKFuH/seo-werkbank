# External SEO data provider interface (initial version)

This extension is a **provenance-aware provider registry** for existing datasets.
It prepares the application for optional external vendor API integrations without
pretending that commercial data has been licensed or fetched.

## Included adapters
- `keyword_import`: user-imported keyword volume, competition and bid figures.
  Search volume is **not** measured by SEO-Werkbank; its source file is exposed.
- `gsc`: the user's **own verified website** Search Console clicks, impressions,
  impression-weighted average position and dated reporting period. API records
  take precedence over CSV records to avoid double counting.
- `backlink_records`: user-imported and optionally locally verified links, with
  recorded status, nofollow and timestamps. Not a web-scale backlink index.

All adapters implement the same `rows(db, site_id, limit, days)` interface
and publish a structured metadata record describing source, unit, and scope.
The explicitly registered providers cannot be changed by remote input.

## Endpoints
- `GET /api/seo-data/providers`
- `GET /api/sites/{site_id}/seo-data/{source}?limit=100&days=28`

Both require normal user authentication; each site query enforces ownership.
The API is read-only. No vendor API keys or external HTTP requests are needed.

## Extending the registry

Implement `Provider.info` and `Provider.rows`, register the class in
`PROVIDERS`, preserve metric units and provide tests for invalid input and
tenant isolation. External provider integrations require their own secure,
encrypted credential storage, documented terms, quota/backoff and provider
response verification. Do not make scraped or heuristic estimates look
like provider measurements.

## Known limitation
The existing keyword-import pipeline retains a single latest imported metric
object per keyword; this layer cannot recover a full history of distinct import
files or vendor provenance beyond the stored filename. Timestamped import
snapshots and multiple-provider history would require a separate migration.
