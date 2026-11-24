# Known Limitations

Read this before relying on the platform for decisions. Nothing here is hidden behind a paid tier; these are limits of free data and of
the current implementation.

## Data that does not exist for free

- **No web-scale backlink index.** Backlink features analyse datasets you import (Search Console link exports, exports from other tools,
  any CSV) and verify them live. Links nobody gave the tool are invisible to it. There is no Domain Rating/Authority equivalent.
- **No search-volume database.** Volumes appear only when you import a Google Ads Keyword Planner file. Search Console impressions are
  shown as the measured alternative for queries your site already appears for.
- **No competitor traffic or ranking-keyword data.** Competitor analysis is limited to what crawling their public site reveals.
- **Rank tracking** is limited to Search Console's average position for your own verified site. There is no per-location, per-device
  daily tracking of arbitrary keywords.
- **Indexed-page counts** cannot be verified without Search Console; sitemap size and indexable crawled pages are shown instead.
- **Google Trends** is not integrated. **Google Analytics 4** is not integrated. Bing Webmaster Tools, IndexNow and Google URL Inspection have implemented integrations but still depend on credentials, permissions and provider availability. **Google Business Profile** requires Google-granted API access and is not implemented.
- **Google Ads Keyword Planner** has no direct API integration; use its CSV export.
- **Bing intelligence is a bounded, on-demand provider sample.** The JSON/HTTP operation signatures are covered by automated
  contract tests, but not every operation and response shape has been verified against an authorized live account. Stored
  snapshots are evidence of the returned payload, not proof of complete site coverage. Temporal content signals are suppressed
  unless each contributing URL/query series covers every expected week in both comparison windows.

## Estimates (always labelled in the UI)

- **Search intent** is a rule-based keyword classifier.
- **Keyword difficulty** is a heuristic from SERP composition. It does not use links and is not comparable with commercial KD scores.
- **Opportunity / extra clicks** multiplies Search Console impressions by a generic CTR-by-position curve.
- **Content score** reflects on-page best practice and comparison with pages you supply; it does not predict rankings.
- **Keyword-to-page mapping** and crawl-based cannibalisation use lexical relevance, not search-engine behaviour.

## Crawler

- **JavaScript rendering** requires installing Playwright and Chromium separately (about 150 MB). It is covered by three automated tests
  (skipped when Chromium is absent) and is much slower than plain fetching. Each browser request is vetted and redirects are refused
  (a rendered page that redirects is not rendered), but DNS is resolved again by the browser stack after our address check, so
  rebinding protection is weaker than for plain HTTP fetching. If the Chromium sandbox cannot start (some containers), set
  `SEO_RENDER_SANDBOX=false`, accepting the added risk.
- **Include/exclude patterns** are plain text with `*`, `^` and `$` (not regular expressions): regular expressions from untrusted input
  can freeze a single-process server.
- **Local Lighthouse** (optional) is administrator-only and runs one audit at a time. Chrome follows redirects itself, so a run can
  *request* an internal address even though the result is then discarded.
- One crawl runs in one process. Around 50 pages/second was measured against a local test site; real sites are bounded by politeness
  delays. Crawls of hundreds of thousands of URLs are possible in principle but untested; memory grows with the link graph.
- Jobs are in-process: a server restart aborts running crawls (they are marked failed and can be restarted).
- Only `<a href>` links and `<img>` sources are followed/checked. Links created by JavaScript events, CSS backgrounds, `srcset`
  candidates and resources inside iframes are not.
- Soft-404 detection, AMP validation and pagination sequence checks (`rel=next/prev` chains) are not implemented.
- External link checks treat 401/403/405/429/999 as "unverifiable", because many sites block automated requests.
- "Mobile friendliness" is assessed from the viewport tag only; there is no rendering-based tap-target or font-size analysis.
  "HTML validation" covers doctype, duplicate `<head>/<body>`, duplicate IDs and charset, not full W3C conformance.
- Response time is time-to-first-byte from the machine running the crawl, not a user-centric metric.

## Structured data

- Validation covers JSON-LD for 25 common types with required/recommended property tables based on Google's public documentation. It is
  not a full schema.org validator, does not validate value formats (dates, URLs, enumerations) and reports Microdata/RDFa types without
  validating them.

## SEO-Operations (Redirects, access logs, JSON-LD)

- **Redirects are planned, not deployed.** The tool proposes and simulates rules but never changes web servers or CMS configuration. Only approved rules can be exported. Apache output is specifically for `.htaccess` at document root, not a virtual-host rewrite context; Nginx uses exact-match locations. Existing server configuration can create conflicts not visible in the simulator.
- **Database migration `0013` is deliberately strict.** If existing rows share `(site_id, source_url)`, the migration stops rather than silently deleting a redirect. Review and resolve duplicates before restarting the upgrade. Concurrent duplicate inserts are rejected with HTTP 409.
- **404-to-redirect candidates are heuristic.** Similar path tokens do not prove equivalent search intent. Candidate comparisons are deliberately capped, so some suitable destinations may not be suggested; final selection and approval are manual.
- **Log parser is intentionally restricted:** Apache/Nginx Common and Combined, with up to two additional trailing quoted fields. Custom `log_format`, JSON logs and arbitrary HTTP variants are not supported. A 64 KiB limit applies per line; longer lines are skipped with bounded buffering. Import and decompression limits still apply.
- **Privacy protection is partial, not guaranteed anonymisation.** Raw log lines, IP addresses, complete User-Agents, referrer paths and query strings are not persisted, but unrecognised personal identifiers may remain in URL paths. Temporary raw files can exist during processing and until recovery after a crash. User-Agent labels such as `googlebot_claim` are not verified by DNS or IP ranges.
- **Jobs are in-process.** On restart, interrupted imports are marked failed and their associated temporary files are removed. Job-start failures are cleaned up, but a process crash before the temporary file is assigned an import ID may leave a staging file until manual/OS cleanup. A missing Googlebot-claim hit in an imported period is not proof of non-indexing.
- **JSON-LD proposals remain raw JSON.** They must not be pasted directly between HTML `<script>` tags. Use the separately HTML-escaped `safe_html` snippet shown for a saved proposal. The validator does not establish schema.org semantic completeness or eligibility for Google Rich Results, and no CMS publishing takes place.
- **Automated CI coverage is not full manual validation.** API checks, Linux/Windows/macOS tests, frontend tests and Docker smoke tests have run, but production server deployments, complete UI click-throughs and every external provider scenario remain unverified.

## Search-engine evidence (Bing, Brave)

- **Mapping level.** A Bing or Brave mapping is either `quoted` (a sentence of the guideline describes the check) or `topic` (the guideline covers the
  subject area only). `topic` rules still count in the engine profile score; treat them as weaker evidence. 12 of the 43 Bing mappings and 2 of the 4 Brave mappings are `topic` only.
- **Sources are snapshots.** Quotes come from the Bing Webmaster Guidelines (local copy, 2026-11-23) and Brave's crawler page (2026-11-23). The Bing page is
  rendered by JavaScript and cannot be fetched automatically, so updates must be re-read by hand. A changed guideline can make a quote stale.
- **Bing AI Preferences are an announcement** (2026-10-30, effective 2027-02-01). Dates and syntax may change; `bing_legacy_ai_directives` only flags
  `noarchive`/`nocache` that apply to Bing (generic or `bingbot`/`msnbot`), not Googlebot-only values.
- **Engine-specific `robots.txt` checks look at the start URL only.** A block of a single path for Googlebot or Bingbot is not reported by
  `robots_googlebot_blocked`/`robots_bingbot_blocked`.
- **Not detected:** `noindex` on a URL that `robots.txt` blocks (blocked URLs are not fetched) and soft-404 pages.
- **Profile scores are not comparable** between engines and are no ranking or compliance estimate.
- **IndexNow is a hint**, not an indexing guarantee, and Google does not take part. Bing and IndexNow were tested with mocked HTTP; no live account was available.

## Content and language

- Readability formulas (Flesch) and the stemmer are calibrated for English. Other languages get tokenised correctly but scores are less
  meaningful. Stop-word removal is English-only.
- Term suggestions are lexical (TF-IDF-style over competitor pages); there are no embeddings or entity extraction.

## SERP analysis

- Needs a provider (self-hosted SearXNG, Google Programmable Search API key, Brave Search API key) or pasted URLs. Provider ordering can
  differ from a live Google result page, and SERP features are limited to what the provider's API reports.

## Search Console

- The OAuth flow needs your own Google Cloud OAuth client. The integration is implemented against the documented API and its parsing and
  reporting logic is tested with imported data, but the live OAuth round-trip was **not verified end to end** during development (no
  Google credentials were available). CSV import is fully tested.
- **URL Inspection API** is implemented at `POST /api/sites/{site_id}/gsc/inspect`. It shows Google's recorded index state, **not** a live URL test or a request for indexation. A real OAuth/Inspection round trip with a verified property remains environment-dependent and was not established by the unit tests.

## Page speed

- PageSpeed Insights tests public URLs only. Without an API key the anonymous quota is small. Field data exists only for pages/origins
  with enough Chrome traffic. Local Lighthouse needs Node.js, the `lighthouse` CLI and Chrome, and was not exercised by automated tests.

## Monitoring

- The scheduler runs inside the API process; monitors do not run while the app is stopped. SMTP (STARTTLS) and HTTPS-webhook notifications are implemented as optional best-effort delivery, disabled by default. They do **not** provide a durable delivery queue; external SMTP/webhook success depends on the deployment configuration.

## Evidence and planning modules (SEO-Werkbank)

- SEO work items, AI observations, research records, funnel steps, trust proofs and comparisons are **manually entered or imported**.
  The app does not verify them; sources are shown as "supplied", never as "verified".
- Matching is lexical (stemmed words), not semantic: content refresh, topic coverage, competitor topic radar and internal link context
  can miss synonyms and paraphrases. The stemmer is tuned mainly for English.
- Competitor topic radar compares only titles and H1s of the latest completed crawls. It says nothing about search volume or rankings.
- Internal link context only covers link opportunities whose target has at least two significant title/H1 words.
- Rank observations from a SERP provider follow that provider's ordering, not Google's. Capture needs a configured provider and works
  only for desktop targets without a city.
- GSC snapshots and the change timeline show temporal changes only; no causal attribution.
- CTA and CRO hints are word matches in page text (for example "jetzt" or "book"); layout, forms and real conversions are not examined.
- The new screens were tested through the API; they have not been clicked through one by one in a browser.

## Keyword portfolio (GSC positions)

- Positions are Search Console averages over all impressions of a query, not a single ranking at one location or time.
- Queries Google anonymises do not appear; totals per keyword are lower than page totals.
- The device filter needs a Search Console sync after this update; CSV imports do not combine query and device.
- Keywords are matched by lower-cased text; spelling variants count as different keywords.

## Website Health

- Checks run from the server SEO-Werkbank runs on, from one location. A problem between that server and the website
  looks like an outage of the website.
- Response time is the total time of the request including redirects and the body (up to 5 MB), measured by this
  server; it is not a browser load time or a Core Web Vital.
- The shortest interval is 15 minutes; outages shorter than one interval can be missed.
- Checks only run while the application runs (in-process scheduler).

## GEO integrity checks

- `noai`/`noimageai` are not part of a standard and the large AI providers do not document support for them; the check
  reports the intent, not an effect.
- The llms.txt draft uses page titles and meta descriptions as crawled and groups by the first path segment. It is a
  starting point; sections and wording need editing before upload.

- Hidden-instruction detection uses fixed English and German phrases; other wording or languages are not found, and a
  match is shown for human review, not judged as an attack.
- The CDN bot-access test sends requests from this server with the crawlers' user agents. CDNs that verify crawlers by
  IP address can treat the real crawler differently in both directions.
- "Schema visible" compares text literally (case and whitespace ignored); values rendered only by JavaScript count as
  not visible.

## Security and multi-user use

- Integration secrets are encrypted at rest using a versioned master key (Fernet). Losing the master key prevents decryption and can prevent startup; backup the key separately from the database. Pre-upgrade backups may still contain older unencrypted secret values.
- Rate limiting is in-memory and per process, intended for a single-instance deployment.
- Access control is per user (each user sees only their own sites). There are no teams, roles beyond admin, or shared workspaces.
- Access tokens cannot be revoked individually before expiry (change `SEO_SECRET_KEY` to invalidate all).

## Not implemented (roadmap)

Custom log formats and verified bot identities · Google Analytics 4 · Google Trends · durable notification delivery/queues · distributed crawling · live-provider end-to-end verification for GSC/Bing/PSI, as applicable.
