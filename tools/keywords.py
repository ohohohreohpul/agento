"""
Keyword research tool.
Tier 1 (always free): Google Autocomplete + "People Also Ask" scraping.
Tier 2 (optional):    DataForSEO API for volume, difficulty, CPC.
Tier 3 (optional):    SerpApi for live SERP data.
"""
from __future__ import annotations

import json
from urllib.parse import quote_plus

import httpx

from config import (
    DATAFORSEO_LOGIN,
    DATAFORSEO_PASSWORD,
    HEADERS,
    REQUEST_TIMEOUT,
    SERPAPI_KEY,
)
from models import KeywordResearchResult, KeywordSuggestion

# ── Google Autocomplete (no key required) ─────────────────────────────────────

def _google_autocomplete(query: str) -> list[str]:
    url = (
        "https://suggestqueries.google.com/complete/search"
        f"?q={quote_plus(query)}&client=firefox&hl=en"
    )
    try:
        r = httpx.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        data = r.json()
        return data[1] if len(data) > 1 else []
    except Exception:
        return []


def _question_variants(seed: str) -> list[str]:
    prefixes = ["how to", "what is", "why is", "best", "how does", "when to", "vs"]
    results = []
    for p in prefixes:
        results.extend(_google_autocomplete(f"{p} {seed}"))
    return list(dict.fromkeys(results))   # deduplicate, preserve order


# ── DataForSEO (optional) ─────────────────────────────────────────────────────

def _dataforseo_keywords(seed: str) -> list[KeywordSuggestion]:
    if not (DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD):
        return []
    endpoint = "https://api.dataforseo.com/v3/dataforseo_labs/google/keyword_suggestions/live"
    payload = [{"keyword": seed, "language_code": "en", "location_code": 2840, "limit": 30}]
    try:
        r = httpx.post(
            endpoint,
            auth=(DATAFORSEO_LOGIN, DATAFORSEO_PASSWORD),
            json=payload,
            timeout=30,
        )
        data = r.json()
        items = (
            data.get("tasks", [{}])[0]
            .get("result", [{}])[0]
            .get("items", [])
        )
        suggestions = []
        for item in items:
            kd = item.get("keyword_info", {})
            suggestions.append(KeywordSuggestion(
                keyword=item.get("keyword", ""),
                search_volume=kd.get("search_volume"),
                competition=_competition_label(kd.get("competition")),
                cpc_usd=kd.get("cpc"),
                keyword_difficulty=item.get("keyword_properties", {}).get("keyword_difficulty"),
            ))
        return suggestions
    except Exception:
        return []


def _competition_label(val: float | None) -> str | None:
    if val is None:
        return None
    if val < 0.33:
        return "low"
    if val < 0.66:
        return "medium"
    return "high"


# ── SerpApi SERP check (optional) ─────────────────────────────────────────────

def check_serp_rank(keyword: str, domain: str) -> dict:
    """Return position of domain for keyword (0 = not in top 10)."""
    if not SERPAPI_KEY:
        return {"keyword": keyword, "domain": domain, "position": None, "source": "no_serpapi_key"}
    try:
        r = httpx.get(
            "https://serpapi.com/search",
            params={"q": keyword, "api_key": SERPAPI_KEY, "num": 10},
            timeout=REQUEST_TIMEOUT,
        )
        results = r.json().get("organic_results", [])
        for i, res in enumerate(results, start=1):
            if domain.lower() in res.get("link", "").lower():
                return {"keyword": keyword, "domain": domain, "position": i, "source": "serpapi"}
        return {"keyword": keyword, "domain": domain, "position": 0, "source": "serpapi"}
    except Exception as e:
        return {"keyword": keyword, "domain": domain, "position": None, "error": str(e)}


# ── Public API ─────────────────────────────────────────────────────────────────

def research_keywords(seed: str, domain: str | None = None) -> KeywordResearchResult:
    """
    Research keywords for a seed term.
    Always returns Google Autocomplete suggestions.
    Adds DataForSEO data (volume/difficulty) if credentials present.
    """
    result = KeywordResearchResult(seed_keyword=seed, domain=domain)

    # Try DataForSEO first for rich data
    dfs = _dataforseo_keywords(seed)
    if dfs:
        result.suggestions = dfs
        result.source = "dataforseo"
    else:
        # Fall back to autocomplete
        raw = _google_autocomplete(seed)
        result.suggestions = [KeywordSuggestion(keyword=kw) for kw in raw[:20]]
        result.source = "google_autocomplete"

    # Question / long-tail variants
    questions = _question_variants(seed)
    result.questions = [q for q in questions if "?" in q or q.lower().startswith(("how", "what", "why", "when"))][:15]
    result.long_tail = [q for q in questions if len(q.split()) >= 4][:15]

    return result
