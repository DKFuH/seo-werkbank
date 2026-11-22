# Browser-, Tracking- und Bild-Diagnostik

Im Frontend unter **Analyse → Tracking & Rendering**.

- **Consent-Zeitfolge:** Explizit gestarteter Browser-Test in separaten, frischen Playwright-Kontexten. Initiale Anfragezeitpunkte und optionale Tests über eindeutig benannte Accept-/Reject-All-Buttons. Die Anwendung protokolliert Hostnamen, zeitlichen Ablauf und Ressourcentypen, nicht Querystrings, Cookies, Header, Request-Körper oder Nutzerdaten. Ein geklickter Button ist **kein** Nachweis erfolgreicher Speicherung der Einwilligung, eine fremde Anfrage kein Gesetzesverstoß.
- **Raw vs. Render:** Abruf des Roh-HTML mit sicherem Fetcher und separater Browser-Render. Zeigt Unterschiede bei Textumfang, Title, Überschriften und Links. Keine Behauptung, dass ein bestimmter KI-Crawler dieselben Ressourcen sieht.
- **Bilder:** Aus dem letzten Crawl erfasste HTML-Bildattribute: fehlendes width/height und potenziell früh positionierte lazy-Bilder. Das erste HTML-Bild ist **nicht** automatisch LCP. Für echte LCP- und CLS-Messwerte PageSpeed verwenden.
- **Voraussetzungen:** Optionales Playwright/Chromium für Browserdiagnosen (`pip install -e ".[render]"` und `playwright install chromium`). Der reguläre Docker-Stack hat Chromium nicht automatisch installiert. Ohne Browser stehen die Bildhinweise aus Crawls zur Verfügung.
- **Sicherheit:** Nur genau die Domain der eigenen, angemeldeten Website; Requests durch vorhandene SSRF-Browser-Guards; kein Zugriff auf andere Website-Projekte. Consent-Klicks nur nach explizitem Benutzerauslöser. Getrennte Sessions, maximal drei Szenarien und 120 protokollierte Requests je Szenario.
- Kein automatischer DSGVO-, Consent-Mode- oder Tag-Manager-Compliance-Score. Eine gesonderte Kontrolle mit Browser-Devtools ist für Entscheidungen weiterhin erforderlich.
