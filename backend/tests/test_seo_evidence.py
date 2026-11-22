"""Local evidence and publication summaries never invent Google review or link status."""
from app.db import session_scope
from app.models import Backlink, Citation, SeoWorkItem


def test_local_actions_and_publication_reconciliation(client, auth, fixture_site):
    site = client.post("/api/sites", headers=auth, json={
        "name": "Local evidence test", "url": fixture_site.url + "/"}).json()
    sid = site["id"]
    with session_scope() as db:
        db.add_all([
            Citation(site_id=sid, source="Directory A", url="https://directory.example/a",
                     name="Example Shop", address="Example Street 1", phone="+49 123 456"),
            Citation(site_id=sid, source="Directory B", name="Different Shop",
                     address="Example Street 1", phone="+49 123 456"),
            SeoWorkItem(site_id=sid, kind="review", status="requested", title="Request honest feedback"),
            SeoWorkItem(site_id=sid, kind="publication", status="published", title="Guest article",
                        source_url="https://press.example/story", target_url=fixture_site.url + "/"),
            Backlink(site_id=sid, source_url="https://press.example/story", source_domain="press.example",
                     target_url=fixture_site.url + "/", status="live", origin="manual", nofollow=True),
        ])
    plan=client.get(f"/api/sites/{sid}/local-action-plan",headers=auth)
    assert plan.status_code==200,plan.text
    data=plan.json()
    assert data["citations"]["count"]==2
    assert "name" in data["citations"]["inconsistent"]
    assert data["citations"]["missing"]["url"]==1
    assert data["review_requests"]["by_status"]["requested"]==1
    assert all("rank" not in x["type"] for x in data["actions"])
    evidence=client.get(f"/api/sites/{sid}/publication-evidence",headers=auth)
    assert evidence.status_code==200,evidence.text
    pub=evidence.json()["items"][0]
    assert pub["backlink_record"]["status"]=="live"
    assert pub["backlink_record"]["nofollow"] is True
    assert "redaktionelle Qualität" in pub["interpretation"]
    other=client.post("/api/auth/register",json={"email":"evidence-other@example.com",
                                                    "password":"correct horse battery"}).json()
    h={"Authorization":"Bearer "+other["access_token"]}
    assert client.get(f"/api/sites/{sid}/local-action-plan",headers=h).status_code==404
    assert client.get(f"/api/sites/{sid}/publication-evidence",headers=h).status_code==404
