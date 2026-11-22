# Local SEO & Publication Evidence

This module adds two site-scoped, **read-only** analytical endpoints and a dashboard:

- `GET /api/sites/{site_id}/local-action-plan`: checklist from the existing
  imported local-business citations (name, address, phone, URL) and the statuses
  of manually tracked review-request work items.
- `GET /api/sites/{site_id}/publication-evidence`: manual publication records
  matched against existing backlink records by **source URL** and, where supplied,
  exact **target URL**.

The application does **not** access a Google Business Profile, does not read or
solicit real reviews, does not send invitation emails, does not verify external
publication pages live, and does not predict local pack rankings.

NAP discrepancies are string-based review prompts, not assertions of incorrect
business data. Differences in telephone formats or legitimate multiple
locations can trigger false positives.

A status of `live` is only the status of a backlink verification record.
It does not imply an editorial article, a dofollow endorsement, indexation,
ranking influence, referral traffic, or current continued existence of the link.
Last checked timestamps and `nofollow` information remain visible.

Review requests must be distributed without selective positive-review gating,
incentives, or fabricated review content. The public implementation is deliberately
industry-agnostic and includes no preloaded profiles, company names, statistics
or credentials.
