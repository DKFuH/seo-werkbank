# SEO-Werkbank

Selbst gehostetes SEO-Werkzeug mit deutscher Oberfläche: Crawler, technisches Audit, interne Verlinkung,
Keyword-Recherche, SERP- und Content-Analyse, **WDF\*IDF**, **GEO-Check** für KI-Suchsysteme, Search Console,
**Matomo**, PageSpeed, Monitoring und Berichte. Läuft auf dem eigenen Rechner, die Daten bleiben dort.

SEO-Werkbank ist eine Weiterentwicklung von [OpenSEOSuite](https://github.com/Sushang-Agnihotri/OpenSEOSuite)
(MIT-Lizenz, © The OpenSEOSuite contributors). Die ursprüngliche Dokumentation liegt unter
[docs/UPSTREAM_README.md](docs/UPSTREAM_README.md); Architektur, Sicherheit und Installation gelten unverändert.

## Was gegenüber OpenSEOSuite dazugekommen ist

- **Deutsche Oberfläche**: alle Seiten, die 95 Audit-Regeln, Hinweise und Fehlermeldungen; deutsche Zahlen- und
  Datumsformate. KI-Antworten (optional, Ollama oder OpenAI-kompatibel) auf Deutsch.
- **Deutsche Exporte**: Search-Console-, Keyword-Planer- und Links-CSVs mit deutschen Spaltennamen und Zahlen
  (`1.234`, `8,47`) werden korrekt gelesen.
- **WDF\*IDF-Analyse** (`/wdf-idf`): eigene URL oder Entwurf gegen bis zu zehn Wettbewerber-URLs,
  WDF = log2(f+1)/log2(L+1), IDF = log10(1+N/n), deutsche Stoppwörter, optional Zweiwort-Begriffe,
  Drittelverteilung und Überschriftenvergleich. Zusätzlich direkt in der Content-Optimierung.
- **GEO-Check** (`/geo`): KI-Crawler in robots.txt (OAI-SearchBot, Claude-SearchBot, PerplexityBot, GPTBot …),
  llms.txt, Entität und sameAs, Autor, Aktualität, Antwortstruktur, Listen, Zahlen und Quellen.
- **Matomo** (`/matomo`): Besuche, Kanäle, Einstiegsseiten, Ziele und Geräte aus der Reporting-API, verknüpft
  mit dem letzten Crawl, inklusive indexierbarer Seiten ohne Besuch.
- **Content-Refresh** (`/content-refresh`): GSC-Query-URL-Chancen, redaktionelle Prüfhinweise und kopierbare Briefings;
  keine automatische Veröffentlichung. Details: [Content-Refresh](docs/CONTENT_REFRESH.md).
- **Wirtschaftliche SEO-Chancen** (`/opportunity-value`): Nutzerdefinierte Lead-, Abschluss- und DB-Annahmen
  sowie manuelle Seitenrelevanz; Szenarien, keine Umsatzprognosen.
- **SEO-Maßnahmen** (`/seo-work`): manuelles Tracking für redaktionelle Inhalte, Bewertungen,
  Veröffentlichungen, lokale SEO-Maßnahmen und Wettbewerbsbeobachtungen, GSC-Vergleichsmessungen.
- **KI-Erwähnungen** (`/ai-visibility`): manuelle, zeitgestempelte Beobachtungen zu Markennennungen
  und belegten URLs; keine Live-Überwachung oder erfundene AI-Rankings.
- **Wettbewerber-Themenradar** (`/competitor-radar`): thematische Wortpaare aus tatsächlichen
  Wettbewerber-Crawls mit belegbaren Quellseiten; keine erfundenen Rankings oder Volumina.
- **Lokales SEO & Nachweise** (`/seo-evidence`): Aktionsplan aus importierten NAP-Daten,
  manuell erfassten Bewertungsanfragen und Abgleich von Publikationen mit Backlink-Datensätzen.
- Deutsche Stoppwörter auch in SERP-Analyse und Content-Optimierung; deutsche Signalwörter für kommerzielle
  Suchintention.

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

## Tests

```bash
cd backend && .venv\Scripts\python -m pytest -q
cd frontend && npx vitest run
```

## Lizenz

MIT, siehe [LICENSE](LICENSE). Der Copyright-Vermerk von OpenSEOSuite bleibt erhalten.
