"""
Backlink discovery tool.
Strategy A (always available): Google search for resource pages / guest post opportunities
                                in the target niche.
Strategy B (optional):         DataForSEO Backlinks API for competitor backlink data.
"""
from __future__ import annotations

from urllib.parse import quote_plus, urlparse

import httpx
from bs4 import BeautifulSoup

from config import (
    DATAFORSEO_LOGIN,
    DATAFORSEO_PASSWORD,
    HEADERS,
    REQUEST_TIMEOUT,
)
from models import BacklinkOpportunities, BacklinkProspect

# ── Google search scraper (no API key) ───────────────────────────────────────

_SEARCH_URL = "https://www.google.com/search?q={q}&num=20&hl=en"

_OPPORTUNITY_QUERIES = [
    '"{niche}" "write for us"',
    '"{niche}" "guest post"',
    '"{niche}" "submit a guest post"',
    '"{niche}" "resources" OR "useful links" -site:{domain}',
    '"{niche}" "link roundup"',
    'intitle:"resources" "{niche}" -site:{domain}',
]

OUTREACH_TEMPLATE = """Subject: Guest Post / Link Opportunity — {niche}

Hi {{First Name}},

I came across {prospect_url} while researching {niche} and really enjoyed your content.

I'm reaching out because I've published a detailed guide on [{topic}] that I think your audience would find valuable. I'd love to contribute a guest post or, if that's not a fit right now, explore whether there's a natural place to mention it in one of your existing articles.

Would you be open to a quick chat?

Best,
[Your Name]
"""


def _google_search_results(query: str) -> list[str]:
    """Return a list of result URLs from a Google search (best-effort)."""
    url = _SEARCH_URL.format(q=quote_plus(query))
    try:
        r = httpx.get(url, headers={**HEADERS, "Accept-Language": "en-US,en;q=0.9"}, timeout=REQUEST_TIMEOUT)
        soup = BeautifulSoup(r.text, "lxml")
        links = []
        for a in soup.select("a[href]"):
            href = a["href"]
            if href.startswith("/url?q="):
                href = href[7:].split("&")[0]
            if href.startswith("http") and "google.com" not in href:
                links.append(href)
        return list(dict.fromkeys(links))[:20]
    except Exception:
        return []


def _classify_opportunity(url: str, query: str) -> str:
    if "guest" in query or "write for us" in query or "submit" in query:
        return "guest_post"
    if "resource" in query or "useful" in query or "links" in query:
        return "resource_page"
    if "roundup" in query:
        return "resource_page"
    return "mention"


def _extract_contact_hint(url: str) -> str:
    domain = urlparse(url).netloc
    return f"Try {domain}/contact or search '{domain} email' on Hunter.io"


# ── DataForSEO Backlinks (optional) ──────────────────────────────────────────

def _dfs_competitor_backlinks(competitor_domain: str) -> list[BacklinkProspect]:
    if not (DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD):
        return []
    endpoint = "https://api.dataforseo.com/v3/backlinks/backlinks/live"
    payload = [{"target": competitor_domain, "mode": "as_is", "limit": 20, "filters": [["dofollow", "=", True]]}]
    try:
        r = httpx.post(
            endpoint,
            auth=(DATAFORSEO_LOGIN, DATAFORSEO_PASSWORD),
            json=payload,
            timeout=30,
        )
        items = r.json().get("tasks", [{}])[0].get("result", [{}])[0].get("items", [])
        prospects = []
        for item in items:
            src = item.get("url_from", "")
            domain = urlparse(src).netloc
            prospects.append(BacklinkProspect(
                url=src,
                domain=domain,
                relevance_reason=f"Links to competitor {competitor_domain}",
                contact_hint=_extract_contact_hint(src),
                outreach_type="mention",
            ))
        return prospects
    except Exception:
        return []


# ── Public API ────────────────────────────────────────────────────────────────

def find_backlink_opportunities(
    domain: str,
    niche: str,
    competitor_domain: str | None = None,
) -> BacklinkOpportunities:
    """
    Find link-building prospects for *domain* in *niche*.
    Combines Google search prospecting + optional DataForSEO competitor analysis.
    """
    result = BacklinkOpportunities(target_domain=domain, niche=niche)
    seen_domains: set[str] = set()

    # Strategy A — search-based prospecting
    for query_tpl in _OPPORTUNITY_QUERIES:
        query = query_tpl.format(niche=niche, domain=domain)
        urls = _google_search_results(query)
        for url in urls:
            d = urlparse(url).netloc
            if d in seen_domains or d == domain:
                continue
            seen_domains.add(d)
            result.prospects.append(BacklinkProspect(
                url=url,
                domain=d,
                relevance_reason=f"Matched search: {query_tpl.split('{niche}')[0].strip()}",
                contact_hint=_extract_contact_hint(url),
                outreach_type=_classify_opportunity(url, query),
            ))
        if len(result.prospects) >= 25:
            break

    # Strategy B — competitor backlinks via DataForSEO
    if competitor_domain:
        comp_prospects = _dfs_competitor_backlinks(competitor_domain)
        for p in comp_prospects:
            if p.domain not in seen_domains:
                seen_domains.add(p.domain)
                result.prospects.append(p)

    result.prospects = result.prospects[:30]
    result.outreach_template = OUTREACH_TEMPLATE.format(
        niche=niche,
        prospect_url="[their URL]",
        topic=f"[your topic related to {niche}]",
    )
    return result
