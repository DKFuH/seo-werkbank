# Secret-Verschlüsselung und Browser-CI (0.2)

Alle Integrationseinstellungen einschließlich GSC-OAuth-Tokens werden vor dem Speichern mit **Fernet (authentifizierte AES-128-CBC-Verschlüsselung)** verschlüsselt. Beim Upgrade verschlüsselt der Startvorgang bestehende, unverschlüsselte Einstellungen **transaktional** und kontrolliert die Lesbarkeit bereits verschlüsselter Daten. Ein verlorener Schlüssel führt zum **Startfehler**, nicht zu leer ersetzten Zugangsdaten.

**Empfohlen für Produktion:** Ein eigener, sicher gespeicherter `SEO_MASTER_KEY` (Fernet-formatierter Schlüssel). Erzeugung: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`. Den Schlüssel **nicht** in git ablegen; getrennt von Datenbank-/Volume-Backups sichern. Ohne Umgebungsvariable erzeugt die Einzelplatzinstallation eine Datei `SEO_DATA_DIR/.integration_master_key` mit eingeschränkten Dateirechten. In Docker muss deshalb das vollständige App-Datenvolume gesichert werden.

**Achtung:** Die erste Migration entfernt lesbare Secrets aus den aktiven DB-Zeilen, nicht aus vorherigen Datenbank-Backups oder externen Logs. Vor dem Upgrade Datenbank und Schlüssel sicher sichern. Änderungen des Schlüssels an einer bestehenden Installation ohne gesonderte Rotation machen die Integration unlesbar. Bei Schlüsselrotation zunächst ein konsistentes Backup anlegen.

Die CI installiert Playwright und Chromium und führt die bestehenden JavaScript-Rendering-Tests mit tatsächlich installiertem Browser aus. Ein separater Smoke-Test startet die **lokale Lighthouse-CLI** gegen den isolierten Fixture-HTTP-Server. Dies ist kein echter Search-Console-/Google-API-End-to-End-Test.
