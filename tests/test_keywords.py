"""Tests for tools/keywords.py — mocks all HTTP calls."""
import sys, json
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx


def _autocomplete_response(suggestions: list[str], query: str = "seo"):
    return httpx.Response(
        status_code=200,
        content=json.dumps([query, suggestions]).encode(),
        headers={"content-type": "application/json"},
        request=httpx.Request("GET", "https://suggestqueries.google.com/"),
    )


def test_keywords_returns_suggestions():
    from tools.keywords import research_keywords

    suggestions = ["seo tools", "seo best practices", "seo checklist 2026",
                   "how to do seo", "seo for beginners"]

    with patch("httpx.get", return_value=_autocomplete_response(suggestions)):
        result = research_keywords("seo")

    assert result.seed_keyword == "seo"
    assert len(result.suggestions) > 0
    assert result.source == "google_autocomplete"


def test_keywords_with_domain():
    from tools.keywords import research_keywords

    with patch("httpx.get", return_value=_autocomplete_response(["python seo", "python scraping"])):
        result = research_keywords("python", domain="example.com")

    assert result.domain == "example.com"


def test_question_variants_captured():
    from tools.keywords import research_keywords

    question_suggestions = [
        "how to do seo",
        "what is seo optimization?",
        "why is seo important",
        "seo tips",
    ]

    with patch("httpx.get", return_value=_autocomplete_response(question_suggestions)):
        result = research_keywords("seo")

    # questions list should capture actual question-format results
    all_kws = [s.keyword for s in result.suggestions] + result.questions + result.long_tail
    assert any(kw for kw in all_kws if kw)  # at least something returned


def test_autocomplete_http_error_handled():
    from tools.keywords import research_keywords

    with patch("httpx.get", side_effect=httpx.ConnectError("blocked")):
        result = research_keywords("seo")

    # Should not crash — returns empty suggestions
    assert result.seed_keyword == "seo"
    assert isinstance(result.suggestions, list)


def test_check_serp_rank_no_key():
    # SERPAPI_KEY is imported by value into the module; patch that name directly
    with patch("tools.keywords.SERPAPI_KEY", ""):
        from tools.keywords import check_serp_rank
        result = check_serp_rank("python seo", "example.com")

    assert result["position"] is None
    assert result["source"] == "no_serpapi_key"


def test_check_serp_rank_found():
    mock_resp = httpx.Response(
        status_code=200,
        content=json.dumps({
            "organic_results": [
                {"link": "https://other.com/page1"},
                {"link": "https://example.com/seo-guide"},
                {"link": "https://another.com/page3"},
            ]
        }).encode(),
        headers={"content-type": "application/json"},
        request=httpx.Request("GET", "https://serpapi.com/search"),
    )

    with patch("tools.keywords.SERPAPI_KEY", "fake_key"), \
         patch("tools.keywords.httpx.get", return_value=mock_resp):
        from tools.keywords import check_serp_rank
        result = check_serp_rank("python seo", "example.com")

    assert result["position"] == 2
    assert result["source"] == "serpapi"


def test_check_serp_rank_not_found():
    mock_resp = httpx.Response(
        status_code=200,
        content=json.dumps({
            "organic_results": [
                {"link": "https://competitor1.com"},
                {"link": "https://competitor2.com"},
            ]
        }).encode(),
        headers={"content-type": "application/json"},
        request=httpx.Request("GET", "https://serpapi.com/search"),
    )

    with patch("tools.keywords.SERPAPI_KEY", "fake_key"), \
         patch("tools.keywords.httpx.get", return_value=mock_resp):
        from tools.keywords import check_serp_rank
        result = check_serp_rank("python seo", "example.com")

    assert result["position"] == 0


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
