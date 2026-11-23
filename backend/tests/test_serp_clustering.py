from app.keywords.research import cluster_by_serp


def test_serp_clustering_groups_shared_urls():
    urls = {"keyword a": ["https://example.org/a", "https://example.org/b"],
            "keyword b": ["https://example.org/b", "https://example.org/a"],
            "keyword c": ["https://other.example/a"]}
    out = cluster_by_serp(urls, min_overlap=2)
    assert any(set(g["keywords"]) == {"keyword a", "keyword b"} for g in out)


def test_serp_cluster_api_requires_provider_or_complete_manual_data(client, auth):
    url = "/api/keywords/serp-clusters"
    payload = {"keywords": ["keyword a", "keyword b"], "manual_results": {
        "keyword a": ["https://example.org/a", "https://example.org/b"],
        "keyword b": ["https://example.org/a", "https://example.org/c"]}, "min_overlap": 1}
    res = client.post(url, json=payload, headers=auth)
    assert res.status_code == 200, res.text
    assert len(res.json()["clusters"]) >= 1
    payload["manual_results"].pop("keyword b")
    assert client.post(url, json=payload, headers=auth).status_code == 422
