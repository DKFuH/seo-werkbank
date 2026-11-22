# AI prompt tests and optional Matomo referral observations

Generic, site-owned, explicitly sampled prompts:
- A prompt and exact brand/competitor comparison strings are stored per test.
- A user can paste a real answer and label the provider, model and timestamp.
- A deliberate click can also query a **configured** Ollama or OpenAI-compatible chat
  provider with exactly the stored prompt. This is **not** a live web search,
  does not verify citations, and can incur model API costs.
- The displayed matches are lexical phrase matches, not provider rankings,
  genuine brand recommendations, independent citations or search share.

Instance-wide configured AI-model execution and Matomo referral retrieval are **administrator-only**.\nOther site users may create prompts and save their own manual observations without accessing shared provider credentials.\n\nMatomo attribution is **only** a filtered, read-only referrer report:
- Explicit user action; Matomo token is never returned by the API.
- The Matomo site must have the same domain as the registered site.
- A fixed whitelist of recognizable AI referral hostnames prevents counting
  lookalike domains.
- Conversions are shown **only if Matomo actually returned referrer-specific
  conversion fields**. A blank value is not silently treated as zero.
- Dark traffic, direct visits, post-view conversions, sales/DB, cross-device
  attribution and unauthenticated search assistant users are not represented.

UI: `/ai-intelligence`; endpoints:
`GET/POST /api/sites/{site_id}/ai-prompt-tests`,
`POST /ai-prompt-tests/{id}/samples`, `POST /ai-prompt-tests/{id}/run`,
`DELETE /ai-prompt-tests/{id}`, `GET /api/sites/{site_id}/ai-referrals`.

Requires migration 0007 (stacked on migrations 0001–0006).
No ongoing monitoring or hidden automatic paid model calls.
