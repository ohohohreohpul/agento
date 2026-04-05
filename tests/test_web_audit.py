"""
Tests for tools/web_audit.py — uses httpx mock transport so no network needed.
"""
import sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
import pytest
from unittest.mock import patch


SAMPLE_HTML = """<!DOCTYPE html>
<html>
<head>
  <title>Python SEO Guide 2026 — Example</title>
  <meta name="description" content="A comprehensive guide to Python SEO in 2026.">
  <meta name="robots" content="index, follow">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="canonical" href="https://example.com/python-seo-guide">
  <meta property="og:title" content="Python SEO Guide">
  <meta property="og:description" content="Learn Python SEO">
  <meta property="og:image" content="https://example.com/og.png">
  <script type="application/ld+json">
  {"@context":"https://schema.org","@type":"Article","headline":"Python SEO Guide"}
  </script>
</head>
<body>
  <h1>Python SEO Guide 2026</h1>
  <h2>Why Python for SEO?</h2>
  <h2>Getting Started</h2>
  <h3>Installation</h3>
  <p>Python is a powerful language for SEO automation. It lets you scrape, analyse,
  and optimise at scale. This guide covers everything you need in 2026.</p>
  <p>Use Python to automate technical audits, keyword research, and link building.
  This approach saves hours of manual work and produces consistent results.</p>
  <img src="python-logo.png" alt="Python logo">
  <img src="seo-chart.png" alt="">
  <img src="code-example.png">
  <a href="/about">About us</a>
  <a href="/contact">Contact</a>
  <a href="https://python.org">Python.org</a>
  <a href="https://google.com">Google</a>
</body>
</html>"""


MINIMAL_HTML = """<html><head></head><body><p>Hi</p></body></html>"""


def _mock_response(html: str, status: int = 200, url: str = "https://example.com/test"):
    """Build a fake httpx.Response."""
    return httpx.Response(
        status_code=status,
        content=html.encode(),
        headers={"content-type": "text/html; charset=utf-8"},
        request=httpx.Request("GET", url),
    )


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_full_audit_passes():
    from tools.web_audit import audit_url

    with patch("httpx.get", return_value=_mock_response(SAMPLE_HTML)):
        a = audit_url("https://example.com/python-seo-guide")

    assert a.status_code == 200
    assert a.https is True
    assert a.meta.title == "Python SEO Guide 2026 — Example"
    assert a.meta.title_length == len("Python SEO Guide 2026 — Example")
    assert "A comprehensive guide" in a.meta.meta_description
    assert a.meta.canonical == "https://example.com/python-seo-guide"
    assert a.meta.robots_meta == "index, follow"
    assert a.meta.og_title == "Python SEO Guide"
    assert a.meta.og_image == "https://example.com/og.png"


def test_headings():
    from tools.web_audit import audit_url

    with patch("httpx.get", return_value=_mock_response(SAMPLE_HTML)):
        a = audit_url("https://example.com/")

    assert a.headings.h1 == ["Python SEO Guide 2026"]
    assert len(a.headings.h2) == 2
    assert len(a.headings.h3) == 1
    assert any("H1" in p for p in a.passes)   # single H1 → pass


def test_images():
    from tools.web_audit import audit_url

    with patch("httpx.get", return_value=_mock_response(SAMPLE_HTML)):
        a = audit_url("https://example.com/")

    # 3 images: one has alt, one has empty alt, one missing alt entirely
    assert len(a.images) == 3
    assert a.images_missing_alt == 2
    assert any("image" in issue.lower() and "alt" in issue.lower() for issue in a.issues)


def test_links():
    from tools.web_audit import audit_url

    with patch("httpx.get", return_value=_mock_response(SAMPLE_HTML)):
        a = audit_url("https://example.com/")

    assert a.links.internal_links == 2   # /about, /contact
    assert a.links.external_links == 2   # python.org, google.com


def test_schema_detected():
    from tools.web_audit import audit_url

    with patch("httpx.get", return_value=_mock_response(SAMPLE_HTML)):
        a = audit_url("https://example.com/")

    assert "Article" in a.schema_markup.types_found
    assert any("Schema" in p or "schema" in p for p in a.passes)


def test_missing_title_and_meta():
    from tools.web_audit import audit_url

    with patch("httpx.get", return_value=_mock_response(MINIMAL_HTML)):
        a = audit_url("https://example.com/")

    assert any("title" in issue.lower() for issue in a.issues)
    assert any("meta description" in issue.lower() for issue in a.issues)
    assert any("H1" in issue for issue in a.issues)
    assert any("viewport" in issue.lower() for issue in a.issues)
    assert any("schema" in issue.lower() or "structured" in issue.lower() for issue in a.issues)


def test_non_200_status():
    from tools.web_audit import audit_url

    with patch("httpx.get", return_value=_mock_response("", status=404)):
        a = audit_url("https://example.com/missing")

    assert a.status_code == 404
    assert any("404" in issue for issue in a.issues)


def test_fetch_exception():
    from tools.web_audit import audit_url

    with patch("httpx.get", side_effect=httpx.ConnectError("timed out")):
        a = audit_url("https://example.com/")

    assert a.status_code == 0
    assert any("Fetch failed" in issue for issue in a.issues)


def test_word_count_thin():
    from tools.web_audit import audit_url

    thin = "<html><head></head><body><p>Short page.</p></body></html>"
    with patch("httpx.get", return_value=_mock_response(thin)):
        a = audit_url("https://example.com/")

    assert a.word_count < 300
    assert any("Thin content" in issue for issue in a.issues)


def test_extract_page_text():
    from tools.web_audit import extract_page_text

    html = "<html><body><script>var x=1;</script><p>Hello world</p></body></html>"
    with patch("httpx.get", return_value=_mock_response(html)):
        text = extract_page_text("https://example.com/")

    assert "Hello world" in text
    assert "var x=1" not in text   # script stripped


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
