# SEO-Werkbank

[![CI](https://github.com/DKFuH/seo-werkbank/actions/workflows/ci.yml/badge.svg)](https://github.com/DKFuH/seo-werkbank/actions/workflows/ci.yml)
[![Security](https://github.com/DKFuH/seo-werkbank/actions/workflows/security.yml/badge.svg)](https://github.com/DKFuH/seo-werkbank/actions/workflows/security.yml)
[![Lizenz: MIT](https://img.shields.io/badge/Lizenz-MIT-green)](LICENSE)
![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue)
![Node 20](https://img.shields.io/badge/Node-20-339933)
![Selbst gehostet](https://img.shields.io/badge/selbst%20gehostet-ja-6366f1)
[![Mitmachen](https://img.shields.io/badge/PRs-willkommen-brightgreen)](CONTRIBUTING.md)

**Selbst gehostetes SEO-Werkzeug mit deutscher Oberfläche.** Crawler, technisches Audit mit 122 Regeln,
Search Console, Bing Webmaster Tools, Keyword- und SERP-Analyse, **WDF\*IDF**, **GEO-Check** für KI-Suchsysteme,
Weiterleitungen, Logfile-Analyse, Schema-Management, Matomo, PageSpeed, Monitoring und Berichte.
Läuft auf dem eigenen Rechner, die Daten bleiben dort. Kein bezahlter API-Zugang nötig.

SEO-Werkbank ist eine Weiterentwicklung von [OpenSEOSuite](https://github.com/Sushang-Agnihotri/OpenSEOSuite)
(MIT-Lizenz, © The OpenSEOSuite contributors).

## Leitlinien

- **Keine erfundenen Zahlen.** Jede Angabe ist gemessen, importiert, als Schätzung mit Methode gekennzeichnet oder nicht verfügbar.
- **Freigabe statt Automatik.** Weiterleitungen, Schema und Content-Änderungen entstehen als Entwurf, ein Mensch gibt frei.
  Die Werkbank verändert keine fremden Server und kein CMS.
- **Suchmaschinen getrennt betrachten.** Google, Bing und Brave haben eigene Profile; eine Regel gilt nicht automatisch für alle.
- **Datensparsam.** Logfiles werden nur als Aggregate gespeichert, Zugangsdaten verschlüsselt.

## Funktionen im Überblick

| Bereich | Was dazugehört |
| --- | --- |
| **Analyse** | Site-Audit mit Herkunft je Regel und Scores für Google, Bing, Brave und GEO · Crawler (auch mit JavaScript-Rendering) · Interne Verlinkung · Sitemaps · Strukturierte Daten mit Schema-Management · PageSpeed · Internationales und Lokales SEO · **[Weiterleitungen](docs/REDIRECTS.md)** · **[Logfile und 404-Monitor](docs/LOG_ANALYSIS.md)** |
| **Sichtbarkeit** | Search Console mit URL Inspection · **[Bing und IndexNow](docs/BING_INDEXNOW.md)** · Ranktracker · Keyword-Recherche und SERP-Clustering · SERP-Analyse · KI-Erwähnungen · GEO-Check · Wettbewerber · Backlinks |
| **Content** | Research · Content-Optimierung · WDF\*IDF · Content-Refresh · Content-Entwürfe mit Freigabe · Content Studio · Qualität und CRO |
| **Conversion** | Matomo · Conversion und Trust · wirtschaftliche Chancen |
| **Maßnahmen** | SEO-Maßnahmen mit Vorher-Nachher-Messung · Lokale Nachweise · Website Health · Monitoring · Berichte (PDF, CSV, Excel) |

Die vollständige Liste mit Erklärungen steht in [docs/FEATURES.md](docs/FEATURES.md).

**SEO-Operations nach PR #45:** Redirects werden nur simuliert, freigegeben und als Konfigurationsentwurf exportiert; die `.htaccess`-Ausgabe ist nicht für unveränderte Übernahme in Apache-vHost-Dateien gedacht. Der Logimport verarbeitet begrenzte Common-/Combined-Formate und ermittelt nur nicht verifizierte User-Agent-Indizien. JSON-LD-Content-Entwürfe bleiben rohes JSON; zum Einbetten in HTML steht separat ein sicher serialisierter `safe_html`-Block bereit. Bei Upgrades kann Migration `0013` vorhandene doppelte Redirect-Quell-URLs zur manuellen Prüfung melden. Weitere Details: [Benutzerhandbuch Kapitel 23](docs/BENUTZERHANDBUCH.md#23-seo-operations-redirects-logfiles-und-schema) und [bekannte Grenzen](KNOWN_LIMITATIONS.md).

## Schnellstart

**Mit Docker** (Docker Compose v2 und Python 3.11+): SEO-Werkbank, PostgreSQL und eine interne Metasuche in einem Kommando.

```bash
python scripts/full_stack.py up
```

Danach <http://localhost:8000> öffnen und den ersten Administrator anlegen. Passwörter werden beim ersten Start
zufällig erzeugt und in der ignorierten `.env` gespeichert. Details, Updates und Backups: [Docker-Gesamtausgabe](docs/DOCKER_FULL.md).

**Ohne Docker (Windows):**

```bash
cd backend
python -m venv .venv
.venv\Scripts\pip install -e ".[dev]"
cd ../frontend
npm install
npm run build
```

Danach `start-seo-werkbank.cmd` ausführen und <http://localhost:8000> öffnen. Andere Betriebssysteme und PostgreSQL:
[Originaldokumentation](docs/UPSTREAM_README.md).

**Neu hier?** Der [Schnellstart für Anwender](docs/SCHNELLSTART.md) führt durch Installation, erste Website, Crawl,
Search Console und die erste Content-Maßnahme. Das [Benutzerhandbuch](docs/BENUTZERHANDBUCH.md) erklärt Schritt für Schritt,
wo du klickst und was die Ergebnisse bedeuten. In der App gibt es außerdem eine integrierte Hilfe unter `/help`.

## Dokumentation

| Thema | Dokument |
| --- | --- |
| Bedienung | [Schnellstart](docs/SCHNELLSTART.md) · [Benutzerhandbuch](docs/BENUTZERHANDBUCH.md) |
| Audit und Suchmaschinen | [Herkunft der Regeln](docs/AUDIT_PROVENANCE.md) · [Google, Bing, Brave](docs/SEARCH_ENGINE_RULES.md) · [Technische Diagnose](docs/TECHNICAL_DIAGNOSTICS.md) |
| Integrationen | [Search Console](docs/GSC_URL_INSPECTION.md) · [Bing und IndexNow](docs/BING_INDEXNOW.md) · [Benachrichtigungen und PageSpeed](docs/NOTIFICATIONS_PAGESPEED.md) · [Zugangsdaten](docs/SECURE_INTEGRATIONS.md) · [Datenanbieter](docs/SEO_DATA_PROVIDERS.md) |
| Betrieb | [Docker](docs/DOCKER_FULL.md) · [Architektur](docs/ARCHITECTURE.md) · [API](docs/API.md) · [Sicherheitsprüfung](docs/SECURITY_REVIEW.md) |
| KI und MCP | [Lokaler MCP-Server](docs/MCP_SERVER.md) (nur lesend) · [KI-Sichtbarkeit](docs/AI_VISIBILITY.md) |
| Projekt | [Roadmap](docs/ROADMAP.md) · [Projektstatus](PROJECT_STATUS.md) · [Bekannte Grenzen](KNOWN_LIMITATIONS.md) · [Changelog](CHANGELOG.md) |

## Mitmachen

Beiträge sind willkommen, von Fehlermeldungen über Dokumentation bis zu neuen Prüfregeln.

1. Lies [CONTRIBUTING.md](CONTRIBUTING.md): Grundregeln, Entwicklungsumgebung, Ablauf eines Pull Requests.
2. Suche dir eine Aufgabe: [good first issue](https://github.com/DKFuH/seo-werkbank/labels/good%20first%20issue),
   [help wanted](https://github.com/DKFuH/seo-werkbank/labels/help%20wanted) oder die [Roadmap](docs/ROADMAP.md).
   Schreibe kurz in das Issue, dass du es übernimmst.
3. Fragen und Ideen gehören in die [Diskussionen](https://github.com/DKFuH/seo-werkbank/discussions), Fehler in die
   [Issues](https://github.com/DKFuH/seo-werkbank/issues/new/choose).
4. Sicherheitslücken bitte nicht öffentlich melden, sondern wie in [SECURITY.md](SECURITY.md) beschrieben.

Für Mitwirkende gilt der [Verhaltenskodex](CODE_OF_CONDUCT.md).

Die wichtigsten Prüfungen, die auch die CI ausführt:

```bash
cd backend && .venv\Scripts\python -m pytest -q && .venv\Scripts\python -m ruff check app tests
cd frontend && npm run typecheck && npm test && npm run build
```

Unter Windows die Frontend-Tests aus PowerShell mit einem `C:\`-Pfad starten, nicht aus Git Bash (sonst scheitert Vitest am Laufwerksbuchstaben).

## Lizenz

MIT, siehe [LICENSE](LICENSE). Der Copyright-Vermerk von OpenSEOSuite bleibt erhalten.

### Intelligence-Module (PRs #54–#57)

Die Werkbank ergänzt die bestehenden GSC- und Crawl-Daten um **Content Decay, URL-Überschneidungen und Query-Trends**, **Indexstatus-Historie aus echten Google-URL-Inspection-Antworten** und **Sitemap-Vergleiche zwischen Crawls**. Redaktionelle Entwürfe erhalten einen deterministischen QA-Hinweisbericht; Backlink-Recovery ist ein manueller Maßnahmen-Workflow. Berichte lassen sich als unveränderliche HTML-/PDF-Datenstände archivieren und optional über einen Monitor periodisch erfassen.

**Optionale Anbieter:** Google Analytics 4 und Microsoft Clarity sind über echte APIs mit separat verschlüsselten Zugangsdaten je Website angebunden. Lokale organische und Maps-Ranks können über den **kostenpflichtigen DataForSEO-Dienst** ausdrücklich einzeln gemessen werden. Keine Anbieter-Verbindung erzeugt ohne gültige Zugangsdaten Messwerte; bei Clarity und Google gelten API-Kontingente. Es werden keine selbst erfundenen Ranking-, Indexierungs- oder Conversion-Zahlen verwendet. [Methodik, Anleitungen und Grenzen](docs/INTELLIGENCE_MODULES.md).
