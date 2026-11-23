# Funktionsübersicht

Ausführliche Liste aller Funktionen der SEO-Werkbank, einschließlich dessen, was gegenüber
[OpenSEOSuite](https://github.com/Sushang-Agnihotri/OpenSEOSuite) dazugekommen ist.
Die Kurzfassung steht in der [README](../README.md); Bedienung erklärt das [Benutzerhandbuch](BENUTZERHANDBUCH.md).

## Neue SEO-Operations-Werkzeuge

- **Bing & IndexNow** (`/bing`): Bing-Webmaster-Daten und URL-Meldungen per IndexNow, getrennt von Google ([Details](BING_INDEXNOW.md)).
- **Audit-Profile** (Site-Audit): jede Regel mit Herkunft (technisch, Google-Empfehlung, Heuristik, GEO-Hypothese) und getrennte Scores für Google, Bing, Brave und GEO ([Details](AUDIT_PROVENANCE.md)).
- **Weiterleitungen** (`/redirects`): Vorschläge, Simulation, menschliche Freigabe, Apache-/Nginx-/CSV-Konfigurationsexporte ([Details](REDIRECTS.md)).
- **Logfile & 404** (`/logs`): begrenzter Apache-/Nginx-Import ohne persistente IPs und Rohlogs; 404-Redirect-Vorschläge ([Details](LOG_ANALYSIS.md)).
- **Schema-Management** (Reiter unter `/schema`): Daten aus Crawls vorbefüllen, JSON-LD-Diff, Vorlagen und Freigabe-Workflow ([Details](STRUCTURED_DATA.md)).

## Hilfe, Keyword-Clustering und Demo

- **Integrierte Hilfe** unter `/help`: direkte Verweise zu Werkzeugen und passenden Handbuchkapiteln.
- **SERP-basiertes Keyword-Clustering** im Cluster-Werkzeug; 2–15 Keywords, tatsächlich erfasste SERP-URL-Listen oder ein konfigurierter Anbieter ([Anleitung](KEYWORD_SERP_CLUSTERING.md)).
- **Screenshots und kurzer Rundgang:** Mit `python scripts/capture_demo.py` auf einer gestarteten Installation aufnehmen. Das Skript erzeugt authentische PNG-Screenshots und ein WebM-Video unter `docs/media/generated/`. **Im GitHub-CI-Job `demo-capture` werden echte Screenshots und eine WebM-Aufnahme einer isolierten Testinstallation als Workflow-Artefakt erzeugt.** Die Aufnahmen werden nicht automatisch im README veröffentlicht. Vor einer Übernahme in das Repository müssen die Artefakte geprüft werden.
- **0.2 Integrationen:** [verschlüsselte Zugangsdaten](SECURE_INTEGRATIONS.md), [Google URL Inspection](GSC_URL_INSPECTION.md), [SMTP/Webhooks und Batch-PageSpeed](NOTIFICATIONS_PAGESPEED.md).

## Bedienung: Benutzerhandbuch und Schnellstart

**Neu hier?** Beginne mit dem [Schnellstart für Anwender](SCHNELLSTART.md):
Installation, erste Website, Crawl, Google Search Console und Content-Maßnahme.

Das ausführliche **[Benutzerhandbuch](BENUTZERHANDBUCH.md)** erklärt Schritt für Schritt
**wo du klickst, welche Daten benötigt werden, was das Ergebnis bedeutet und wie die
Funktionen zusammenarbeiten** – einschließlich Admin-Einstellungen, Importen,
Crawling, Keyword-Recherche, KI-Sichtbarkeit, Content-Freigabe, Matomo, Monitoring,
Exporten und Fehlerbehebung.

- **Browser- und Bilddiagnostik:** Consent-Request-Zeitfolgen, Roh-/JS-Rendering und Markup-Hinweise für mögliche LCP-Bilder ([Anleitung](TECHNICAL_DIAGNOSTICS.md)).

- **Erweiterte Audits** in den passenden Bereichen: SERP-Überschneidung (SERP-Analyse), Relaunch-Vergleich (Crawler),
  Paginierung (Interne Verlinkung) und Rich-Result-Potenzial (Strukturierte Daten) ([Anleitung](ADVANCED_SEO.md)).

- **Verzeichnisse & KI-Quellen:** Verzeichnisbewertung (Lokale Nachweise) und wiederkehrende KI-Zitate
  (KI-Erwähnungen) ([Anleitung](AUTHORITY_INTELLIGENCE.md)).

## Was gegenüber OpenSEOSuite dazugekommen ist

- **Deutsche Oberfläche**: alle Seiten, die 122 Audit-Regeln, Hinweise und Fehlermeldungen; deutsche Zahlen- und
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
  keine automatische Veröffentlichung. Details: [Content-Refresh](CONTENT_REFRESH.md).
- **Wirtschaftliche SEO-Chancen** (`/opportunity-value`): Nutzerdefinierte Lead-, Abschluss- und DB-Annahmen
  sowie manuelle Seitenrelevanz; Szenarien, keine Umsatzprognosen.
- **SEO-Maßnahmen** (`/seo-work`): manuelles Tracking für redaktionelle Inhalte, Bewertungen,
  Veröffentlichungen, lokale SEO-Maßnahmen und Wettbewerbsbeobachtungen, GSC-Vergleichsmessungen.
  Details: [SEO-Maßnahmen](SEO_WORKFLOW.md).
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
