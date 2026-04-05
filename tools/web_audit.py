"""
Technical SEO auditor — fetches a URL and extracts all on-page signals.
Works without any API key.
"""
from __future__ import annotations

import json
import time
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from config import HEADERS, REQUEST_TIMEOUT
from models import (
    HeadingStructure,
    ImageInfo,
    LinkInfo,
    MetaInfo,
    SchemaFound,
    TechnicalAudit,
)


def audit_url(url: str) -> TechnicalAudit:
    """Fetch a URL and return a full technical SEO audit."""
    audit = TechnicalAudit(url=url)
    audit.https = url.startswith("https://")

    t0 = time.monotonic()
    try:
        resp = httpx.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT, follow_redirects=True)
    except Exception as exc:
        audit.issues.append(f"Fetch failed: {exc}")
        return audit

    audit.load_time_ms = round((time.monotonic() - t0) * 1000, 1)
    audit.status_code = resp.status_code
    audit.page_size_bytes = len(resp.content)

    if resp.status_code != 200:
        audit.issues.append(f"Non-200 status code: {resp.status_code}")
        return audit

    soup = BeautifulSoup(resp.text, "lxml")

    # ── Meta info ──────────────────────────────────────────────────────────────
    meta = MetaInfo()

    title_tag = soup.find("title")
    if title_tag:
        meta.title = title_tag.get_text(strip=True)
        meta.title_length = len(meta.title)
    else:
        audit.issues.append("Missing <title> tag")

    desc_tag = soup.find("meta", attrs={"name": "description"})
    if desc_tag:
        meta.meta_description = desc_tag.get("content", "")
        meta.meta_description_length = len(meta.meta_description)
    else:
        audit.issues.append("Missing meta description")

    canonical_tag = soup.find("link", rel="canonical")
    if canonical_tag:
        meta.canonical = canonical_tag.get("href", "")

    robots_tag = soup.find("meta", attrs={"name": "robots"})
    if robots_tag:
        meta.robots_meta = robots_tag.get("content", "")

    for prop, field in [
        ("og:title", "og_title"),
        ("og:description", "og_description"),
        ("og:image", "og_image"),
    ]:
        tag = soup.find("meta", property=prop)
        if tag:
            setattr(meta, field, tag.get("content", ""))

    audit.meta = meta

    # ── Title / description length checks ─────────────────────────────────────
    if meta.title_length and meta.title_length < 30:
        audit.issues.append(f"Title too short ({meta.title_length} chars, aim 50–60)")
    elif meta.title_length > 60:
        audit.issues.append(f"Title too long ({meta.title_length} chars, aim 50–60)")
    else:
        audit.passes.append("Title length OK")

    if meta.meta_description_length and meta.meta_description_length < 70:
        audit.issues.append(f"Meta description too short ({meta.meta_description_length} chars)")
    elif meta.meta_description_length > 160:
        audit.issues.append(f"Meta description too long ({meta.meta_description_length} chars)")
    elif meta.meta_description_length:
        audit.passes.append("Meta description length OK")

    # ── Headings ───────────────────────────────────────────────────────────────
    headings = HeadingStructure(
        h1=[t.get_text(strip=True) for t in soup.find_all("h1")],
        h2=[t.get_text(strip=True) for t in soup.find_all("h2")],
        h3=[t.get_text(strip=True) for t in soup.find_all("h3")],
    )
    audit.headings = headings

    if len(headings.h1) == 0:
        audit.issues.append("No H1 tag found")
    elif len(headings.h1) > 1:
        audit.issues.append(f"Multiple H1 tags ({len(headings.h1)}), use exactly one")
    else:
        audit.passes.append("Single H1 tag present")

    # ── Images ─────────────────────────────────────────────────────────────────
    images = []
    for img in soup.find_all("img"):
        alt = img.get("alt", None)
        images.append(ImageInfo(
            src=img.get("src", ""),
            alt=alt or "",
            missing_alt=(alt is None or alt.strip() == ""),
        ))
    audit.images = images
    audit.images_missing_alt = sum(1 for i in images if i.missing_alt)
    if audit.images_missing_alt:
        audit.issues.append(
            f"{audit.images_missing_alt} image(s) missing alt text"
        )
    elif images:
        audit.passes.append("All images have alt text")

    # ── Links ──────────────────────────────────────────────────────────────────
    base_domain = urlparse(url).netloc
    internal, external, candidates = 0, 0, []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith("#") or href.startswith("javascript"):
            continue
        absolute = urljoin(url, href)
        if urlparse(absolute).netloc == base_domain:
            internal += 1
        else:
            external += 1
        if href.startswith("http") and len(candidates) < 5:
            candidates.append(absolute)

    audit.links = LinkInfo(
        internal_links=internal,
        external_links=external,
        broken_link_candidates=candidates,
    )

    # ── Structured data / schema ───────────────────────────────────────────────
    schema_types, raw_schemas = [], []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            schemas = data if isinstance(data, list) else [data]
            for s in schemas:
                t = s.get("@type", "Unknown")
                schema_types.append(t)
                raw_schemas.append(json.dumps(s, indent=2)[:400])
        except (json.JSONDecodeError, AttributeError):
            pass
    audit.schema_markup = SchemaFound(types_found=schema_types, raw_schemas=raw_schemas)

    if not schema_types:
        audit.issues.append("No structured data (schema.org JSON-LD) found")
    else:
        audit.passes.append(f"Schema markup present: {', '.join(schema_types)}")

    # ── Viewport meta ─────────────────────────────────────────────────────────
    viewport = soup.find("meta", attrs={"name": "viewport"})
    audit.has_viewport_meta = viewport is not None
    if not audit.has_viewport_meta:
        audit.issues.append("Missing viewport meta tag (mobile unfriendly)")
    else:
        audit.passes.append("Viewport meta present")

    # ── Word count ────────────────────────────────────────────────────────────
    body = soup.find("body")
    if body:
        text = body.get_text(separator=" ", strip=True)
        audit.word_count = len(text.split())
    if audit.word_count < 300:
        audit.issues.append(f"Thin content: {audit.word_count} words (aim ≥ 600)")
    else:
        audit.passes.append(f"Word count OK: {audit.word_count} words")

    # ── HTTPS ─────────────────────────────────────────────────────────────────
    if not audit.https:
        audit.issues.append("Page served over HTTP (not HTTPS)")
    else:
        audit.passes.append("HTTPS enabled")

    return audit


def extract_page_text(url: str) -> str:
    """Return clean visible text from a URL (used by GEO optimizer)."""
    try:
        resp = httpx.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT, follow_redirects=True)
        resp.raise_for_status()
    except Exception:
        return ""
    soup = BeautifulSoup(resp.text, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)[:8000]
