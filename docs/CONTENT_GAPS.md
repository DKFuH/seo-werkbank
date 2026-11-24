# Content-Gap-Analyse (GSC + Website-Crawl)

Die **Content-Gap-Analyse** steht unter **Content → Content-Gaps** (`/content-gap`).
Sie verknüpft **tatsächlich gemessene Search-Console-Suchanfrage-URL-Paare**
mit **Title, H1, Überschriften und sichtbarem Seiteninhalt** des letzten
abgeschlossenen, eigenen Crawls. Das Modul erstellt keine Seiten und
veröffentlicht keine Inhalte.

## Voraussetzungen

1. Für die ausgewählte Website mindestens einen erfolgreichen Crawl durchführen.
2. Search Console verbinden und synchronisieren oder einen
   **kombinierten** CSV-Export mit *Suchanfrage und zugehöriger Seite* importieren.
   Zwei getrennte Tabellen „Suchanfragen“ und „Seiten“ sind **nicht** ausreichend.
3. Zeitraum (7–365 Tage über API, Oberfläche mit typischen Zeiträumen)
   und Mindestimpressionen wählen. Ohne Datum gilt kein Zeitraumfilter.

## Vier Ergebnisse

| Kategorie | Bedeutung | Was als Nächstes zu prüfen ist |
| --- | --- | --- |
| **Neuen Inhalt prüfen** | Weder die aktuell rankende URL noch andere indexierbare Crawl-Seiten zeigen deutliche lexikalische Abdeckung | Echte Suchintention, SERP, bestehende Abschnittsstruktur, zusätzliche fachliche Substanz |
| **Bestehenden Inhalt erweitern** | Die GSC-Landingpage hat bereits Teilabdeckung | Ob ein zusätzlicher Abschnitt statt einer neuen URL genügt |
| **Zuordnung/Suchintention prüfen** | Die GSC-URL fehlt im Crawl oder eine andere Seite deckt die Begriffe stärker ab | URL-Normalisierung, Canonical, Crawl-Abdeckung und fachlich passende Zielseite |
| **Vorerst keine Maßnahme** | Suchbegriffe sind in Überschriften und Text bereits stark vertreten | Ein lexikalischer Treffer ist kein Beweis für erfüllte Nutzerintention |

## Nachvollziehbare Belege

Pro Suchanfrage werden die rankende URL, echte GSC-Impressionen, Klicks,
impressionsgewichtete Durchschnittsposition, lexikalische Abdeckung in
Überschriften und Text sowie bis zu fünf rankende URLs angezeigt.
Bekommt mehr als eine URL relevante Impressionen, meldet die Werkbank
nur **„mögliche Überschneidung prüfen“**, keine nachgewiesene Kannibalisierung.

Sehr ähnliche Suchanfragen werden anhand eines deterministischen
Token-Jaccard-Vergleichs gruppiert. Die angezeigten Gruppenimpressionen
sind die **Summe der GSC-Impressionen verschiedener Queries**, keine
Anzahl eindeutiger Suchenden, kein Keyword-Planer-Suchvolumen und keine
zu erwartenden Klicks. Ohne unabhängigen Intent-/SERP-Abgleich ist die
Zuordnung zu einem gemeinsamen Thema **vorläufig**.

**Grenzen:** Es werden maximal 10.000 GSC-Query-URL-Paare, 4.000
indexierbare Crawl-Seiten und 800 bewertete Suchanfragen verarbeitet;
die Ergebnisliste ist zusätzlich begrenzt. Seiteninhalt wird bis 20.000
Zeichen pro Seite untersucht. Das ist bewusst begrenzt; aus fehlenden
Treffern können keine abschließenden Content-Lücken abgeleitet werden.
Die Wortanalyse ist eine einfache mehrsprachige Token-Heuristik und
**keine** KI-/Semantikprüfung oder verbindliche Intent-Klassifikation.

## Datenherkunft und Datenschutz

- Nur `GscRow.dataset=query_page`, also **Query und URL gemeinsam**.
- Wenn für eine Website API- und CSV-Paare vorliegen, werden API-Paare
  bevorzugt. Sie werden **nicht** addiert, um Importe nicht doppelt zu zählen.
- Die Auswertung endet am neuesten GSC-Datum im ausgewählten Datensatz.
- Google anonymisiert seltene Suchanfragen und limitiert die API-Ausgabe;
  ein fehlender Query-Eintrag ist kein Nachweis fehlender Nachfrage.
- Alle Abfragen und Maßnahmen sind auf die Website des angemeldeten
  Eigentümers begrenzt. Es werden keine Daten an neue Drittdienste gesendet.

## Redaktionsablauf

1. Kategorie und Einzelbelege prüfen.
2. *Briefing kopieren* enthält GSC-Metriken, rankende URLs und die
   ausdrücklich als Heuristik bezeichnete Empfehlung.
3. Gegebenenfalls **Als Maßnahme erfassen** wählen und eine URL der
   eigenen Website angeben. Das erstellt lediglich ein
   `SeoWorkItem(kind=content, status=planned)` in **SEO-Maßnahmen**.
4. Redaktionell planen, Inhalte über bestehende Freigabekanäle bearbeiten
   und eine spätere GSC-Messung als Vorher-/Nachher-Befund ergänzen.
   Die Werkbank beansprucht **keine kausale Rankingverbesserung**.

## Quellen und technische Vergleiche

Die Methodik wurde gegen offizielle Quellen und Open-Source-Ansätze
abgeglichen; es wurde **kein Fremdcode übernommen**:

- Google, Search Analytics API: https://developers.google.com/webmaster-tools/v1/searchanalytics/query
- Google, Einschränkungen der Performance-Daten: https://developers.google.com/search/blog/2022/10/performance-data-deep-dive
- Google, Duplicate Content und Canonicalisierung: https://developers.google.com/search/docs/crawling-indexing/canonicalization
- GitHub, OpenGSC (andere, umfangreichere Content-Suite): https://github.com/fenjo26/opengsc
- GitHub, seo-content-gap-analyzer (externer Wettbewerbsvergleich): https://github.com/mehranmoghadasi/seo-content-gap-analyzer

Die Implementierung verwendet **nur vorhandene** GSC-Daten, Crawl-Texte
und SEO-Maßnahmen der SEO-Werkbank. Kein SERP-Scraping, keine kostenpflichtigen
Datenprovider, keine externen Suchvolumenschätzungen.
