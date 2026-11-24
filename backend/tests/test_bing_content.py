from datetime import date, timedelta

from app.services.bing_content import analyze_sample, normalize_page_queries


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


def _row(day, query, page, impressions, clicks):
    return {"day": day, "query": query, "page": page, "impressions": impressions,
            "clicks": clicks, "position": 5.0}


def test_temporal_signals_require_complete_coverage_per_series():
    end = date(2026, 11, 23)
    weekly = [end - timedelta(weeks=offset) for offset in range(8)]
    complete_page = "https://example.com/complete"
    incomplete_page = "https://example.com/incomplete"
    rows = []
    for index, day in enumerate(weekly):
        rows.append(_row(day, "stable query", complete_page, 100, 20 if index >= 4 else 15))
    rows.extend([
        _row(weekly[4], "incomplete falling", incomplete_page, 100, 20),
        _row(weekly[0], "incomplete falling", incomplete_page, 100, 0),
        _row(weekly[0], "new incomplete trend", incomplete_page, 100, 5),
    ])

    result = analyze_sample(rows, [], weeks=4)

    assert result["comparable_windows"] is True
    assert all(item["url"] != incomplete_page for item in result["decay"])
    assert all(item["query"] not in {"incomplete falling", "new incomplete trend"}
               for item in result["trends"])


def test_bing_analysis_labels_shared_results_as_bing_not_gsc():
    end = date(2026, 11, 23)
    weekly = [end - timedelta(weeks=offset) for offset in range(8)]
    rows = []
    for day in weekly:
        rows.extend([
            _row(day, "shared query", "https://example.com/a", 80, 8),
            _row(day, "shared query", "https://example.com/b", 40, 4),
        ])

    result = analyze_sample(rows, [], weeks=4)

    assert result["cannibalisation"]
    assert "Bing" in result["cannibalisation"][0]["interpretation"]
    assert "GSC" not in result["cannibalisation"][0]["interpretation"]
    assert "Bing" in result["method"]
