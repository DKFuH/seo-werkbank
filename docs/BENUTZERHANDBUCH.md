# SEO-Werkbank – Benutzerhandbuch

**Stand:** Hauptbranch vom 23. November 2026  
**Zielgruppe:** Websitebetreiber, SEO-Redakteure, Agenturen und Administratoren  
**Projekt:** https://github.com/DKFuH/seo-werkbank  
**Lizenz:** MIT · Basierend auf OpenSEOSuite

> **Wichtiger Unterschied:** Dieses Handbuch beschreibt die Funktionen, die im Repository vorhanden sind. Eine dokumentierte API-Möglichkeit ist nicht automatisch eine bereits verbundene externe Datenquelle. Google-Messwerte, manuelle Beobachtungen und eigene Schätzungen werden im Programm unterschiedlich behandelt.

## Inhaltsverzeichnis

1. [So benutzt du dieses Handbuch](#1-so-benutzt-du-dieses-handbuch)
2. [Schnellstart in 15 Minuten](#2-schnellstart-in-15-minuten)
3. [Installation und erster Administrator](#3-installation-und-erster-administrator)
4. [Orientierung und Navigation](#4-orientierung-und-navigation)
5. [Website anlegen und auswählen](#5-website-anlegen-und-auswählen)
6. [Crawler einrichten und starten](#6-crawler-einrichten-und-starten)
7. [Technische Ergebnisse richtig bearbeiten](#7-technische-ergebnisse-richtig-bearbeiten)
8. [Google Search Console verbinden oder importieren](#8-google-search-console-verbinden-oder-importieren)
9. [Keywords, Rankings und SERP-Analyse](#9-keywords-rankings-und-serp-analyse)
10. [Wettbewerber, Backlinks und lokale SEO](#10-wettbewerber-backlinks-und-lokale-seo)
11. [Content recherchieren und optimieren](#11-content-recherchieren-und-optimieren)
12. [SEO-Maßnahme, Entwurf und Freigabe](#12-seo-maßnahme-entwurf-und-freigabe)
13. [KI-Sichtbarkeit und GEO](#13-ki-sichtbarkeit-und-geo)
14. [Conversion, Matomo und Wirtschaftlichkeit](#14-conversion-matomo-und-wirtschaftlichkeit)
15. [Monitoring, Berichte und Exporte](#15-monitoring-berichte-und-exporte)
16. [Administratoreinstellungen](#16-administratoreinstellungen)
17. [Vollständige Menü- und Funktionsübersicht](#17-vollständige-menü--und-funktionsübersicht)
18. [Empfohlener Wochenablauf](#18-empfohlener-wochenablauf)
19. [Fehlerbehebung](#19-fehlerbehebung)
20. [Datenqualität, Berechtigungen und Grenzen](#20-datenqualität-berechtigungen-und-grenzen)
21. [Betrieb, Updates und Sicherungen](#21-betrieb-updates-und-sicherungen)
22. [Weiterführende Dokumentation](#22-weiterführende-dokumentation)

---

## 1. So benutzt du dieses Handbuch

Das Handbuch ist nach dem **Weg durch die Anwendung** aufgebaut. Jeder Ablauf enthält möglichst:

- **Wo?** Menübereich und exakte Bildschirmbezeichnung.
- **Voraussetzung:** Welche Daten, Berechtigungen oder Einstellungen vorher nötig sind.
- **Wie?** Schritte in der richtigen Reihenfolge.
- **Ergebnis:** Was anschließend sichtbar bzw. gespeichert wird.
- **Grenze:** Was das Ergebnis *nicht* beweist.

Die Oberfläche ist deutschsprachig. Die Menübereiche lauten **Übersicht, Analyse, Sichtbarkeit, Content, Conversion, Maßnahmen und System**. Sie lassen sich auf- und zuklappen. Auf schmalen Bildschirmen wird die Navigation über das Menü geöffnet. Die aktive Website wird oben in der Kopfzeile ausgewählt; fast alle Auswertungen beziehen sich auf diese Auswahl.

**Begriffe:**

- **Website:** Ein vom Nutzer angelegtes Projekt mit Start-URL und Crawl-Konfiguration.
- **Crawl:** Zeitpunktbezogene Untersuchung der Website und ihrer erreichbaren URLs.
- **Befund:** Regelbasierter Hinweis des Crawlers; sollte an der betroffenen URL geprüft werden.
- **GSC:** Google Search Console; liefert gemessene Such-Impressionen, Klicks, CTR und Durchschnittspositionen.
- **SERP:** Suchergebnisseite eines Suchdienstes bzw. eines konfigurierten SERP-Anbieters.
- **Nachweis:** Manuell erfasste Quelle/URL; eine gespeicherte Adresse ist noch keine externe Verifikation.
- **Entwurf:** Gespeicherter Änderungsvorschlag; die Website wird dadurch nicht geändert.
- **Szenario:** Rechnung mit vom Nutzer gewählten Annahmen; keine Umsatzprognose.

## 2. Schnellstart in 15 Minuten

**Ziel:** Eine Website erstmals technisch prüfen und die ersten Maßnahmen erkennen.

1. Installation gemäß Kapitel 3 starten und die Oberfläche öffnen.
2. Beim ersten Besuch ein Administratorkonto einrichten und anmelden.
3. **Übersicht → Websites → Website hinzufügen** öffnen. Projektname und vollständige Start-URL eintragen, z. B. `https://example.de/`.
4. Die neue Website über **Auswählen** aktivieren; sie erscheint danach in der Kopfzeile.
5. **Analyse → Crawler** öffnen. Falls nötig über **Optionen** das URL-Limit und die Parallelität anpassen. **Crawl starten** wählen.
6. Nach Abschluss **Analyse → Website-Audit** öffnen. Zuerst *kritische* und *hohe* Befunde ansehen und die betroffenen URLs prüfen.
7. **Analyse → Interne Verlinkung** öffnen und Seiten mit geringer Verlinkung oder konkrete Linkchancen betrachten.
8. Optional **Sichtbarkeit → Search Console** öffnen. Dort entweder Google verbinden oder eine vorhandene Leistungs-CSV importieren.
9. **Content → Content-Refresh** aufrufen, sofern **GSC-Suchanfrage-URL-Daten** vorliegen. Eine Seite mit nachvollziehbarem Potenzial auswählen.
10. **Maßnahmen → SEO-Maßnahmen**: Einen Content-Vorgang mit Ziel-URL anlegen. Weitere Schritte stehen in Kapitel 12.

**Fertig, wenn:** Ein abgeschlossener Crawl vorliegt, die ersten Befunde gesichtet sind und mindestens eine konkrete Maßnahme mit Verantwortlichkeit außerhalb oder innerhalb der Teamorganisation geplant ist.

**Noch nicht nötig:** Matomo, ein KI-Anbieter, MCP oder ein kostenpflichtiger SERP-Dienst. Grundlegende Crawls und Audits funktionieren ohne sie.

### 2.1 Zusätzliche Diagnosen nach dem ersten Crawl

Wenn du bereits einen Crawl hast, sind drei weitere Arbeitswege besonders nützlich:

- **Analyse → Tracking & Rendering:** Eine **URL deiner ausgewählten Website** eingeben und Roh-HTML mit dem JavaScript-Rendering vergleichen; bei installiertem Playwright und entsprechender Berechtigung optional Consent-Abläufe ausdrücklich testen. Bildwarnungen nutzen den letzten Crawl (Kapitel 7.4 und 7.5).
- **Analyse → Crawler → einen Crawl anzeigen → Relaunch:** Zwei abgeschlossene Crawls derselben Website vor und nach einer Umstellung auswählen (Kapitel 6.4).
- **Sichtbarkeit → SERP-Analyse → Zwei Keywords vergleichen:** Gemeinsame Ergebnis-URLs zweier Keywords vergleichen, entweder über einen konfigurierten Anbieter oder zwei manuelle URL-Listen (Kapitel 9.4).

Im weiteren Verlauf findest du auch die Paginierung, die Schema-Prüfung, die Verzeichnisbewertung und wiederholte KI-Zitationsquellen – jeweils im passenden Fachmodul. Für den laufenden Betrieb lohnen sich außerdem **Maßnahmen → Website Health** (Erreichbarkeit und Antwortzeit, Kapitel 15.1) und das **Portfolio im Ranktracker** (echte GSC-Positionen der Zielkeywords, Kapitel 9.2).

## 3. Installation und erster Administrator

### 3.1 Empfohlener Docker-Start (PostgreSQL + interne SearXNG-Suche)

**Voraussetzung:** Docker mit Compose v2, Python 3.11 oder neuer, genügend freier Speicher und Netzwerkzugang für das Herunterladen der Images.

Im Terminal ausführen:

```bash
git clone https://github.com/DKFuH/seo-werkbank.git
cd seo-werkbank
python scripts/full_stack.py up
```

Unter Windows ggf. `py -3 scripts/full_stack.py up` verwenden.

Dann im Browser **http://localhost:8000** öffnen und beim ersten Aufruf das Administratorkonto anlegen. Die weiteren Seiten sind erst nach Anmeldung verfügbar.

Der Starthelfer legt **fehlende** Datenbank- und SearXNG-Geheimnisse in der lokalen, nicht einzucheckenden `.env`-Datei an. Vorhandene Zugangsdaten werden nicht überschrieben. Die Daten werden in Docker-Volumes gespeichert.

Die integrierte SearXNG-Suche läuft ausschließlich innerhalb des Compose-Netzwerks: `http://searxng:8080` ist **keine** Browseradresse deines Rechners. In der Anwendung ist SearXNG als Anbieter vorausgewählt, solange noch kein anderer SERP-Anbieter gespeichert wurde.

Weitere Befehle:

```bash
python scripts/full_stack.py ps
python scripts/full_stack.py logs
python scripts/full_stack.py down
```

`down` stoppt die Installation, **ohne** die Daten-Volumes zu löschen. `docker compose down -v` kann Daten unwiederbringlich entfernen und ist kein normaler Stopp-Befehl.

### 3.2 Windows ohne Docker

Für eine lokale Entwickler-/Einzelplatzinstallation existiert ein Windows-Startweg:

```bat
cd backend
python -m venv .venv
.venv\Scripts\pip install -e ".[dev]"
cd ..\frontend
npm install
npm run build
```

Anschließend im Stammverzeichnis `start-seo-werkbank.cmd` ausführen und **http://localhost:8000** öffnen. Dieser Weg setzt eine geeignete Python- und Node.js-Installation voraus. Bei Problemen siehe die Projekt-README und die ursprüngliche Installationsdokumentation.

### 3.3 Sicherheitsgrundregeln

- Das erste angelegte Konto erhält Administratorrechte. Verwende ein eigenes, starkes Passwort.
- Die Docker-Gesamtausgabe bindet die Anwendung standardmäßig nur an `127.0.0.1`. Für einen öffentlichen Zugriff sind HTTPS-Reverse-Proxy, Zugriffskontrolle, Backups und Härtung nötig.
- PostgreSQL und die private SearXNG-Instanz **nicht öffentlich freigeben**.
- API-Schlüssel und OAuth-Secrets nicht als Text in Screenshots, Tickets oder GitHub-Issues veröffentlichen.
- **Nicht mit echten Website-/Kundendaten experimentieren, ohne zu prüfen, wo diese gespeichert oder an externe KI-Anbieter übermittelt werden.**

Detaillierte Betriebsanleitung: [Docker-Gesamtausgabe](DOCKER_FULL.md).

## 4. Orientierung und Navigation

### 4.1 Grundaufbau

**Links:** Die Funktionsgruppen. **Oben:** Auswahl der aktuell bearbeiteten Website, Crawl-Status, Meldungen sowie Konto-/Darstellungsaktionen. **Mitte:** Der jeweils gewählte Arbeitsbereich.

Die Navigation bleibt trotz vieler Unterseiten kompakt: Ein Klick auf eine Gruppe klappt sie auf; der Bereich der aktiven Seite ist automatisch geöffnet.

**System → Hilfe & Handbuch** führt von jedem Thema direkt zum passenden Bildschirm und zur ausführlichen Anleitung.

### 4.2 Was zeigt das Dashboard?

**Übersicht → Dashboard** enthält für die gewählte Website vier Bereichskarten:

1. **Technisches SEO:** Letzter Crawl, Score, wichtige Probleme, untersuchte Seiten.
2. **Google-Suche:** GSC-Klicks, Impressionen, mittlere Position und ggf. ein vergleichbarer Vorzeitraum.
3. **KI-Erwähnungen:** Dokumentierte manuelle Stichproben; keine automatisch gemessene KI-Reichweite.
4. **Optimierungen:** Offene und abgeschlossene SEO-Vorgänge.

Darunter folgen technische Crawl-Diagramme sowie Meldungen und Jobs. Bei fehlenden Daten erscheint eine Leermeldung, **kein geschätzter Ersatzwert**.

**Tipp:** Immer zuerst kontrollieren, ob oben die **richtige Website** ausgewählt ist. Dies ist die häufigste Ursache für vermeintlich „fehlende“ Daten.

## 5. Website anlegen und auswählen

**Wo:** `Übersicht → Websites`

1. **Website hinzufügen** klicken.
2. Im Feld **Name** eine sprechende Projektbezeichnung eintragen.
3. Im Feld **URL** die vollständige Start-URL inklusive `https://` angeben.
4. **Website hinzufügen** bestätigen.
5. In der Tabelle **Auswählen** anklicken oder die Website oben im Auswahlfeld aktivieren.

**Bearbeiten:** Mit dem Stift-Symbol öffnet sich das Formular für den Namen und die **Standard-Crawleinstellungen**. Die Start-URL selbst lässt sich nach Anlage nicht ändern; dafür muss eine neue Website angelegt werden.

**Löschen:** Das Papierkorb-Symbol entfernt die Website nach Bestätigung. Vorher benötigte Exporte und Sicherungen erstellen; bei laufendem Crawl kann das Löschen gesperrt sein.

**Wichtig:** Die Domain-Auswahl beeinflusst die Zuordnung eigener Suchdaten, Crawls, Linkziele und KI-Zitationen. Eigene Website und Wettbewerber sind **getrennte Objekte**.

## 6. Crawler einrichten und starten

**Wo:** `Analyse → Crawler`

### 6.1 Ersten Crawl ausführen

1. Website oben auswählen.
2. **Crawler** öffnen.
3. Unter **Crawl starten** bei Bedarf **Optionen** öffnen.
4. Ein angemessenes **Max. URLs**-Limit setzen; beim ersten Test klein anfangen.
5. **Parallelität** und **Pause (ms)** so wählen, dass der Zielserver nicht unnötig belastet wird.
6. **robots.txt beachten** aktiviert lassen; **XML-Sitemaps nutzen**, wenn passende Sitemaps vorhanden sind.
7. **Crawl starten** anklicken.
8. Fortschritt beobachten; der Crawl läuft serverseitig weiter, auch wenn du die Ansicht verlässt.
9. Nach Abschluss im **Crawl-Verlauf** den Durchlauf mit **Anzeigen** öffnen.

**Wenn ein Crawl läuft:** Über **Crawl abbrechen** bzw. **Abbrechen** kannst du ihn stoppen.

### 6.2 Einstellungen verstehen

| Einstellung | Bedeutung | Empfehlung |
|---|---|---|
| Max. URLs | Obergrenze der zu untersuchenden URLs | Für einen ersten Probelauf bewusst begrenzen |
| Max. Tiefe | Anzahl Links ab Startseite | Nicht zu niedrig wählen, wenn Unterseiten wichtig sind |
| Parallelität | Gleichzeitige Serveranfragen | Bei kleinen Websites/Servern niedrig beginnen |
| Pause (ms) | Abstand zwischen Anfragen | Belastung des Zielservers berücksichtigen |
| robots.txt beachten | Für Crawler ausgeschlossene Bereiche nicht crawlen | Normalerweise aktiviert lassen |
| XML-Sitemaps nutzen | Weitere URLs über vorhandene Sitemaps finden | Für normale Website-Audits hilfreich |
| Subdomains einbeziehen | Auch Unterdomains berücksichtigen | Nur bei Bedarf aktivieren |
| nofollow-Links folgen | Auch gekennzeichnete Links verfolgen | Je nach Prüfziel |
| Externe Links prüfen | Status ausgehender Linkziele abrufen | Zusätzliche Zeit/Anfragen berücksichtigen |
| Bilder prüfen | Bilddateien prüfen | Für Bildfehler und Größenanalyse |
| JavaScript rendern | Browserbasiertes Rendering über Playwright | Nur wenn auf dem Server verfügbar; wesentlich langsamer |
| Einschluss-/Ausschluss-Muster | URL-Bereiche eingrenzen/auslassen | Sinnvoll bei großen oder dynamischen Websites |

**Weitere Optionen:** Timeout, Wiederholungen, externe Link-/Bildlimits und User-Agent sind im erweiterten Konfigurationsformular der Website verfügbar. Die dort gespeicherten Werte gelten für neue Crawls; im Crawler können sie pro Durchlauf geändert werden.

**Einschluss-/Ausschluss-Muster** sind einfache Textmuster mit `*`, `^` und `$`, keine uneingeschränkten regulären Ausdrücke. Falsch gesetzte Muster können den Crawl auf unerwartet wenige Seiten beschränken.

### 6.3 Ergebnisse des Crawlers

Im geöffneten Crawl stehen unter anderem folgende Reiter zur Verfügung:

- **Seiten:** URL, HTTP-Status, Indexierbarkeit, Klicktiefe, Wortzahl, Antwortzeit, Befunde und Score.
- **Links:** Intern, extern, defekt, Weiterleitung oder `nofollow`; mit Quell- und Zielangaben.
- **Weiterleitungen:** Weiterleitungsketten und Zielstatus.
- **Duplikate:** Auffälligkeiten bei Title, Description, H1 und Inhalt.
- **Struktur:** Klicktiefe, HTTP-Statusklassen, Inhaltstypen und Gründe fehlender Indexierbarkeit.
- **Relaunch:** Zwei abgeschlossene Crawls mit optionalen alten/neuen URL-Zuordnungen abgleichen (Kapitel 6.4).

**Nummerierung:** Crawls werden pro Website gezählt, „Crawl 1“ bis „Crawl n“; Wettbewerber-Crawls haben eine eigene Zählung. Wird ein Crawl gelöscht, rücken die späteren nach, die Zählung bleibt lückenlos. Dieselbe Nummer steht in Exporten und im PDF-Bericht.

**Export:** Aus dem Crawler können unter anderem Seiten, Befunde und Links als CSV exportiert werden. Wenn zwei Durchläufe vorhanden sind, kannst du im Audit die Entwicklung vergleichen.

**Grenze:** Der Crawl untersucht erreichbare Seiten zu einem bestimmten Zeitpunkt. Dynamische Zustände, nicht gerenderte Inhalte oder Loginbereiche können fehlen.

### 6.4 Relaunch nach einer Website-Umstellung überprüfen

**Wo:** `Analyse → Crawler → abgeschlossenen Crawl mit „Anzeigen“ öffnen → Reiter „Relaunch“`

**Voraussetzungen:** Mindestens **zwei abgeschlossene Crawls derselben Website**, idealerweise einer *vor* und einer *nach* dem Relaunch. Ohne den älteren Crawl kann das Werkzeug keine historische Ausgangslage rekonstruieren.

1. Den Crawler öffnen, den nach dem Relaunch erstellten Crawl mit **Anzeigen** öffnen und den Reiter **Relaunch** wählen.
2. Im Feld **Crawl vor dem Relaunch** den älteren, im Feld **Crawl nach dem Relaunch** den neueren Durchlauf auswählen. Die Anwendung bietet die abgeschlossenen Crawls in Auswahllisten an.
3. Falls sich URLs geändert haben, unter **Geplante URL-Zuordnungen (optional)** pro Zeile eine Zuordnung eingeben, beispielsweise:
   ```text
   https://example.org/alt => https://example.org/neu
   https://example.org/ratgeber-alt → https://example.org/ratgeber-neu
   ```
   Auch `->` wird akzeptiert. Zeilen ohne gültigen Trenner werden ignoriert.
4. Auf **Relaunch prüfen** klicken und die angezeigten Statusgruppen sichten.
5. **„Ziel fehlt im neuen Crawl“** bedeutet nur: Im neueren gespeicherten Crawl nicht gefunden. **„Weiterleitung prüfen“** bedeutet, dass die notwendige Weiterleitung der alten URL im Crawl **nicht eindeutig belegt** ist. **„Ziel nicht indexierbar“**, **„Canonical weicht ab“** und **„Titel geändert“** müssen an den konkreten Seiten überprüft werden.
6. Kritische URLs im Browser und ggf. mit einer separaten HTTP-Weiterleitungsprüfung kontrollieren, die Änderungen im CMS/Server vornehmen und danach erneut crawlen.

**Ergebnis:** Eine Liste alter, geplanter neuer und beobachteter Ziel-URLs einschließlich technischer Auffälligkeiten. **Kein** automatischer Redirect-Eintrag, kein vollständiger Cross-Domain-Migrationsassistent und kein Beleg, dass eine im Crawl nicht gefundene URL tatsächlich fehlt. Für einen Domainwechsel unterstützt der aktuelle Vergleich nicht automatisch zwei getrennte Website-Projekte.

## 7. Technische Ergebnisse richtig bearbeiten

### 7.1 Website-Audit und Template-Prüfung

**Wo:** `Analyse → Website-Audit`

1. Website auswählen und abgeschlossenen Crawl sicherstellen.
2. **Website-Audit** öffnen.
3. Nach Schweregrad und Kategorie priorisieren.
4. Einen Befund anklicken: Betroffene URLs und Prüfhilfe ansehen.
5. Problem an der Website selbst nachvollziehen.
6. Nach der externen Korrektur erneut crawlen.
7. Wenn vorhanden **Mit früherem Crawl vergleichen** verwenden.
8. Nachweise als Aufgabe unter **Maßnahmen → SEO-Maßnahmen** dokumentieren.

**Template-Content-Erkennung:** Das Audit kann Seiten mit einem ungewöhnlich hohen Anteil gleicher Textpassagen auf anderen indexierbaren Seiten markieren. Dies ist ein **Hinweis zur manuellen Prüfung**, nicht ein automatischer Google-Penalty-Nachweis. Gemeinsame Navigations- und CTA-Blöcke werden bei der Erkennung teilweise herausgefiltert.

### 7.2 Interne Links

**Wo:** `Analyse → Interne Verlinkung`

Unter **Top-Seiten**, **Schwache Seiten**, **Verwaist**, **Ankertexte**, **Linkchancen**, **Linkgraph** und **Paginierung** findest du verschiedene Sichten auf die internen Links.

**Vorgehen:** Eine relevante Zielseite mit wenigen eingehenden Links auswählen → unter **Linkchancen** einen semantisch sinnvollen Kontext suchen → vorgeschlagene Textpassage/Anker prüfen → Link **im CMS manuell** setzen → nach erneutem Crawl kontrollieren.

Ein Linkvorschlag ändert die Website noch nicht.

### 7.3 Sitemaps, Schema, PageSpeed, International und Local

**Sitemaps & Indexierung:** `Analyse → Sitemaps & Indexierung`. Prüft Sitemap-URLs, robots.txt, fehlende indexierbare Seiten und Canonical-Abweichungen. Ein erzeugtes `sitemap.xml`-Dokument muss bei Bedarf selbst im Webauftritt bereitgestellt werden.

**Strukturierte Daten:** `Analyse → Strukturierte Daten`. Unter **Validator** eine URL oder JSON-LD eingeben und prüfen; unter **Generator** einen Schema-Typ auswählen, Felder ausfüllen, Markup erzeugen und anschließend **selbst** in die Website einbauen. Der zusätzliche Reiter **Rich-Result-Potenzial** wertet JSON-LD des letzten Crawls aus (siehe 7.7).

**PageSpeed:** `Analyse → PageSpeed`. URL und Gerät auswählen, Quelle festlegen, **Test starten**. Feldwerte echter Chrome-Nutzer (wenn vorhanden) von Lighthouse-Labormesswerten unterscheiden. Unter **Top-Seiten im Batch prüfen** lassen sich die 3, 5 oder 10 am besten verlinkten Seiten des letzten Crawls auf einmal mobil testen; die **Felddaten-Abdeckung** zeigt, für welche Seiten echte LCP-, INP- und CLS-Werte vorliegen. Fehlen Chrome-UX-Report-Daten, bleibt der echte Wert unbekannt. Details: [Monitoring und Batch-PageSpeed](NOTIFICATIONS_PAGESPEED.md).

**Internationales SEO:** `Analyse → Internationales SEO`. Hreflang-Angaben, HTML-Sprache und Sprach-/Länderverzeichnisse kontrollieren.

**Lokales SEO:** `Analyse → Lokales SEO`. LocalBusiness-Daten, NAP-Konsistenz (Name/Adresse/Telefon), Standortseiten und importierte Verzeichniseinträge prüfen.

### 7.4 Consent- und Tracking-Zeitfolge im Browser untersuchen

**Wo:** `Analyse → Tracking & Rendering`, Karte **Consent- und Tracking-Zeitfolge**

**Voraussetzungen:** Die gewünschte URL gehört zur aktuell ausgewählten Website. Auf dem Backend müssen **Playwright und Chromium** installiert sein (siehe Kapitel 21 und [Browserdiagnostik](TECHNICAL_DIAGNOSTICS.md)). Standard-Docker enthält Chromium nicht. Teste nur Websites, auf denen du zu solchen Browserinteraktionen berechtigt bist.

1. Website oben auswählen und im Feld **Seiten-URL der ausgewählten Website** die vollständige `https://`-URL eintragen.
2. Für den ersten Überblick die optionalen Zustimmung-/Ablehnungsfelder **nicht** auswählen. Es wird dann nur die **erste frische Browsersitzung** untersucht.
3. Wenn du zusätzlich die Reaktion einer Consent-Oberfläche untersuchen willst, das jeweilige Kontrollkästchen für **„Alle akzeptieren“** bzw. **„Alle ablehnen“** aktivieren. Beide Szenarien starten in **getrennten frischen Browserkontexten**.
4. **„Ich darf die angegebene Website mit Browserinteraktionen testen.“** bestätigen.
5. **Consent-Diagnose ausdrücklich starten** auswählen.
6. Unter den Szenarien `initial`, `accept` oder `reject` Anzahl und zeitliche Reihenfolge der Anfragen ansehen. **„clicked_candidate_button“** bedeutet lediglich, dass ein passend beschrifteter sichtbarer Button geklickt wurde. **„not_found“** bedeutet, dass kein passender Button gefunden wurde; damit ist keine Aussage über eine CMP-Konfiguration verbunden.
7. Auffällige **Zeitpunkte und Dritthosts** notieren und, falls nötig, mit den Browser-Entwicklertools und der tatsächlichen Consent-Plattform überprüfen.

**Beispiel:** Eine Anfrage an einen Analyse-Host beim Seitenaufruf *vor* einer Nutzeraktion ist ein Anlass zur Prüfung der Einwilligungslogik. **Nicht** automatisch ein Verstoß oder ein Beweis für fehlerhaftes Tracking.

**Ergebnis:** Pro Szenario bis zu **120 Anfragen** mit relative(m) Zeitpunkt, Hostname, Ressourcentyp und grobem Tracker-Hinweis. **Nicht enthalten** sind vollständige Request-URLs, Cookies, Header, Payloads oder ein rechtsverbindlicher DSGVO-/Consent-Mode-Test. Die Untersuchung erfolgt nur nach ausdrücklicher Auslösung; der tatsächliche CMP-Speicherzustand wird damit nicht verifiziert.

### 7.5 Roh-HTML mit JavaScript-Rendering vergleichen und Bilder prüfen

**Wo:** `Analyse → Tracking & Rendering`

**Roh-HTML vs. Rendering:**

1. Eine URL **der ausgewählten Website** in **Seiten-URL** eingeben.
2. **Roh-HTML und JavaScript vergleichen** auswählen (Playwright/Chromium muss installiert sein).
3. Die Werte für **Wörter**, **Seitentitel**, **Links** und **neue Überschriften** betrachten.
4. Bei deutlichen Unterschieden den Quelltext der Seite und die gerenderte Ansicht prüfen. Beispielsweise kann ein bedeutender Ratgeberabschnitt erst nach JavaScript-Ausführung erscheinen.
5. Bei Bedarf die technische Ursache im Website-Code beheben und erneut testen.

Das Ergebnis ist der Vergleich zwischen HTTP-Roh-HTML und **einem** Playwright-Rendering. Er simuliert **nicht** automatisch den tatsächlichen Zugriff von ChatGPT, Perplexity, Googlebot oder anderen Crawlern und beweist keine Aufnahme in KI-Suchergebnisse.

**Bild- und LCP-Hinweise:**

1. Zunächst einen normalen Crawl abschließen. Für diese Teilprüfung ist **kein Playwright erforderlich**.
2. Auf derselben Seite die Karte **Bild- und mögliche LCP-Risiken (letzter Crawl)** aufrufen.
3. Geprüft werden die im HTML erfassten Bilder, insbesondere **fehlende `width`-/`height`-Attribute** und **frühe Bilder mit `loading="lazy"`**.
4. Den betreffenden Bildbereich manuell prüfen. Ein fehlendes HTML-Attribut kann durch CSS kompensiert sein; ein Bild weit oben im HTML muss nicht das tatsächliche LCP-Element sein.
5. Für echte LCP-/CLS-Messungen **Analyse → PageSpeed** und reale bzw. Lighthouse-Daten verwenden.

**Grenze:** Die Bildhinweise sind Markup-Heuristiken aus den ersten untersuchten Bildern/Seiten des letzten Crawls. Weder das echte LCP-Element noch die Wirkung auf den Core Web Vitals Score wird hier gemessen.

### 7.6 Paginierung und tiefe Archivseiten überprüfen

**Wo:** `Analyse → Interne Verlinkung → Reiter „Paginierung“`

1. Einen Crawl durchführen, der auch Kategorie- und Archivseiten einschließt.
2. **Interne Verlinkung → Paginierung** öffnen.
3. Bei auffälligen Blätterseiten die **Klicktiefe**, die Zahl der **eingehenden Links** und die **technische Indexierbarkeit** prüfen.
4. Seiten mit hoher Tiefe oder wenigen Eingangslinks im realen Navigationspfad testen. Dabei kontrollieren, ob wichtige Produkt- oder Ratgeberseiten zuverlässig erreichbar sind.
5. Im CMS ggf. Paginierungslinks und zusätzliche sinnvolle interne Pfade verbessern, dann erneut crawlen.

**Ergebnis:** Hinweise zu Seiten mit typischen Paginierungs-URLs oder `rel="next"/"prev"`. Eine paginierte Seite ist nicht automatisch fehlerhaft; die `rel`-Angaben sind kein allgemeiner Google-Indexierungszwang.

### 7.7 Strukturierte Daten und mögliches Rich-Result-Potenzial

**Wo:** `Analyse → Strukturierte Daten → Reiter „Rich-Result-Potenzial“`

1. Den jüngsten Crawl der Website abschließen.
2. **Strukturierte Daten** öffnen und **Rich-Result-Potenzial** auswählen.
3. Pro URL **vorhandene JSON-LD-Typen**, **mögliche Google-Suchfunktionen** sowie die Zahl der **Validator-Fehler und Hinweise** ansehen.
4. Bei Fehlern die angezeigten konkreten Prüffunde (`level`, `path`, `message`) sichten. Zum Nachprüfen **Validator** verwenden und den betroffenen JSON-LD-Block oder die URL eingeben.
5. Korrekturen im CMS vornehmen, neu crawlen und zusätzlich die **aktuelle Google-Search-Central-Dokumentation** für den konkreten Rich-Result-Typ konsultieren.

**Ergebnis:** Eine technisch-redaktionelle Vorprüfung der im Crawl dokumentierten JSON-LD-Daten. Die Liste unterstützter Rich-Result-Typen ist **nicht vollständig**; Validierung und möglicher Typ bedeuten **nicht**, dass Google die Seite für ein Rich Result qualifiziert oder eines anzeigt.

## 8. Google Search Console verbinden oder importieren

**Wo:** `Sichtbarkeit → Search Console`

Es gibt zwei Wege. Du brauchst **keinen** Google-OAuth-Client, um CSV-Daten einzulesen.

### 8.1 Google-API anbinden (Administratorvorbereitung)

1. Unter **System → Einstellungen → Google Search Console** den Bereich öffnen.
2. In Google Cloud ein Projekt anlegen, die **Google Search Console API** aktivieren und einen OAuth-Client vom Typ **Webanwendung** erstellen.
3. Die unter Einstellungen angezeigte **Autorisierte Weiterleitungs-URI** bei Google **exakt** hinterlegen.
4. **OAuth-Client-ID** und **OAuth-Client-Secret** in der Werkbank speichern.
5. **Sichtbarkeit → Search Console** öffnen und **Google Search Console verbinden** auswählen.
6. Ein Google-Konto autorisieren, das Zugriff auf die gewünschte Search-Console-Property besitzt.
7. Die **Property für die ausgewählte Website** wählen und **Property speichern** anklicken.
8. **Tage synchronisieren** einstellen und **Jetzt synchronisieren** starten.

Der Import läuft als Job; währenddessen wird ein Fortschritt angezeigt. Google liefert Suchdaten oft erst mit Verzögerung.

**Wenn die Google-Property nicht erscheint:** Berechtigung des Google-Kontos und Property-Typ kontrollieren; in der Werkbank die richtige Website auswählen.

### 8.2 GSC-CSV importieren (ohne OAuth)

1. In der Google Search Console den Leistungsbericht für den gewünschten Zeitraum öffnen.
2. Exportierte CSV-Datei(en) herunterladen.
3. In der Werkbank **Search Console → CSV importieren** öffnen.
4. Eine Datei mit **CSV importieren** auswählen.
5. Im Fenster **Spalten zuordnen** prüfen, welche Spalte der Datei zu welchem Feld gehört. Erkannte Spalten sind
   vorausgewählt; jede Zuordnung lässt sich ändern oder auf „nicht importieren“ stellen. Daneben stehen Beispielwerte
   aus der Datei. Pflichtfelder sind mit * markiert. Bei Bedarf das Zahlenformat (Deutsch 1.234,5 / Englisch 1,234.5)
   festlegen, dann **… Zeilen importieren**.
6. Den Importstatus prüfen. Weitere Dateien einzeln importieren.
7. Die Option **Bisher importierte Zeilen derselben Art ersetzen** verwenden, wenn ein alter Import derselben Art ersetzt werden soll.

Unterstützt werden deutsche und englische Spaltennamen wie `Suchanfragen / Queries`, `Seiten / Pages`, `Klicks / Clicks`, `Impressionen / Impressions`. Deutsche Zahlenformate werden erkannt. Dateien mit anderen Spaltennamen (etwa aus anderen Tools oder selbst gebauten Tabellen) lassen sich über die Zuordnung importieren.

Dasselbe Zuordnungsfenster gibt es bei allen CSV-Importen: Backlinks, Branchenverzeichnisse (Lokales SEO) und Keywords. Dateien aus Excel in Windows-1252 und Keyword-Planer-Exporte mit Titelzeilen werden erkannt.

**Wichtig beim Import:**

- Eine Datei **ohne Datum** liefert keine belastbaren Zeitvergleiche.
- Eine Datei nur mit **Suchanfragen**, eine zweite nur mit **Seiten** bildet **keine Query-URL-Paare**.
- Für **Content-Refresh**, Keyword-Targeting und GSC-Maßnahmen-Snapshots werden Daten benötigt, in denen **Suchanfrage UND zugehörige URL in derselben Datenzeile** stehen.
- Dieselbe CSV nicht versehentlich zweimal im Anhänge-Modus importieren, sonst können Datensätze doppelt gezählt werden.

### 8.3 GSC-Bereiche interpretieren

- **Leistung:** Klicks, Impressionen, CTR, durchschnittliche Position, Verlauf und Dimensionen (Suchanfragen, Seiten, Länder, Geräte).
- **Auswertungen:** Chancen, rückläufige/neue/verlorene Suchanfragen, rückläufige Seiten und mögliche Kannibalisierung.
- **Content-Refresh:** Priorisierte Query-URL-Chancen und kopierbare redaktionelle Briefings.
- **Keyword-Recherche → Seitenzuordnung & Kannibalisierung:** Gewünschte Zielseite mit jener URL vergleichen, die für ein Keyword im verfügbaren GSC-Query-URL-Datensatz die meisten Impressionen erhält. Bei Abweichung wird ein Zielseitenkonflikt markiert.

GSC-Positionen sind **impressionsgewichtete Durchschnittswerte**, keine neutralen, einzelnen Platzierungen bei einer beliebigen Suche.

### 8.4 Eine URL bei Google auf Indexierung prüfen

**Wo:** `Sichtbarkeit → Search Console`, Bereich **Google URL Inspection**

**Voraussetzung:** Search Console per OAuth verbunden (8.1) und die zur Website gehörende Property gespeichert.

1. Eine URL derselben Website eintragen.
2. **URL bei Google prüfen** anklicken.
3. Den von Google gemeldeten Indexierungsstatus, den letzten Google-Crawl und die Canonical-Angaben ansehen.

Die Abfrage nutzt die **Google URL Inspection API**. Sie führt **keinen Live-Test** aus, ändert nichts an Googles Index und unterliegt Googles Kontingent. Details: [Google URL Inspection](GSC_URL_INSPECTION.md).

## 9. Keywords, Rankings und SERP-Analyse

### 9.1 Keyword-Recherche

**Wo:** `Sichtbarkeit → Keyword-Recherche`

1. Im Reiter **Recherche** ein Ausgangs-Keyword und passende Sprache/Land eingeben.
2. Autocomplete-Vorschläge abrufen und passende Begriffe **speichern**.
3. Unter **Gespeicherte Keywords** die Liste pflegen oder eine CSV aus dem Keyword-Planer importieren.
4. Unter **Seitenzuordnung & Kannibalisierung** prüfen, welche Seiten zu den gespeicherten Keywords passen.
5. Im **Cluster-Werkzeug** mehrere Begriffe anhand gemeinsamer Wörter gruppieren (lexikalisch).
6. Alternativ im Cluster-Werkzeug **SERP-Overlap-Clustering** wählen: 2–15 Keywords zeilenweise eintragen, einen SERP-Anbieter nutzen oder für **alle** Keywords Ergebnislisten einfügen, Überschneidungsschwelle wählen und **SERP-Cluster berechnen**. Gruppen auf die tatsächliche Suchintention prüfen; Cluster können transitiv sein, nicht jedes Keyword-Paar einer Gruppe ist zwingend ähnlich. Details: [SERP-Keyword-Clustering](KEYWORD_SERP_CLUSTERING.md).

**Keine erfundenen Suchvolumina:** Wenn weder ein gemessener Wert noch ein geeigneter Import vorliegt, darf eine Nachfragezahl fehlen.

### 9.2 Ranktracking

**Wo:** `Sichtbarkeit → Ranktracker`, Tabs **Portfolio (GSC)**, **Alle GSC-Keywords** und **Anbieter-Messungen**

**Portfolio (GSC)** zeigt die echten Positionen deiner Zielkeywords aus der Search Console, also dort, wo Google die Website tatsächlich ausgespielt hat.

1. Unter **Zielkeyword hinzufügen** Keyword, **Label** (frei, z. B. „lokal“), **Ziel-URL**, **Messart** (National, Lokal, Marke) und **Priorität** (P1–P3) eintragen. Vorhandene GSC-Historie ist sofort sichtbar.
2. Oben **Zeitraum** (7 Tage bis 12 Monate), **Gerät** und **Label** wählen. Verglichen wird immer mit dem gleich langen Zeitraum direkt davor.
3. Die Kacheln zeigen die **Ø Position** (nach Impressionen gewichtet, kleinere Zahl ist besser) mit Bewegung, die Verteilung auf 1–3, 4–10, 11–20, 21–50 und 51+, die Zahl verbesserter und verschlechterter Keywords und die reale Nachfrage (Impressionen, Klicks, CTR).
4. In der Tabelle zeigt **Ranking-URL**, welche Seite Google ausspielt. Weicht sie von der Ziel-URL ab, steht die Ziel-URL orange darunter. **„kleine Stichprobe“** heißt: weniger als 10 Impressionen im Zeitraum.
5. Ein Klick auf das Keyword öffnet die **Detailseite** mit Positionsverlauf und **Änderungsjournal**. Maßnahmen mit Datum notieren; sie erscheinen als orange Linie im Diagramm.

**Alle GSC-Keywords** listet jede Suchanfrage, für die Google die Website gezeigt hat, mit Trackingstatus:

- **Top-3-Fund:** nicht getrackt, Position bis 3, ab 10 Impressionen.
- **Chance:** nicht getrackt, Position 4–20, ab 10 Impressionen.
- **Ins Monitoring** übernimmt eine Suchanfrage samt vorhandener Historie ins Portfolio.

Über der Tabelle stehen Filter für Trackingstatus, Ranking-Bereich und Mindest-Impressionen; jede Spalte lässt sich sortieren.

**Gerätefilter:** braucht Daten aus dem Search-Console-Abruf; nach dem Update einmal neu synchronisieren. CSV-Exporte enthalten Suchanfrage und Gerät nicht zusammen.

**Anbieter-Messungen** erfasst Positionen von einem SERP-Anbieter oder von Hand, je Land und Gerät:

1. **Neues Zielkeyword**: Keyword, Land (zweistelliger ISO-Code), Sprache, Gerät und optional die gewünschte Zielseite eintragen.
2. **Keyword hinzufügen**.
3. Entweder eine selbst beobachtete Position über **Manuell speichern** dokumentieren oder **SERP-Anbieter abfragen** bewusst auslösen.
4. Bei weiteren Beobachtungen die Positionshistorie und den Vergleich **gleicher Anbieter** ansehen.

Bei mobilen oder stadtspezifischen Suchen sind die automatischen Anbieterabfragen eingeschränkt; solche Beobachtungen werden ggf. nur manuell erfasst. Ein nicht gefundener Treffer innerhalb der abgerufenen Ergebnistiefe beweist **keine** Nichtindexierung.

### 9.3 SERP-Analyse

**Wo:** `Sichtbarkeit → SERP-Analyse`

**Voraussetzung:** Unter **Einstellungen → SERP-Anbieter** muss z. B. SearXNG, Brave oder Google Programmable Search eingerichtet sein.

1. Keyword eingeben, bei Bedarf eigene URL ergänzen.
2. Analyse starten.
3. Tatsächlich geladene Ergebnis-URLs, Wortzahlen, Überschriften, Themen, Fragen und strukturierte Daten vergleichen.
4. Befunde als **redaktionelle Hinweise** verwenden und mit der eigenen Nutzerintention abgleichen.

SearXNG verwendet externe Suchmaschinen. Es kann CAPTCHA/Sperren erhalten und ist kein unabhängiger Google-Rankingindex. Ein SearXNG-Resultat ist nicht automatisch ein nachgewiesener Google-Platz.

### 9.4 Zwei Keywords anhand ihrer SERP-Überschneidung vergleichen

**Wo:** `Sichtbarkeit → SERP-Analyse`, Karte **„Zwei Keywords vergleichen (SERP-Überschneidung)“**

1. **Keyword A** und **Keyword B** eintragen, beispielsweise `günstige bürostühle` und `ergonomische bürostühle`.
2. Entweder einen SERP-Anbieter unter **System → Einstellungen → SERP-Anbieter** eingerichtet haben **oder** für **beide** Keywords Ergebnis-URLs in die beiden optionalen URL-Felder kopieren (jeweils eine vollständige URL pro Zeile, idealerweise in der beobachteten Ranking-Reihenfolge).
3. **Vergleichen** klicken.
4. Auf **Anbieter** (z. B. `manual` oder `searxng`), **Anzahl beider Ergebnislisten**, **gemeinsame URLs** und **Jaccard-Wert** achten.
5. Die gemeinsamen URLs und die tatsächliche Suchintention prüfen. Viele Überschneidungen *können* für eine gemeinsame Seite sprechen, wenige für getrennte Schwerpunkte. Die endgültige Seitenstruktur beruht aber nicht auf einem starren Schwellenwert.

**Beispiel:** Liste A enthält 10 URLs, Liste B enthält 10 URLs, davon 6 identisch. Das zeigt eine Überschneidung der beiden erfassten Ergebnislisten – aber keine verbindliche Google-Empfehlung, ob du eine oder zwei Landingpages brauchst.

**Grenzen:** Der Vergleich nutzt **exakt erfasste URL-Überschneidungen** und für automatische Abfragen den eingestellten Anbieter. Er liefert keine neutralen Google-Rankings, keine automatisch verifizierte KI-SERP und keine vollständige semantische Intent-Entscheidung. Das Formular verwendet die voreingestellten Länderspracheinstellungen `de`/`de`; weitere Locale-Varianten können über die zugrunde liegende API berücksichtigt werden.

## 10. Wettbewerber, Backlinks und lokale SEO

### 10.1 Wettbewerber untersuchen

**Wo:** `Sichtbarkeit → Wettbewerber`

1. Konkurrenzwebsite mit Namen und URL eintragen.
2. **Crawlen** anklicken.
3. Die technischen Daten mit der eigenen Website vergleichen.
4. Optional im **Themenradar** Unterschiede zwischen Wettbewerber-Crawls und eigenem Crawl betrachten.
5. Relevante Erkenntnisse als Maßnahmen erfassen.

Der Themenradar verwendet Wortgruppen aus tatsächlich gefundenen Seitenüberschriften; eine fehlende Wortgruppe ist keine bewiesene Marktlücke.

### 10.2 Backlinks

**Wo:** `Sichtbarkeit → Backlinks`

Vorhandene Backlinkdaten importieren und über die Ansichten **Links**, **Verweisende Domains**, **Anker**, **Linkziele** und **Chancen** sichten. Mit **Links prüfen** kann der gespeicherte Status überprüft werden; Export als CSV und Excel ist vorgesehen.

**Grenze:** Die SEO-Werkbank besitzt **keinen vollständigen Internet-Backlinkindex**. Sie kennt nur vorhandene/importierte bzw. lokal geprüfte Links. `nofollow`, Veröffentlichungsnachweis, Linkexistenz und Rankingwirkung sind unterschiedliche Eigenschaften.

### 10.3 Lokale Nachweise und Reputation

**Wo:** `Maßnahmen → Lokale Nachweise`

- Eigene Unternehmens-/NAP-Einträge und deren Übereinstimmung prüfen.
- Manuell erfasste Bewertungsanfragen verfolgen.
- Dokumentierte Publikationen mit vorhandenen Backlink-Daten abgleichen.

Die Werkbank verschickt weder Rezensionseinladungen noch verändert sie Google-Unternehmensprofile automatisch. Bewertungsanfragen dürfen nicht ausschließlich zufriedenen Kunden vorbehalten werden.

### 10.4 Branchenverzeichnisse nach Qualität statt bloßer Anzahl vergleichen

**Erfassung:** `Content → SEO-Research → Funktion „Verzeichnisqualität“`  
**Auswertung:** `Maßnahmen → Lokale Nachweise`, Karte **„Branchenverzeichnisse bewerten“**

1. Zunächst tatsächlich infrage kommende Portale recherchieren. Prüfen, ob sie fachlich/örtlich zur Website passen und einen nachvollziehbaren Nutzerwert haben.
2. In **SEO-Research** die Funktion **Verzeichnisqualität** auswählen.
3. **Titel** sowie die Pflichtangaben **Verzeichnisname**, **Listing-URL**, **Relevanz** und **redaktioneller Nutzwert** erfassen. Für die beiden Bewertungen jeweils einen **eigenen Wert von 0 bis 3** eintragen; dies sind keine gemessenen Google-Metriken.
4. Wenn bekannt, **Kosten in Euro**, **tatsächlich beobachtete Referral-Besuche** und eine **Quellennotiz** ergänzen. Keine geschätzten Besucher als Messwerte eingeben.
5. Den Research-Eintrag speichern, zu **Lokale Nachweise** wechseln und die Karte **Branchenverzeichnisse bewerten** ansehen.
6. Vorhandene **importierte Verzeichniseinträge und Backlink-Datensätze** gegen die erfasste URL vergleichen. Auch ein passender Datensatz bestätigt nicht automatisch redaktionelle Qualität oder echten Traffic.
7. Den Eintrag bei positiven Ergebnissen separat beantragen, dessen Status dokumentieren und – falls verfügbar – echte Referral-Daten nachtragen.

**Beispiel:** 120 € Kosten und **sechs tatsächlich erfasste Referral-Besuche** ergeben 20 € pro Referral-Besuch. Ohne identischen Zeitraum und saubere Quelle ist dieser Quotient nur eine Rechenhilfe; er beweist keine Conversion oder SEO-Wirkung.

**Grenzen:** Die Verzeichnisbewertung ist **subjektiv**. Es werden **kein Domain-Authority-Score**, keine garantierte Linkkraft, keine Google-Rankingwirkung und keine automatisch geprüfte Reichweite erzeugt. Ein kostenpflichtiger Eintrag ist nicht automatisch schlechter oder besser als ein kostenloser.

## 11. Content recherchieren und optimieren

### 11.1 Themen- und Fragenplanung

**Wo:** `Content → SEO-Research`

1. Unter **Rechercheeintrag erstellen** im Feld **Funktion** den gewünschten Datentyp wählen.
2. Titel sowie die für diesen Eintrag angezeigten Pflichtfelder ausfüllen.
3. Ggf. eine nachvollziehbare Quellen-URL und Notizen hinzufügen.
4. **Eintrag speichern**.
5. Die passenden Auswertungen unten bzw. unter **Qualität & CRO**, **SEO-Verlauf & GEO** oder **Content Studio** ansehen.

**Häufige Eintragsarten:**

| Auswahl im Research-Workspace | Was du eingibst | Wo du das Ergebnis nutzt |
|---|---|---|
| Geschäftsbezogene Themenlandkarte | Angebot, Merkmale, Zielgruppe | Überschriften-Wortabgleich im Research-Workspace |
| PAA-Fragenhierarchie | Thema, tatsächlich beobachtete Frage | Fragenhierarchie im Research-Workspace |
| Suchreise und Linkpfad | Quellseite, Zielseite, Funnel-Phase | Geplante Suchreisen / Linkprüfung |
| Content-Nachweise | Seiten-URL, konkrete Aussage, Beleg | **Qualität & CRO** |
| Landingpage-CRO-Audit | Seite, Kriterium, beobachtetes Ergebnis | **Qualität & CRO** |
| Vergleichs-/Alternativen-Audit | Vergleichsobjekte, Kriterium, Quelle | **Qualität & CRO** |
| Linkable-Asset-Briefing | Zweck, Zielgruppe, Format | **Qualität & CRO** |
| Indexierungsprotokoll | Seite, gemeldeter Status, Beleg | **SEO-Verlauf & GEO** |
| SERP-Feature-Beobachtung | Keyword, Quelle, Merkmale | **SEO-Verlauf & GEO** |
| SEO-Änderungsjournal | Ereignisdatum, Typ, Beschreibung | **SEO-Verlauf & GEO** |
| GEO-Quellenstichprobe | Plattform, Testprompt, Antwort, URLs | **SEO-Verlauf & GEO** |
| Conversion-Funnel-Schritt | Seite, Phase, Handlung, Hürde | **Conversion & Trust** |
| Vertrauensnachweis | Seite, Behauptung, Quelle | **Conversion & Trust** |
| Markenpositionierung | Markenname, Leistung, Positionierung | **Conversion & Trust** |
| Fallstudie | Projekt, Problem, Vorgehen, Ergebnis | **Content Studio** |
| Echte Kundenfrage | Anonymisierte Frage, Kontext, Zielgruppe | **Content Studio** |
| Externe Markenaussage | Aussage, Quelle, erwarteter Wortlaut | **Content Studio** |
| Marketing-Experiment | Hypothese, Kennzahl, Einheit, Datumswerte | **Content Studio** |
| Verzeichnisqualität | Verzeichnis, Listing-URL, eigene Relevanz 0–3, eigener redaktioneller Nutzwert 0–3, optional Kosten und Besuche | **Maßnahmen → Lokale Nachweise** |

**Hinweis:** Research-Einträge sind überwiegend **manuell dokumentierte Angaben**, keine live ermittelten Google-Fakten.

### 11.2 Content-Optimierung

**Wo:** `Content → Content-Optimierung`

1. Bestehende URL über **Von URL laden** übernehmen oder einen Textentwurf eingeben.
2. **Ziel-Keyword**, Title, Meta-Description und gegebenenfalls Nebenkeywords erfassen.
3. Optional bis zu zehn geeignete Wettbewerber-URLs eintragen.
4. **Inhalt analysieren** anklicken.
5. Titel, Lesbarkeit, relevante Begriffe, Themenabdeckung, FAQ-Anregungen, Strukturierung und interne Links prüfen.
6. Die sinnvollsten Änderungen redaktionell auswählen. Keine Texte nur zur Erhöhung eines errechneten Scores mit Keywords auffüllen.

Das Werkzeug analysiert Text; es nimmt keine automatische CMS-Änderung vor.

### 11.3 WDF*IDF

**Wo:** `Content → WDF*IDF`

1. Fokus-Keyword eingeben.
2. Eigene URL **oder** eigenen Text einfügen.
3. Bis zu zehn Wettbewerber-URLs eintragen.
4. **Analysieren** klicken.
5. Kurven, Wortverteilungen und Überschriften vergleichen.

**Wichtig:** Ein hohes WDF*IDF-Ergebnis ist **kein** offizieller Google-Rankingfaktor. Es ist eine sprachstatistische Vergleichshilfe.

### 11.4 Content-Refresh

**Wo:** `Content → Content-Refresh`

1. Datierte GSC-Query-URL-Daten bereitstellen.
2. Optional vorher crawlen.
3. Zeitraum einstellen.
4. Eine Seite mit aussagekräftiger Suchfrage, Impressionen und Position prüfen.
5. **Briefing kopieren** auswählen.
6. Das Briefing anhand von Suchintention, Fachwissen und nachprüfbaren Quellen überarbeiten.
7. Den Änderungsprozess über **SEO-Maßnahmen** und **Content-Entwürfe** fortsetzen.

„Zusätzliche Klicks“ im Content-Refresh sind, sofern angezeigt, eine **hypothetische CTR-Szenariorechnung**.

## 12. SEO-Maßnahme, Entwurf und Freigabe

Dies ist der empfohlene Workflow für nachvollziehbare Websiteänderungen.

### 12.1 Maßnahme anlegen

**Wo:** `Maßnahmen → SEO-Maßnahmen`

1. Unter **Neuen Vorgang dokumentieren** einen **Vorgangstyp** wählen.
2. Für redaktionelle Änderungen **Content** wählen.
3. Titel, **Ziel-URL** (für Content erforderlich), optional Quell-/Nachweis-URL und Notizen eintragen.
4. **Vorgang anlegen**.
5. Den Vorgang im passenden Status pflegen.

Typische Statusfolgen:

| Typ | Statusfolge |
|---|---|
| Content | `planned → draft → approved → published → measured` |
| Bewertung | `planned → requested → received` |
| Veröffentlichung | `planned → pitched → accepted → published → verified / lost` |
| Lokale Maßnahme | `planned → in_progress → completed` |
| Wettbewerb | `observed → investigating → actioned / dismissed` |

Statuswechsel außerhalb des jeweiligen Vorgangstyps werden abgelehnt. Die Zustände dokumentieren Arbeit – sie lösen **keine E-Mails und keine CMS-Veröffentlichung** aus.

### 12.2 Content-Entwurf anlegen und freigeben

**Wo:** `Content → Content-Entwürfe`

1. Den zuvor angelegten **Content-Vorgang** auswählen.
2. **Ausgangstext** (optional), **geplanten neuen Text** und **Änderungsgrund** eintragen.
3. Entwurf speichern.
4. Den eingeblendeten Textvergleich prüfen.
5. Erst nach redaktioneller Prüfung **freigeben**.
6. Änderungen **außerhalb der SEO-Werkbank im CMS** durchführen.
7. Wenn tatsächlich veröffentlicht, den Vorgang **als veröffentlicht markieren**.

Bei Bedarf kann ein freigegebener, noch nicht publizierter Entwurf zur weiteren Bearbeitung wieder geöffnet werden. Ein als veröffentlicht markierter Eintrag ist nicht automatisch durch Live-Websiteprüfung bestätigt.

**Für Fallstudien:** Unter **Content → SEO-Research** einen **Fallstudie**-Eintrag anlegen, dann unter **Content → Content Studio** einen Entwurf zur Freigabe erzeugen. Die Funktion formatiert nur eingegebene Fakten.

### 12.3 Wirkung anhand von GSC beobachten

**Wo:** `Maßnahmen → SEO-Maßnahmen`, beim betroffenen **Content-Vorgang**.

1. Vor der Änderung **28-Tage-Baseline messen** verwenden.
2. Nach Publikation und hinreichender Datenverfügbarkeit **Folgemessung aufnehmen**.
3. Klicks, Impressionen und Positionen vergleichen.
4. Ergebnis samt Datum und weiteren möglichen Einflussfaktoren dokumentieren.

**Voraussetzung:** Datierte GSC-Zeilen, die Suchanfrage und Ziel-URL zusammen enthalten. Ein direkter Vorher/Nachher-Vergleich beweist keine Kausalität.

## 13. KI-Sichtbarkeit und GEO

### 13.1 GEO-Check

**Wo:** `Sichtbarkeit → GEO-Check`

1. Öffentliche URL eingeben und **Prüfen** anklicken.
2. Die Ergebnisse nach Gruppen durchgehen:
   - **Zugang:** KI-Crawler in robots.txt, Indexierbarkeit, Snippet-Grenzen (`max-snippet`, `data-nosnippet`), Text ohne JavaScript, **KI-Signale in robots.txt** (ein von Cloudflare eingefügter Abschnitt mit KI-Sperren und `Content-Signal`-Werte), **KI-Sperren per Meta-Tag oder Header** (z. B. `<meta name="GPTBot" content="noindex">` oder `noai`) sowie **llms.txt** nach llmstxt.org samt `/llms-full.txt`.
   - **Integrität:** mögliche versteckte Anweisungen an KI-Systeme, strukturierte Daten, die nicht sichtbar auf der Seite stehen, widersprüchliche Datumsangaben und ein uneinheitlicher Markenname.
   - **Entität, Struktur, Belege:** Organisation/Person, sameAs, Autor, Aktualität, Antwort am Anfang, Frage-Überschriften, Listen und Tabellen, Zahlen und Quellen.
3. Auffälligkeiten redaktionell oder technisch prüfen und ggf. als Maßnahme dokumentieren.

Bei `Content-Signal` gilt: `search=no` oder `ai-input=no` hält die Website aus KI-Antworten heraus, `ai-train=no` betrifft nur das Training. Dieselben Zugangs- und Integritätsprüfungen laufen bei jedem Crawl als Audit-Regeln mit (Kategorie **GEO / KI-Suche**).

**Sperrt das CDN KI-Crawler?** Die Karte ruft eine Seite der ausgewählten Website einmal mit Browser- und dann mit der Kennung von elf KI-Crawlern ab (OAI-SearchBot, ClaudeBot, PerplexityBot, Googlebot, Applebot …). „gesperrt“ oder „Prüfseite“ heißt: Cloudflare oder eine Firewall weist diese Kennung ab, obwohl robots.txt sie vielleicht erlaubt. Die Anfragen kommen von diesem Server, nicht aus den Netzen der Anbieter; CDNs, die Crawler über ihre IP prüfen, behandeln echte Crawler unter Umständen anders. Das Ergebnis ist ein starker Hinweis, kein Beweis.

**llms.txt-Entwurf:** Die Karte erzeugt aus dem letzten Crawl einen Entwurf: Abschnitte nach dem ersten Pfadteil, am besten verlinkte Seiten zuerst, Titel und Meta-Description der Seiten als Text. Kopieren oder als Datei laden, prüfen, kürzen und dann als `/llms.txt` ins Wurzelverzeichnis der Website legen.

Die Erfüllung solcher Kriterien garantiert keine Aufnahme in KI-Antworten.

### 13.2 KI-Erwähnungen

**Wo:** `Sichtbarkeit → KI-Erwähnungen`

Manuell beobachtete Antworten mit Plattform, Prompt, möglicher Markennennung und belegter URL erfassen. Auswertungen beziehen sich **nur auf diese Stichproben**.

### 13.3 Wiederholbare KI-Prompttests

**Wo:** `Sichtbarkeit → KI-Empfehlungen & Referrals`

1. Unter **Prompt-Test anlegen** die **Testfrage** eingeben.
2. **Eigene Markennamen** und optional Wettbewerbernamen kommagetrennt erfassen.
3. **Test speichern**.
4. Eine **manuell beobachtete Antwort** samt Plattform eingeben und speichern, **oder** als Administrator einen konfigurierten Chatmodell-Test **bewusst ausführen**.
5. Beobachtete Markenworttreffer und Wettbewerbernennungen im Verlauf vergleichen.

Ein normales Sprachmodell, das einen Prompt beantwortet, ist **keine verifizierte Live-KI-Suchmaschine**. Texte können falsche oder erfundene Angaben enthalten.

### 13.4 SEO-Verlauf & GEO

**Wo:** `Sichtbarkeit → SEO-Verlauf & GEO`

Hier werden zuvor unter **SEO-Research** erfasste Änderungsevents, SERP-Merkmale, Indexierungsnotizen und KI-Zitationsstichproben zusammengeführt. Eine Kombination von zeitlich nahen Veränderungen ist noch keine Ursache-Wirkung-Beziehung.

### 13.5 Stabilität beobachteter KI-Quellen prüfen

**Wo:** `Sichtbarkeit → KI-Erwähnungen`, Karte **„Wiederkehrende KI-Quellen“**

1. Eine für deine Zielgruppe relevante Frage auswählen und sie **auf derselben KI-Plattform** an verschiedenen Tagen unter möglichst vergleichbaren Bedingungen erneut stellen.
2. Jede tatsächliche Beobachtung unter **KI-Erwähnungen** mit **Plattform**, **exaktem Prompt**, bei Bedarf **Modell/Version**, **tatsächlich angegebener Quellen-URL** und Datum erfassen; bei Bedarf alternativ passende `geo_sample`-Einträge unter **Content → SEO-Research** pflegen.
3. Die Karte **Wiederkehrende KI-Quellen** öffnen. Sie gruppiert Beobachtungen nach **Plattform und gleichlautender, normalisierter Frage**.
4. Unter den Quellen die Anzahl **unterschiedlicher Tage** ansehen, an denen eine bestimmte URL dokumentiert wurde. **„wiederholt“** bedeutet: mindestens an zwei unterschiedlichen Tagen beobachtet.
5. Auffällige Quellen als Rechercheanlass nutzen; einen Link oder eine Erwähnung nicht ohne Quellenprüfung als echte Empfehlung bewerten.

**Beispiel:** Dieselbe URL wird auf derselben Plattform bei identischer Frage am Montag und Donnerstag dokumentiert. Das wird als **zwei beobachtete Tage** gezählt. Zwei Wiederholungen am Montag allein belegen **keine zeitliche Stabilität**.

**Grenzen:** Es handelt sich um manuell dokumentierte Stichproben, nicht um vollständige Live-KI-Suche, verifizierte Zitationsanteile, Marktanteile, Sichtbarkeitsgarantien oder eine repräsentative Statistik. Modelländerungen und schwankende Antworten sind möglich.

## 14. Conversion, Matomo und Wirtschaftlichkeit

### 14.1 Matomo anbinden

**Administrator:** `System → Einstellungen → Matomo`

1. In Matomo unter **Persönlich → Sicherheit** einen API-Token mit Leserechten anlegen.
2. Unter Einstellungen **Matomo-URL** und `token_auth` eintragen.
3. Speichern.
4. `Conversion → Matomo` öffnen, Zeitraum und passende Matomo-Website auswählen.
5. Besuche, Kanäle, Suchmaschinen, Einstiegsseiten, Geräte und ggf. Ziele betrachten.

Crawl- und Matomo-Daten werden in der Auswertung auf die Website bezogen. Nicht jede indexierbare Seite muss Besucher erhalten, und fehlende Besuche beweisen nicht automatisch mangelnde Qualität.

### 14.2 KI-Referrals in Matomo

**Wo:** `Sichtbarkeit → KI-Empfehlungen & Referrals`, Bereich **KI-Referral-Besuche aus Matomo**.

1. Als Administrator die Matomo-Integration einrichten.
2. Einen Zeitraum wählen.
3. **Matomo bewusst abrufen** klicken.
4. Erkennbare Referral-Domains und nur tatsächlich verfügbare Conversion-Werte prüfen.

**Grenze:** Direkte Besucher, verdeckte Referrals, geräteübergreifende Abschlüsse und tatsächliche Umsätze können nicht vollständig zugeordnet werden.

### 14.3 Conversion & Trust

**Wo:** `Conversion → Conversion & Trust`

1. Unter **Content → SEO-Research** Einträge wie **Conversion-Funnel-Schritt**, **Vertrauensnachweis** und **Markenpositionierung** anlegen.
2. Seite, Funnel-Phase, konkrete Handlung, mögliche Hürde und Beleg-URL dokumentieren.
3. **Conversion & Trust** öffnen.
4. Gemeldete Funnel-Phasen, fehlende Beleglinks und einfache Crawl-Textsignale prüfen.
5. Visuelle Benutzerführung, Formulare und Echtheit von Rezensionen **manuell** testen.

Das Modul ist kein automatisierter Screenshot-/UX-Test und kein Ranking- oder Premium-Qualitätsscore.

### 14.4 Wirtschaftliche SEO-Chancen

**Wo:** `Conversion → Wirtschaftliche Chancen`

1. GSC-Daten und Content-Refresh-Chancen bereitstellen.
2. Eigene Annahmen für **Leadquote, Abschlussquote, Deckungsbeitrag je Auftrag** eingeben.
3. Je URL den **wirtschaftlich relevanten Besucheranteil** einschätzen.
4. Szenariowerte vergleichen.

**Wichtig:** Die Eingaben werden derzeit nicht dauerhaft gespeichert und sind keine Prognose. Es werden keine Standard-Leadquoten erfunden.

## 15. Monitoring, Berichte und Exporte

### 15.1 Website Health

**Wo:** `Maßnahmen → Website Health`

1. Website auswählen und **Überwachung starten**. Geprüft wird die Website-URL alle 15 Minuten.
2. Oben stehen der aktuelle Status (**UP**, **LANGSAM**, **DOWN**) und die Verfügbarkeit im gewählten Zeitraum (24 Stunden, 7 oder 30 Tage).
3. Die **Statusleiste** zeigt je Zeitabschnitt, ob alle Prüfungen in Ordnung waren, langsam oder fehlerhaft.
4. Das **Kerzendiagramm** zeigt die Antwortzeit je Zeitabschnitt: erste und letzte Prüfung als Kerzenkörper, schnellste und langsamste als Linie. Die gestrichelte Linie ist der Alert-Grenzwert, rote Marken unten zeigen Ausfälle.
5. **Vorfälle** listet jeden Ausfall und jede Phase mit hoher Antwortzeit mit Beginn, Dauer und Ursache, z. B. „HTTP Status Code 200 (Hohe Antwortzeit)“, „Timeout“ oder „SSL-Fehler“. Suchen, filtern und sortieren ist möglich.
6. Die **Monitoring-Übersicht** zeigt die geprüften Fehlerklassen und zählt die Vorfälle im Zeitraum: Weiterleitungen, Seite nicht gefunden, Serverfehler, Verbindungsstatus, Ladezeit, Timeouts, SSL, DNS, Content-Encoding, unvollständige Ladevorgänge, zu große Inhalte.
7. **Einstellungen** am Diagramm: Grenzwert in ms (Standard 2.000), nach wie vielen langsamen Prüfungen in Folge ein Vorfall entsteht (Standard 2) und das Prüfintervall (ab 15 Minuten). Weitere URLs lassen sich unter **Monitoring** im Erreichbarkeits-Monitor eintragen.

Jeder neue und jeder behobene Vorfall erzeugt eine Meldung (Glocke oben rechts) und geht über eingerichtete Benachrichtigungskanäle raus (15.2). Geprüft wird von dem Server aus, auf dem die SEO-Werkbank läuft: Ein Netzproblem zwischen diesem Server und der Website sieht wie ein Ausfall aus. Die Prüfungen laufen nur, solange die Anwendung läuft.

### 15.2 Wiederkehrende Monitore und Benachrichtigungen

**Wo:** `Maßnahmen → Monitoring`

1. Reiter **Monitore** öffnen.
2. **Neuer Monitor** wählen.
3. Monitorart (Erreichbarkeit, Audit, Sitemap, Metadaten, Wettbewerber, Search Console), optionalen Namen, Prüfintervall und ggf. zu prüfende URLs angeben.
4. Je nach Typ URL-Limit oder Positionsänderungsschwelle setzen.
5. Monitor anlegen; mit **Jetzt ausführen** manuell testen.
6. Unter **Meldungen** die Ergebnisse prüfen und bearbeitete Meldungen als gelesen markieren.

**Benachrichtigungen per E-Mail oder Webhook:** Als Administrator unter **System → Einstellungen → Monitor-Benachrichtigungen** einen SMTP-Server (STARTTLS) mit Absender und Empfänger und/oder einen HTTPS-Webhook eintragen, die Mindestschwere wählen und den Versand **ausdrücklich aktivieren**. Pro Monitorlauf gibt es einen gebündelten Versandversuch. Der Versand ist „best effort“; eine dauerhafte Wiederholungswarteschlange gibt es nicht.

Die Positionsmeldungen eines Search-Console-Monitors sind etwas anderes als das Portfolio im Ranktracker (9.2): Der Monitor meldet Änderungen, das Portfolio zeigt Stand und Verlauf.

### 15.3 Berichte

**Wo:** `Maßnahmen → Berichte`

1. Richtige Website wählen.
2. Bericht oder Exportformat auswählen.
3. Datei herunterladen.
4. Bei fehlendem Crawl oder fehlender Datenquelle zunächst die entsprechende Analyse durchführen.

Je nach Bereich stehen PDF-, CSV- und Excel-Exporte zur Verfügung. Dateinamen und PDF-Kopf tragen die Crawl-Nummer des Projekts („Crawl 3“). Ein Bericht ersetzt nicht die manuelle Prüfung besonders wichtiger Befunde.

## 16. Administratoreinstellungen

**Wo:** `System → Einstellungen`

| Bereich | Was du einrichtest | Pflicht? |
|---|---|---|
| Konto | Passwort ändern | Bei Bedarf |
| SERP-Anbieter | SearXNG, Brave oder Google Programmable Search | Für SERP-Anbieterabfragen |
| PageSpeed Insights | Optionaler API-Schlüssel | Für höhere/verlässlichere API-Kontingente sinnvoll |
| Matomo | URL und API-Token mit Leserechten | Für Besucher- und Zielauswertungen |
| KI-Anbieter | Ollama oder OpenAI-kompatible API, Modellkennung und ggf. Schlüssel | Nur für optionale KI-Funktionen |
| Google Search Console | OAuth-Client-ID und Client-Secret | Für Google-API-Verbindung und URL Inspection; CSV-Import geht ohne |
| Monitor-Benachrichtigungen | SMTP (STARTTLS) und/oder HTTPS-Webhook, Mindestschwere, Aktivierung | Für Meldungen per E-Mail/Webhook (15.2) |
| Über | Version, Backend-Status, Sicherheitsstatus | Information |

**Nur Administratoren** ändern die instanzweiten Integrationen. Der Zugriff auf instanzweit konfigurierte KI-Modellaufrufe und Matomo-Referral-Abfragen ist ebenfalls administrativ beschränkt. Benutzer verwalten ihre jeweils eigenen Websites; es existiert nicht automatisch eine gemeinsame Mandantenverwaltung für alle Projekte.

**SearXNG in Docker:** Normalerweise ist `http://searxng:8080` intern bereits eingestellt. Eine selbst eingetragene andere SERP-Konfiguration überschreibt diese Voreinstellung.

**Bei externer KI-API:** Prompts und ggf. Seiteninhalte können den eigenen Server verlassen. Vorher Kosten, Datenschutz, Zweck und Nutzungsrechte prüfen.

Alle hier gespeicherten Geheimnisse (API-Schlüssel, Passwörter, OAuth-Tokens) liegen **verschlüsselt** in der Datenbank. Zum Schlüssel siehe Kapitel 21.3.

## 17. Vollständige Menü- und Funktionsübersicht

Diese Tabelle ist zugleich ein **„Wo finde ich was?“**-Nachschlagewerk.

| Menübereich | Bildschirm | Zweck / Einstieg |
|---|---|---|
| Übersicht | **Dashboard** (`/`) | Lagebild zu Technik, Google, KI und Maßnahmen |
| Übersicht | **Websites** (`/sites`) | Website anlegen, wählen, Crawl-Standards ändern |
| Analyse | **Website-Audit** (`/audit`) | Regelbasierte Fehler und Hinweise je Crawl |
| Analyse | **Crawler** (`/crawler`) | Crawls starten, Fortschritt, Seiten, Links, Duplikate und **Relaunch**-Reiter |
| Analyse | **Tracking & Rendering** (`/diagnostics`) | Consent-Zeitfolge, Roh-/JS-Rendering und Bildhinweise |
| Analyse | **Interne Verlinkung** (`/internal-links`) | Linkstruktur, verwaiste Seiten, Linkchancen und **Paginierung** |
| Analyse | **Sitemaps & Indexierung** (`/sitemaps`) | Sitemap-/robots-/Canonical-Abgleich |
| Analyse | **Strukturierte Daten** (`/schema`) | JSON-LD prüfen, Markup erstellen und **Rich-Result-Potenzial** prüfen |
| Analyse | **PageSpeed** (`/pagespeed`) | Performance- und Web-Vitals-Prüfung |
| Analyse | **Internationales SEO** (`/international`) | Sprach- und Länderangaben |
| Analyse | **Lokales SEO** (`/local`) | LocalBusiness, NAP, Standortdaten |
| Sichtbarkeit | **Search Console** (`/search-console`) | Google-Messwerte per API oder CSV |
| Sichtbarkeit | **Ranktracker** (`/rank-tracking`) | GSC-Portfolio, alle GSC-Keywords mit Chancen, Anbieter-Messungen; Keyword-Detail unter `/rank-tracking/keywords/…` |
| Sichtbarkeit | **Keyword-Recherche** (`/keywords`) | Vorschläge, Keywords, Zuordnung, Cluster |
| Sichtbarkeit | **SERP-Analyse** (`/serp`) | Suchergebnisse und **Keyword-SERP-Überschneidungen** analysieren |
| Sichtbarkeit | **KI-Erwähnungen** (`/ai-visibility`) | Manuelle KI-Antworten und **wiederkehrende Zitationsquellen** |
| Sichtbarkeit | **KI-Empfehlungen & Referrals** (`/ai-intelligence`) | Prompttests und Matomo-KI-Referrals |
| Sichtbarkeit | **GEO-Check** (`/geo`) | KI-Zugang, Integrität, CDN-Test für KI-Crawler, llms.txt-Entwurf |
| Sichtbarkeit | **SEO-Verlauf & GEO** (`/research-monitoring`) | Änderungshistorie, SERP-/Index-/KI-Notizen |
| Sichtbarkeit | **Wettbewerber** (`/competitors`) | Konkurrenten hinzufügen und crawlen |
| Sichtbarkeit | **Themenradar** (`/competitor-radar`) | Themenindikatoren aus Wettbewerber-Crawls |
| Sichtbarkeit | **Backlinks** (`/backlinks`) | Importierte Links und Überprüfungen |
| Content | **SEO-Research** (`/research`) | Manuelle Forschungs-/Planungseinträge |
| Content | **Content-Optimierung** (`/content`) | Einzeltext/Seite prüfen |
| Content | **WDF*IDF** (`/wdf-idf`) | Sprachstatistischer Wettbewerbsvergleich |
| Content | **Content-Refresh** (`/content-refresh`) | GSC-basierte Aktualisierungschancen |
| Content | **Content-Entwürfe** (`/content-proposals`) | Änderungstexte speichern und freigeben |
| Content | **Content Studio** (`/content-studio`) | Fallstudien, Fragen, Marken, Experimente |
| Content | **Qualität & CRO** (`/research-quality`) | Quellen, CRO-Notizen und Asset-Briefings |
| Conversion | **Matomo** (`/matomo`) | Websitebesuche und Kanalentwicklung |
| Conversion | **Conversion & Trust** (`/conversion-trust`) | Funnel-/Nachweisprüfung |
| Conversion | **Wirtschaftliche Chancen** (`/opportunity-value`) | Eigene DB-Szenarien je SEO-Chance |
| Maßnahmen | **SEO-Maßnahmen** (`/seo-work`) | Aufgaben-/Veröffentlichungsstatus, Messung |
| Maßnahmen | **Lokale Nachweise** (`/seo-evidence`) | Verzeichnisse, **Verzeichnisqualität**, Bewertungen und Publikationen |
| Maßnahmen | **Website Health** (`/health`) | Erreichbarkeit, Antwortzeit, Vorfälle |
| Maßnahmen | **Monitoring** (`/monitoring`) | Regelmäßige Prüfungen und Meldungen |
| Maßnahmen | **Berichte** (`/reports`) | Export und Auswertung |
| System | **Einstellungen** (`/settings`) | Konto, Integrationen, Benachrichtigungen |
| System | **Hilfe & Handbuch** (`/help`) | Themen mit Direktlink zum Bildschirm und zur Anleitung |

Viele Spezialprüfungen haben keinen eigenen Menüpunkt, sondern sitzen im passenden Fachbildschirm: Relaunch im Crawler, Paginierung in der internen Verlinkung, Rich-Result-Potenzial bei den strukturierten Daten, SERP-Überschneidung in der SERP-Analyse, Verzeichnisqualität bei den lokalen Nachweisen und wiederkehrende KI-Quellen bei den KI-Erwähnungen.

**Hinweis zu den Links:** Die relativen Pfade in dieser Tabelle sind **Anwendungsrouten**, keine GitHub-Seiten. In deiner laufenden Installation lauten sie etwa `http://localhost:8000/search-console`.

## 18. Empfohlener Wochenablauf

Die folgende Routine ist eine **Arbeitsorganisation**, keine eingebaute vollautomatische Wochenaufgabe.

### Einmalige Einrichtung

- Website anlegen und ersten Crawl durchführen.
- GSC per API oder CSV bereitstellen.
- Optional Matomo, SERP-Anbieter und KI-Anbieter konfigurieren.
- Relevante Keywords und Wettbewerber erfassen.
- **Website Health** starten und bei Bedarf weitere Monitore und Benachrichtigungen einrichten.

### Jede Woche (z. B. Montag)

1. **Dashboard**: technische Änderungen, Google-Suchdaten, neue Meldungen, offene Maßnahmen.
2. **Ranktracker → Portfolio**: Bewegungen der Zielkeywords; unter **Alle GSC-Keywords** neue Top-3-Funde und Chancen.
3. **Search Console**: rückläufige Suchanfragen und auffällige Seiten.
4. **Content-Refresh**: zwei bis drei nachvollziehbare Kandidaten für redaktionelle Prüfung auswählen.
5. **Website-Audit**: neue wichtige Probleme kontrollieren; nicht blind jede Warnung beseitigen.
6. **SEO-Maßnahmen**: Status aktualisieren und neue Vorgänge anlegen; umgesetzte Änderungen im Änderungsjournal des Keywords notieren.
7. **Content-Entwürfe**: bei Bedarf prüfen und freigeben.
8. **Website Health** und **Monitoring**: Vorfälle der Woche und offene Meldungen durchsehen.
9. **Berichte**: nur für benötigte Stakeholder exportieren.

### Einmal monatlich

- Strategische Keywords und Zielseiten-Zuordnung kontrollieren.
- Wettbewerber- und Backlinkdaten aktualisieren.
- Bereits umgesetzte Maßnahmen mit einem neuen Crawl und geeigneten GSC-Zeiträumen vergleichen.
- Bei vorhandenen Matomo-Daten die besucherstarken Einstiegsseiten und Conversions prüfen.
- Gewählte KI-Prompts unter identischen Rahmenbedingungen wiederholen, falls KI-Sichtbarkeit Teil der Strategie ist.

### Hinweise zu einzelnen Prüfungen

**Tracking & Rendering:** Bei verdächtigen Drittanfragen zunächst die **initiale Sitzung** beobachten. Danach allenfalls mit ausdrücklicher Berechtigung getrennt **Akzeptieren** und **Ablehnen** testen. Die Protokolle sind keine automatische Einwilligungsprüfung.

**Relaunch:** Vor einer Änderung den Crawl sichern; nach der Änderung erneut crawlen und die **alten/neuen URLs explizit zuordnen**. Fehlende URLs im neuen Crawl separat live prüfen.

**SERP-Overlap:** Falls kein Suchanbieter erreichbar ist, **für beide Keywords** die manuell recherchierten Ergebnis-URLs einfügen. Die Positionen sollten aus derselben Quelle und einem vergleichbaren Zeitpunkt stammen.

**KI-Quellen:** Mindestens **dieselbe Frage auf derselben Plattform an zwei unterschiedlichen Tagen** dokumentieren, sonst kann keine Wiederholung über Tage erscheinen.

## 19. Fehlerbehebung

| Problem | Was du zuerst prüfst |
|---|---|
| Keine Daten im Dashboard | Richtige Website gewählt? Mindestens ein Crawl/GSC-Datensatz vorhanden? |
| Crawler findet kaum Seiten | robots.txt, Einschluss-/Ausschluss-Muster, Start-URL, Sitemap, URL-Limit, Tiefe, JavaScript-Rendering |
| Crawl bricht ab | Crawler-Verlauf/Fehlertext, Serverlogs, Timeout, Parallelität, Ressourcen |
| Kein GSC-Vergleich | Datumsspalte vorhanden? Ausreichend Tage? Daten für Suchanfrage UND URL in derselben Zeile? |
| API-Verbindung zu Google fehlt | OAuth-Client gespeichert? Exakte Redirect-URI? Richtiges Google-Konto? Berechtigte Property? |
| Ziel-URL wird falsch zugeordnet | Gewünschte Zielseite und die tatsächlich GSC-dominante Query-URL prüfen; Datenfenster beachten |
| Browserdiagnose meldet Playwright/Chromium nicht verfügbar | Die optionalen Pakete und den Chromium-Browser auf dem **Backend-Server** installieren; Standard-Docker enthält ihn nicht. Bilder aus Crawls funktionieren separat. |
| Consent-Button wird nicht gefunden | Die UI erkennt nur eindeutig beschriftete sichtbare „Alle akzeptieren“-/„Alle ablehnen“-Buttons. Eine andere CMP-Oberfläche nicht durch automatisches Klicken ersetzen; manuell prüfen. |
| Roh-/JS-Vergleich schlägt fehl | URL muss der ausgewählten Website gehören, HTML erreichbar sein und Playwright/Chromium auf dem Server laufen. Private Netzwerke sind für Browserdiagnosen gesperrt. |
| Keine Bildhinweise | Zuerst einen Crawl abschließen; fehlende Hinweise bedeuten nicht, dass echte LCP-/CLS-Messungen erfolgreich waren. |
| Relaunch zeigt kein Ergebnis | Zwei **abgeschlossene** Crawls derselben Website wählen; nach der Umstellung erneut crawlen; URL-Zuordnungen auf vollständige URLs prüfen. |
| Paginierung zeigt keine Seiten | Im letzten Crawl wurden keine URLs/`rel`-Signale mit den unterstützten Paginierungsmustern erkannt; URL-Tiefe und Crawl-Limits prüfen. |
| SERP-Overlap nicht möglich | Entweder einen SERP-Anbieter einrichten oder **beide** manuellen Ergebnislisten ausfüllen; Keywords müssen vorhanden sein. |
| Keine Verzeichnisqualitätsdaten | Unter **Content → SEO-Research → Verzeichnisqualität** zuerst einen Eintrag anlegen und Pflichtfelder (Relevanz, redaktioneller Wert) ausfüllen. |
| Keine wiederkehrenden KI-Quellen | Dieselbe Frage auf derselben Plattform an **mindestens zwei verschiedenen Tagen** mit Quellen-URL dokumentieren. |
| Keine SERP-Treffer | Anbieter konfiguriert? SearXNG intern erreichbar? Externe Engines durch CAPTCHA/Sperre beeinträchtigt? |
| KI-Test kann nicht starten | Als Administrator angemeldet? KI-Modell konfiguriert und erreichbar? |
| Matomo liefert keine Daten | Matomo-URL, Token, Site-Auswahl, Zeitraum und Rechte prüfen |
| Kein Content-Refresh | Query-URL-Paare statt getrennter Standardexporte bereitstellen |
| Kein Entwurf auswählbar | Zuerst einen Content-Vorgang mit Ziel-URL unter SEO-Maßnahmen anlegen |
| Kein GSC-Snapshot möglich | Datierte Query-URL-Daten mit Impressionen im aktuellen Vergleichsfenster nötig |
| Report nicht verfügbar | Zunächst Crawl oder Datenimport für den jeweiligen Bericht durchführen |
| Daten nach Docker-Neustart weg | Wurde mit `down -v` gearbeitet? Volumes und Datenpfad prüfen; Backup zurückspielen |
| Andere Webadresse im Docker-Netz nicht erreichbar | `searxng` ist der interne Docker-Dienstname, nicht der Hostname des Browsers |
| MCP kann nicht zugreifen | Backend lokal erreichbar? Gültiger Benutzer-Token? Nur Loopback-URL? |
| CSV-Import: „Pflichtfeld ohne Spalte“ | Im Fenster **Spalten zuordnen** die fehlende Spalte von Hand zuordnen; Zahlenformat prüfen |
| Ranktracker: Gerätefilter ohne Daten | Search Console einmal neu synchronisieren; CSV-Importe enthalten Suchanfrage und Gerät nicht zusammen |
| Ranktracker: Keyword ohne Position | Hat Google die Website im Zeitraum für genau diese Schreibweise ausgespielt? Zeitraum vergrößern |
| Website Health zeigt keine Prüfungen | Überwachung gestartet und Monitor aktiv? Die Anwendung muss laufen; mit **Jetzt prüfen** testen |
| Website Health meldet Ausfälle, die Website ist aber erreichbar | Netzverbindung des Servers prüfen, auf dem die Werkbank läuft; ggf. Firewall/CDN des Zielservers |
| Anwendung startet nach Update nicht (Schlüsselfehler) | `SEO_MASTER_KEY` bzw. Schlüsseldatei aus dem Backup wiederherstellen (Kapitel 21.3) |
| Neue Bildschirme fehlen nach Update (ohne Docker) | Im Ordner `frontend` `npm run build` ausführen, Anwendung neu starten, Browser mit Strg+F5 neu laden |

Zum Prüfen des Docker-Stacks:

```bash
python scripts/full_stack.py ps
python scripts/full_stack.py logs
```

**Bug melden:** Im GitHub-Repository ein Issue erstellen. Version/Commit, Betriebssystem, Installationsweg, exakten Ablauf und Fehlermeldung angeben; Geheimnisse aus Screenshots und Logs entfernen.

## 20. Datenqualität, Berechtigungen und Grenzen

### 20.1 Drei Arten von Zahlen unterscheiden

**Gemessen/importiert:** Beispielsweise GSC-Klicks/-Impressionen oder tatsächlich importiertes Keywordvolumen. Quelle, Datum und ggf. Datenfenster prüfen.

**Manuell dokumentiert:** Beispielsweise KI-Erwähnung, externe Markenaussage, Bewertungsanfrage oder Linkveröffentlichung. Eine manuelle Angabe wird nicht automatisch unabhängig verifiziert.

**Berechnet/heuristisch:** Beispielsweise technische Auditscores, Textähnlichkeiten, Themenlücken oder potenziell zusätzliche Klicks. Solche Werte sind Arbeitsindikatoren und **keine offiziellen Google-Scores**.

### 20.2 Wichtige Grenzen

- Kein eigener weltweiter Index für Suchvolumen, Rankings oder Backlinks.
- SearXNG ersetzt keine kommerzielle SEO-Datenbank.
- Ranktracker-Positionen aus der Search Console sind Durchschnittswerte über alle Impressionen, keine Einzelplatzierung an einem Ort; Anbieter-Messungen folgen der Reihenfolge des jeweiligen Anbieters.
- Die URL Inspection zeigt Googles gespeicherten Stand, keinen Live-Test.
- Website Health und der CDN-Test für KI-Crawler prüfen von einem einzigen Standort aus, dem Server der Werkbank.
- Kein automatischer Zugriff auf alle ChatGPT-/Perplexity-Antworten.
- Ein KI-Modell ohne verbundene Websuche liefert keine belastbaren Live-Suchergebnisse.
- Content-Vorschläge und Fallstudien werden nicht automatisch im CMS veröffentlicht.
- „Veröffentlichung markiert“ bedeutet eine **manuelle Statusangabe**.
- Weder semantische Rankings noch Conversion-Erfolge sollten aus simplen Worttreffern abgeleitet werden.
- Consent-Antwortzeiten und Hostnamen beweisen keine rechtswirksame Einwilligung; eine erfolgreich geklickte CMP-Schaltfläche bestätigt keinen Speicherzustand.
- Der Roh-/Rendering-Vergleich ist kein offizieller KI-Crawler-Test; Bild-Attribute sind keine realen LCP- oder CLS-Messwerte.
- SERP-Overlap ist ein Vergleich der jeweiligen Ergebnislisten, keine Regel über die Zahl benötigter Landingpages.
- Ein neues Relaunch-Ziel mit HTTP 200 beweist **nicht**, dass die alte URL korrekt per 301/308 weiterleitet.
- „Rich-Result-Potenzial“ ist keine Zusage einer tatsächlichen Google-Suchdarstellung.
- Verzeichnisbewertungen und wiederholte KI-Zitationen beruhen auf dokumentierten Angaben bzw. Stichproben, nicht auf extern verifizierter Reichweite.

### 20.3 Mehrbenutzer- und Admin-Rechte

Normale Benutzer verwalten ihre eigenen Websites. Instanzweite Integrationen dürfen nur Administratoren ändern. Gemeinsame KI-Modell- und Matomo-Referral-Abfragen sind administratorbeschränkt. Sensible Kundendaten nur nach gesonderter Berechtigungs- und Datenschutzprüfung erfassen.

## 21. Betrieb, Updates und Sicherungen

### 21.1 Updates

Vor einem Update:

1. Aktuellen Stand/Version und verfügbare Änderungen prüfen.
2. Datenbank, App-Daten **und** den Schlüssel für verschlüsselte Zugangsdaten (21.3) sichern.
3. Bei Bedarf Rückspielbarkeit testen.
4. Images/Code aktualisieren und nach der Änderung einen kurzen Funktionstest durchführen: Anmeldung, Websiteauswahl, Crawl-Verlauf, Einstellungen, GSC/Matomo und optional SearXNG.

Datenbank-Migrationen laufen beim Start automatisch. Bei einer Installation ohne Docker nach einem Update im Ordner `backend` die Abhängigkeiten aktualisieren (`.venv\Scripts\pip install -e ".[dev]"`) und im Ordner `frontend` einmal `npm run build` ausführen, sonst fehlen neue Pakete oder Bildschirme.

Der Docker-Launcher baut die App beim Start. Für reproduzierbare produktive Installationen die Version des SearXNG-Images bewusst festlegen, statt dauerhaft ungeprüft `latest` zu verwenden.

### 21.2 Backups

In der Docker-Gesamtausgabe sind insbesondere **PostgreSQL-Daten** und **Anwendungsdaten** dauerhaft gespeichert. Beide benötigen konsistente Backups. Eine Kopie der Container-Images **allein** ist keine Datensicherung.

Speichere Zugangsdaten/Secrets getrennt vom öffentlich freigegebenen Quellcode und schütze alle Datenbank-Backups. Ein Passwortwechsel darf nicht blind an einem bestehenden PostgreSQL-Volume vorbeigehen.

### 21.3 Verschlüsselte Zugangsdaten und Schlüssel

Gespeicherte API-Schlüssel, Passwörter und OAuth-Tokens sind in der Datenbank verschlüsselt.

1. In verwalteten Installationen einen Fernet-Schlüssel über die Umgebungsvariable `SEO_MASTER_KEY` sicher hinterlegen. Ohne diese Variable erzeugt eine Einzelplatzinstallation die Datei `SEO_DATA_DIR/.integration_master_key`.
2. Den Schlüssel **getrennt vom Datenbank-Backup** aufbewahren. Ohne Schlüssel sind gespeicherte Zugangsdaten nicht mehr lesbar.
3. Ein nicht entschlüsselbarer Eintrag verhindert den Start der Anwendung. Dann den passenden Schlüssel aus dem Backup wiederherstellen.

**Keine Schlüsselrotation durch bloßes Ersetzen von `SEO_MASTER_KEY`.** Details: [Verschlüsselte Zugangsdaten](SECURE_INTEGRATIONS.md).

### 21.4 Optionaler MCP-Lesezugang

Für kompatible KI-Desktopclients gibt es einen optionalen schreibgeschützten MCP-Server.

**Voraussetzung:** Laufender Backend-REST-Server auf dem lokalen Rechner, ein gültiger **Benutzer-Access-Token**, optionales Backend-Paket `.[mcp]`.

```bash
cd backend
pip install -e ".[mcp]"
# API-URL und eigenen Benutzer-Token im Secret-Manager des MCP-Clients setzen.
python -m app.mcp_server
```

Die Umgebungsvariablen heißen `SEO_MCP_API_URL` und `SEO_MCP_API_TOKEN`. Nur lokale Loopback-Adressen werden akzeptiert, keine beliebigen externen Server. Zugangstoken nicht im Git-Repository speichern. Der Server liest ausgewählte SEO-Daten; **er veröffentlicht und bearbeitet keine Seiten**.

Vollständige Einrichtung: [MCP-Server](MCP_SERVER.md).

## 22. Weiterführende Dokumentation

Die technische Dokumentation des Projekts enthält Details zu Methoden, Grenzwerten und Schnittstellen:

- [Tracking, Rendering und Bilddiagnostik](TECHNICAL_DIAGNOSTICS.md)
- [Advanced SEO: Overlap, Relaunch, Paginierung, Schema](ADVANCED_SEO.md)
- [Verzeichnisqualität und KI-Quellenstabilität](AUTHORITY_INTELLIGENCE.md)
- [Verschlüsselte Zugangsdaten](SECURE_INTEGRATIONS.md)
- [Google URL Inspection](GSC_URL_INSPECTION.md)
- [Benachrichtigungen und PageSpeed-Batch](NOTIFICATIONS_PAGESPEED.md)
- [SERP-Keyword-Clustering und Demo](KEYWORD_SERP_CLUSTERING.md)
- [Docker-Gesamtausgabe](DOCKER_FULL.md)
- [MCP-Server](MCP_SERVER.md)
- [SEO-Datenanbieter](SEO_DATA_PROVIDERS.md)
- [GSC Content-Refresh](CONTENT_REFRESH.md)
- [Wirtschaftliche Chancen](OPPORTUNITY_VALUE.md)
- [SEO-Maßnahmen und Messung](SEO_WORKFLOW.md)
- [Content-Entwürfe und Freigabe](CONTENT_PROPOSALS.md)
- [Keyword-Ranktracker](RANK_TRACKING.md)
- [SEO-Research](SEO_RESEARCH.md)
- [Qualität und CRO](RESEARCH_QUALITY.md)
- [SEO-Verlauf und GEO](RESEARCH_MONITORING.md)
- [Conversion und Vertrauen](CONVERSION_TRUST.md)
- [KI-Prompttests und Matomo-Referrals](AI_INTELLIGENCE.md)
- [Content Studio](CONTENT_STUDIO.md)
- [Lokale Nachweise](LOCAL_EVIDENCE.md)
- [API-Referenz](API.md)
- [Upstream-README / Originaldokumentation](UPSTREAM_README.md)

---

**Mitmachen und Fehler melden:** https://github.com/DKFuH/seo-werkbank  
**Dokumentationsprinzip:** Ein sichtbarer Wert benötigt eine belegbare Herkunft. Ein gespeicherter Entwurf benötigt vor der Veröffentlichung eine eigenständige fachliche Prüfung.
