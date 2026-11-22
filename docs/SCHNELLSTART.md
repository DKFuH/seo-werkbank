# SEO-Werkbank – Schnellstart für Anwender

**Für:** Erstnutzer und Redakteure · **Dauer:** ca. 15–30 Minuten zuzüglich Crawl-Laufzeit  
**Ausführliche Anleitung:** [Benutzerhandbuch](BENUTZERHANDBUCH.md)

## A. Installation (einmalig)

Mit Docker Compose v2 und Python 3.11+:

```bash
git clone https://github.com/DKFuH/seo-werkbank.git
cd seo-werkbank
python scripts/full_stack.py up
```

Dann **http://localhost:8000** öffnen und den ersten Administrator anlegen. Unter Windows ggf. `py -3 scripts/full_stack.py up` benutzen. Der Starthelfer stellt Anwendung, PostgreSQL und eine interne SearXNG-Metasuche bereit. Ohne Docker gibt es auch einen Windows-Startweg in der [README](../README.md).

## B. Deine erste Website untersuchen

1. **Übersicht → Websites → Website hinzufügen**: Name und HTTPS-Start-URL eintragen.
2. Die Website über **Auswählen** aktivieren.
3. **Analyse → Crawler**: **Optionen** öffnen, URL-Limit und Parallelität passend einstellen.
4. **Crawl starten**; nach Ende im Crawl-Verlauf **Anzeigen**.
5. **Analyse → Website-Audit**: kritische und hohe Befunde zuerst prüfen.
6. **Analyse → Interne Verlinkung**: schwache und verwaiste Seiten ansehen.
7. Bei Korrekturen im CMS danach nochmals crawlen und Ergebnisse vergleichen.

## C. Google-Suchperformance hinzufügen

**Sichtbarkeit → Search Console**:

- **API-Variante:** Ein Administrator hinterlegt unter **System → Einstellungen** einen Google-OAuth-Client. Dann mit Google verbinden, Property auswählen, **Property speichern** und **Jetzt synchronisieren**.
- **CSV-Variante:** Leistungs-CSV-Dateien unter **CSV importieren** einzeln hochladen.

**Achtung:** Für Content-Refresh und seitenbezogene Messungen muss eine Zeile die **Suchanfrage und ihre URL zusammen** enthalten. Separate Query- und Pages-CSV-Dateien reichen dafür nicht. Undatierte CSV-Dateien erlauben keine Zeitvergleiche.

## D. Eine Content-Chance umsetzen

1. **Content → Content-Refresh**: Seite und passende Suchanfragen prüfen.
2. **Briefing kopieren** und fachlich überprüfen.
3. **Maßnahmen → SEO-Maßnahmen**: neuen Vorgang vom Typ **Content** mit Ziel-URL anlegen.
4. Falls GSC-Daten geeignet sind: **28-Tage-Baseline messen**.
5. **Content → Content-Entwürfe**: Vorgang auswählen, neuen Text und Grund eintragen, speichern, prüfen und freigeben.
6. **Im eigenen CMS veröffentlichen**. Die Werkbank veröffentlicht nicht selbst.
7. Vorgang anschließend als veröffentlicht markieren und nach ausreichender Zeit eine Folgemessung aufnehmen.

## E. Mehr Funktionen nach Bedarf

| Was willst du tun? | Wo? |
|---|---|
| Zielkeyword speichern / aktuelle Rankingbeobachtung erfassen | **Sichtbarkeit → Ranktracker** |
| Suchergebnisse vergleichen | **Sichtbarkeit → SERP-Analyse** (Suchanbieter nötig) |
| Themen und echte Fragen dokumentieren | **Content → SEO-Research** |
| Einzeltext mit Wettbewerbern vergleichen | **Content → Content-Optimierung** oder **WDF*IDF** |
| KI-Zitierungen protokollieren | **Sichtbarkeit → KI-Erwähnungen** |
| Wiederholbare KI-Prompts speichern | **Sichtbarkeit → KI-Empfehlungen & Referrals** |
| Besuchsdaten ansehen | **Conversion → Matomo** (Zugangsdaten nötig) |
| Funnel- und Vertrauenshinweise erfassen | **Content → SEO-Research**, dann **Conversion → Conversion & Trust** |
| Fallstudien-Entwürfe planen | **Content → SEO-Research**, dann **Content Studio** |
| Regelmäßige Prüfungen anlegen | **Maßnahmen → Monitoring** |
| PDFs, CSVs und Excel-Berichte holen | **Maßnahmen → Berichte** |

## F. Typische Probleme

- **Leeres Dashboard:** Meist fehlt der erste Crawl, ein GSC-Import oder die richtige Websiteauswahl.
- **Kein SERP-Ergebnis:** Unter **System → Einstellungen → SERP-Anbieter** den Anbieter prüfen; SearXNG kann von Suchmaschinen blockiert werden.
- **Keine Content-Refresh-Daten:** Query und URL fehlen als Paar im selben GSC-Datensatz.
- **Kein Content-Entwurf:** Zuerst einen Content-Vorgang unter **SEO-Maßnahmen** erstellen.
- **KI-Modell oder Matomo nicht verfügbar:** Instanzweite Konfiguration ist Administratoraufgabe.
- **Keine Wirkung erkennbar:** Auf denselben Zeitraum, dieselbe Datenquelle und ausreichende Impressionen achten; Veränderungen beweisen keine Kausalität.

Mehr Details, sämtliche Menüpunkte, Datengrenzen, Berechtigungen und Fehlerbehebung: **[Benutzerhandbuch](BENUTZERHANDBUCH.md)**. 
