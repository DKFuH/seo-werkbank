# Redirect-Management

**Navigation:** Analyse → Weiterleitungen · API: `/api/sites/{site_id}/redirects`

Ablauf: **Crawl → Vorschlag → Simulation → explizite Freigabe → Export → manuelle Installation → erneuter Crawl.**
Die Werkbank verändert niemals fremde Server oder CMS-Konfigurationen.

- Vorschläge aus Redirect-Ketten und temporären Weiterleitungen mit nachgewiesenem 200-Ziel.
- Bei 404-Seiten mit internen Links nur zurückhaltende URL-Slug-Ähnlichkeit; das ist **kein Beweis**, dass das Ziel fachlich passt.
- Manuelle Regeln müssen dieselbe Website-Domain betreffen, die Ziel-URL ist frei von Querystrings, Fragmenten und gefährlichen Kodierungen.
- `simulate` erkennt Selbstschleifen, doppelte Quellen, geplante Ketten, Zyklen und anhand des letzten Crawls unbekannte/nicht indexierbare Ziele.
- Exportiert werden ausschließlich freigegebene Regeln als CSV, Apache RewriteRule oder Nginx exact-match location.
- Vor Aktivierung von Apache-Rewrite-Regeln muss `mod_rewrite` aktiv sein; die ausgegebene RewriteRule ist für eine `.htaccess` im Domain-Root gedacht.
- Konfigurationen müssen **vor** Aktivierung in einer Staging-Umgebung geprüft werden. Bestehende Serverregeln können Konflikte auslösen, die der lokale Simulator nicht kennt.
- Export ist kein Nachweis der Live-Aktivierung. Die Wirkung muss im nächsten Crawl sowie in Serverlogs geprüft werden.
- Eine temporäre Weiterleitung auf eine stabile Seite beweist **keinen** dauerhaften Umzug; ein 301-Vorschlag braucht fachliche Freigabe.

Keine automatischen Deployments, Wildcard-Regeln, Cross-Domain-Weiterleitungen oder generelle Querystring-Umschreibungen.

## Datenbankintegrität und Exportkontext

- Migration `0013` erzwingt einen eindeutigen Schlüssel für `(site_id, source_url)`.
  Bereits vorhandene Dubletten werden **nicht** automatisch gelöscht. Der
  Migrationslauf stoppt mit einer Fehlermeldung; Dubletten zuerst manuell prüfen.
- Konkurrierende API-Anfragen bekommen bei einer Kollision `409 Conflict`.

### Update auf Migration 0013

Die Migration läuft beim Start der Anwendung. Gibt es schon doppelte Quellen,
bricht sie ab und die Anwendung startet nicht, bis die Dubletten bereinigt sind.
Das betrifft nur Installationen mit Regeln aus der Zeit vor `0013`; mit der
Anwendungsprüfung entstehen Dubletten normalerweise nicht.

1. Anwendung gestoppt lassen, Datenbank sichern.
2. Dubletten finden:

   ```sql
   SELECT site_id, source_url, COUNT(*) AS n
   FROM redirect_rules
   GROUP BY site_id, source_url
   HAVING COUNT(*) > 1;
   ```

3. Je Quelle genau eine Regel behalten (bevorzugt die freigegebene, sonst die
   neueste) und die übrigen löschen:

   ```sql
   SELECT id, state, target_url, updated_at
   FROM redirect_rules
   WHERE site_id = :site_id AND source_url = :source_url
   ORDER BY id;

   DELETE FROM redirect_rules WHERE id IN (:ids_to_remove);
   ```

4. Anwendung starten; die Migration legt den Unique-Index an.

### Apache-Export und Live-Prüfung

Der Apache-Export setzt `RewriteEngine On` nur einmal und enthält einen Hinweis auf **`.htaccess` im DocumentRoot**. Regeln müssen vor der Verwendung in Apache-vHost-Konfigurationen an deren Rewrite-Kontext angepasst werden. Export, Freigabe und Simulation belegen **keine** bereits auf dem Server installierte Weiterleitung; prüfen Sie die Wirkung nach manueller Installation mit HTTP-Anfragen und erneutem Crawl.
