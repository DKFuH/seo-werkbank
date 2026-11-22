# Google Search Console 0.2 – URL Inspection

**Sichtbarkeit → Search Console → Google URL Inspection:** Einzelne HTTP(S)-URL der ausgewählten Website eingeben und **URL bei Google prüfen** wählen. Hierfür muss die Search Console über OAuth verbunden und eine eigene Property ausgewählt sein. Der Server ruft den Google-Endpoint `urlInspection/index:inspect` mit dem bereits erteilten Lesezugriff ab. Ergebnisse enthalten den Status aus dem Index, Canonical-Angaben und ggf. Zeitpunkt des letzten Crawls.

**Nicht dasselbe wie Live URL Test:** Google URL Inspection API liefert den bekannten Indexierungsstand; sie erzwingt keine Live-URL-Neuprüfung und keine Indexierung. Google kann die Daten zeitversetzt liefern. Property-Berechtigungen und Google-API-Kontingente sind erforderlich.

**OAuth-End-to-End in der Praxis:** Ein Administrator muss einen Google-Cloud-OAuth-Client konfigurieren, die Weiterleitungs-URI exakt registrieren und mit einem berechtigten Google-Konto die Anmeldung, den Callback, die Property-Auswahl, eine Search-Analytics-Synchronisierung und eine URL-Inspection durchführen. Automatisierte Tests können den Google-Dienst nur simulieren; ohne echte Zugangsdaten ist die Live-Verifizierung **offen**.
