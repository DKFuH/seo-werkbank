# Search change and visibility observation workbench

This module gives four **read-only, evidence-labelled** views on top of data
already stored for a site:

1. **Change timeline:** user-entered update events compared with the closest
   same-provider rank observations 14 days before and 14 days after the event.
   Changes are correlations, not evidence that an event caused a ranking shift.
2. **SERP features:** counts of features recorded in rank snapshots or in
   manual/imported research observations, split by source. The count is not
   market share or a measurement across all Google SERPs.
3. **Indexing:** manually recorded index reports compared with the latest
   technical crawl flags (canonical, indexable, technical reason). Technical
   crawl indexability is not Google's confirmed indexing state. A real Google
   URL Inspection API adapter is not yet connected.
4. **GEO citations:** aggregation of user-reported URLs from the AI visibility
   ledger and manually recorded prompt responses. No independently verified
   AI-platform mention rate, no visitor/referral tracking, no search fan-out.

Endpoints:
- `/api/sites/{site_id}/research/change-timeline`
- `/api/sites/{site_id}/research/serp-features`
- `/api/sites/{site_id}/research/indexing-review`
- `/api/sites/{site_id}/research/geo-citations`

The dashboard is `/research-monitoring`; records can be entered using
`/research`. Every API request checks site ownership and limits row counts.
