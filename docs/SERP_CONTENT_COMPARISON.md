# SERP-Content-Wettbewerbsvergleich

Die bestehende SERP-Analyse liefert zusätzlich `content_comparison` und zeigt
die Ergebnisse direkt vor dem vorhandenen KI-Briefing. Es werden keine neuen
Suchanbieter oder externen Dienste benötigt.

- Maximal die ersten zehn Ergebnisse in Anbieter- bzw. manueller Reihenfolge.
- Eigene URL und doppelte Ergebnis-URLs werden ausgeschlossen.
- Seitentyp wird heuristisch anhand URL und Schema geschätzt. Bei erkanntem
  Zielseitentyp werden nur passende geladene Seiten für die Begriffsmatrix
  verwendet; andernfalls bleibt die Vergleichsgruppe ungefiltert.
- Keyword-Prominenz misst zusammenhängende, casefold-normalisierte Wortfolgen
  in Title, Description, H1, H2/H3 und den ersten/letzten 100 Wörtern der
  vorhandenen Textstichprobe. Die Stichprobe ist nicht zwingend der ganze Text.
- Die Matrix basiert auf vorhandenen TF-IDF-Kandidaten und lexikalischen
  Treffern. Fehlende Treffer sind Prüfhinweise, keine bewiesenen Inhaltslücken.
- Briefing-Kandidaten fehlen lexikalisch auf der eigenen geladenen Seite und
  kommen auf mindestens zwei und mindestens 40 Prozent der Vergleichsseiten vor.
- Bildanzahl und Wortanzahl stammen aus dem vorhandenen Parser.

Keine Rankinggarantie, kein Google-Salience-Score und keine echte
Entitätenerkennung. Backlinkstärke ist in diesem Vergleich nicht verfügbar.
Fehlgeschlagene Abrufe bleiben unbekannt, nicht null Bilder oder null Wörter.
Die bestehende API bleibt abwärtskompatibel; kein neues Datenbankschema,
keine separate Persistenz und keine zusätzliche MCP-Funktion in diesem PR.
Die bestehenden Freigabeprozesse bleiben unverändert.

Tests: `backend/tests/test_serp_content_comparison.py`.
