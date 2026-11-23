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
- **CSV-Variante:** Leistungs-CSV-Dateien unter **CSV importieren** einzeln hochladen. Im Fenster **Spalten zuordnen** erkannte Spalten prüfen, fehlende von Hand zuordnen und das Zahlenformat bestätigen.

**Achtung:** Für Content-Refresh und seitenbezogene Messungen muss eine Zeile die **Suchanfrage und ihre URL zusammen** enthalten. Separate Query- und Pages-CSV-Dateien reichen dafür nicht. Undatierte CSV-Dateien erlauben keine Zeitvergleiche.

## D. Rankings und Erreichbarkeit im Blick behalten

1. **Sichtbarkeit → Ranktracker → Portfolio (GSC):** wichtigste Zielkeywords mit Ziel-URL und Label anlegen. Die Positionen stammen aus der Search Console.
2. Im Tab **Alle GSC-Keywords** nach **Top-3-Funden** und **Chancen** (Position 4–20) schauen und passende Suchanfragen **Ins Monitoring** übernehmen.
3. **Maßnahmen → Website Health → Überwachung starten:** Die Website wird alle 15 Minuten auf Erreichbarkeit und Antwortzeit geprüft; Vorfälle erscheinen als Meldung.

## E. Eine Content-Chance umsetzen

1. **Content → Content-Refresh**: Seite und passende Suchanfragen prüfen.
2. **Briefing kopieren** und fachlich überprüfen.
3. **Maßnahmen → SEO-Maßnahmen**: neuen Vorgang vom Typ **Content** mit Ziel-URL anlegen.
4. Falls GSC-Daten geeignet sind: **28-Tage-Baseline messen**.
5. **Content → Content-Entwürfe**: Vorgang auswählen, neuen Text und Grund eintragen, speichern, prüfen und freigeben.
6. **Im eigenen CMS veröffentlichen**. Die Werkbank veröffentlicht nicht selbst.
7. Vorgang anschließend als veröffentlicht markieren und nach ausreichender Zeit eine Folgemessung aufnehmen.

## F. Weitere technische Prüfungen nach Bedarf

Diese Funktionen sind bewusst **nicht** Teil des Pflicht-Schnellstarts. Sie nutzen einen vorhandenen Crawl oder erfordern eine ausdrückliche Diagnose.

1. **Analyse → Tracking & Rendering:** Eigene Seiten-URL eintragen und **„Roh-HTML und JavaScript vergleichen“** wählen. Für den Browservergleich und den Consent-Test muss Playwright/Chromium **auf dem Backend** installiert sein; der normale Docker-Stack bringt Chromium nicht mit.
2. **Consent:** Checkbox für die Berechtigung bestätigen. Optional die getrennten Akzeptieren-/Ablehnen-Szenarien auswählen und **„Consent-Diagnose ausdrücklich starten“** klicken. Ein protokollierter Fremdhost ist keine automatische Rechtsbewertung.
3. **Bilder:** Auf derselben Seite Bildhinweise aus dem **letzten Crawl** ansehen. Ein frühes Lazy-Load-Bild ist nur ein möglicher LCP-Kandidat; echte LCP-/CLS-Werte stehen unter **Analyse → PageSpeed**.
4. **Relaunch:** **Analyse → Crawler → Crawl anzeigen → Relaunch**. Zwei abgeschlossene Crawls vor/nach dem Relaunch auswählen, bei URL-Änderungen Zuordnungen `alt => neu` erfassen und **„Relaunch prüfen“** klicken.
5. **Keyword-Overlap:** **Sichtbarkeit → SERP-Analyse → Zwei Keywords vergleichen**. Zwei Keywords und ggf. zwei manuelle URL-Listen eingeben. Gemeinsame URLs und Suchintention vergleichen.
6. **Paginierung:** **Analyse → Interne Verlinkung → Paginierung**. Tiefe und eingehende Links kontrollieren.
7. **Schema:** **Analyse → Strukturierte Daten → Rich-Result-Potenzial**. Gefundene JSON-LD-Typen und Validator-Hinweise prüfen.
8. **Verzeichnisse:** **Content → SEO-Research → Verzeichnisqualität** dokumentieren; anschließend unter **Maßnahmen → Lokale Nachweise** vergleichen.
9. **KI-Quellen:** Dieselbe tatsächliche Frage an mehreren Tagen unter **Sichtbarkeit → KI-Erwähnungen** erfassen; darunter **„Wiederkehrende KI-Quellen“** ansehen.

**Ausführliche Klickanleitungen:** [Benutzerhandbuch, Kapitel 6.4, 7.4–7.7, 9.4, 10.4 und 13.5](BENUTZERHANDBUCH.md).

## G. Mehr Funktionen nach Bedarf

| Was willst du tun? | Wo? |
|---|---|
| Zielkeywords mit GSC-Positionen verfolgen, Chancen finden | **Sichtbarkeit → Ranktracker** |
| KI-Zugang, llms.txt und CDN-Sperren prüfen | **Sichtbarkeit → GEO-Check** |
| Suchergebnisse vergleichen | **Sichtbarkeit → SERP-Analyse** (Suchanbieter nötig) |
| Themen und echte Fragen dokumentieren | **Content → SEO-Research** |
| Einzeltext mit Wettbewerbern vergleichen | **Content → Content-Optimierung** oder **WDF*IDF** |
| KI-Zitierungen protokollieren | **Sichtbarkeit → KI-Erwähnungen** |
| Wiederholbare KI-Prompts speichern | **Sichtbarkeit → KI-Empfehlungen & Referrals** |
| Besuchsdaten ansehen | **Conversion → Matomo** (Zugangsdaten nötig) |
| Funnel- und Vertrauenshinweise erfassen | **Content → SEO-Research**, dann **Conversion → Conversion & Trust** |
| Fallstudien-Entwürfe planen | **Content → SEO-Research**, dann **Content Studio** |
| Erreichbarkeit und Antwortzeit überwachen | **Maßnahmen → Website Health** |
| Regelmäßige Prüfungen und E-Mail-/Webhook-Meldungen | **Maßnahmen → Monitoring**, **System → Einstellungen** |
| PDFs, CSVs und Excel-Berichte holen | **Maßnahmen → Berichte** |
| Anleitung zu einem Bildschirm finden | **System → Hilfe & Handbuch** |

## H. Typische Probleme

- **Leeres Dashboard:** Meist fehlt der erste Crawl, ein GSC-Import oder die richtige Websiteauswahl.
- **Kein SERP-Ergebnis:** Unter **System → Einstellungen → SERP-Anbieter** den Anbieter prüfen; SearXNG kann von Suchmaschinen blockiert werden.
- **Keine Content-Refresh-Daten:** Query und URL fehlen als Paar im selben GSC-Datensatz.
- **Kein Content-Entwurf:** Zuerst einen Content-Vorgang unter **SEO-Maßnahmen** erstellen.
- **KI-Modell oder Matomo nicht verfügbar:** Instanzweite Konfiguration ist Administratoraufgabe.
- **Tracking & Rendering ohne Browser:** Playwright/Chromium ist eine zusätzliche Installation; die reinen Bildhinweise benötigen nur einen abgeschlossenen Crawl.
- **Keine Relaunch-Daten:** Zwei abgeschlossene Crawls derselben Website auswählen.
- **Keine Verzeichnis-/KI-Quellenbewertung:** Zuerst Research-Einträge bzw. tatsächlich beobachtete KI-Zitationen dokumentieren.
- **CSV-Import bricht ab:** Im Fenster **Spalten zuordnen** fehlt ein Pflichtfeld; die passende Spalte von Hand wählen.
- **Ranktracker ohne Gerätedaten:** Search Console einmal neu synchronisieren.
- **Keine Wirkung erkennbar:** Auf denselben Zeitraum, dieselbe Datenquelle und ausreichende Impressionen achten; Veränderungen beweisen keine Kausalität.

Mehr Details, sämtliche Menüpunkte, Datengrenzen, Berechtigungen und Fehlerbehebung: **[Benutzerhandbuch](BENUTZERHANDBUCH.md)**. 

## E. Optional: SEO-Operations nach dem ersten Crawl

Nach dem ersten abgeschlossenen Crawl kannst du unter **Analyse → Weiterleitungen** sichere Redirect-Entwürfe erstellen, simulieren und nach Freigabe als Konfiguration exportieren. Der Export installiert nichts auf dem Server. [Weiterleitungen](REDIRECTS.md)

Unter **Sichtbarkeit → Logfile & 404** kannst du Apache-/Nginx-Access-Logs importieren und verdichtete 404-Statistiken ansehen. User-Agent-Angaben wie `googlebot_claim` sind nicht verifiziert. Bei passenden Ersatzzielen wird lediglich ein freigabepflichtiger Redirect-Entwurf angelegt. [Logfile-Anleitung](LOG_ANALYSIS.md)

Unter **Analyse → Strukturierte Daten → Schema-Management** entstehen JSON-LD-Vorschläge aus Crawl-Fakten. Speichere sie als Content-Entwurf, prüfe sie separat und verwende zum Einbetten in HTML nur den **sicher serialisierten HTML-Block** aus der Freigabeansicht, nicht den rohen JSON-Entwurf. [Schema-Management](STRUCTURED_DATA.md)

**Update von älteren Versionen:** Migration `0013` stoppt bei vorhandenen doppelten Redirect-Quell-URLs pro Website; betroffene Datensätze müssen vor erneutem Start geprüft werden. Die [bekannten Einschränkungen](../KNOWN_LIMITATIONS.md) dokumentieren die Grenzen.
