"""Rank targets remain site-scoped and track measured vs manually entered observations."""
def test_rank_targets_isolation_and_observation(client, auth, fixture_site):
    site = client.post("/api/sites", headers=auth, json={
        "name": "Rank tracker test", "url": fixture_site.url + "/"}).json()
    sid = site["id"]
    path = f"/api/sites/{sid}/rank-targets"
    created = client.post(path, headers=auth, json={"keyword": "example target", "country": "de",
                                                     "language": "de", "device": "desktop"})
    assert created.status_code == 201, created.text
    target = created.json()
    assert target["history"] == []
    assert client.post(path, headers=auth, json={"keyword": "example target"}).status_code == 409
    sample = client.post(f"{path}/{target['id']}/observations", headers=auth,
                         json={"position": 7, "search_depth": 10, "serp_features": ["FAQ"]})
    assert sample.status_code == 201, sample.text
    assert sample.json()["provider"] == "manual"
    assert client.post(f"{path}/{target['id']}/observations", headers=auth,
                       json={"position": 11, "search_depth": 10}).status_code == 422
    client.post(f"{path}/{target['id']}/observations", headers=auth,
                json={"position": 4, "search_depth": 10})
    rows = client.get(path, headers=auth).json()["items"]
    assert rows[0]["position_delta"] == 3
    assert rows[0]["history"][0]["serp_features"] == ["FAQ"]
    other = client.post("/api/auth/register", json={
        "email": "rank-other@example.com", "password": "correct horse battery"}).json()
    h = {"Authorization": "Bearer " + other["access_token"]}
    assert client.get(path, headers=h).status_code == 404
    assert client.post(f"{path}/{target['id']}/observations", headers=h, json={"position": 1}).status_code == 404
    assert client.delete(f"{path}/{target['id']}", headers=h).status_code == 404
    assert client.post(f"{path}/{target['id']}/capture", headers=auth).status_code == 422
    assert client.delete(f"{path}/{target['id']}", headers=auth).status_code == 204


def test_bare_host_treats_www_and_apex_as_same_site():
    from app.api.rank_tracking import _bare_host

    assert _bare_host("https://www.Example.de/a") == "example.de"
    assert _bare_host("https://example.de") == "example.de"
    assert _bare_host("not a url") == ""


def test_observation_offset_is_converted_to_utc(client, auth, fixture_site):
    site = client.post("/api/sites", headers=auth, json={"name": "Rank tz", "url": fixture_site.url + "/"}).json()
    path = f"/api/sites/{site['id']}/rank-targets"
    target = client.post(path, headers=auth, json={"keyword": "timezone target"}).json()
    r = client.post(f"{path}/{target['id']}/observations", headers=auth,
                    json={"position": 3, "observed_at": "2026-01-10T12:00:00+02:00"})
    assert r.status_code == 201, r.text
    assert r.json()["observed_at"] == "2026-01-10T10:00:00"
