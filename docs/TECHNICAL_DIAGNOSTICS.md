# Browser-, Tracking- und Bild-Diagnostik

Im Frontend unter **Analyse → Tracking & Rendering**.

- **Consent-Zeitfolge:** Explizit gestarteter Browser-Test in separaten, frischen Playwright-Kontexten. Initiale Anfragezeitpunkte und optionale Tests über eindeutig benannte Accept-/Reject-All-Buttons. Die Anwendung protokolliert Hostnamen, zeitlichen Ablauf und Ressourcentypen, nicht Querystrings, Cookies, Header, Request-Körper oder Nutzerdaten. Ein geklickter Button ist **kein** Nachweis erfolgreicher Speicherung der Einwilligung, eine fremde Anfrage kein Gesetzesverstoß.
- **Raw vs. Render:** Abruf des Roh-HTML mit sicherem Fetcher und separater Browser-Render. Zeigt Unterschiede bei Textumfang, Title, Überschriften und Links. Keine Behauptung, dass ein bestimmter KI-Crawler dieselben Ressourcen sieht.
- **Bilder:** Aus dem letzten Crawl erfasste HTML-Bildattribute: fehlendes width/height und potenziell früh positionierte lazy-Bilder. Das erste HTML-Bild ist **nicht** automatisch LCP. Für echte LCP- und CLS-Messwerte PageSpeed verwenden.
- **Voraussetzungen:** Optionales Playwright/Chromium für Browserdiagnosen (`pip install -e ".[render]"` und `playwright install chromium`). Der reguläre Docker-Stack hat Chromium nicht automatisch installiert. Ohne Browser stehen die Bildhinweise aus Crawls zur Verfügung.
- **Sicherheit:** Nur genau die Domain der eigenen, angemeldeten Website; Requests durch vorhandene SSRF-Browser-Guards; kein Zugriff auf andere Website-Projekte. Consent-Klicks nur nach explizitem Benutzerauslöser. Getrennte Sessions, maximal drei Szenarien und 120 protokollierte Requests je Szenario.
- Kein automatischer DSGVO-, Consent-Mode- oder Tag-Manager-Compliance-Score. Eine gesonderte Kontrolle mit Browser-Devtools ist für Entscheidungen weiterhin erforderlich.

## Bedienung Schritt für Schritt

**Navigation:** `Analyse → Tracking & Rendering`.

1. Oben die richtige Website auswählen und die vollständige URL aus dieser Domain eintragen.
2. Für den Roh-HTML-/JavaScript-Vergleich **„Roh-HTML und JavaScript vergleichen“** drücken. Unterschiede bei Wortzahl, Title, Überschriften und Links sind manuell zu interpretieren.
3. Für Consent zuerst **nur die Initialsitzung** aktiv lassen; die Berechtigungs-Checkbox setzen und **„Consent-Diagnose ausdrücklich starten“** klicken.
4. Erst bei konkretem Bedarf die optionalen getrennten Klickversuche **„Alle akzeptieren“** und/oder **„Alle ablehnen“** auswählen. Die Software erkennt keine beliebigen CMP-Oberflächen und prüft keinen gespeicherten Consent-Zustand.
5. Die **Bildwarnungen aus dem letzten Crawl** betrachten. Für reale LCP-/CLS-Metriken **Analyse → PageSpeed** öffnen.

**Beispiel:** Zeitfolge mit einer Anfrage an einen Analyse-Host vor einem sichtbaren Consent-Klick → den konkreten Tracking-Aufbau im Browser manuell untersuchen. Daraus folgt weder automatisch ein rechtswidriges Tracking noch eine gesicherte Ursache fehlender Conversions.

**Bei Fehlermeldungen:** Playwright und Chromium müssen **auf dem Rechner/Container laufen, auf dem das Backend ausgeführt wird**. Die Domain muss zur ausgewählten Website gehören. Private Netzwerke sind für die Browserinteraktion nicht freigegeben.

Mehr Details: [Benutzerhandbuch, Kapitel 7.4–7.5](BENUTZERHANDBUCH.md).
