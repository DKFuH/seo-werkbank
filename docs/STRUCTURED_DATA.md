# Schema-Management: Crawl → Entwurf → Freigabe

Das Schema-Management ist ein neuer Reiter unter **Analyse → Strukturierte Daten**.
Es ersetzt weder Googles Rich Results Test noch die redaktionelle Prüfung.

## Ablauf

1. Im letzten abgeschlossenen Crawl eine **indexierbare HTML-Seite** auswählen.
2. Schema-Typ wählen und eine vorbefüllte JSON-LD-Fassung erzeugen.
3. Beobachtete Werte stammen aus Title/H1, Beschreibung, Canonical, Sprache
   und ggf. OG-Bild. **Nicht belegte** Preise, Verfügbarkeiten,
   Anschriften, Rezensionen, FAQ-Antworten und Datum werden nicht ergänzt.
4. Vorhandene JSON-LD-Strukturen und Entwurf im Diff vergleichen.
5. Fehlende Fakten manuell ergänzen und als **Content-Maßnahme mit
   `content_type=application/ld+json`** speichern.
6. Unter **Maßnahmen → Content-Entwürfe** getrennt prüfen und freigeben.
   Der Freigabeschritt validiert JSON-LD und blockiert Strukturfunde/Fehler.
   **Keine automatische CMS-Änderung oder Veröffentlichung**.
7. Nach manueller Veröffentlichung Crawl erneut starten und prüfen,
   ob das erwartete Markup tatsächlich ausgeliefert wird.

## Vorlagen

- Site-scoped `SchemaTemplate`: Name, Schema-Typ, URL-Pfad-Glob, Feldzuordnung.
- Pfadmuster sind einfache Globs (beispielsweise `/ratgeber/*`),
  keine Regex und keine ausführbaren Ausdrücke.
- Erlaubte Feldnamen: `name`, `headline`, `url`, `description`,
  `image`, `inLanguage`.
- Zulässige Platzhalter: `{title}`, `{h1}`, `{description}`, `{url}`,
  `{canonical}`, `{lang}`, `{og_image}`, `{site_name}`, `{site_url}`.
- **Vorlagen auf Seiten anwenden (Vorschau)** verarbeitet maximal 30
  passende Seiten und verändert keine davon. Pro Seite sind Quelle,
  Diff und Validator-Befunde sichtbar.
- Neue Vorlagen werden je Website gespeichert; sie sind für andere
  Mandanten nicht sichtbar.

## Deutsche Generator-Defaults

Die generischen Vorlagen verwenden `EUR`, `DE` und
`inLanguage=de` als **editierbare Beispiele**, nicht als nachgewiesene
Eigenschaften einer Seite. Insbesondere wird keine Lieferbarkeit behauptet.
Die Datenbasierte Vorbefüllung setzt Sprachangaben nur aus dem Crawl;
Land/Preis werden **nicht** automatisch aus einer .de-Domain gefolgert.

## Grenzen

- Der Validator prüft eine dokumentierte Teilmenge typischer schema.org-
  und Google-Felder, **keine vollständige semantische schema.org-Gültigkeit**.
- Die korrekte Syntax garantiert **keine** Google-Rich-Result-Berechtigung,
  Darstellung, Indexierung oder Rankingverbesserung.
- Aus URL-Segmenten erzeugte Breadcrumb-Beschriftungen sind Vorschläge,
  keine bestätigte sichtbare Navigation.
- Der Entwurf referenziert den letzten Crawl, nicht zwingend den aktuellen
  Live-Zustand. Bei anderen Änderungen einen neuen Crawl erstellen.
- Bestehende Freigabeprotokolle und Berechtigungen bleiben erhalten.

Primärquellen:
- https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data
- https://developers.google.com/search/docs/appearance/structured-data/sd-policies
- https://schema.org/docs/documents.html
