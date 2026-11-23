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
- Der bisherige Gesamtscore bleibt unverändert. Zusätzlich berechnet die
  Audit-Ansicht Google-, Bing-, Brave- und GEO-Profil-Scores mit denselben
  Schweregrad-Abzügen, aber jeweils nur aus den zugeordneten Regeln.
- Die Suchmaschinen-Scores sind keine Rankingschätzung und kein Compliance-
  Score. Bing und Brave berücksichtigen nur Regeln mit hinterlegter
  thematischer Dokumentation; `not_evaluated`-Regeln werden nicht eingerechnet.
- Wegen der unterschiedlichen Zahl zugeordneter Regeln sind die Profil-Scores
  nicht direkt zwischen Suchmaschinen vergleichbar. Der GEO-Crawlscore nutzt
  GEO-Befunde des gemeinsamen Crawls und ist nicht identisch mit dem separaten
  GEO-Check für eine einzelne URL.

## Darstellung in der Oberfläche

- **Site-Audit:** vier Profil-Kacheln (Google, Bing, Brave, GEO). Ein Klick
  filtert die Befundtabelle auf das Profil, ein zweiter hebt den Filter auf.
  Die Tabelle zeigt je Befund die Spalten „Herkunft“ (Technisch,
  Google-Empfehlung, Heuristik, GEO-Hypothese) und „Profile“.
- **Befund-Detailseite:** Karte „Einordnung“ mit der Klassifizierung und dem
  Status je Suchmaschine („dokumentiert · im Score“ bzw. „nicht bewertet“)
  samt Link zur Dokumentation.
- **Fundstellen:** In der Karte „Einordnung“ steht je Suchmaschine, ob ein Satz der Leitlinie die Prüfung wörtlich beschreibt
  („Zitat“) oder nur das Themenfeld („Themenbezug“), mit Abschnitt und Datum der Quelle
  (siehe [SEARCH_ENGINE_RULES.md](SEARCH_ENGINE_RULES.md)).
- **Exporte:** Der Issue-Export (CSV/XLSX/JSON) enthält die Spalten
  `classification` und `profiles`; der PDF-Bericht zeigt die Profil-Scores
  und je Befund die Spalte „Basis“.
- Jede Nicht-GEO-Regel steht explizit in genau einer der drei Mengen in
  `rules.py`; ein Test schlägt fehl, wenn eine neue Regel nicht eingeordnet ist.

Offizielle Anlaufstellen:

- <https://developers.google.com/search/docs/essentials>
- <https://developers.google.com/search/docs/fundamentals/seo-starter-guide>
- <https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls>
- <https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data>

## Nächste Arbeiten

1. Jede Regel einzeln durchsehen, mit relevanter konkreter Google-Quelle und
   Stand-Datum auszeichnen; für eigene Heuristiken statt Google-Zitat die
   Prüfmethodik dokumentieren.
2. Bewusst gesetzte `noindex`-, `canonical`-, `robots`- und
   Sprachvarianten gegen die gewünschte Indexierungsstrategie prüfen.
3. Die Quellen und Zuordnungen jeder einzelnen Regel weiter präzisieren.
4. Optional einen separaten technischen Google-Indexierungsstatus bilden –
   aber keinen scheinbar offiziellen Google-Compliance-Score behaupten.
5. Die Profil-Scores bei Bedarf nach gesonderter Validierung um eigene
   Gewichtungen oder historische Vergleiche erweitern.
