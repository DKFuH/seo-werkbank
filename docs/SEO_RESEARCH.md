# SEO-Research workspace – sources and limitations

A generic, site-scoped editorial research ledger stores manually entered or imported evidence.
The feature is industry-agnostic and **does not** scrape Google PAA or assert official
search-engine factors.

The initial endpoints support:
- **Business-first topical map:** offers and attributes vs. actually crawled page headings.
  Results are lexical hints, not semantic topic coverage or ranking probability.
- **Question tree:** manually observed PAA-style questions, grouped by topic, with optional
  source URLs. No automatic extraction from Google.
- **Search journey:** planned page-to-page transitions checked against internal links in the
  latest crawler snapshot. This is not observed user behavior.
- Additional record schemas for content evidence, CRO, comparisons, index notes, SERP features,
  change events, AI citations and linkable asset plans. Dedicated analyzers may be extended separately.

Read and write operations check the owner of the site. Payloads are size-limited,
categories are explicitly listed, and all source data is recorded as manual/imported.

API: `GET/POST /api/sites/{site_id}/research`, `PATCH/DELETE /api/sites/{site_id}/research/{id}`,
plus `/research/topic-coverage`, `/research/question-tree` and `/research/journeys`.
