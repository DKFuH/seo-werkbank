from datetime import date

from app.db import session_scope
from app.models import GscRow


def test_seo_experiments_crud_and_metrics(client, auth, fixture_site):
    # 1. Create a site
    site = client.post("/api/sites", headers=auth, json={
        "name": "Exp Site", "url": fixture_site.url}).json()
    site_id = site["id"]

    # 2. Add GSC rows for testing before & after performance
    # Applied date: 2026-10-15
    # Before: 2026-10-01 to 2026-10-14 (14 days, e.g. 10 clicks, 100 imp, pos 12.0)
    # After:  2026-10-15 to 2026-10-28 (14 days, e.g. 20 clicks, 150 imp, pos 8.0)
    target_url = fixture_site.url + "/ratgeber-kueche"

    with session_scope() as db:
        # Before rows
        for d in range(1, 15):
            db.add(GscRow(
                site_id=site_id,
                source="api",
                dataset="query_page",
                day=date(2026, 10, d),
                query="kueche planung",
                page=target_url,
                clicks=10,
                impressions=100,
                position=12.0,
            ))
        # After rows
        for d in range(15, 29):
            db.add(GscRow(
                site_id=site_id,
                source="api",
                dataset="query_page",
                day=date(2026, 10, d),
                query="kueche planung",
                page=target_url,
                clicks=20,
                impressions=150,
                position=8.0,
            ))
        db.commit()

    # 3. Create an experiment
    create_res = client.post(f"/api/sites/{site_id}/experiments", headers=auth, json={
        "title": "Ratgeber H1 und Content Überarbeitung",
        "category": "content",
        "hypothesis": "Überarbeitung des Ratgebers steigert Klicks um 50 %",
        "applied_date": "2026-10-15",
        "target_url": target_url,
        "notes": "Title-Tag und H1 auf Intent 'kueche planung' optimiert",
    })
    assert create_res.status_code == 201
    exp = create_res.json()
    exp_id = exp["id"]
    assert exp["title"] == "Ratgeber H1 und Content Überarbeitung"
    assert exp["applied_date"] == "2026-10-15"

    # 4. List experiments
    list_res = client.get(f"/api/sites/{site_id}/experiments", headers=auth)
    assert list_res.status_code == 200
    assert list_res.json()["count"] == 1
    assert list_res.json()["items"][0]["id"] == exp_id

    # 5. Timeline annotations
    anno_res = client.get(f"/api/sites/{site_id}/experiments/timeline-annotations", headers=auth)
    assert anno_res.status_code == 200
    annos = anno_res.json()
    assert len(annos) == 1
    assert annos[0]["date"] == "2026-10-15"

    # 6. Metrics evaluation (14 days window)
    metrics_res = client.get(f"/api/sites/{site_id}/experiments/{exp_id}/metrics?days=14", headers=auth)
    assert metrics_res.status_code == 200
    m = metrics_res.json()
    assert m["has_data"] is True
    assert m["before_window"]["metrics"]["clicks"] == 140
    assert m["after_window"]["metrics"]["clicks"] == 280
    assert m["delta"]["clicks_pct"] == 100.0
    assert m["delta"]["position_change"] == -4.0  # Improved from 12.0 to 8.0!
    assert "timeline" in m
    assert any(point["is_experiment_marker"] for point in m["timeline"])

    # 7. Patch conclusions
    patch_res = client.patch(f"/api/sites/{site_id}/experiments/{exp_id}", headers=auth, json={
        "conclusions": "Signifikanter Klickanstieg bestätigt.",
    })
    assert patch_res.status_code == 200
    assert patch_res.json()["conclusions"] == "Signifikanter Klickanstieg bestätigt."

    # 8. Delete
    del_res = client.delete(f"/api/sites/{site_id}/experiments/{exp_id}", headers=auth)
    assert del_res.status_code == 204
    assert client.get(f"/api/sites/{site_id}/experiments", headers=auth).json()["count"] == 0
