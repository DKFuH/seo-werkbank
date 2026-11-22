# Erweiterte SEO-Prüfungen: Overlap, Relaunch, Paginierung und Schema

Im Frontend unter **Analyse → Erweiterte SEO-Prüfungen**.

1. **SERP-Overlap:** Zwei Keywords über denselben eingestellten Suchanbieter abrufen oder zwei selbst erfasste Top-URL-Listen vergleichen. Exakte gemeinsame URLs, Jaccard-Overlap und Deckung der kleineren Liste werden berechnet. Ergebnis ist eine redaktionelle Hilfe für Keyword-Mapping, keine verbindliche Strategieentscheidung. SearXNG und andere Provider liefern nicht zwingend Google-Suchergebnisse.
2. **Relaunch:** Zwei vollständig abgeschlossene Crawl-Snapshots derselben Website vergleichen. Optional explizite alte→neue URLs angeben. Prüft, ob Zielseiten im neuen Crawl gefunden wurden und welche Status-, Title-, Canonical- und Indexierungsinformationen beobachtet wurden. Das Fehlen im neuen Crawl beweist keine fehlende Weiterleitung; es gibt keine automatische Redirect-Bereitstellung.
3. **Paginierung:** Markiert Seiten mit Seitenzahl-URLs und/oder rel next/prev. Hinweise für hohe Klicktiefe, wenige eingehende Links oder technische Nichtindexierbarkeit. Eine lineare Paginierung ist nicht automatisch ein Fehler. Google erfordert kein rel next/prev.
4. **Schema.org:** JSON-LD im letzten Crawl gegen vorhandene Schema-Prüfungen und eine konservative, nicht vollständige Typenliste auswerten. Markiert lediglich mögliche Suchdarstellungstypen. Weder semantische Gültigkeit im gesamten Schema.org-Vokabular noch Berechtigung/Anzeige eines Google Rich Results werden garantiert.

**Sicherheit:** Alle Crawl-IDs müssen der ausgewählten Website des aktuellen Nutzers gehören. SERP-Anbieterzugriffe erfolgen nur bei ausdrücklicher Anfrage. Keine Google-SERP-Scraping-Integration. Für relaunchübergreifende Domains derzeit kein gemeinsamer Crawl-Vergleich.
