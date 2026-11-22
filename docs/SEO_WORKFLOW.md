# SEO-Maßnahmen und GSC-Vergleichsmessungen

Seite: `/seo-work` · API: `/api/sites/{id}/seo-work`

## Vorgänge

Ein Vorgang ist ein manuell gepflegter Eintrag. Die App veröffentlicht nichts, verschickt keine Bewertungsanfragen und pitcht nichts
automatisch.

| Typ | Erlaubte Status |
|---|---|
| `content` | planned → draft → approved → published → measured |
| `review` | planned → requested → received |
| `publication` | planned → pitched → accepted → published → verified / lost |
| `local` | planned → in_progress → completed |
| `competitor` | observed → investigating → actioned / dismissed |

- Content-Vorgänge brauchen eine Ziel-URL.
- Ein Status, der nicht zum Typ passt, wird mit `422` abgelehnt.
- Content-Entwürfe mit getrennter Freigabe hängen an Content-Vorgängen (siehe [Content-Entwürfe](CONTENT_PROPOSALS.md)).

## GSC-Vergleichsmessungen (Snapshots)

Für Content-Vorgänge kann ein Snapshot `baseline` (einmalig) und beliebig viele `followup` gespeichert werden.

- Grundlage sind nur **datierte GSC-Zeilen mit Suchanfrage UND URL** (`query_page`), deren URL exakt der Ziel-URL entspricht.
  Zeilen ohne Suchanfrage werden nie einer Seite zugeordnet.
- Liegen API- und CSV-Daten vor, zählen nur die API-Daten; beide werden nie addiert.
- Das Zeitfenster (7–180 Tage, Standard 28) **endet am neuesten Datentag der gesamten Site** in dieser Quelle, nicht am letzten Tag
  der URL. Hatte die Seite im Fenster keine Impressionen, wird der Snapshot mit `422` abgelehnt, statt still einen alten Zeitraum zu
  verwenden.
- Position ist der impressionsgewichtete Mittelwert der Query-Zeilen.
- Klicks und Impressionen aus Query-URL-Paaren sind niedriger als die Seitensummen in der GSC-Oberfläche, weil Google anonymisierte
  Suchanfragen nicht ausliefert.

Ein Vorher/Nachher-Vergleich zeigt nur eine zeitliche Veränderung. Saisonalität, Google-Updates und andere Änderungen sind nicht
herausgerechnet; eine Kausalaussage über die Maßnahme ist daraus nicht ableitbar.
