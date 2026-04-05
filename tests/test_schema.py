"""Tests for tools/schema.py — pure logic, no network."""
import sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.schema import generate_schema


def _parse_ld(markup: str) -> dict:
    """Extract and parse the JSON inside the <script> block."""
    start = markup.index("{")
    end = markup.rindex("}") + 1
    return json.loads(markup[start:end])


def test_faq_schema():
    s = generate_schema("faq", {
        "qa_pairs": [
            {"question": "What is GEO?", "answer": "GEO stands for Generative Engine Optimization."},
            {"question": "How long does SEO take?", "answer": "3 to 6 months typically."},
        ]
    })
    assert s.page_type == "faq"
    assert '<script type="application/ld+json">' in s.json_ld
    data = _parse_ld(s.json_ld)
    assert data["@type"] == "FAQPage"
    assert len(data["mainEntity"]) == 2
    assert data["mainEntity"][0]["name"] == "What is GEO?"
    assert "GEO stands for" in data["mainEntity"][0]["acceptedAnswer"]["text"]


def test_article_schema():
    s = generate_schema("article", {
        "headline": "Python SEO Guide 2026",
        "author_name": "Jane Doe",
        "date_published": "2026-01-01",
        "date_modified": "2026-04-05",
        "url": "https://example.com/python-seo",
        "description": "Learn how to use Python for SEO.",
    })
    data = _parse_ld(s.json_ld)
    assert data["@type"] == "Article"
    assert data["headline"] == "Python SEO Guide 2026"
    assert data["author"]["name"] == "Jane Doe"
    assert data["datePublished"] == "2026-01-01"
    assert data["description"] == "Learn how to use Python for SEO."


def test_howto_schema():
    s = generate_schema("howto", {
        "name": "How to Optimise a Blog Post",
        "description": "Step-by-step SEO optimisation.",
        "steps": ["Research keywords", "Write the draft", "Add schema markup"],
        "total_time": "PT2H",
    })
    data = _parse_ld(s.json_ld)
    assert data["@type"] == "HowTo"
    assert len(data["step"]) == 3
    assert data["step"][0]["text"] == "Research keywords"
    assert data["step"][0]["position"] == 1
    assert data["totalTime"] == "PT2H"


def test_local_business_schema():
    s = generate_schema("local_business", {
        "name": "Acme SEO Agency",
        "address": "123 Main St",
        "city": "London",
        "country": "GB",
        "phone": "+44 20 1234 5678",
        "url": "https://acmeseo.co.uk",
    })
    data = _parse_ld(s.json_ld)
    assert data["@type"] == "LocalBusiness"
    assert data["address"]["addressLocality"] == "London"
    assert data["telephone"] == "+44 20 1234 5678"


def test_product_schema():
    s = generate_schema("product", {
        "name": "SEO Pro Tool",
        "description": "AI-powered SEO automation.",
        "price": "99.00",
        "currency": "USD",
        "availability": "InStock",
        "sku": "SEO-001",
    })
    data = _parse_ld(s.json_ld)
    assert data["@type"] == "Product"
    assert data["offers"]["price"] == "99.00"
    assert data["offers"]["priceCurrency"] == "USD"
    assert "InStock" in data["offers"]["availability"]


def test_breadcrumb_schema():
    s = generate_schema("breadcrumb", {
        "items": [
            {"name": "Home", "url": "https://example.com"},
            {"name": "Blog", "url": "https://example.com/blog"},
            {"name": "SEO Guide", "url": "https://example.com/blog/seo"},
        ]
    })
    data = _parse_ld(s.json_ld)
    assert data["@type"] == "BreadcrumbList"
    assert len(data["itemListElement"]) == 3
    assert data["itemListElement"][2]["position"] == 3
    assert data["itemListElement"][0]["name"] == "Home"


def test_website_schema():
    s = generate_schema("website", {
        "name": "Example",
        "url": "https://example.com",
        "search_url_template": "https://example.com/search?q={search_term_string}",
    })
    data = _parse_ld(s.json_ld)
    assert data["@type"] == "WebSite"
    assert "potentialAction" in data
    assert data["potentialAction"]["@type"] == "SearchAction"


def test_invalid_type_returns_empty():
    s = generate_schema("nonsense", {})
    assert s.json_ld == ""
    assert "Supported" in s.implementation_note


def test_missing_required_field():
    s = generate_schema("article", {"headline": "Only a title"})
    assert s.json_ld == ""
    assert "Missing required field" in s.implementation_note


def test_none_values_cleaned():
    s = generate_schema("article", {
        "headline": "Test",
        "author_name": "Bob",
        "date_published": "2026-01-01",
        "date_modified": "2026-04-01",
        "url": "https://example.com",
        "image_url": "",     # empty → should be omitted
        "description": "",   # empty → should be omitted
    })
    data = _parse_ld(s.json_ld)
    assert "image" not in data      # empty stripped
    assert "description" not in data


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
