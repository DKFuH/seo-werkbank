from app.serp.content_comparison import compare, occurrences, prominence


def test_exact_phrase_and_prominence():
    assert occurrences("Küche planen", "Küche planen, Küchen planen") == 1
    data = prominence("Küche planen", {
        "title": "Küche planen", "text": "Küche planen und gestalten",
        "headings": [{"level": 1, "text": "Küche planen"}],
    })
    assert data["title"] and data["h1"] and data["first_100"]
    assert data["mentions_in_sample"] == 1


def test_comparison_excludes_other_types_and_failed_pages():
    own = "https://example.org/ratgeber/kuche"
    guide = "https://other.org/ratgeber/kuche"
    shop = "https://other.org/shop/kuche"
    failed = "https://example.net/ratgeber/kuche"
    pages = {
        own: {"status": 200, "text": "Küche planen"},
        guide: {"status": 200, "text": "Küche planen Kosten Abstand"},
        shop: {"status": 200, "text": "Küche kaufen"},
        failed: {"status": 403},
    }
    results = [{"url": url, "position": i} for i, url in enumerate(pages, 1)]
    report = compare("Küche", results, pages, own)
    assert report["selected_urls"] == [guide]
    assert report["rows"][-1]["prominence"] is None
    assert report["backlink_status"] == "unavailable"


def test_empty_comparison():
    report = compare("Küche", [], {}, None)
    assert report["matrix"] == []
    assert report["own_prominence"] is None
    assert report["briefing_candidates"] == []
