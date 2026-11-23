"""Authenticated log import, redirect proposal and tenant isolation."""
from tests.conftest import wait_for_job


def test_log_import_and_404_handoff(client, auth, fixture_site):
    site = client.post("/api/sites", headers=auth, json={
        "name": "Logs test", "url": fixture_site.url + "/"}).json()
    sid = site["id"]
    sample = (
        '192.0.2.7 - - [10/Oct/2026:13:55:36 +0200] '
        '"GET /old HTTP/1.1" 404 123 '
        '"https://ref.example/page" "Googlebot/2.1"\n'
    )
    result = client.post(f"/api/sites/{sid}/logs/import", headers=auth,
        files={"file": ("access.log", sample.encode(), "text/plain")},
        data={"fmt": "combined"})
    assert result.status_code == 200, result.text
    job = wait_for_job(client, auth, result.json()["job_id"])
    assert job["status"] == "completed", job
    summary = client.get(f"/api/sites/{sid}/logs/summary", headers=auth).json()
    assert summary["status_counts"]["404"] == 1
    assert summary["top_404"][0]["path"] == "/old"
    assert summary["top_404"][0]["referrer_host"] == "ref.example"
    assert client.post(f"/api/sites/{sid}/logs/404/redirect", headers=auth,
        json={"path": "/old", "target_url": fixture_site.url + "/"}).status_code == 201
    rules = client.get(f"/api/sites/{sid}/redirects", headers=auth).json()
    assert rules[0]["state"] == "proposed"
    assert rules[0]["origin"] == "404"

    other = client.post("/api/auth/register", json={
        "email": "another-log-user@example.com",
        "password": "correct horse battery"}).json()
    second_user = {"Authorization": "Bearer " + other["access_token"]}
    assert client.get(f"/api/sites/{sid}/logs", headers=second_user).status_code == 404
    assert client.delete(f"/api/sites/{sid}/logs/{result.json()['import_id']}",
                         headers=second_user).status_code == 404
    assert client.delete(f"/api/sites/{sid}/logs/{result.json()['import_id']}",
                         headers=auth).status_code == 204
