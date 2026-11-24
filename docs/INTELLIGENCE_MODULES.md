# SEO-Werkbank: Intelligence-Erweiterungen

## Content Intelligence (Content → Content Intelligence)

Das Modul vergleicht zwei gleich lange Zeitfenster innerhalb datierter
Google-Search-Console-Zeilen, jeweils Suchanfrage **und** rankende URL.
Benötigt GSC-`query_page`-Daten; API-Daten werden beim Vorhandensein
bevorzugt und CSV nicht doppelt addiert.

1. **Content Decay:** Mindestens 40 Impressionen im Vorzeitraum und ein
   Klickrückgang ab 15 %; differenziert Positions-, Impressions- und
   CTR-Rückgang als **Hinweise**, nicht Ursachenbeweise.
2. **URL-Überschneidung:** Dasselbe Keyword auf mindestens zwei URLs mit
   nennenswertem Impressionanteil; dokumentiert einen eventuellen
   Wechsel der URL mit den meisten Impressionen. Kein automatischer
   Kannibalisierungsbeweis oder Canonical-/Redirect-Vorschlag.
3. **Trend-Radar:** Neue oder mindestens 40 % gestiegene Query-Impressionen
   im beobachteten Datensatz, nicht im gesamten Suchmarkt.
   Ein Keyword ist „neu in der Stichprobe“, nicht neu bei Google.

Grenzen: Google anonymisiert Suchanfragen und zeigt nicht sämtliche Daten.
Ein Zeilenlimit von 50.000 begrenzt die Arbeit und wird als Kürzung ausgewiesen.
Positionen sind impressionsgewichtete Mittelwerte, kein einzelnes Ranking.
Keine automatische Publikation oder unverifizierte Ranking-Empfehlung.

Referenz: https://developers.google.com/webmaster-tools/v1/searchanalytics/query

## Index Intelligence (Analyse → Sitemaps & Indexierung)

**Sitemap-Historie** rekonstruiert die URL-Abdeckung aus den letzten
abgeschlossenen Crawls. Es werden beobachtete Sitemap-URLs, Lastmod-Abdeckung,
neu beobachtete und nicht mehr beobachtete URLs verglichen. Ein Crawl-Limit,
blockierte URLs oder andere Crawl-Einstellungen können scheinbare Änderungen
erzeugen. Keine Aussage über den Google-Index wird daraus abgeleitet.

**Google URL Inspection Batch:** Bei vorhandener, berechtigter Google Search
Console werden bis zu **10** URLs pro explizitem Job untersucht, priorisiert
nach neu im Crawl, verändertem Content-Hash und Inlinks.
Nur tatsächliche Google-URL-Inspection-Antworten werden als
`google_url_inspection_api` persistiert. Historische Statusübergänge von
`PASS` zu einem anderen Urteil werden als Prüfhinweis angezeigt.
Der Job stellt **keine** Indexierungsanträge, führt keine Live-URL-Tests
aus und respektiert zusätzliche Google-API-Kontingente.
Bei Quoten-/Berechtigungsfehlern wird der Batch abgebrochen statt
aggressiv wiederholt zu werden.

Beide Module sind auf die angemeldete Website begrenzt. Vorhandene
Infrastruktur: `SeoResearchRecord` zur Historisierung, keine zusätzliche
Datenbankmigration.

Quelle: https://developers.google.com/webmaster-tools/v1/urlInspection.index/inspect
Quoten: https://developers.google.com/webmaster-tools/limits
