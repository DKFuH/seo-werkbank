# Ranktracking

The rank tracker (`/rank-tracking`) has three tabs.

## Portfolio (GSC) and all GSC queries

- Positions come from Search Console rows: impression-weighted average position per query, for the selected period ending at the newest GSC day, compared with the equally long period directly before. API rows win over CSV rows of the same days.
- Tracked keywords carry label, target URL, measurement (national, local, brand) and priority 1–3. The ranking URL is the page with the most impressions for the query in the period; a different path than the target URL is flagged.
- Buckets 1–3, 4–10, 11–20, 21–50, 51+. Fewer than 10 impressions = small sample.
- All queries: top-3 discovery = untracked, position ≤ 3, ≥ 10 impressions; opportunity = untracked, position 4–20, ≥ 10 impressions. "Ins Monitoring" tracks the query; its history is matched by lower-cased text.
- Device filter uses the `query_device` dataset (date × query × device) from the Search Console sync; CSV imports do not provide it.
- Keyword detail: trend (daily up to 28 days, weekly beyond) and a change journal shown as markers.
- API: `/api/sites/{id}/rank-gsc/portfolio`, `/queries`, `/keywords/{id}`, `/adopt`, notes.

## Provider measurements: target-specific observations

- Explicit keyword, country, language, device and optional intended URL.
- Observation history with its **real provenance**: manually entered, CSV-imported or the configured supported SERP provider.
- Provider capture is possible only for desktop without city targeting. The existing optional provider may return Brave, Google Programmable Search or SearXNG results. Their order is **not a neutral, verified Google ranking**.
- No automatic hourly/daily schedule, no Google scraping, no independent keyword database. No provider is queried without explicit user action.
- Deltas are reported only between two consecutive observations from the same source.
- Provider capture counts a result as the own site when its host equals the site host or is a subdomain of it; a leading `www.` is
  ignored on both sides (`www.example.de` and `example.de` are the same site).
- Timestamps sent with a UTC offset are converted to UTC before they are stored.
- A missing URL in the first 10 results means only "not found in first 10", not "not indexed".
- Each route verifies ownership of the site and target.
