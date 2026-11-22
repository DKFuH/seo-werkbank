# Conversion & Trust Intelligence

This industry-agnostic module builds on the site-scoped SEO research records.

- **Funnel steps:** action, stage, intended URL, manually observed friction, form field notes and optional evidence.
- **Trust proofs:** named claim, optional external proof URL, type of evidence.
- **Brand profiles:** positioning, offer, target audience and source.
- **Crawl reconciliation:** actual title/H1/meta and lexical CTA hints for URLs with records.

Missing evidence is marked explicitly. An entered URL does **not** prove a
certification, testimonial, award or claim is genuine. A CTA word is not a
visual landing-page test. The absence of a documented funnel stage is not proof
that a website lacks that stage.

No automated review scraping, trust score, invented premium positioning score,
private customer data, Form submission automation or conversion lift attribution.

UI: `/conversion-trust`; entry forms: `/research`
API: `GET /api/sites/{site_id}/conversion-trust`
All routes check ownership of the selected site.
