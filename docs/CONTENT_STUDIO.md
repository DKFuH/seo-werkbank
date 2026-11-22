# Evidence-led Content Studio

The public, industry-agnostic studio works with four new kinds of site-owned
research record created under `/research`:

- **Case studies:** project, challenge, approach, outcome, an intended site
  URL and optionally a supporting link and note. The output is a deterministic
  formatting of submitted facts, not a generated success narrative. A button
  can create a `SeoWorkItem` and `SeoContentProposal` in **draft** status.
  A separate review/approval is required; the app never publishes to a CMS.
- **Buyer questions:** anonymized customer questions, context, target audience
  and optional proposed article URL. No search-volume estimate is implied.
- **Brand consistency:** literal comparison between submitted source statements
  and expected statements; the source URL's existence and truth are unverified.
- **Marketing experiments:** hypothesis, metric, unit, date, optional baseline,
  follow-up, costs and source note. The display calculates arithmetic differences
  only when both numeric values are explicitly supplied; no causal attribution
  or ROI prediction.

No project-specific company data or marketing claims are hardcoded. Avoid
adding personal customer information to the public app unless independently
authorized and protected.

UI `/content-studio`; GET `/api/sites/{site_id}/content-studio`;
POST `/api/sites/{site_id}/content-studio/case-studies/{record_id}/draft`.
All endpoints enforce website ownership. Existing content proposal approval
rules remain authoritative; the case-draft endpoint never approves or publishes.
