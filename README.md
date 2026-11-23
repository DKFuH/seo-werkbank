# SEO-Werkbank

Selbst gehostetes SEO-Werkzeug mit deutscher Oberfläche: Crawler, technisches Audit, interne Verlinkung,
Keyword-Recherche, SERP- und Content-Analyse, **WDF\*IDF**, **GEO-Check** für KI-Suchsysteme, Search Console,
**Matomo**, PageSpeed, Monitoring und Berichte. Läuft auf dem eigenen Rechner, die Daten bleiben dort.

SEO-Werkbank ist eine Weiterentwicklung von [OpenSEOSuite](https://github.com/Sushang-Agnihotri/OpenSEOSuite)
(MIT-Lizenz, © The OpenSEOSuite contributors). Die ursprüngliche Dokumentation liegt unter
[docs/UPSTREAM_README.md](docs/UPSTREAM_README.md); Architektur, Sicherheit und Installation gelten unverändert.

## Hilfe, Keyword-Clustering und Demo

- **Integrierte Hilfe** unter `/help`: direkte Verweise zu Werkzeugen und passenden Handbuchkapiteln.
- **SERP-basiertes Keyword-Clustering** im Cluster-Werkzeug; 2–15 Keywords, tatsächlich erfasste SERP-URL-Listen oder ein konfigurierter Anbieter ([Anleitung](docs/KEYWORD_SERP_CLUSTERING.md)).
- **Screenshots und kurzer Rundgang:** Mit `python scripts/capture_demo.py` auf einer gestarteten Installation aufnehmen. Das Skript erzeugt authentische PNG-Screenshots und ein WebM-Video unter `docs/media/generated/`. **Im GitHub-CI-Job `demo-capture` werden echte Screenshots und eine WebM-Aufnahme einer isolierten Testinstallation als Workflow-Artefakt erzeugt.** Die Aufnahmen werden nicht automatisch im README veröffentlicht. Vor einer Übernahme in das Repository müssen die Artefakte geprüft werden.
- **0.2 Integrationen:** [verschlüsselte Zugangsdaten](docs/SECURE_INTEGRATIONS.md), [Google URL Inspection](docs/GSC_URL_INSPECTION.md), [SMTP/Webhooks und Batch-PageSpeed](docs/NOTIFICATIONS_PAGESPEED.md).

## Bedienung: Benutzerhandbuch und Schnellstart

**Neu hier?** Beginne mit dem [Schnellstart für Anwender](docs/SCHNELLSTART.md):
Installation, erste Website, Crawl, Google Search Console und Content-Maßnahme.

Das ausführliche **[Benutzerhandbuch](docs/BENUTZERHANDBUCH.md)** erklärt Schritt für Schritt
**wo du klickst, welche Daten benötigt werden, was das Ergebnis bedeutet und wie die
Funktionen zusammenarbeiten** – einschließlich Admin-Einstellungen, Importen,
Crawling, Keyword-Recherche, KI-Sichtbarkeit, Content-Freigabe, Matomo, Monitoring,
Exporten und Fehlerbehebung.

- **Browser- und Bilddiagnostik:** Consent-Request-Zeitfolgen, Roh-/JS-Rendering und Markup-Hinweise für mögliche LCP-Bilder ([Anleitung](docs/TECHNICAL_DIAGNOSTICS.md)).

- **Erweiterte Audits** in den passenden Bereichen: SERP-Überschneidung (SERP-Analyse), Relaunch-Vergleich (Crawler),
  Paginierung (Interne Verlinkung) und Rich-Result-Potenzial (Strukturierte Daten) ([Anleitung](docs/ADVANCED_SEO.md)).

- **Verzeichnisse & KI-Quellen:** Verzeichnisbewertung (Lokale Nachweise) und wiederkehrende KI-Zitate
  (KI-Erwähnungen) ([Anleitung](docs/AUTHORITY_INTELLIGENCE.md)).

## Was gegenüber OpenSEOSuite dazugekommen ist

- **Deutsche Oberfläche**: alle Seiten, die 95 Audit-Regeln, Hinweise und Fehlermeldungen; deutsche Zahlen- und
  Datumsformate. KI-Antworten (optional, Ollama oder OpenAI-kompatibel) auf Deutsch.
- **Deutsche Exporte**: Search-Console-, Keyword-Planer- und Links-CSVs mit deutschen Spaltennamen und Zahlen
  (`1.234`, `8,47`) werden korrekt gelesen.
- **WDF\*IDF-Analyse** (`/wdf-idf`): eigene URL oder Entwurf gegen bis zu zehn Wettbewerber-URLs,
  WDF = log2(f+1)/log2(L+1), IDF = log10(1+N/n), deutsche Stoppwörter, optional Zweiwort-Begriffe,
  Drittelverteilung und Überschriftenvergleich. Zusätzlich direkt in der Content-Optimierung.
- **GEO-Check** (`/geo`): KI-Crawler in robots.txt (OAI-SearchBot, Claude-SearchBot, PerplexityBot, GPTBot …),
  llms.txt, Entität und sameAs, Autor, Aktualität, Antwortstruktur, Listen, Zahlen und Quellen. Dazu Snippet-Grenzen,
  versteckte Anweisungen an KI-Systeme (Prompt-Injection), sichtbare strukturierte Daten, stimmige Datumsangaben, ein
  einheitlicher Markenname und auf Knopfdruck ein Test, ob das CDN KI-Crawler per User-Agent abweist.
- **Matomo** (`/matomo`): Besuche, Kanäle, Einstiegsseiten, Ziele und Geräte aus der Reporting-API, verknüpft
  mit dem letzten Crawl, inklusive indexierbarer Seiten ohne Besuch.
- **Content-Refresh** (`/content-refresh`): GSC-Query-URL-Chancen, redaktionelle Prüfhinweise und kopierbare Briefings;
  keine automatische Veröffentlichung. Details: [Content-Refresh](docs/CONTENT_REFRESH.md).
- **Wirtschaftliche SEO-Chancen** (`/opportunity-value`): Nutzerdefinierte Lead-, Abschluss- und DB-Annahmen
  sowie manuelle Seitenrelevanz; Szenarien, keine Umsatzprognosen.
- **SEO-Maßnahmen** (`/seo-work`): manuelles Tracking für redaktionelle Inhalte, Bewertungen,
  Veröffentlichungen, lokale SEO-Maßnahmen und Wettbewerbsbeobachtungen, GSC-Vergleichsmessungen.
  Details: [SEO-Maßnahmen](docs/SEO_WORKFLOW.md).
- **Linkkontext** (`/internal-links`): zu bestehenden internen Linkchancen eine echte Textpassage der Quellseite und ein
  Ankervorschlag; keine automatische Linksetzung.
- **KI-Erwähnungen** (`/ai-visibility`): manuelle, zeitgestempelte Beobachtungen zu Markennennungen
  und belegten URLs; keine Live-Überwachung oder erfundene AI-Rankings.
- **Wettbewerber-Themenradar** (`/competitor-radar`): thematische Wortpaare aus tatsächlichen
  Wettbewerber-Crawls mit belegbaren Quellseiten; keine erfundenen Rankings oder Volumina.
- **Lokales SEO & Nachweise** (`/seo-evidence`): Aktionsplan aus importierten NAP-Daten,
  manuell erfassten Bewertungsanfragen und Abgleich von Publikationen mit Backlink-Datensätzen.
- **Content-Entwürfe** (`/content-proposals`): gespeicherter Ausgangstext und Entwurf,
  Diff, gesonderte Freigabe sowie rein manuelle Dokumentation einer Veröffentlichung.
- **Ranktracker** (`/rank-tracking`): ausgewählte Zielkeywords, dokumentierte Positionshistorie und
  manuelle oder anbieterbezogene SERP-Beobachtungen. Keine unabhängige Google-Messung.
- **SEO-Research** (`/research`): mandantengetrennte Themen- und Fragenhierarchien,
  Suchreise-Planung, belegbare Beobachtungen und Rechercheprotokolle.
- **Qualität & CRO** (`/research-quality`): transparente Content-Nachweise, Landingpage-Textsignale,
  Quellenprüfung für Vergleiche und QA-Checklisten für Linkable-Assets.
- **SEO-Verlauf & GEO** (`/research-monitoring`): erfasste Ereignisse mit Positionshistorie,
  beobachtete SERP-Features, Indexierungs-Crawl-Abgleich und KI-Zitationsstichproben.
- **Conversion & Trust** (`/conversion-trust`): dokumentierte Funnel-Stufen, Vertrauensbelege
  und Markenpositionierungen im Abgleich mit dem Website-Crawl.
- **KI-Stichproben & Referrals** (`/ai-intelligence`): explizite Prompttests, manuelle oder
  konfigurierte Chatmodellantworten und optionale Matomo-Referrals (keine garantierte KI-Suche).
- **Content Studio** (`/content-studio`): Fallstudien aus erfassten Fakten als freizugebende
  Entwürfe, Käuferfragen, Markenabgleich und Marketing-Experimente.
- Deutsche Stoppwörter auch in SERP-Analyse und Content-Optimierung; deutsche Signalwörter für kommerzielle
  Suchintention.

## Docker-Gesamtausgabe mit SearXNG

Mit einem Kommando SEO-Werkbank, PostgreSQL und eine **interne** SearXNG-Metasuche
starten (Docker Compose v2 und Python 3.11+ erforderlich):

```bash
python scripts/full_stack.py up
```

Danach <http://localhost:8000> öffnen und den ersten Administrator anlegen.
Passwörter/Secrets werden beim ersten Start zufällig erzeugt und in der
ignorierten `.env` gespeichert. Die Metasuche wird nur innerhalb des Docker-Netzes
erreichbar sein und in der App automatisch vorausgewählt, solange noch kein
SERP-Anbieter gespeichert wurde. Das bisherige einfache Docker-Setup bleibt erhalten.

**Anleitung, Sicherheit, Updates und Backups:** [Docker-Gesamtausgabe](docs/DOCKER_FULL.md).

## Lokaler MCP-Zugang (optional)

Ein schreibgeschützter MCP-Server für Desktop-KI-Assistenten verbindet sich über einen
lokal laufenden SEO-Werkbank-REST-Server und einen normalen Benutzerzugang.
Keine freigegebenen Schreibwerkzeuge, kein öffentliches MCP-HTTP und keine Umgehung
von Website-Berechtigungen. [Installation und Sicherheitsgrenzen](docs/MCP_SERVER.md).

## Schnellstart (Windows, ohne Docker)

```bash
cd backend
python -m venv .venv
.venv\Scripts\pip install -e ".[dev]"
cd ../frontend
npm install
npm run build
```

Danach `start-seo-werkbank.cmd` ausführen und <http://localhost:8000> öffnen. Beim ersten Aufruf wird das
Administratorkonto angelegt. Docker und PostgreSQL funktionieren wie in der
[Originaldokumentation](docs/UPSTREAM_README.md) beschrieben.

Matomo: in Matomo unter *Persönlich → Sicherheit* einen Auth-Token mit Leserechten anlegen und unter
*Einstellungen → Matomo* zusammen mit der Matomo-URL eintragen.

## Datenanbieter-Schnittstelle (optional erweiterbar)

Ein quellennachvollziehbares, lesendes Provider-Register macht vorhandene GSC-,
Keyword-Import- und Backlink-Daten einheitlich abrufbar. Suchvolumen, Rankings
oder Backlink-Indizes werden **nicht** ohne Datenquelle erfunden. Erweiterung und
Schnittstellen: [Datenanbieter](docs/SEO_DATA_PROVIDERS.md).

## Tests

```bash
cd backend && .venv\Scripts\python -m pytest -q
cd frontend && npx vitest run
```

## Lizenz

MIT, siehe [LICENSE](LICENSE). Der Copyright-Vermerk von OpenSEOSuite bleibt erhalten.
