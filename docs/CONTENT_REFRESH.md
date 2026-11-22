# Content-Refresh (Release A – erster Baustein)

Die SEO-Werkbank verknüpft gemessene Google-Search-Console-Suchanfragen mit
**derselben URL in derselben GSC-Zeile**. Das Modul ist bewusst **lesend**:
Es schlägt redaktionelle Prüfungen vor, verändert keine Inhalte und veröffentlicht nichts.

## Einstieg

1. Website anlegen und Google Search Console verbinden oder CSV mit den Spalten
   Suchanfrage **und** Seite (URL) importieren. Getrennte Standardexporte
   mit lediglich Suchanfragen oder lediglich Seiten reichen für eine Zuordnung
   nicht aus.
2. Optional einen Crawl der Website durchführen. Dessen Texte und Überschriften
   liefern zusätzliche lexikalische Hinweise, keine bestätigten Content-Lücken.
3. Unter **Content-Refresh** einen Zeitraum wählen. Pro URL werden passende
   Suchanfragen, Messwerte und vorsichtige redaktionelle Hinweise angezeigt.
4. **Briefing kopieren** erstellt eine Prüfliste für die manuelle Redaktion.

## Methodik und Grenzen

- Vorschläge bei Position 4–20 oder bei niedriger CTR auf Top-Positionen.
- Positionen sind mit Impressionen gewichtet. Die CTR wird aus Klicks und
  Impressionen berechnet.
- „Zusatzklicks“ ist ein hypothetisches Szenario mit einer vereinfachten
  allgemeinen CTR-Kurve, **keine Vorhersage**.
- Wenn API- und CSV-Daten vorliegen, bevorzugt das Modul API-Daten, um
  doppelte Zählungen zu vermeiden. Bei undatierten CSV-Zeilen ist keine
  Zeitfensterfilterung möglich.
- Die Auswertung ist derzeit auf 10.000 Query-URL-Kombinationen begrenzt.
  Ein Hinweis erscheint, wenn die Grenze erreicht wird.
- Der lexikalische Abgleich nutzt nur vorhandenen Crawl-Text. Eine fehlende
  Wortgruppe bedeutet nicht automatisch fehlende Themenabdeckung.
- Für eine spätere CMS-Anbindung gilt: ausschließlich Entwurf und
  gesonderte Freigabe; keine direkte Veröffentlichung.

API: `GET /api/sites/{site_id}/content-refresh?days=28`
