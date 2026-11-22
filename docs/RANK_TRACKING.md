# Ranktracking: target-specific observations

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
