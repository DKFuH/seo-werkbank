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

## Redaktionelle QA (Content → Content-Entwürfe)

Der Button **Aktuellen Entwurf prüfen** vergleicht Ausgangstext und neue
Fassung **vor dem Speichern**; der gespeicherte Entwurf kann zusätzlich
über die API abgefragt werden. Erkannt werden neue numerische Werte,
Maßangaben, Jahresangaben, externe URLs, Markdown-Überschriften und
mögliche Eigennamen. Das sind deterministische **Prüfhinweise**:
kein semantischer Faktencheck, keine rechtliche oder technische Freigabe,
kein Plagiatsnachweis. Die bestehende menschliche Freigabe ist weiterhin
notwendig. Die Daten werden nicht an einen externen KI-Anbieter gesendet.

## Berichts-Snapshots (Maßnahmen → Berichte)

- Ein Snapshot friert Website, Crawl, Score, gezählte Seiten und
  vorhandene datierte GSC-Messwerte **zum Zeitpunkt der Erstellung** ein.
  Der HTML-/PDF-Export verwendet ausschließlich die gespeicherten Daten,
  nicht neu eingespielte Messwerte.
- GSC-Quelle `api` hat bei doppelten Quellen Vorrang vor `csv`;
  Query-URL-Impressionen sind nicht eindeutig pro Suchanfrage.
- Optional per **Monitoring** einen Monitor des Typs **Bericht** anlegen.
  Standardintervall 720 Stunden (30 Tage); die einfache In-Process-
  Zeitplanung läuft nur bei aktivem API-Prozess. Automatisch erzeugte
  Snapshots werden **nicht** an fremde Empfänger geschickt.
- Die API bietet keinen Edit-Endpunkt für bestehende Snapshots.
  Report-Snapshots benötigen Alembic-Migration `0014`.

## Link-Recovery (Sichtbarkeit → Backlinks)

Der bestehende Link-Checker speichert nun Übergänge zwischen einem
zuvor verifizierten Live-Link und `lost` bzw. Wiedergewinnung.
Die Link-Recovery zeigt nur importierte und geprüfte Backlinks und
kennzeichnet, ob `live → lost` tatsächlich beobachtet wurde.
Links ohne nachgewiesenen früheren Live-Zustand werden getrennt
bewertet. Eine **Recovery-Aufgabe** erstellt lediglich eine geplante
SEO-Maßnahme, ohne Quellseiten automatisch anzuschreiben, Links
abzubauen, eine Disavow-Liste zu erstellen oder Weiterleitungen
zu installieren.

Die Link-Überprüfung kann durch HTML-Umbauten, Weiterleitungen oder
Serverprobleme falsche Verlustsignale erzeugen. Vor einer Kontaktaufnahme
ist eine manuelle Gegenprüfung erforderlich.

## Optionale Anbieter: GA4 und Microsoft Clarity

Unter **Conversion → GA4, Clarity & lokale SERPs** werden die
Zugangsdaten **pro Website und Eigentümer verschlüsselt** hinterlegt.
Ein vorhandener Zugang beweist nicht, dass die API für die Property
berechtigt ist.

- **GA4 Data API**: Property-ID, Service-Account-E-Mail und RSA-Private-Key
  nötig. Das Service Account muss in Google Analytics mindestens
  Leserechte auf die Property haben. Ein expliziter Klick fragt aggregierte
  Sessions, aktive Nutzer, Seitenaufrufe und Conversions für einen
  ausgewählten Zeitraum ab; keine geschätzten Daten.
  Dokumentation: https://developers.google.com/analytics/devguides/reporting/data/v1/rest/v1beta/properties/runReport
- **Microsoft Clarity Export API**: Bearer-Token erforderlich.
  Unterstützt nur einen Zeitraum von 1–3 Tagen. Zusätzlich zum
  anbieterseitigen Limit (10 Anfragen/Projekt/Tag) setzt die Werkbank
  ein vorsichtiges lokales Budget (8 Abfragen/Website und User/Tag).
  Es werden nur zulässige aggregierte Metrikfelder zurückgegeben.
  Dokumentation: https://learn.microsoft.com/en-us/clarity/setup-and-installation/clarity-data-export-api

Es findet keine Hintergrundüberwachung oder automatisierte Berechnung
von GA4/Clarity-Kennzahlen ohne explizite Abfrage statt.

## Lokales organisches und Maps-Ranktracking

Die vorhandenen Rank-Targets können mit einem **konkreten Standort**
(DataForSEO-`location_name`) verbunden werden. Eine Messung ruft nach
ausdrücklicher Kostenbestätigung **zwei kostenpflichtige Endpunkte**
(DataForSEO Google Organic und Google Maps) auf. Die Ergebnisse werden
als getrennte `RankObservation.provider=dataforseo:organic` bzw.
`dataforseo:maps` gespeichert.

Ein Ergebnis gilt nur als Treffer, wenn DataForSEO eine Website-Domain
übermittelt, die exakt der ausgewählten Website entspricht. Maps-Einträge
ohne überprüfbare Domain werden als „nicht eindeutig zuordenbar“
behandelt. Ein Anbieter-Rank ist **nicht** mit der GSC-Ø-Position zu
vergleichen. Die tatsächlichen API-Kosten trägt der Nutzer selbst;
die Werkbank schickt keine automatischen bezahlten Abfragen.

Quelle: https://docs.dataforseo.com/v3/serp/google/organic/live/advanced/
und https://docs.dataforseo.com/v3/serp/google/maps/live/advanced/
