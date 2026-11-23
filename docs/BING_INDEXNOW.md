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

Grenze: Bing akzeptiert den API-Schlüssel nur als URL-Parameter. Er wird
ausschließlich an `ssl.bing.com` gesendet und nicht protokolliert.

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

Nur echte Änderungen melden. Wiederholtes Melden unveränderter URLs bringt
nichts und kann als Spam gewertet werden.
