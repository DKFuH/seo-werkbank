"""Crawls are numbered 1..n per project (site), separately per competitor, without gaps after a deletion."""
from __future__ import annotations

from app.api.sites import crawl_number
from app.db import session_scope
from app.models import Competitor, Crawl, Site, User


def test_run_numbers_per_site_and_competitor(client):
    with session_scope() as db:
        user = User(email="numbers@example.com", password_hash="x")
        db.add(user)
        db.flush()
        a = Site(owner_id=user.id, name="A", url="https://a.example/", domain="a.example")
        b = Site(owner_id=user.id, name="B", url="https://b.example/", domain="b.example")
        db.add_all([a, b])
        db.flush()
        comp = Competitor(site_id=a.id, name="C", url="https://c.example/", domain="c.example")
        db.add(comp)
        db.flush()

        def crawl(site, competitor=None):
            c = Crawl(site_id=site.id, competitor_id=competitor.id if competitor else None, status="completed",
                      start_url=site.url, config={})
            db.add(c)
            db.flush()
            return c

        a1, b1, a2, c1, a3 = crawl(a), crawl(b), crawl(a), crawl(a, comp), crawl(a)
        assert [crawl_number(db, c) for c in (a1, a2, a3)] == [1, 2, 3]
        assert crawl_number(db, b1) == 1  # numbering is per project, not global
        assert crawl_number(db, c1) == 1  # competitor crawls count on their own
        db.delete(a2)
        db.flush()
        assert crawl_number(db, a3) == 2  # gap-free after a deletion


def test_crawl_api_returns_number(client, auth, crawled):
    crawls = client.get(f"/api/sites/{crawled['site']['id']}/crawls", headers=auth).json()
    assert crawls and all(isinstance(c["number"], int) and c["number"] >= 1 for c in crawls)
    assert sorted(c["number"] for c in crawls) == list(range(1, len(crawls) + 1))
