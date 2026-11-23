"""CSV import preview and user-defined column mapping for all imports."""
from __future__ import annotations

import json

import pytest

from app.services import csv_import

GERMAN_GSC = "Häufigste Suchanfragen;Klicks;Impressionen;CTR;Position\nküche planen;12;1.234;1%;8,5\n".encode()
ODD_HEADERS = "Begriff;Treffer;Sichtungen;Rang\nküche planen;12;1234;8.5\nküchenstudio;3;400;12.0\n".encode()


def test_preview_suggests_columns_and_number_format():
    p = csv_import.preview(GERMAN_GSC, "gsc")
    fields = {f["key"]: f for f in p["fields"]}
    assert fields["query"]["suggested"] == 0 and fields["clicks"]["suggested"] == 1 and fields["impressions"]["suggested"] == 2
    assert fields["clicks"]["required"] and p["number_format"] == "de" and p["rows"] == 1
    assert p["columns"][2] == {"index": 2, "name": "Impressionen", "samples": ["1.234"]}


def test_unknown_headers_need_mapping():
    with pytest.raises(csv_import.ImportFormatError, match="Pflichtfeld ohne Spalte"):
        csv_import.resolve(ODD_HEADERS, "gsc", None)
    mapping = json.dumps({"query": 0, "clicks": 1, "impressions": 2, "position": 3})
    header, rows, cols = csv_import.resolve(ODD_HEADERS, "gsc", mapping)
    assert cols == {"query": 0, "clicks": 1, "impressions": 2, "position": 3} and len(rows) == 2


def test_invalid_mapping_is_rejected():
    for bad, message in ((json.dumps({"query": 9}), "existiert nicht"), (json.dumps({"nope": 0}), "Unbekanntes Feld"),
                         ("[1, 2]", "Objekt"), ("{", "gültiges JSON"), (json.dumps({"clicks": True}), "existiert nicht")):
        with pytest.raises(csv_import.ImportFormatError, match=message):
            csv_import.resolve(ODD_HEADERS, "gsc", bad)
    with pytest.raises(csv_import.ImportFormatError, match="Mindestens eine"):
        csv_import.resolve(ODD_HEADERS, "gsc", json.dumps({"clicks": 1, "impressions": 2}))


def test_keyword_planner_preamble_and_windows_encoding():
    raw = ("Keyword Stats 2026-11-01\nAll locations\nKeyword;Avg. monthly searches\nküche;1.000\n").encode("cp1252")
    header, rows, cols = csv_import.resolve(raw, "keywords", None)
    assert header[0] == "Keyword" and rows == [["küche", "1.000"]] and cols == {"keyword": 0, "search_volume": 1}


def test_gsc_import_with_mapping_and_forced_number_format(client, auth, fixture_site):
    sid = client.post("/api/sites", headers=auth, json={"name": "Mapping", "url": fixture_site.url + "/"}).json()["id"]
    url = f"/api/sites/{sid}/gsc/import"
    files = {"file": ("odd.csv", ODD_HEADERS, "text/csv")}
    assert client.post(url, headers=auth, files=files).status_code == 400  # no known columns
    mapping = json.dumps({"query": 0, "clicks": 1, "impressions": 2, "position": 3})
    r = client.post(url, headers=auth, files={"file": ("odd.csv", ODD_HEADERS, "text/csv")},
                    data={"mapping": mapping, "number_format": "en"})
    assert r.status_code == 200, r.text
    assert r.json()["rows"] == 2
    perf = client.get(f"/api/sites/{sid}/gsc/performance", headers=auth).json()
    assert perf["totals"]["impressions"] == 1634 and perf["totals"]["clicks"] == 15
    preview = client.post("/api/imports/preview", headers=auth, params={"kind": "gsc"},
                          files={"file": ("odd.csv", ODD_HEADERS, "text/csv")})
    assert preview.status_code == 200 and [c["name"] for c in preview.json()["columns"]] == ["Begriff", "Treffer", "Sichtungen", "Rang"]


def test_citations_and_backlinks_with_mapping(client, auth, fixture_site):
    sid = client.post("/api/sites", headers=auth, json={"name": "Mapping 2", "url": fixture_site.url + "/"}).json()["id"]
    cit = b"Portal;Link;Firma\nGelbe Seiten;https://gs.example/x;Muster GmbH\n"
    r = client.post(f"/api/sites/{sid}/citations/import", headers=auth, files={"file": ("c.csv", cit, "text/csv")},
                    data={"mapping": json.dumps({"source": 0, "url": 1, "name": 2})})
    assert r.status_code == 200 and r.json()["imported"] == 1
    links = "Von;Nach;Text\nhttps://blog.example/a;https://m.example/;Küchen\n".encode()
    assert client.post(f"/api/sites/{sid}/backlinks/import", headers=auth,
                       files={"file": ("b.csv", links, "text/csv")}).status_code == 400
    r = client.post(f"/api/sites/{sid}/backlinks/import", headers=auth, files={"file": ("b.csv", links, "text/csv")},
                    data={"mapping": json.dumps({"source": 0, "target": 1, "anchor": 2})})
    assert r.status_code == 200 and r.json()["added"] == 1
