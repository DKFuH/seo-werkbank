# Suchmaschinenbezogene Audit-Evidenz (Google, Bing, Brave)

Die 122 Audit-Regeln werden nicht automatisch zu 122 offiziellen Suchmaschinenanforderungen.
Das Regelwerk trennt vorhandene technische Befunde, **Provenienz der Regel** und
**suchmaschinenspezifische Quellen**. `rule_dict(id)` stellt dafür `search_engines`
mit getrennten Feldern für **Bing** und **Brave** bereit.

- `related_guidance`: Eine öffentliche Primärquelle beschreibt den Themenbereich.
  Das bestätigt **nicht** automatisch den konkreten Schwellenwert, Score oder Fehlerstatus.
- `not_evaluated`: Keine ausreichend konkrete öffentliche Zuordnung im Katalog
  hinterlegt. **Nicht** als fehlende Unterstützung des Suchdienstes interpretieren.
- Google wird über `classification` und `google_documentation` separat dargestellt.
- `profiles` weist Regeln den Score- und Filterprofilen zu: Google erhält
  technische Anforderungen und Google-Empfehlungen, Bing/Brave ausschließlich
  Regeln mit `related_guidance`, GEO die als `geo_experiment` klassifizierten
  Regeln. Nicht zugeordnete SEO-Heuristiken bleiben in „Alle Befunde“ sichtbar.
- Die zusätzlichen Scores verwenden die bisherigen Schweregrad-Abzüge; der
  bestehende Gesamtscore und die Crawl-Ausführung bleiben unverändert; die
  Profil-Scores werden ergänzend gespeichert. Aufgrund der unterschiedlichen
  Regelabdeckung sind Profil-Scores nicht direkt vergleichbar und keine
  Rankingprognose. Der GEO-Crawlscore ist getrennt vom bestehenden
  Einzelseiten-GEO-Check.

## Nachweisstufen

Jede Zuordnung zu Bing oder Brave nennt ihre Fundstelle (`section`, `quote`) und eine Stufe:

- **Zitat (`quoted`):** Ein Satz der Leitlinie beschreibt genau diese Prüfung. Er steht wörtlich in der Detailansicht des Befunds.
- **Themenbezug (`topic`):** Die Leitlinie behandelt das Themenfeld, enthält aber keinen Satz zu genau dieser Prüfung.
  Die Regel zählt im Profil-Score, ist aber nicht als Suchmaschinen-Vorgabe belegt.

Quelle der Zitate: Bing Webmaster Guidelines (lokale Kopie, geprüft am 23.11.2026, einschließlich des Hinweises zu den
AI Preferences vom 30.10.2026) und die Brave-Crawler-Hilfeseite (abgerufen am 23.11.2026). Ändert sich eine Leitlinie,
müssen die Zitate neu geprüft werden. Die Zuordnung liegt in `backend/app/audit/engine_guidance.py`.

## Microsoft Bing

Primärquelle: https://www.bing.com/webmasters/help/webmaster-guidelines-30fba23a

Im Gegensatz zur Google Search Console sind die Daten der Bing Webmaster Tools eine **eigene** Datenquelle. Ein
Google-Indexstatus sagt nichts Sicheres über Bing aus. Zuordnung mit Zitat (Auswahl):

| Befund | Abschnitt | Wörtlich |
| --- | --- | --- |
| `redirect_temporary` | 7 | „Use 302 redirects only for very short-term changes (less than 2 days)“ |
| `title_*`, `description_*` (fehlend, doppelt, zu kurz) | 13 | „Missing, duplicate, or overly short title tags and meta descriptions may reduce indexing reliability, ranking, and eligibility …“ |
| `url_many_params` | 8 | „… URLs with numerous parameters“ |
| `sitemap_lastmod_missing` | 3 | „Include freshness signals (such as lastmod) where applicable“ |
| `robots_bingbot_group_incomplete` | robots.txt-Anleitung | „On finding a specific set of instructions for itself, Bingbot will ignore the directives listed in the generic section …“ |
| `robots_bingbot_blocked`, `robots_blocks_site` | 8 | „Blocking Bingbot in your robots.txt file“ |
| `noindex` | 10 | „Use NOINDEX when a URL should NOT appear in Bing search, Copilot experiences, or grounding API results.“ |

**Nicht** in den Leitlinien und deshalb für Bing nicht bewertet: Weiterleitungsketten, Längen-Obergrenzen für Title und
Description (nur „overly short“ ist genannt, ohne Zahl), Mobilfreundlichkeit, Ladezeit, hreflang, Dokumentgröße.
Auch Behauptungen aus Agenturblogs (etwa stärkere Gewichtung von Meta-Tags, Alt-Texten, Social Signals oder Seitenalter
bei Bing) stehen dort nicht und sind nicht übernommen.

### Bing AI Preferences (Ankündigung vom 30.10.2026)

Microsoft trennt **AI Training** und **AI Grounding** und ersetzt dafür `noarchive` und `nocache`:

- `robots.txt` (nur Training): `User-Agent: __usage_ai-training` mit `Disallow: /`.
- Seite (Training und Grounding): `<meta name="Bingbot" content="ai-grounding:disallow">` oder
  `X-Robots-Tag: Bingbot: ai-training:disallow`. Grounding kennt zusätzlich `disallowextended`.
- Beides ist standardmäßig erlaubt. Die Einstellungen ändern nichts an der Sichtbarkeit in der normalen Bing-Suche.

Fristen: **15.12.2026** befristete Einstellung in den Bing Webmaster Tools möglich, **1.2.2027** Microsoft wertet die neuen
Angaben aus, **1.3.2027** letzter Termin für alle, die `noarchive` oder `nocache` heute zum Ausschluss vom Grounding nutzen
(sonst gilt bis zum nächsten Abruf „Allow“), **30.9.2027** laufen befristete Einstellungen ab.
Der Befund `bing_legacy_ai_directives` weist auf Seiten mit `noarchive` oder `nocache` hin. Googlebot-eigene Angaben
(`googlebot: noarchive`) zählen dabei nicht.

## Brave Search

Primärquelle: https://search.brave.com/help/brave-search-crawler

Auf der Seite belegt:

- „if a domain or page is not crawlable by Googlebot, then Brave Search's bot will not crawl it either.“
  Der Befund `robots_googlebot_blocked` prüft deshalb, ob `robots.txt` Googlebot sperrt, den Crawler der Werkbank aber nicht.
- „robots.txt is not used to prevent a page from being indexed.“ und „A site owner can delist a page by using [the robots noindex directive].“
- Kein eigener User-Agent („does not advertise a differentiated user agent“), Entdeckung teilweise über das opt-in
  Web Discovery Project, und ein [Formular zum erneuten Abruf oder Entfernen](https://search.brave.com/submit-url).

**Nicht** auf der Seite und deshalb nicht übernommen: Abbruch nach 10 Sekunden, 2-MB-Grenze, fehlendes JavaScript-Rendering,
„Weiterleitungen machen Seiten privat“. Sie bleiben, wo sie sind, als allgemeine Heuristiken (`slow_response`,
`html_too_large`, Roh-gegen-gerendert-Vergleich).

Nicht behaupten: Einen separaten Bravebot-UA zuverlässig messen, IndexNow als Brave-Anforderung darstellen,
Google-URL-Inspection als Beleg für Brave-Indexierung verwenden oder eine vollumfängliche offizielle Brave-SEO-Regelliste
aus allgemeinen Heuristiken ableiten.

## Nicht umgesetzt

- **`noindex` auf einer per `robots.txt` gesperrten URL:** Bing und Brave nennen den Widerspruch, aber gesperrte URLs ruft der
  Crawl nicht ab; das Tag lässt sich ohne zusätzlichen Abruf nicht sehen.
- **Soft-404-Erkennung** (Bing: Fehlerseiten müssen 404 liefern): braucht einen Test-Abruf einer nicht existierenden URL und
  ist deshalb ein eigener Schritt.

## Nächste Schritte

1. ~~Pro Regel die genaue Fundstelle hinterlegen~~ – umgesetzt (`section`, `quote`, Stufe `quoted`/`topic`). Offen: für die
   Regeln der Stufe `topic` einen Satz der Leitlinie finden oder sie aus dem Profil nehmen.
2. ~~Bing-Datenanbindung und IndexNow~~ – umgesetzt, siehe [BING_INDEXNOW.md](BING_INDEXNOW.md).
3. Soft-404-Prüfung.
4. Fundstellen bei jeder Änderung der Bing- oder Brave-Leitlinie neu prüfen.

## Warum keine eigene Gewichtung je Suchmaschine

Die Profile unterscheiden Suchmaschinen bereits dadurch, **welche** Regeln in
ihren Score einfließen. Unterschiedliche Punktabzüge je Suchmaschine (etwa
„fehlender Title wiegt bei Bing schwerer“) würden eine Genauigkeit
behaupten, die keine der Suchmaschinen dokumentiert. Deshalb verwenden alle
Profile dieselben Schweregrad-Abzüge. Eine eigene Gewichtung kommt erst
infrage, wenn eine konkrete, datierte Quelle sie stützt.
