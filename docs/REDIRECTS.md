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
