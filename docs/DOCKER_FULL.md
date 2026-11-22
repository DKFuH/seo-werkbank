# Vollständige Docker-Ausgabe: SEO-Werkbank + PostgreSQL + SearXNG

Eine zusätzliche, unabhängige Docker-Compose-Konfiguration startet die Anwendung
mit PostgreSQL und einer **internen** SearXNG-Metasuchinstanz. Die bestehenden
SQLite- und PostgreSQL-Compose-Dateien bleiben weiterhin erhalten.

## Voraussetzungen

Docker Engine oder Docker Desktop mit Compose v2; Python 3.11+ zum einmaligen
Einrichten und Starten. Der erste Start lädt Container-Images aus dem Internet.

## Schnellstart

```bash
git clone https://github.com/DKFuH/seo-werkbank.git
cd seo-werkbank
python scripts/full_stack.py up
```

Unter Windows gegebenenfalls `py -3 scripts/full_stack.py up` verwenden.

Das Skript erzeugt **nur fehlende** Zufallswerte für `POSTGRES_PASSWORD` und
`SEARXNG_SECRET` in der lokalen, ignorierten `.env`-Datei. Geheimnisse werden
nicht ausgegeben oder in Git gespeichert. Es überschreibt keine bestehenden
Passwörter. Ein bereits eingerichtetes PostgreSQL-Volume muss denselben
Datenbankbenutzer und dasselbe Passwort behalten.

Im Browser `http://localhost:8000` öffnen. Beim ersten Start das
Administratorkonto anlegen. Unter *Einstellungen → SERP-Anbieter* ist SearXNG
vorausgewählt, **solange noch keine SERP-Einstellungen gespeichert wurden**.
Danach können Benutzer andere Anbieter wählen oder die Suche deaktivieren.

## Betrieb

```bash
python scripts/full_stack.py ps
python scripts/full_stack.py logs
python scripts/full_stack.py down
```

`down` bewahrt alle Daten-Volumes. **NICHT** `down -v` ausführen, wenn
Daten erhalten bleiben sollen. Backups von `seo-postgres` und `seo-data`
regelmäßig prüfen; reine Container-Backups reichen nicht aus.

Alternativ: `python scripts/full_stack.py init` und danach
`docker compose -f docker-compose.full.yml up -d --build`.

## Internes SearXNG

- JSON-Antwortformat für die SERP-Analyse ist in
  `deploy/searxng/settings.yml` aktiviert.
- Die URL `http://searxng:8080` gilt **innerhalb** des Compose-Netzwerks.
  Der Host kann diese Adresse im normalen Browser nicht auflösen.
- Die SearXNG-Instanz veröffentlicht **keinen Host-Port**. PostgreSQL ebenso nicht.
  Nur die SEO-Werkbank wird standardmäßig an 127.0.0.1:8000 veröffentlicht.
- Die SearXNG-Limiter-Funktion ist ausschließlich für diese abgeschottete
  Privatinstanz deaktiviert. Die Konfiguration darf **nicht unverändert als
  öffentlich erreichbare SearXNG-Instanz** betrieben werden.
- SearXNG verwendet externe Suchmaschinen. Einzelne Engines können
  CAPTCHA, Sperren, Verzögerungen oder unterschiedliche Resultate liefern.
  SearXNG ist **kein neutraler Google-Ranktracker**, keine Ahrefs-Datenbank und
  hat keine eingebauten Suchvolumen- oder Backlinkdaten.
- Das Image lässt sich über `SEARXNG_VERSION` in `.env` auf eine geprüfte
  feste Version pinnen. Der Standard `latest` muss für reproduzierbare
  produktive Updates bewusst durch eine getestete Version ersetzt werden.

## Sicherheit / Hosting

Veröffentliche die Instanz nicht ohne HTTPS-Reverse-Proxy,
Benutzerverwaltung, Netzwerk- und Backup-Konzept. Gib SearXNG und PostgreSQL
keine öffentlichen Ports. Die Anwendung speichert externe API-Tokens derzeit
in ihrer Anwendungsdatenbank ohne separate Feldverschlüsselung: Datenbankdateien
und Datenbank-Backups entsprechend schützen.

`SEO_BIND=0.0.0.0` ist nur hinter einem passend konfigurierten Reverse
Proxy vorgesehen. Datenbankzugriff bleibt im Docker-Netzwerk.

## Fehlersuche

1. `python scripts/full_stack.py ps` für Containerzustände.
2. `python scripts/full_stack.py logs` für Startprobleme.
3. Prüfe unter *Einstellungen → SERP-Anbieter*, ob ein bereits gespeicherter
   anderer Anbieter die Docker-Voreinstellung überschreibt.
4. Prüfe, dass Suchmaschinen SearXNG nicht blockieren. Die bloße HTTP-200-
   Antwort bedeutet **nicht**, dass alle Engines echte Treffer liefern.
5. Wenn eine bestehende `.env` ein schwaches Beispielpasswort enthält,
   wird der Start absichtlich verweigert. Bei vorhandenen Datenbank-Volumes
   Passwörter nicht blind austauschen.
