# Suchmaschinenbezogene Audit-Evidenz (Google, Bing, Brave)

Die 117 Audit-Regeln werden nicht automatisch zu 117 offiziellen Suchmaschinenanforderungen.
Das Regelwerk trennt vorhandene technische Befunde, **Provenienz der Regel** und
**suchmaschinenspezifische Quellen**. `rule_dict(id)` stellt dafür `search_engines`
mit getrennten Feldern für **Bing** und **Brave** bereit.

- `related_guidance`: Eine öffentliche Primärquelle beschreibt den Themenbereich.
  Das bestätigt **nicht** automatisch den konkreten Schwellenwert, Score oder Fehlerstatus.
- `not_evaluated`: Keine ausreichend konkrete öffentliche Zuordnung im Katalog
  hinterlegt. **Nicht** als fehlende Unterstützung des Suchdienstes interpretieren.
- Google wird über `classification` und `google_documentation` separat dargestellt.

## Microsoft Bing

Primärquelle: https://www.bing.com/webmasters/help/webmaster-guidelines-30fba23a

Relevante Themen: Crawling, robots.txt, NOINDEX, Canonicalisierung,
Sitemaps, Contentqualität und Suchmaschinenrichtlinien. Im Gegensatz zur
Google Search Console sind die Daten der Bing Webmaster Tools eine **eigene**
Datenquelle. Ein Google-Indexstatus sagt nichts Sicheres über Bing aus.

**Noch offen:** Getrennte Bing-URL-Inspection, Bing-Webmaster-Tools-Daten,
IndexNow-Konfiguration und Rückmeldungen. IndexNow ist eine schnelle
Änderungsbenachrichtigung, **keine Garantie der Indexierung und keine
Google-Pflicht**. Offizielle Informationen:
https://www.bing.com/webmasters/help/indexnow-0z209wby

## Brave Search

Primärquelle: https://search.brave.com/help/brave-search-crawler

Laut Braver eigener Dokumentation wird der Suchcrawler nicht mit einem
eindeutig unterscheidbaren User-Agent angekündigt. Er crawlt eine Seite
nicht, wenn sie für Googlebot nicht crawlbar ist. **robots.txt ist keine
Methode, Seiten sicher aus dem Brave-Index zu entfernen**; hierfür ist
`noindex` maßgeblich. Eine explizite Googlebot-Sperre kann somit auch
Brave betreffen.

**Nicht behaupten:** Einen separaten Bravebot-UA zuverlässig messen,
IndexNow als Brave-Anforderung darstellen, Google-URL-Inspection als
Beleg für Brave-Indexierung verwenden oder eine vollumfängliche offizielle
Brave-SEO-Regelliste aus allgemeinen Heuristiken ableiten.

## Nächste Schritte

1. Pro einzelner Regel die genaue Fundstelle und Dokumentationsstand
   hinterlegen, nicht bloß einen allgemeinen Link.
2. Bing-Datenanbindung und IndexNow als optionale, unabhängig getestete
   Module planen und entwickeln.
3. Brave-Check auf nachweisbare Crawl-Sperren und `noindex` beschränken;
   Indexierungsstatus als unbekannt kennzeichnen, sofern keine Quelle vorliegt.
4. UI und Exporte um Suchmaschinenfilter und `not_evaluated` ergänzen;
   erst dann ein getrenntes, kontextbezogenes Scoring testen.
