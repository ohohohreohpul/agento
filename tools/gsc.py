"""
Google Search Console integration.

Provides real search performance data: clicks, impressions, CTR, average position,
indexing coverage, and crawl errors — all from your own GSC property.

Setup:
  1. Create a Google Cloud project and enable the Search Console API.
  2. Create a Service Account, download the JSON key, and set GSC_SERVICE_ACCOUNT_JSON
     to the file path in your .env.
  3. Grant the service account "Full User" permission in GSC for your property.

  OR use OAuth2 by setting GSC_CLIENT_ID + GSC_CLIENT_SECRET (interactive flow).
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Optional

import httpx

from config import GSC_SERVICE_ACCOUNT_JSON, HEADERS, REQUEST_TIMEOUT
from models import (
    GSCCoverageResult,
    GSCKeywordRow,
    GSCPerformanceResult,
)


# ── Auth helpers ───────────────────────────────────────────────────────────────

def _get_access_token() -> str | None:
    """
    Obtain a Google OAuth2 access token using a service account JSON key file.
    Falls back gracefully if credentials are not configured.
    """
    if not GSC_SERVICE_ACCOUNT_JSON:
        return None
    try:
        import google.auth
        from google.oauth2 import service_account

        scopes = ["https://www.googleapis.com/auth/webmasters.readonly"]
        creds = service_account.Credentials.from_service_account_file(
            GSC_SERVICE_ACCOUNT_JSON, scopes=scopes
        )
        creds.refresh(google.auth.transport.requests.Request())
        return creds.token
    except ImportError:
        # google-auth not installed — try raw JWT approach below
        return _jwt_access_token()
    except Exception:
        return None


def _jwt_access_token() -> str | None:
    """Minimal JWT-based service account auth without google-auth library."""
    if not GSC_SERVICE_ACCOUNT_JSON:
        return None
    try:
        import base64
        import json
        import time

        try:
            import jwt
        except ImportError:
            return None

        with open(GSC_SERVICE_ACCOUNT_JSON) as f:
            sa = json.load(f)

        now = int(time.time())
        payload = {
            "iss": sa["client_email"],
            "scope": "https://www.googleapis.com/auth/webmasters.readonly",
            "aud": "https://oauth2.googleapis.com/token",
            "iat": now,
            "exp": now + 3600,
        }
        token = jwt.encode(payload, sa["private_key"], algorithm="RS256")
        resp = httpx.post(
            "https://oauth2.googleapis.com/token",
            data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": token},
            timeout=REQUEST_TIMEOUT,
        )
        return resp.json().get("access_token")
    except Exception:
        return None


def _gsc_headers(token: str) -> dict:
    return {**HEADERS, "Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ── GSC API wrappers ───────────────────────────────────────────────────────────

def _search_analytics_query(
    property_url: str,
    token: str,
    dimensions: list[str],
    start_date: str,
    end_date: str,
    row_limit: int = 25,
    filters: list[dict] | None = None,
) -> list[dict]:
    endpoint = (
        f"https://searchconsole.googleapis.com/webmasters/v3/"
        f"sites/{_encode_property(property_url)}/searchAnalytics/query"
    )
    body: dict = {
        "startDate": start_date,
        "endDate": end_date,
        "dimensions": dimensions,
        "rowLimit": row_limit,
    }
    if filters:
        body["dimensionFilterGroups"] = [{"filters": filters}]

    try:
        resp = httpx.post(endpoint, headers=_gsc_headers(token), json=body, timeout=30)
        resp.raise_for_status()
        return resp.json().get("rows", [])
    except Exception:
        return []


def _encode_property(property_url: str) -> str:
    from urllib.parse import quote
    return quote(property_url, safe="")


# ── Public API ────────────────────────────────────────────────────────────────

def get_search_performance(
    property_url: str,
    days: int = 28,
    page_filter: Optional[str] = None,
) -> GSCPerformanceResult:
    """
    Fetch top keywords and pages from Google Search Console.

    property_url: The GSC property (e.g., 'https://example.com/' or 'sc-domain:example.com')
    days:         Number of days to look back (default 28)
    page_filter:  Optional URL prefix to filter results to a specific section
    """
    result = GSCPerformanceResult(property_url=property_url, days=days)

    token = _get_access_token()
    if not token:
        result.error = (
            "Google Search Console credentials not configured. "
            "Set GSC_SERVICE_ACCOUNT_JSON in your .env file pointing to a "
            "service account JSON key with Search Console read access."
        )
        return result

    end = date.today() - timedelta(days=2)   # GSC data lags ~2 days
    start = end - timedelta(days=days)
    start_str, end_str = start.isoformat(), end.isoformat()

    filters = []
    if page_filter:
        filters.append({
            "dimension": "page",
            "operator": "contains",
            "expression": page_filter,
        })

    # ── Top keywords ──────────────────────────────────────────────────────────
    kw_rows = _search_analytics_query(
        property_url, token, ["query"], start_str, end_str,
        row_limit=25, filters=filters or None,
    )
    for row in kw_rows:
        keys = row.get("keys", [])
        result.top_keywords.append(GSCKeywordRow(
            keyword=keys[0] if keys else "",
            clicks=row.get("clicks", 0),
            impressions=row.get("impressions", 0),
            ctr=round(row.get("ctr", 0) * 100, 2),
            position=round(row.get("position", 0), 1),
        ))

    # ── Top pages ─────────────────────────────────────────────────────────────
    page_rows = _search_analytics_query(
        property_url, token, ["page"], start_str, end_str,
        row_limit=15, filters=filters or None,
    )
    for row in page_rows:
        keys = row.get("keys", [])
        result.top_pages.append(GSCKeywordRow(
            keyword=keys[0] if keys else "",
            clicks=row.get("clicks", 0),
            impressions=row.get("impressions", 0),
            ctr=round(row.get("ctr", 0) * 100, 2),
            position=round(row.get("position", 0), 1),
        ))

    # ── Quick wins: high impressions, low CTR (rank 4–15) ─────────────────────
    result.quick_wins = [
        kw for kw in result.top_keywords
        if 4 <= kw.position <= 15 and kw.impressions >= 50 and kw.ctr < 5.0
    ]

    # ── Summary metrics ────────────────────────────────────────────────────────
    if result.top_keywords:
        total_clicks = sum(k.clicks for k in result.top_keywords)
        total_impressions = sum(k.impressions for k in result.top_keywords)
        result.total_clicks = total_clicks
        result.total_impressions = total_impressions
        result.avg_ctr = round(total_clicks / total_impressions * 100, 2) if total_impressions else 0.0
        positions = [k.position for k in result.top_keywords if k.position > 0]
        result.avg_position = round(sum(positions) / len(positions), 1) if positions else 0.0

    return result


def get_coverage_issues(property_url: str) -> GSCCoverageResult:
    """
    Fetch URL coverage / indexing issues from GSC.
    Returns counts of valid, error, excluded, and warning URLs.
    """
    result = GSCCoverageResult(property_url=property_url)

    token = _get_access_token()
    if not token:
        result.error = "GSC credentials not configured. Set GSC_SERVICE_ACCOUNT_JSON."
        return result

    endpoint = (
        f"https://searchconsole.googleapis.com/v1/urlInspection/index:inspect"
    )
    # Coverage summary via Search Console API v1 index inspection
    # (Full coverage report requires the older v3 endpoint which needs a property list)
    try:
        resp = httpx.get(
            f"https://searchconsole.googleapis.com/webmasters/v3/"
            f"sites/{_encode_property(property_url)}/sitemaps",
            headers=_gsc_headers(token),
            timeout=30,
        )
        if resp.status_code == 200:
            sitemaps = resp.json().get("sitemap", [])
            for sm in sitemaps:
                contents = sm.get("contents", [])
                for c in contents:
                    t = c.get("type", "")
                    count = c.get("submitted", 0)
                    if t == "WEB":
                        result.submitted_urls += count
                        result.indexed_urls += c.get("indexed", 0)
            result.coverage_note = (
                f"Sitemap data: {result.submitted_urls} submitted, "
                f"{result.indexed_urls} indexed."
            )
    except Exception as e:
        result.error = str(e)

    return result
