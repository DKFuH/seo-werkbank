# KI-Erwähnungen und -Quellen: manuelle Beobachtungen

Die öffentliche SEO-Werkbank kann eine Stichprobe einer KI-Antwort mit Zeitpunkt, Plattform, optionaler Modellversion, konkreter Eingabe, Markenerwähnung, tatsächlich angegebener URL, Auszug und Nachweis dokumentieren.

## Grenzen der Aussage
- Sämtliche Beobachtungen werden vom Benutzer **manuell eingegeben**. Die Angabe `verified: false` bedeutet: nicht über einen Plattform-API-Dienst bestätigt.
- **Marken-Erwähnung**, **URL-Zitation** und **tatsächlicher Referral-Besuch** sind unterschiedliche Ereignisse. Für Referral-Besuche wären Webanalyse-Rohdaten erforderlich.
- Der Nutzer kann nachträglich ein Beobachtungsdatum erfassen; es wird nicht die tatsächliche Plattformantwort digital signiert.
- Die Anzeige ist keine repräsentative GEO-Sichtbarkeitskennzahl. Suchergebnisse sind dynamisch und teilweise personalisiert; das System kann keine internen Fan-out-Abfragen sehen.
- Der vorhandene GEO-Check testet crawlerfreundliche Signale und ist keine Messung von KI-Quellennennungen.
- Keine Google-Docs-Manipulationen, keine künstlichen Zitierungen, keine Rankings ohne Belege.

**API:** `GET/POST /api/sites/{site_id}/ai-visibility/observations`, `DELETE /api/sites/{site_id}/ai-visibility/observations/{id}`. Alle Endpunkte prüfen die Site-Eigentümerschaft.
