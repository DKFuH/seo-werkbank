# Reviewable content proposals

This module stores **manually entered** source text, proposed text and editorial
rationale for a content work item. It does not generate text, fetch content
automatically, modify an external CMS or publish anything.

Workflow:

1. Create a `content` work item under `/seo-work`.
2. Open `/content-proposals` and enter the source text, proposal and rationale.
3. Save draft. The app shows a unified line diff.
4. Explicitly approve the saved draft. While approved the proposal is immutable,
   but it can be explicitly reopened for revision.
5. After actual publication outside this application, mark the approved proposal
   as published. This operation **records the user's declaration**; it does not
   verify publication.

The proposal is immutable after it is marked as published. A new work item is
needed for a further change. Repeated edits during draft stage replace the
previous draft: **this is not a full historical version-control system**.

Read/write API (all routes require ownership of the site):
- `GET/PUT /api/sites/{site_id}/seo-work/{item_id}/content-proposal`
- `POST /api/sites/{site_id}/seo-work/{item_id}/content-proposal/approve`
- `POST /api/sites/{site_id}/seo-work/{item_id}/content-proposal/reopen`
- `POST /api/sites/{site_id}/seo-work/{item_id}/content-proposal/mark-published`

A real CMS adapter, user-level approval roles, an immutable audit log,
evidence/reference validation and effect attribution remain out of scope.
