"""Tests for tools/backlinks.py — mocks Google search results."""
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx


MOCK_SERP_HTML = """<html><body>
<a href="/url?q=https://guestpost-site.com/write-for-us&sa=U">Write for us</a>
<a href="/url?q=https://resource-page.net/seo-resources&sa=U">SEO resources</a>
<a href="/url?q=https://blog.example.io/seo-roundup&sa=U">SEO roundup</a>
<a href="https://irrelevant.com/no-match">Irrelevant</a>
</body></html>"""


def _mock_serp_response():
    return httpx.Response(
        status_code=200,
        content=MOCK_SERP_HTML.encode(),
        headers={"content-type": "text/html"},
        request=httpx.Request("GET", "https://www.google.com/search"),
    )


def test_find_prospects_returns_results():
    from tools.backlinks import find_backlink_opportunities

    with patch("httpx.get", return_value=_mock_serp_response()):
        result = find_backlink_opportunities(
            domain="mysite.com",
            niche="SEO tools",
        )

    assert result.target_domain == "mysite.com"
    assert result.niche == "SEO tools"
    assert len(result.prospects) >= 1
    assert result.outreach_template != ""


def test_prospect_has_required_fields():
    from tools.backlinks import find_backlink_opportunities

    with patch("httpx.get", return_value=_mock_serp_response()):
        result = find_backlink_opportunities(
            domain="mysite.com",
            niche="digital marketing",
        )

    for p in result.prospects:
        assert p.url
        assert p.domain
        assert p.relevance_reason
        assert p.contact_hint
        assert p.outreach_type in ("guest_post", "resource_page", "mention", "broken_link")


def test_own_domain_excluded():
    from tools.backlinks import find_backlink_opportunities

    # Inject a result that IS the target domain — should be filtered out
    html_with_self = """<html><body>
    <a href="/url?q=https://mysite.com/page1&sa=U">Own site</a>
    <a href="/url?q=https://external-site.com/resources&sa=U">External</a>
    </body></html>"""

    resp = httpx.Response(
        status_code=200,
        content=html_with_self.encode(),
        headers={"content-type": "text/html"},
        request=httpx.Request("GET", "https://www.google.com/search"),
    )

    with patch("httpx.get", return_value=resp):
        result = find_backlink_opportunities(domain="mysite.com", niche="SEO")

    domains = [p.domain for p in result.prospects]
    assert "mysite.com" not in domains


def test_no_duplicates():
    from tools.backlinks import find_backlink_opportunities

    with patch("httpx.get", return_value=_mock_serp_response()):
        result = find_backlink_opportunities(domain="mysite.com", niche="SEO")

    domains = [p.domain for p in result.prospects]
    assert len(domains) == len(set(domains)), "Duplicate domains found"


def test_outreach_template_contains_niche():
    from tools.backlinks import find_backlink_opportunities

    with patch("httpx.get", return_value=_mock_serp_response()):
        result = find_backlink_opportunities(domain="mysite.com", niche="content marketing")

    assert "content marketing" in result.outreach_template


def test_http_error_handled_gracefully():
    from tools.backlinks import find_backlink_opportunities

    with patch("httpx.get", side_effect=httpx.ConnectError("blocked")):
        result = find_backlink_opportunities(domain="mysite.com", niche="SEO")

    # Should not raise — just returns empty prospects
    assert isinstance(result.prospects, list)


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
