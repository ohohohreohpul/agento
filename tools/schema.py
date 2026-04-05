"""
JSON-LD schema markup generator.
Supports: Article, FAQPage, HowTo, LocalBusiness, Product, BreadcrumbList, WebSite.
"""
from __future__ import annotations

import json
from models import SchemaMarkup


def _clean(d: dict) -> dict:
    """Remove None/empty values from a schema dict."""
    return {k: v for k, v in d.items() if v not in (None, "", [], {})}


# ── Schema builders ───────────────────────────────────────────────────────────

def build_article(
    headline: str,
    author_name: str,
    date_published: str,
    date_modified: str,
    url: str,
    image_url: str = "",
    description: str = "",
) -> dict:
    return _clean({
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": headline,
        "description": description,
        "image": image_url or None,
        "author": {"@type": "Person", "name": author_name},
        "datePublished": date_published,
        "dateModified": date_modified,
        "url": url,
    })


def build_faq(qa_pairs: list[dict]) -> dict:
    """qa_pairs: [{"question": "...", "answer": "..."}]"""
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": qa["question"],
                "acceptedAnswer": {"@type": "Answer", "text": qa["answer"]},
            }
            for qa in qa_pairs
        ],
    }


def build_howto(
    name: str,
    description: str,
    steps: list[str],
    total_time: str = "",
) -> dict:
    return _clean({
        "@context": "https://schema.org",
        "@type": "HowTo",
        "name": name,
        "description": description,
        "totalTime": total_time or None,
        "step": [
            {"@type": "HowToStep", "text": step, "position": i + 1}
            for i, step in enumerate(steps)
        ],
    })


def build_local_business(
    name: str,
    address: str,
    city: str,
    country: str,
    phone: str = "",
    url: str = "",
    business_type: str = "LocalBusiness",
) -> dict:
    return _clean({
        "@context": "https://schema.org",
        "@type": business_type,
        "name": name,
        "telephone": phone or None,
        "url": url or None,
        "address": {
            "@type": "PostalAddress",
            "streetAddress": address,
            "addressLocality": city,
            "addressCountry": country,
        },
    })


def build_product(
    name: str,
    description: str,
    price: str,
    currency: str,
    availability: str = "InStock",
    image_url: str = "",
    sku: str = "",
) -> dict:
    return _clean({
        "@context": "https://schema.org",
        "@type": "Product",
        "name": name,
        "description": description,
        "image": image_url or None,
        "sku": sku or None,
        "offers": {
            "@type": "Offer",
            "price": price,
            "priceCurrency": currency,
            "availability": f"https://schema.org/{availability}",
        },
    })


def build_breadcrumb(items: list[dict]) -> dict:
    """items: [{"name": "Home", "url": "https://..."}]"""
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": i + 1,
                "name": item["name"],
                "item": item["url"],
            }
            for i, item in enumerate(items)
        ],
    }


def build_website(name: str, url: str, search_url_template: str = "") -> dict:
    schema: dict = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": name,
        "url": url,
    }
    if search_url_template:
        schema["potentialAction"] = {
            "@type": "SearchAction",
            "target": {"@type": "EntryPoint", "urlTemplate": search_url_template},
            "query-input": "required name=search_term_string",
        }
    return schema


# ── Public API ────────────────────────────────────────────────────────────────

_BUILDERS = {
    "article": build_article,
    "faq": build_faq,
    "howto": build_howto,
    "local_business": build_local_business,
    "product": build_product,
    "breadcrumb": build_breadcrumb,
    "website": build_website,
}

_NOTES = {
    "article": "Place inside <head> or just before </body>. Update dateModified on each edit.",
    "faq": "Great for GEO/AEO — directly feeds AI answer engines. Each Q&A should be concise and self-contained.",
    "howto": "Eligible for rich results in Google Search and AI Overviews.",
    "local_business": "Add to every page of a local business site for consistent NAP data.",
    "product": "Enables price/availability rich results. Keep 'availability' updated.",
    "breadcrumb": "Helps both search engines and users understand site structure.",
    "website": "Add a sitelinks searchbox to encourage direct navigation from SERPs.",
}


def generate_schema(page_type: str, data: dict) -> SchemaMarkup:
    """
    Generate a JSON-LD schema block.
    page_type: one of article | faq | howto | local_business | product | breadcrumb | website
    data: keyword arguments for the matching builder function.
    """
    builder = _BUILDERS.get(page_type.lower())
    if not builder:
        supported = ", ".join(_BUILDERS.keys())
        return SchemaMarkup(
            page_type=page_type,
            json_ld="",
            implementation_note=f"Unknown page_type. Supported: {supported}",
        )

    try:
        schema_dict = builder(**data)
    except TypeError as e:
        return SchemaMarkup(
            page_type=page_type,
            json_ld="",
            implementation_note=f"Missing required field: {e}",
        )

    json_ld = (
        '<script type="application/ld+json">\n'
        + json.dumps(schema_dict, indent=2)
        + "\n</script>"
    )
    return SchemaMarkup(
        page_type=page_type,
        json_ld=json_ld,
        implementation_note=_NOTES.get(page_type.lower(), ""),
    )
