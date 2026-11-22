# Wirtschaftliche SEO-Chancen (Release B – Szenariorechnung)

Die Oberfläche `/opportunity-value` baut auf dem Content-Refresh-Endpunkt aus Release A auf. Sie sortiert die dort erkannten URLs nach einem **freiwilligen, manuell konfigurierten Deckungsbeitragsszenario**, nicht nach einer erfundenen Suchmaschine- oder Conversion-Prognose.

## Berechnung

`geschätzte Zusatzklicks × wirtschaftlich relevanter Anteil × Leadquote × Abschlussquote × Deckungsbeitrag pro Auftrag`

- **Beobachtet:** Google-Search-Console-Klicks, -Impressionen und -Positionen.
- **Bereits hypothetisch:** geschätzte Zusatzklicks aus allgemeiner CTR-Kurve der Vorstufe.
- **Vom Benutzer angenommen:** relevanter Anteil je URL, Leadquote, Abschlussquote und DB je Auftrag.
- **Ergebnis:** ein unverbindlicher Szenariowert; ausdrücklich keine Umsatzprognose oder gemessene Conversion.

Die drei globalen Annahmen sind zunächst leer. Ebenso ist der relevante Anteil jeder URL leer. Solange eine Eingabe fehlt, wird keine wirtschaftliche Bewertung errechnet und die URL in der Liste hinter bewerteten Einträgen angezeigt. 0 % Relevanz ist ein zulässiger, ausdrücklich eingegebener Wert.

Alle Annahmen sind vorübergehend im React-Komponentenzustand gespeichert, **nicht** in einer Datenbank, nicht im Browser-Storage und nicht bei Matomo. Als nächster Schritt können persistent gespeicherte Annahmen, kontrollierte Datenquellen zur Lead-Attribution und Maßnahmenkosten eingeführt werden. Erst mit belastbaren Daten wären echte Vergleiche zwischen geplantem und tatsächlich realisiertem Deckungsbeitrag möglich.

Einheitlicher Wertmaßstab für die Projektbewertung ist der **Deckungsbeitrag**, nicht der Warenumsatz. Verfügbarer SEO-Traffic ist allein noch keine geschäftliche Priorität.
