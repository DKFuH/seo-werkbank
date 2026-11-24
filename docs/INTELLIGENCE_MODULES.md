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
