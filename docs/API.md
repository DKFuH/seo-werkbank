# API Guide

The complete, always-current reference is generated from the code:

- Swagger UI: `http://localhost:8000/api/docs`
- ReDoc: `http://localhost:8000/api/redoc`
- OpenAPI schema: `http://localhost:8000/api/openapi.json`

All endpoints live under `/api`. Most accept and return JSON; uploads use multipart form data, and exports may return files. Except for explicitly public endpoints, calls require
`Authorization: Bearer <token>`.

## SEO-Operations API (Stand: PR #49)

Sämtliche Pfade in dieser Tabelle haben das Präfix `/api`, benötigen ein authentifiziertes Bearer-Token und prüfen die Berechtigung auf die jeweilige Website. Alle URL-Prüfungen und Exporte erfolgen ohne Änderung am Webserver.

| Bereich | Methode und Pfad | Zweck / Grenze |
|---|---|---|
| Redirects | `GET/POST /sites/{site_id}/redirects` | Regeln anzeigen / neuen unfreigegebenen Entwurf anlegen; gleiche Website-Domain erforderlich |
| Redirects | `PATCH /sites/{site_id}/redirects/{rule_id}` | Nur unfreigegebene Entwürfe bearbeiten |
| Redirects | `POST /sites/{site_id}/redirects/{rule_id}/approve\|reject\|reopen` | Manuelle Entscheidung; Konflikte blockieren Freigabe |
| Redirects | `POST /sites/{site_id}/redirects/suggest` | Vorschläge aus letztem Crawl (keine Fachentscheidung) |
| Redirects | `POST /sites/{site_id}/redirects/simulate` | Snapshot-Prüfung ohne Live-Serverabruf |
| Redirects | `GET /sites/{site_id}/redirects/export?format=apache\|nginx\|csv` | Nur freigegebene Regeln, als Konfigurationsentwurf |
| Logfiles | `POST /sites/{site_id}/logs/import` | Multipart: `file` und `fmt=auto\|common\|combined`, Job-Antwort enthält `job_id` |
| Logfiles | `GET /sites/{site_id}/logs`, `GET /sites/{site_id}/logs/summary?import_id=…` | Importverlauf und aggregierte Auswertungen |
| Logfiles | `DELETE /sites/{site_id}/logs/{import_id}` | Gespeicherte Aggregate eines abgeschlossenen/fehlgeschlagenen Imports löschen |
| Logfiles | `POST /sites/{site_id}/logs/404/redirect` | 404-Pfad und Ziel zu einem **nicht freigegebenen** Redirect-Entwurf zusammenführen |
| Schema | `GET /sites/{site_id}/schema-manager/pages` | Crawl-Seiten zur Auswahl |
| Schema | `POST /sites/{site_id}/schema-manager/prefill` | JSON-LD aus Crawl-Werten, Diff und HTML-escaped Beispiel erzeugen |
| Schema | `POST /sites/{site_id}/schema-manager/proposals` | Separat freizugebende JSON-LD-Content-Maßnahme speichern |
| Schema | `GET/POST /sites/{site_id}/schema-manager/templates` | Site-scoped JSON-LD-Templates verwalten |
| Schema | `PUT/DELETE /sites/{site_id}/schema-manager/templates/{template_id}` | Template ändern/löschen |
| Bing | `GET /bing/sites` | Websites des Bing-API-Schlüssels (Einstellung `bing.api_key`) |
| Bing | `GET /sites/{site_id}/bing/overview?site_url=…` | Suchanfragen (Wochenwerte je Anfrage summiert, Position impressionsgewichtet) und Bingbot-Crawlstatistik; ohne `site_url` Zuordnung über die Domain |
| IndexNow | `GET /sites/{site_id}/indexnow/status` | Schlüsseldatei prüfen und Kandidaten seit dem vorherigen Crawl: `new`, `changed`, `removed` (404/410, vorher indexierbar) mit Zählern |
| IndexNow | `POST /sites/{site_id}/indexnow/submit` | Body `source`: `manual\|new\|changed\|removed\|new_changed\|all`, bei `manual` zusätzlich `urls`; nur URLs des eigenen Hosts, Antwort mit IndexNow-Status. Hinweis, keine Indexierungsgarantie |
| Schema | `POST /sites/{site_id}/schema-manager/templates/{template_id}/preview` | Bis zu 30 passende Seiten vorbefüllt ansehen, keine Veröffentlichung |
| Content-Freigabe | `GET/PUT /sites/{site_id}/seo-work/{item_id}/content-proposal` und `POST …/approve` | `proposed_text` ist rohes JSON; bei JSON-LD ist `safe_html` der sicher serialisierte Script-Block |

**Fehlerfälle:** Redirect-Dubletten werden datenbankseitig durch Migration `0013` verhindert und ergeben `409 Conflict`. Nach unerwarteten Log-Jobstartfehlern bleibt der Import als `failed` löschbar. `404`-Vorschläge und Schema-Prüfungen sind keine Belege für eine bereits umgesetzte Änderung oder für Google-Rich-Result-Berechtigung.

## Authentication

| Method | Path | Notes |
|---|---|---|
| GET | `/auth/status` | Public. Whether any account exists and whether registration is open |
| POST | `/auth/register` | `{email, password}`; the first account becomes administrator |
| POST | `/auth/login` | `{email, password}` → `{access_token, user}` |
| GET | `/auth/me` | Current user |
| POST | `/auth/password` | Change password |

## Endpoint groups

| Area | Endpoints (prefix `/api`) |
|---|---|
| Sites | `GET/POST /sites`, `GET/PATCH/DELETE /sites/{id}`, `GET /sites/{id}/overview`, `GET /dashboard` |
| Crawls | `POST/GET /sites/{id}/crawls`, `GET/DELETE /crawls/{id}`, `POST /crawls/{id}/cancel`, `GET /crawls/{a}/compare/{b}` |
| Crawl data | `GET /crawls/{id}/pages` (search, filters, sort, pagination), `/pages/{page_id}`, `/links`, `/redirects`, `/duplicates` |
| Audit | `GET /crawls/{id}/issues`, `/issues/{rule_id}`, `GET /rules` (public rule catalogue). Regeln und Befundgruppen enthalten `classification`, `profiles` und `search_engines.{bing,brave}` mit `status`, `evidence` (`quoted`\|`topic`), `section`, `quote`, `source_status`; die Zusammenfassung zusätzlich `profile_scores` (Google, Bing, Brave, GEO) |
| Architecture | `GET /crawls/{id}/internal-links`, `/link-opportunities`, `/graph` |
| Sitemaps / schema / i18n / local | `GET /crawls/{id}/sitemaps`, `/sitemap.xml`, `/schema`, `/hreflang`, `/local`; `POST /sites/{id}/citations/import` |
| Exports | `GET /crawls/{id}/export?dataset=pages|issues|links|broken_links|redirects|all&format=csv|xlsx|json`, `GET /crawls/{id}/report.pdf` |
| Keywords | `POST /keywords/suggest`, `/keywords/cluster`, `/keywords/intent`; `GET/POST/DELETE /sites/{id}/keywords`, `/keywords/import`, `/keywords/mapping`, `/keywords/export` |
| SERP | `GET /serp/providers`, `POST /serp/analyze` |
| Content | `POST /content/analyze`, `POST /content/fetch` |
| Schema tools | `GET /schema/types`, `POST /schema/validate`, `POST /schema/generate` |
| Page speed | `GET /pagespeed/status`, `POST /pagespeed/run`, `GET /pagespeed/history`, `GET /pagespeed/{id}` |
| Competitors | `GET/POST /sites/{id}/competitors`, `DELETE .../{cid}`, `POST .../{cid}/crawl`, `GET .../report.pdf` |
| Backlinks | `GET /sites/{id}/backlinks`, `/backlinks/summary`, `POST /backlinks/import`, `/backlinks/verify`, `GET /backlinks/export`, `DELETE /backlinks` |
| Search Console | `GET /gsc/status`, `/gsc/auth-url`, `/gsc/properties`, `POST /gsc/disconnect`; `POST /sites/{id}/gsc/sync`, `/gsc/import`, `GET /gsc/performance`, `/gsc/insights`, `DELETE /gsc/data` |
| Monitoring | `GET /monitoring/kinds`, `GET/POST /sites/{id}/monitors`, `PATCH/DELETE /monitors/{id}`, `POST /monitors/{id}/run`, `GET /alerts`, `POST /alerts/read`, `GET /alerts/export` |
| Link context | `GET /crawls/{id}/link-opportunities/context` |
| Content refresh / value | `GET /sites/{id}/content-refresh` (value scenarios are computed in the browser) |
| SEO work items | `GET/POST /sites/{id}/seo-work`, `PATCH/DELETE .../{item}`, `GET/POST .../{item}/snapshots` |
| Content proposals | `GET/PUT /sites/{id}/seo-work/{item}/content-proposal`, `POST .../approve`, `/reopen`, `/mark-published` |
| AI visibility | `GET/POST /sites/{id}/ai-visibility/observations`, `DELETE .../{observation}` |
| Competitor radar / local evidence | `GET /sites/{id}/competitor-topic-radar`, `/local-action-plan`, `/publication-evidence` |
| Rank tracker | `GET/POST /sites/{id}/rank-targets`, `DELETE .../{target}`, `POST .../{target}/observations`, `POST .../{target}/capture` |
| SEO research | `GET/POST /sites/{id}/research`, `PATCH/DELETE .../{record}`; `GET /sites/{id}/research/topic-coverage`, `/question-tree`, `/journeys`, `/content-evidence`, `/cro-audit`, `/comparison-review`, `/asset-briefs`, `/change-timeline`, `/serp-features`, `/indexing-review`, `/geo-citations` |
| Conversion & trust | `GET /sites/{id}/conversion-trust` |
| Jobs | `GET /jobs`, `GET /jobs/{id}`, `POST /jobs/{id}/cancel` |
| Settings (admin) | `GET/PUT /settings` |
| AI (optional) | `GET /ai/status`, `POST /ai/run` |
| System | `GET /health` (public) |

Long-running operations (crawls, backlink verification, Search Console sync, monitor runs) return `202` with a `job_id`; poll
`GET /jobs/{id}` until `status` is `completed`, `failed` or `cancelled`.

## Example: audit a site from a script

```bash
BASE=http://localhost:8000/api
TOKEN=$(curl -s $BASE/auth/login -H 'Content-Type: application/json' \
  -d '{"email":"you@example.com","password":"your password"}' | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
AUTH="Authorization: Bearer $TOKEN"

# create the site and start a crawl
SITE=$(curl -s $BASE/sites -H "$AUTH" -H 'Content-Type: application/json' -d '{"name":"Example","url":"https://example.com"}' \
  | python -c "import sys,json;print(json.load(sys.stdin)['id'])")
CRAWL=$(curl -s $BASE/sites/$SITE/crawls -H "$AUTH" -H 'Content-Type: application/json' -d '{"max_urls":200}')
CRAWL_ID=$(echo $CRAWL | python -c "import sys,json;print(json.load(sys.stdin)['id'])")
JOB_ID=$(echo $CRAWL | python -c "import sys,json;print(json.load(sys.stdin)['job_id'])")

# wait for it
until curl -s $BASE/jobs/$JOB_ID -H "$AUTH" | grep -Eq '"status":"(completed|failed|cancelled)"'; do sleep 3; done

# results
curl -s $BASE/crawls/$CRAWL_ID/issues -H "$AUTH"
curl -s -o audit.pdf  "$BASE/crawls/$CRAWL_ID/report.pdf" -H "$AUTH"
curl -s -o crawl.xlsx "$BASE/crawls/$CRAWL_ID/export?dataset=all&format=xlsx" -H "$AUTH"
```

## Conventions

- Pagination: `page` (1-based) and `per_page` (max 500); responses contain `total`, `page`, `per_page`, `items`.
- Errors: `{"detail": "message"}` (or FastAPI's validation array for 422). Objects owned by another user return 404.
- Rate limits: 600 requests/minute per IP by default (10/minute for login and registration); exceeding them returns 429.
- Provenance: responses that include estimates carry a `method`, `basis`, `note` or `status` field saying so.

## Content-Gap-Analyse

- `GET /api/sites/{site_id}/content-gap?days=90&min_impressions=10&limit=80`: Authentifizierte, datumsbezogene GSC-Query-URL-Paare mit letztem Crawl abgleichen. Gibt Kategorien, Messwerte, URL-Belege und methodische Warnungen zurück. Begrenzt auf 10.000 Paare und 4.000 Seiten; kein Suchvolumen.
- `POST /api/sites/{site_id}/content-gap/work` mit `{query,target_url,action}`: Erstellt ausschließlich eine geplante Content-Maßnahme auf der eigenen Website, keine CMS-Veröffentlichung. `action` ist `expand`, `new_candidate` oder `review`.

Details: [Content-Gap-Analyse](CONTENT_GAPS.md).

## Intelligence-Module (PRs #54–#57)

Alle Endpunkte sind auf den Eigentümer der ausgewählten Website beschränkt und beginnen mit `/api`:

- `GET /sites/{id}/content-intelligence?days=28`: GSC-Decay, URL-Überschneidung und Query-Trends.
- `GET /sites/{id}/index-intelligence/candidates|history|sitemap-history`: Crawl-Vorschläge, Google-Indexstatus-Historie und Sitemap-Zeitreihe.
- `POST /sites/{id}/index-intelligence/inspect` mit `{\"limit\": 1..10}`: Echte Google-URL-Inspection-Abfragen, kein Live-Test und keine Indexierungsanforderung.
- `POST /sites/{id}/seo-work/{item_id}/editorial-qa`: Analyse eines **noch nicht gespeicherten** redaktionellen Entwurfs; `GET` analysiert gespeicherten Entwurf.
- `GET/POST /sites/{id}/reports/snapshots` sowie `GET /sites/{id}/reports/snapshots/{snapshot_id}.html|.pdf`: archivierte Berichte ohne nachträgliche Messwertänderung.
- `GET /sites/{id}/link-recovery`, `POST /sites/{id}/link-recovery/{backlink_id}/work`: importierte/verifizierte verlorene Links und manuelle Recovery-Maßnahmen.
- `GET /sites/{id}/external-intelligence/status`, `PUT /sites/{id}/external-intelligence/config`, `DELETE /sites/{id}/external-intelligence/config/{provider}`: je Website verschlüsselte GA4-/Clarity-/DataForSEO-Anbieterzugänge, keine Geheimnisse in GET-Antworten.
- `GET /sites/{id}/external-intelligence/ga4|clarity`: **nur echte externe Daten**, Clarity mit lokalem Tageslimit.
- `POST /sites/{id}/external-intelligence/local-rank` mit `{\"target_id\": N, \"acknowledge_cost\":true}`: **zwei explizite kostenpflichtige** DataForSEO-Anfragen für Organic/Maps; Rank-Beobachtungen mit getrennter Anbieterherkunft.

Kein Endpoint bewirkt CMS-Veröffentlichung, externen Outreach oder automatisches Disavow.
