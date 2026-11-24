from datetime import date

from app.db import session_scope
from app.models import GscRow


def test_dependency_audit_landingpage_and_brand(client, auth, fixture_site):
    site = client.post("/api/sites", headers=auth, json={
        "name": "Klas Küchen", "url": fixture_site.url}).json()
    site_id = site["id"]

    # 1. No data case
    res_empty = client.get(f"/api/sites/{site_id}/dependency-audit", headers=auth)
    assert res_empty.status_code == 200
    assert res_empty.json()["has_data"] is False

    # 2. Add fixture GSC data
    # URL 1 (Hero URL): 80 clicks (Brand: "klas küchen münchen") -> 80% of total
    # URL 2: 15 clicks (Non-brand: "moderne kücheninseln")
    # URL 3: 5 clicks (Non-brand: "holz arbeitsplatte pflege")
    # Total: 100 clicks
    with session_scope() as db:
        for day_num in range(1, 11):
            db.add(GscRow(
                site_id=site_id,
                source="api",
                dataset="query_page",
                day=date(2026, 11, day_num),
                query="klas küchen beratung",
                page=fixture_site.url + "/hero-page",
                clicks=8,
                impressions=50,
                position=1.0,
            ))
            db.add(GscRow(
                site_id=site_id,
                source="api",
                dataset="query_page",
                day=date(2026, 11, day_num),
                query="moderne kücheninseln holz",
                page=fixture_site.url + "/kuecheninseln",
                clicks=1.5,
                impressions=40,
                position=4.0,
            ))
            db.add(GscRow(
                site_id=site_id,
                source="api",
                dataset="query_page",
                day=date(2026, 11, day_num),
                query="holz arbeitsplatte pflege",
                page=fixture_site.url + "/arbeitsplatten",
                clicks=0.5,
                impressions=30,
                position=7.0,
            ))
        db.commit()

    # 3. Query audit
    res = client.get(f"/api/sites/{site_id}/dependency-audit?days=28", headers=auth)
    assert res.status_code == 200
    data = res.json()
    assert data["has_data"] is True
    assert data["total_clicks"] == 100

    # Landingpage concentration
    lp = data["landingpage_concentration"]
    assert lp["total_landing_pages"] == 3
    assert lp["top_1_share"] == 0.8  # 80%
    assert lp["risk_level"] == "kritisch"
    assert lp["top_pages"][0]["single_point_of_failure"] is True
    assert lp["top_pages"][0]["url"] == fixture_site.url + "/hero-page"

    # Search term concentration
    st = data["search_term_concentration"]
    assert "klas" in st["brand_tokens_used"]
    assert st["brand_share"] == 0.8  # 80% Brand
    assert st["brand_risk_level"] == "hohe_markenabhaengigkeit"
    assert st["non_brand_share"] == 0.2  # 20% Non-Brand

    # Custom brand term parameter
    res_custom = client.get(f"/api/sites/{site_id}/dependency-audit?days=28&brand_term=arbeitsplatte", headers=auth)
    assert res_custom.status_code == 200
    st_custom = res_custom.json()["search_term_concentration"]
    assert st_custom["brand_tokens_used"] == ["arbeitsplatte"]
    assert st_custom["brand_share"] == 0.05  # Only 5 clicks on arbeitsplatte
