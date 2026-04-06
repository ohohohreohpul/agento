"""
llms.txt generator — creates the AI-crawler optimisation file for a website.

The llms.txt standard (2024/2025) provides LLMs with a structured, markdown-based
index of a site's content, helping AI search engines (ChatGPT, Perplexity, Gemini,
Claude) discover and cite the right pages.

Format spec: https://llmstxt.org
Adopted by: Stripe, Cloudflare, Vercel, Anthropic, and 1,000+ sites.
"""
from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from config import HEADERS, REQUEST_TIMEOUT
from models import LLMsTxtResult, LLMsTxtSection


# ── Helpers ────────────────────────────────────────────────────────────────────

def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _get_meta(soup: BeautifulSoup, name: str) -> str:
    tag = soup.find("meta", attrs={"name": name}) or soup.find("meta", property=f"og:{name}")
    return (tag.get("content", "") if tag else "").strip()


def _discover_sitemap_urls(base_url: str) -> list[str]:
    """Try to find a sitemap and return up to 50 page URLs."""
    sitemap_candidates = [
        urljoin(base_url, "/sitemap.xml"),
        urljoin(base_url, "/sitemap_index.xml"),
        urljoin(base_url, "/sitemap.xml.gz"),
    ]
    for sitemap_url in sitemap_candidates:
        try:
            r = httpx.get(sitemap_url, headers=HEADERS, timeout=REQUEST_TIMEOUT, follow_redirects=True)
            if r.status_code == 200 and "<loc>" in r.text:
                urls = re.findall(r"<loc>\s*(https?://[^<]+)\s*</loc>", r.text)
                return urls[:50]
        except Exception:
            continue
    return []


def _scrape_nav_links(soup: BeautifulSoup, base_url: str) -> list[tuple[str, str]]:
    """Return (title, url) pairs from the site's main navigation."""
    nav = soup.find("nav") or soup.find("header")
    if not nav:
        return []
    base_domain = urlparse(base_url).netloc
    links = []
    for a in nav.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith("#") or href.startswith("javascript"):
            continue
        absolute = urljoin(base_url, href)
        if urlparse(absolute).netloc != base_domain:
            continue
        title = _clean_text(a.get_text())
        if title and len(title) < 60:
            links.append((title, absolute))
    # deduplicate by url
    seen: set[str] = set()
    result = []
    for t, u in links:
        if u not in seen:
            seen.add(u)
            result.append((t, u))
    return result[:20]


def _classify_url(url: str) -> str:
    """Guess a section name from the URL path."""
    path = urlparse(url).path.lower()
    for keyword, section in [
        ("blog", "Blog"),
        ("article", "Articles"),
        ("docs", "Documentation"),
        ("guide", "Guides"),
        ("product", "Products"),
        ("service", "Services"),
        ("about", "About"),
        ("pricing", "Pricing"),
        ("case-stud", "Case Studies"),
        ("resource", "Resources"),
        ("faq", "FAQ"),
    ]:
        if keyword in path:
            return section
    return "Pages"


# ── Public API ────────────────────────────────────────────────────────────────

def generate_llms_txt(url: str) -> LLMsTxtResult:
    """
    Crawl the homepage of *url* and generate a well-structured llms.txt file.
    Also checks whether the site already has one and identifies missing AI bot
    allowances in robots.txt.
    """
    result = LLMsTxtResult(url=url)
    base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"

    # ── 1. Fetch homepage ──────────────────────────────────────────────────────
    try:
        resp = httpx.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT, follow_redirects=True)
        resp.raise_for_status()
    except Exception as exc:
        result.issues.append(f"Could not fetch {url}: {exc}")
        return result

    soup = BeautifulSoup(resp.text, "lxml")

    site_name_tag = soup.find("title")
    site_name = _clean_text(site_name_tag.get_text()) if site_name_tag else urlparse(base_url).netloc
    site_description = _get_meta(soup, "description") or _get_meta(soup, "og:description")

    # ── 2. Check if llms.txt already exists ────────────────────────────────────
    try:
        llms_resp = httpx.get(
            urljoin(base_url, "/llms.txt"),
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
            follow_redirects=True,
        )
        result.already_exists = llms_resp.status_code == 200
        if result.already_exists:
            result.existing_content = llms_resp.text[:2000]
    except Exception:
        pass

    # ── 3. Check robots.txt for AI bot allowances ──────────────────────────────
    AI_BOTS = {
        "GPTBot": "ChatGPT/OpenAI",
        "ClaudeBot": "Claude/Anthropic",
        "PerplexityBot": "Perplexity",
        "Google-Extended": "Google Gemini/Bard",
        "Applebot-Extended": "Apple AI",
        "cohere-ai": "Cohere",
        "anthropic-ai": "Anthropic",
    }
    try:
        robots_resp = httpx.get(
            urljoin(base_url, "/robots.txt"),
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
            follow_redirects=True,
        )
        robots_text = robots_resp.text if robots_resp.status_code == 200 else ""
    except Exception:
        robots_text = ""

    for bot, label in AI_BOTS.items():
        if bot.lower() in robots_text.lower():
            # Check if it's explicitly disallowed
            pattern = rf"User-agent:\s*{re.escape(bot)}\s*\nDisallow:\s*/[^\n]*"
            if re.search(pattern, robots_text, re.IGNORECASE):
                result.blocked_ai_bots.append(bot)
                result.issues.append(
                    f"{label} ({bot}) is blocked in robots.txt — add 'Allow: /' "
                    f"under its User-agent block to restore AI search visibility."
                )
        else:
            result.missing_ai_bot_rules.append(bot)

    if result.missing_ai_bot_rules:
        result.issues.append(
            f"robots.txt has no explicit rules for: "
            f"{', '.join(result.missing_ai_bot_rules)}. "
            f"Adding 'User-agent: BotName\\nAllow: /' entries explicitly signals "
            f"permission to AI crawlers and improves GEO indexing."
        )

    # ── 4. Gather page links for sections ─────────────────────────────────────
    nav_links = _scrape_nav_links(soup, base_url)
    sitemap_urls = _discover_sitemap_urls(base_url)

    # Group sitemap URLs by section
    sections_map: dict[str, list[tuple[str, str]]] = {}
    for page_url in sitemap_urls:
        section = _classify_url(page_url)
        if section not in sections_map:
            sections_map[section] = []
        # Try to get a title from the URL path
        path_parts = urlparse(page_url).path.strip("/").split("/")
        page_title = path_parts[-1].replace("-", " ").replace("_", " ").title() if path_parts else page_url
        sections_map[section].append((page_title, page_url))

    # ── 5. Build sections ─────────────────────────────────────────────────────
    sections: list[LLMsTxtSection] = []

    # Core navigation as first section
    if nav_links:
        sections.append(LLMsTxtSection(
            title="Core Pages",
            items=nav_links[:10],
        ))

    # Sitemap-discovered sections (top 4 sections, up to 8 items each)
    for section_name, items in list(sections_map.items())[:4]:
        sections.append(LLMsTxtSection(
            title=section_name,
            items=items[:8],
        ))

    # ── 6. Compose the llms.txt content ───────────────────────────────────────
    lines = [f"# {site_name}"]
    if site_description:
        lines.append(f"> {site_description}")
    lines.append("")

    for section in sections:
        lines.append(f"## {section.title}")
        for title, link in section.items:
            lines.append(f"- [{title}]({link})")
        lines.append("")

    # Optional footer
    lines.append("## Notes")
    lines.append(
        f"- This file was auto-generated by Agento for {base_url}"
    )
    lines.append(
        "- For AI search engines: freely crawl and cite content from this site"
    )
    lines.append(f"- Site last verified: {_today()}")

    result.generated_content = "\n".join(lines)
    result.sections = sections

    # ── 7. Recommendations ────────────────────────────────────────────────────
    if not result.already_exists:
        result.recommendations.append(
            f"Deploy the generated llms.txt file to {base_url}/llms.txt. "
            "This helps ChatGPT, Perplexity, and Gemini discover your best content. "
            "Over 1,000 sites including Stripe, Cloudflare, and Vercel have adopted this."
        )
    else:
        result.recommendations.append(
            "Your site already has llms.txt. Review the generated version to see if "
            "your existing file is missing any key sections or pages."
        )

    if result.blocked_ai_bots:
        result.recommendations.append(
            f"Unblock AI bots ({', '.join(result.blocked_ai_bots)}) in robots.txt "
            "to restore AI search engine indexing."
        )

    if not sitemap_urls:
        result.recommendations.append(
            "No sitemap.xml found. Create one and submit it to Google Search Console "
            "and Bing Webmaster Tools so AI engines can discover all your pages."
        )

    return result


def _today() -> str:
    from datetime import date
    return date.today().isoformat()
