# Bing Webmaster Tools und IndexNow

Seite in der Werkbank: **Sichtbarkeit → Bing & IndexNow** (`/bing`).
Einrichtung: **System → Einstellungen → Bing Webmaster Tools / IndexNow**
(nur Administratoren).

## Bing Webmaster Tools

1. In [Bing Webmaster Tools](https://www.bing.com/webmasters) die Website
   verifizieren (der Import aus der Google Search Console geht am schnellsten).
2. Unter *Einstellungen → API-Zugriff* einen API-Schlüssel erzeugen und in der
   Werkbank speichern. Er wird verschlüsselt gespeichert und nie wieder
   angezeigt.
3. Die Seite `/bing` wählt automatisch die Bing-Website mit gleicher Domain;
   sonst oben rechts auswählen.

Angezeigt werden:

- **Suchanfragen:** Bing liefert Wochenwerte der letzten Monate. Die Werkbank
  summiert Klicks und Impressionen je Anfrage; die Position ist nach
  Impressionen gewichtet.
- **Crawling durch Bingbot:** gecrawlte Seiten, Seiten im Index, Crawl-Fehler.
- **Bing Intelligence:** ausdrücklich ausgelöste, nur lesende Abrufe für die in der Oberfläche angebotenen Datensätze. Jede
  Antwort kann als unveränderlicher Snapshot gespeichert und später erneut gelesen werden; sie wird nie mit GSC-Werten
  zusammengeführt.
- **Content-Analyse:** eine begrenzte Stichprobe der stärksten Bing-Seiten wird mit echten Page-Query-Wochenwerten und dem
  letzten Crawl verglichen. Content-Lücken bleiben lexikalische Prüfkandidaten. Decay-, Trend- und URL-Überschneidungssignale
  erscheinen nur für Serien, die in beiden Vergleichsfenstern jede erwartete Woche abdecken.

Grenze: Bing akzeptiert den API-Schlüssel nur als URL-Parameter. Er wird
ausschließlich an `ssl.bing.com` gesendet und nicht protokolliert.
Die dokumentierten JSON/HTTP-Signaturen sind mit Mock- und Vertragstests abgedeckt; ein autorisierter Live-Test sämtlicher
Operationen und Antwortformen steht weiterhin aus. Ein Snapshot belegt nur die erhaltene Providerantwort zum Abrufzeitpunkt,
nicht Vollständigkeit, Kausalität, Linkverlust oder einen externen Suchtrend. Snapshot-Payloads sind auf 2 MB begrenzt.

## IndexNow

[IndexNow](https://www.indexnow.org/documentation) meldet neue, geänderte oder
gelöschte URLs an Bing und weitere teilnehmende Suchmaschinen. **Google nimmt
nicht teil.** Eine Meldung ist ein Hinweis, keine Garantie für Crawling oder
Indexierung.

1. In den Einstellungen einen Schlüssel **erzeugen** und speichern.
2. Auf jeder Website, die gemeldet werden soll, die Datei
   `https://deine-domain/<schlüssel>.txt` mit genau dem Schlüssel als Inhalt
   ablegen. Alternativ einen eigenen Ort (https, `.txt`, gleiche Domain)
   eintragen.
3. Auf `/bing` zeigt die Werkbank, ob die Schlüsseldatei erreichbar ist und
   passt. Weiterleitungen gelten als Fehler, die Datei muss direkt antworten.
4. URLs melden:
   - **Neu + geändert seit vorherigem Crawl:** indexierbare HTML-Seiten des
     letzten Crawls, die im vorherigen Crawl fehlten oder deren Inhalts-Hash
     sich geändert hat. Braucht zwei abgeschlossene Crawls.
   - **Neu, geändert und gelöscht seit vorherigem Crawl:** zusätzlich URLs, die im vorherigen Crawl indexierbar waren und
     jetzt 404 oder 410 liefern. Eine Weiterleitung (301) zählt nicht als Löschung. Bing nennt IndexNow ausdrücklich auch
     für entfernte URLs.
   - **Eigene Liste:** eine URL pro Zeile; URLs anderer Hosts werden
     ausgelassen.

Antworten der IndexNow-API:

| HTTP | Bedeutung |
| --- | --- |
| 200 | übermittelt |
| 202 | angenommen, Schlüsselprüfung steht noch aus |
| 400 | ungültiges Format |
| 403 | Schlüssel ungültig (Datei fehlt oder Inhalt passt nicht) |
| 422 | URLs gehören nicht zum Host |
| 429 | zu viele Anfragen |

Bing empfiehlt, Änderungen möglichst laufend statt gebündelt zu melden („Avoid batch submissions when possible“); die
Werkbank sendet eine Liste je Klick, am besten nach jedem Crawl oder jeder Veröffentlichung. Nur echte Änderungen melden. Wiederholtes Melden unveränderter URLs bringt
nichts und kann als Spam gewertet werden.
