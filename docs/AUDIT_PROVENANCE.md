# Herkunft und Aussagekraft der Audit-Regeln

Die Audit-Werkbank trennt ab sofort **Schweregrad** und **Herkunft der Aussage**.
`rule_dict(id)` liefert zusätzlich `classification`, `classification_label`,
`google_documentation` und `google_requirement`. Das ist ein erster, bewusst
konservativer Metadaten-Schritt, **keine offizielle Google-Zertifizierung**.

| classification | Interpretation |
| --- | --- |
| `technical_requirement` | Technisches Problem mit direktem Bezug auf Abrufbarkeit, Indexierbarkeit oder valide Verarbeitung; nicht jede betroffene Seite muss indexierbar sein. |
| `google_recommendation` | Bekannte Best Practice. Die genaue Relevanz ist URL- und Feature-abhängig. |
| `seo_heuristic` | Redaktionelle oder technische Faustregel, keine verbindliche Google-Vorgabe. |
| `geo_experiment` | Experimentelle Heuristik für KI-Antwortsysteme; kein nachgewiesener Google-Rankingfaktor. |

## Wichtige Grenzen

- Google verlangt **keine** fixen Title- oder Description-Zeichenlängen, keine
  Mindestwortzahl von 200, keine durchgehend einzigartige H1 und keine `llms.txt`.
- `robots.txt`, `noindex`, Canonical und andere Angaben können absichtlich
  gesetzt sein. Nicht jeder Fund ist ein Fehler.
- Die Klasse `technical_requirement` bedeutet **nicht**, dass Google jede
  Seitenabweichung als Richtlinienverstoß wertet. Der konkrete Seitenzweck zählt.
- Ein allgemeiner Link zu Googles Dokumentation belegt **keine** individuelle
  Schwelle; deshalb sind heuristische und GEO-Regeln nicht mit solchen Links
  ausgezeichnet.
- Das bestehende vierstufige Scoring bleibt in diesem PR unverändert. **Ein
  Compliance-Score wird damit ausdrücklich noch nicht eingeführt.** Dafür
  braucht es ein separates, getestetes Scoring-Modell und Anpassungen in UI,
  Exporten und historischen Vergleichen.

Offizielle Anlaufstellen:
- https://developers.google.com/search/docs/essentials
- https://developers.google.com/search/docs/fundamentals/seo-starter-guide
- https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls
- https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data

## Nächste Arbeiten

1. Jede Regel einzeln durchsehen, mit relevanter konkreter Google-Quelle und
   Stand-Datum auszeichnen; für eigene Heuristiken statt Google-Zitat die
   Prüfmethodik dokumentieren.
2. Bewusst gesetzte `noindex`-, `canonical`-, `robots`- und
   Sprachvarianten gegen die gewünschte Indexierungsstrategie prüfen.
3. UI-Filter für die vier Klassifizierungen einführen und die Erläuterungen
   in Berichten/Exporten anzeigen.
4. Optional einen separaten technischen Google-Indexierungsstatus bilden –
   aber keinen scheinbar offiziellen Google-Compliance-Score behaupten.
5. Erst danach die Gewichtung und den Score inklusive Migration historischer
   Werte und Vergleichstests überarbeiten.
