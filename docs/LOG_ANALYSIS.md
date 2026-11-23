# Logfile-Analyse und 404-Monitor

Navigation: **Sichtbarkeit → Logfile & 404**; API `/api/sites/{id}/logs`.

## Vorgehen

1. Apache-/Nginx-Logdatei als `.log`, `.txt` oder `.gz` auswählen.
2. `combined`, `common` oder automatische Formatprüfung verwenden.
3. Der Upload wird stückweise in eine **temporäre Datei** kopiert und im Job verarbeitet.
4. Danach werden nur aggregierte Pfad-/Status-/Agentdaten, 404-Referrer-**Hosts**
   und Importstatistiken gespeichert. Temporäre Rohdateien werden entfernt.
5. Unter den häufigsten 404-Pfaden kann ein Ziel explizit eingetragen werden.
   Die Weiterleitung wird als **unfreigegebener Entwurf** in der Redirect-Verwaltung angelegt.
6. Über **Löschen** werden Aggregat- und 404-Daten eines Imports gelöscht.

## Datenschutz und methodische Grenzen

- IP-Adressen, ganze Zugriffszeilen, vollständige User-Agents, Referrer-Pfade
  und URL-Querystrings werden nicht dauerhaft gespeichert.
- Offensichtliche Pfad-Tokens/IDs werden ersetzt. Eine **vollständige
  Anonymisierung freier URL-Pfade kann nicht garantiert** werden.
  Dateien vor dem Upload datenschutzrechtlich und technisch prüfen.
- Die Serverlogdatei existiert während des Importjobs kurzzeitig auf dem
  Server. Sie wird nach Erfolg, Fehler oder Abbruch gelöscht, sofern der
  Prozess normal weiterläuft; bei Prozessabsturz können temporäre Dateien
  zurückbleiben. Temporäre Verzeichnisse sollten bereinigt werden.
- User-Agent-Klassifizierung ist **nicht** per Reverse-DNS oder IP-Range
  verifiziert. Auch Treffer mit `googlebot_claim` beweisen nicht, dass Google
  die URL besucht hat. Braves Suchcrawler lässt sich nicht zuverlässig
  gesondert anhand eines eigenen User-Agents erkennen.
- Ein importierter Zeitraum enthält möglicherweise nicht alle Zugriffe;
  URLs ohne Treffer sind **kein** Beweis für Nichtindexierung.
- Die maximale Uploadgröße ist über `SEO_MAX_LOG_UPLOAD_MB` (Default 100)
  konfigurierbar. Entpackte Daten sind auf 500 MB, 5 Millionen Zeilen und
  200.000 Aggregate begrenzt. Zu große oder fehlerhafte Dateien werden
  nicht teilweise als abgeschlossene Imports gespeichert.
- Der Parser unterstützt klassische Combined-/Common-Zeilen. Eigene
  Nginx-Formate, HTTP/3-Varianten und JSON-Logs benötigen separate Adapter.
- Keine Live-Abfrage fremder Server, keine automatischen Redirects.

## Auswertung

Statuscodes, User-Agent-Klassen, Googlebot-Claim-Verlauf nach Tagen,
404-Pfade samt Referrer-Host und ein Abgleich indexierbarer URLs des
letzten abgeschlossenen Crawls mit den im Import gefundenen
Googlebot-User-Agent-Treffern.

**Wichtig:** Ein 404-Redirect ist nur sinnvoll, wenn ein fachlich passendes
Ersatzziel existiert; ein pauschales Redirect auf die Startseite kann
Nutzern und Suchmaschinen schaden.
