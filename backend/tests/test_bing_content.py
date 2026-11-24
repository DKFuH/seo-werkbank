from app.services.bing_content import normalize_page_queries, analyze_sample


def test_no_fabricated_pairs_or_dates():
    data = [{"Query": "kitchen", "Date": "2026-11-01", "Clicks": 2,
             "Impressions": 20, "AvgImpressionPosition": 5}]
    rows = normalize_page_queries("https://example.com/kitchen", data + data)
    assert len(rows) == 1
    assert rows[0]["page"] == "https://example.com/kitchen"
    result = analyze_sample(rows, [], weeks=4)
    assert result["provider"] == "bing"
    assert not result["comparable_windows"]
    assert result["decay"] == result["trends"] == []


def test_invalid_observation_is_omitted():
    assert normalize_page_queries("https://example.com/", [{"Query": "x"}]) == []
