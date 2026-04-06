"""
Competitor gap analysis tool.

Uses DataForSEO to surface:
- Keywords a competitor ranks for that you don't (keyword gap)
- Backlinks pointing to a competitor that you haven't acquired yet (backlink gap)
- Top-performing competitor pages by organic traffic estimate
"""
from __future__ import annotations

from urllib.parse import urlparse

import httpx

from config import DATAFORSEO_LOGIN, DATAFORSEO_PASSWORD, REQUEST_TIMEOUT
from models import (
    CompetitorAnalysis,
    CompetitorKeywordGap,
    CompetitorBacklinkGap,
    CompetitorPage,
)


# ── DataForSEO helpers ─────────────────────────────────────────────────────────

def _dfs_post(endpoint: str, payload: list) -> dict:
    if not (DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD):
        return {}
    try:
        r = httpx.post(
            f"https://api.dataforseo.com/v3/{endpoint}",
            auth=(DATAFORSEO_LOGIN, DATAFORSEO_PASSWORD),
            json=payload,
            timeout=45,
        )
        return r.json()
    except Exception:
        return {}


def _dfs_items(resp: dict) -> list:
    try:
        return (
            resp.get("tasks", [{}])[0]
            .get("result", [{}])[0]
            .get("items", [])
        )
    except Exception:
        return []


# ── Keyword gap ───────────────────────────────────────────────────────────────

def _keyword_gap(your_domain: str, competitor_domain: str) -> list[CompetitorKeywordGap]:
    """Keywords the competitor ranks for (positions 1–30) that you don't."""
    payload = [{
        "targets": [your_domain, competitor_domain],
        "location_code": 2840,
        "language_code": "en",
        "limit": 30,
        "filters": [
            ["keyword_data.keyword_info.search_volume", ">", 50],
            "and",
            [f"ranked_serp_element.serp_item.rank_group.{competitor_domain}", "<=", 30],
        ],
    }]
    resp = _dfs_post(
        "dataforseo_labs/google/keyword_gap/live", payload
    )
    gaps: list[CompetitorKeywordGap] = []
    for item in _dfs_items(resp):
        kw = item.get("keyword_data", {}).get("keyword", "")
        kd = item.get("keyword_data", {}).get("keyword_info", {})
        your_rank_info = item.get("ranked_serp_element", {}).get(your_domain)
        comp_rank_info = item.get("ranked_serp_element", {}).get(competitor_domain)
        gaps.append(CompetitorKeywordGap(
            keyword=kw,
            competitor_position=comp_rank_info.get("rank_group", 0) if comp_rank_info else 0,
            your_position=your_rank_info.get("rank_group", None) if your_rank_info else None,
            search_volume=kd.get("search_volume"),
            keyword_difficulty=item.get("keyword_data", {}).get("keyword_properties", {}).get("keyword_difficulty"),
            opportunity="high" if not your_rank_info else "medium",
        ))
    return gaps


# ── Backlink gap ──────────────────────────────────────────────────────────────

def _backlink_gap(your_domain: str, competitor_domain: str) -> list[CompetitorBacklinkGap]:
    """Referring domains linking to the competitor but not to you."""
    payload = [{
        "targets": [your_domain, competitor_domain],
        "limit": 25,
        "filters": [
            [f"referring_links_tld.{competitor_domain}", ">", 0],
            "and",
            [f"referring_links_tld.{your_domain}", "=", 0],
        ],
    }]
    resp = _dfs_post("backlinks/domain_intersection/live", payload)
    gaps: list[CompetitorBacklinkGap] = []
    for item in _dfs_items(resp):
        domain = item.get("domain", "")
        dr = item.get("domain_rank", 0)
        gaps.append(CompetitorBacklinkGap(
            referring_domain=domain,
            domain_rank=dr,
            links_to_competitor=item.get(competitor_domain, 0),
            links_to_you=item.get(your_domain, 0),
            contact_hint=f"Try {domain}/contact or search '{domain} editor email'",
        ))
    return gaps


# ── Top competitor pages ──────────────────────────────────────────────────────

def _top_pages(competitor_domain: str) -> list[CompetitorPage]:
    """Competitor's top organic pages by traffic estimate."""
    payload = [{
        "target": competitor_domain,
        "location_code": 2840,
        "language_code": "en",
        "limit": 15,
        "filters": [["estimated_paid_traffic_cost", ">", 0]],
        "order_by": ["estimated_paid_traffic_cost,desc"],
    }]
    resp = _dfs_post("dataforseo_labs/google/top_pages/live", payload)
    pages: list[CompetitorPage] = []
    for item in _dfs_items(resp):
        pages.append(CompetitorPage(
            url=item.get("page_address", ""),
            estimated_traffic=item.get("estimated_paid_traffic_cost", 0),
            top_keyword=item.get("top_keyword", ""),
            keywords_count=item.get("keywords_count", 0),
        ))
    return pages


# ── Fallback: Google search estimate (no API key) ─────────────────────────────

def _estimate_competitor_content(competitor_domain: str) -> list[CompetitorPage]:
    """
    Very rough estimation of top competitor pages via Google search operators
    when DataForSEO is not configured.
    """
    from urllib.parse import quote_plus
    from bs4 import BeautifulSoup
    from config import HEADERS

    query = f"site:{competitor_domain}"
    url = f"https://www.google.com/search?q={quote_plus(query)}&num=15"
    pages = []
    try:
        r = httpx.get(url, headers={**HEADERS, "Accept-Language": "en-US"}, timeout=15)
        soup = BeautifulSoup(r.text, "lxml")
        for a in soup.select("a[href^='/url?q=']"):
            href = a["href"][7:].split("&")[0]
            if competitor_domain in href:
                snippet_el = a.find_parent("div", class_=True)
                snippet = snippet_el.get_text(separator=" ", strip=True)[:120] if snippet_el else ""
                pages.append(CompetitorPage(
                    url=href,
                    estimated_traffic=0,
                    top_keyword=snippet,
                    keywords_count=0,
                ))
        return pages[:10]
    except Exception:
        return []


# ── Public API ────────────────────────────────────────────────────────────────

def analyze_competitor(
    your_domain: str,
    competitor_domain: str,
) -> CompetitorAnalysis:
    """
    Full competitor gap analysis: keyword gaps, backlink gaps, and top pages.
    Requires DataForSEO for rich data; falls back to Google search without it.
    """
    result = CompetitorAnalysis(
        your_domain=your_domain,
        competitor_domain=competitor_domain,
    )

    if DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD:
        result.keyword_gaps = _keyword_gap(your_domain, competitor_domain)
        result.backlink_gaps = _backlink_gap(your_domain, competitor_domain)
        result.competitor_top_pages = _top_pages(competitor_domain)
        result.data_source = "dataforseo"
    else:
        result.competitor_top_pages = _estimate_competitor_content(competitor_domain)
        result.data_source = "google_search_estimate"
        result.note = (
            "DataForSEO credentials not configured — keyword gap and backlink gap "
            "analysis requires DataForSEO. Set DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD "
            "in .env for full competitor intelligence."
        )

    # ── Prioritise keyword gaps by opportunity ────────────────────────────────
    result.keyword_gaps.sort(
        key=lambda x: (x.opportunity == "high", x.search_volume or 0),
        reverse=True,
    )

    # ── Prioritise backlink gaps by domain rank ───────────────────────────────
    result.backlink_gaps.sort(key=lambda x: x.domain_rank, reverse=True)

    return result
