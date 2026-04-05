"""Tests for tools/geo_optimizer.py — pure logic, no network."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.geo_optimizer import analyze_for_geo

URL = "https://example.com/test"


WELL_OPTIMISED = """
## What is Python?

Python is a high-level, interpreted programming language known for its simplicity.
It was created by Guido van Rossum in 1991 and has grown to be one of the most
popular languages in the world.

## How does Python work?

Python executes code line by line using an interpreter rather than a compiler.

## Why use Python for SEO?

Python is fast, readable, and has excellent libraries for web scraping and data analysis.

## Frequently Asked Questions

Q: Is Python free to use?
A: Yes, Python is completely open-source and free.

Q: What is Python used for in 2026?
A: Python is used for AI, data science, web scraping, and automation.

Steps to get started with Python SEO:

1. Install Python 3.11+ from python.org
2. Install httpx and BeautifulSoup
3. Write your first scraper
4. Automate your audit workflow

Key resources: https://python.org https://pypi.org https://docs.python.org

By Jane Doe, Senior SEO Engineer — Updated April 2026

<script type="application/ld+json">{"@context":"https://schema.org","@type":"Article"}</script>
"""

THIN_CONTENT = "We sell products. Buy now. Contact us. Great deals."


def test_well_optimised_scores_high():
    a = analyze_for_geo(URL, WELL_OPTIMISED)
    assert a.ai_readiness_score >= 70, f"Score too low: {a.ai_readiness_score}"
    assert a.has_faq_section
    assert a.has_direct_answers
    assert a.has_author_info
    assert a.has_schema_markup
    assert len(a.recommended_schemas) >= 1


def test_thin_content_scores_low():
    a = analyze_for_geo(URL, THIN_CONTENT)
    assert a.ai_readiness_score < 20, f"Score too high for thin content: {a.ai_readiness_score}"
    assert len(a.issues) >= 5


def test_no_faq_triggers_issue():
    text = "Python is great. It was created in 1991."
    a = analyze_for_geo(URL, text)
    categories = [i.category for i in a.issues]
    descs = [i.description for i in a.issues]
    assert any("faq" in d.lower() for d in descs)


def test_faq_detected():
    text = "## Frequently Asked Questions\nQ: What is SEO?\nA: Search Engine Optimization."
    a = analyze_for_geo(URL, text)
    assert a.has_faq_section


def test_direct_answer_in_intro():
    text = "Python is a high-level programming language. " * 20
    a = analyze_for_geo(URL, text)
    assert a.has_direct_answers


def test_missing_direct_answer():
    text = "Welcome to our amazing page about Python! " * 20
    a = analyze_for_geo(URL, text)
    assert not a.has_direct_answers
    descs = [i.description for i in a.issues]
    assert any("direct answer" in d.lower() for d in descs)


def test_author_detected():
    text = "Python is great. " * 30 + "\nBy John Smith, Developer."
    a = analyze_for_geo(URL, text)
    assert a.has_author_info


def test_freshness_with_recent_year():
    text = "This guide was updated in 2026. " * 20
    a = analyze_for_geo(URL, text)
    assert "2026" in a.content_freshness


def test_freshness_without_year():
    text = "This is a guide about Python. " * 20
    a = analyze_for_geo(URL, text)
    assert "No year reference" in a.content_freshness
    descs = [i.description for i in a.issues]
    assert any("outdated" in d.lower() for d in descs)


def test_schema_markup_detected():
    text = 'Content here. <script type="application/ld+json">{"@type":"Article"}</script>'
    a = analyze_for_geo(URL, text)
    assert a.has_schema_markup


def test_missing_schema_is_critical():
    text = "Just plain content. " * 30
    a = analyze_for_geo(URL, text)
    assert not a.has_schema_markup
    critical = [i for i in a.issues if i.severity == "critical"]
    assert any("schema" in i.description.lower() or "structured" in i.description.lower()
               for i in critical)


def test_external_citations_count():
    few = "Content. " * 30
    a1 = analyze_for_geo(URL, few)
    has_citation_issue = any("citation" in i.category for i in a1.issues)
    assert has_citation_issue

    many = "Content. https://a.com https://b.com https://c.com https://d.com " * 5
    a2 = analyze_for_geo(URL, many)
    no_citation_issue = all("citation" not in i.category for i in a2.issues)
    assert no_citation_issue


def test_recommended_schemas_populated():
    a = analyze_for_geo(URL, WELL_OPTIMISED)
    assert isinstance(a.recommended_schemas, list)
    assert len(a.recommended_schemas) > 0


def test_score_capped_at_100():
    a = analyze_for_geo(URL, WELL_OPTIMISED)
    assert a.ai_readiness_score <= 100


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
