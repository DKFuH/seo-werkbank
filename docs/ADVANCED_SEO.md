# Erweiterte SEO-Prüfungen: Overlap, Relaunch, Paginierung und Schema

Die vier Prüfungen haben keine eigene Seite, sondern stehen dort, wo ihr Thema liegt:

| Prüfung | Fundort |
|---|---|
| SERP-Überschneidung | **Sichtbarkeit → SERP-Analyse**, Karte „Zwei Keywords vergleichen“ |
| Relaunch-Vergleich | **Analyse → Crawler**, Tab „Relaunch“ (Crawls per Auswahlliste) |
| Paginierung | **Analyse → Interne Verlinkung**, Tab „Paginierung“ |
| Rich-Result-Potenzial | **Analyse → Strukturierte Daten**, Tab „Rich-Result-Potenzial“ |

1. **SERP-Overlap:** Zwei Keywords über denselben eingestellten Suchanbieter abrufen oder zwei selbst erfasste Top-URL-Listen vergleichen. Exakte gemeinsame URLs, Jaccard-Overlap und Deckung der kleineren Liste werden berechnet. Ergebnis ist eine redaktionelle Hilfe für Keyword-Mapping, keine verbindliche Strategieentscheidung. SearXNG und andere Provider liefern nicht zwingend Google-Suchergebnisse.
2. **Relaunch:** Zwei vollständig abgeschlossene Crawl-Snapshots derselben Website vergleichen. Optional geplante Zuordnungen angeben, eine pro Zeile: `alte URL => neue URL` (auch `->` oder `→`). Prüft, ob Zielseiten im neuen Crawl gefunden wurden und welche Status-, Title-, Canonical- und Indexierungsinformationen beobachtet wurden. Das Fehlen im neuen Crawl beweist keine fehlende Weiterleitung; es gibt keine automatische Redirect-Bereitstellung.
3. **Paginierung:** Markiert Seiten mit Seitenzahl-URLs und/oder rel next/prev. Hinweise für hohe Klicktiefe, wenige eingehende Links oder technische Nichtindexierbarkeit. Eine lineare Paginierung ist nicht automatisch ein Fehler. Google erfordert kein rel next/prev.
4. **Schema.org:** JSON-LD im letzten Crawl gegen vorhandene Schema-Prüfungen und eine konservative, nicht vollständige Typenliste auswerten. Markiert lediglich mögliche Suchdarstellungstypen. Weder semantische Gültigkeit im gesamten Schema.org-Vokabular noch Berechtigung/Anzeige eines Google Rich Results werden garantiert.

**Sicherheit:** Alle Crawl-IDs müssen der ausgewählten Website des aktuellen Nutzers gehören. SERP-Anbieterzugriffe erfolgen nur bei ausdrücklicher Anfrage. Keine Google-SERP-Scraping-Integration. Für relaunchübergreifende Domains derzeit kein gemeinsamer Crawl-Vergleich.

## Schritt-für-Schritt-Anleitungen

### SERP-Overlap

1. **Sichtbarkeit → SERP-Analyse** öffnen und die Karte **„Zwei Keywords vergleichen“** suchen.
2. Zwei Keywords eintragen; entweder den eingestellten SERP-Anbieter verwenden oder **beide** manuellen Ergebnislisten ausfüllen (je URL eine Zeile).
3. **„Vergleichen“** klicken und gemeinsame URLs, Quell-Anbieter und Jaccard-Überlappung lesen.
4. Erst danach prüfen, ob Suchintention und Nutzererwartung für eine gemeinsame Zielseite sprechen.

### Relaunch

1. Einen Crawl **vor**, einen weiteren Crawl **nach** dem Relaunch abschließen.
2. **Analyse → Crawler → Crawl anzeigen → Relaunch** öffnen.
3. Über die Auswahllisten den älteren und neueren Durchlauf wählen.
4. Wenn URLs umbenannt wurden, **Geplante URL-Zuordnungen** ergänzen, z. B. `https://example.org/alt => https://example.org/neu`.
5. **„Relaunch prüfen“**. Abweichende Status wie **„Weiterleitung prüfen“** oder **„Canonical weicht ab“** an echten URLs nachvollziehen. Ein HTTP-200-Ziel belegt keine Weiterleitung der alten URL.

### Paginierung und Schema

- **Analyse → Interne Verlinkung → Paginierung:** Blätterseiten, Crawltiefe, Inlinks und Indexierbarkeitsmerkmale prüfen; bei Bedarf die realen Navigationspfade verbessern.
- **Analyse → Strukturierte Daten → Rich-Result-Potenzial:** JSON-LD-Typen, mögliche Google-Typen und konkrete Validator-Hinweise prüfen. Zur Detailkorrektur den **Validator** nutzen.

Mehr Details: [Benutzerhandbuch, Kapitel 6.4, 7.6–7.7 und 9.4](BENUTZERHANDBUCH.md).
