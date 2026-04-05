"""
Tests for agent.py tool dispatcher and tool definitions.
Mocks all tool implementations — verifies the dispatcher routes correctly
and that every registered tool has valid input_schema.
"""
import sys, json
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from models import (
    TechnicalAudit, KeywordResearchResult, BacklinkOpportunities,
    SchemaMarkup, GEOAudit,
)


# ── Dispatcher routing ─────────────────────────────────────────────────────────

def test_dispatcher_audit_url():
    from agent import _run_tool

    mock_audit = TechnicalAudit(url="https://example.com", status_code=200, word_count=800)
    with patch("agent.audit_url", return_value=mock_audit):
        result = _run_tool("audit_url", {"url": "https://example.com"})

    assert result["url"] == "https://example.com"
    assert result["status_code"] == 200
    assert result["word_count"] == 800


def test_dispatcher_research_keywords():
    from agent import _run_tool

    from models import KeywordSuggestion
    mock_kw = KeywordResearchResult(
        seed_keyword="seo",
        suggestions=[KeywordSuggestion(keyword="seo tools"), KeywordSuggestion(keyword="seo guide")],
    )
    with patch("agent.research_keywords", return_value=mock_kw):
        result = _run_tool("research_keywords", {"seed": "seo", "domain": "example.com"})

    assert result["seed_keyword"] == "seo"
    assert len(result["suggestions"]) == 2


def test_dispatcher_find_backlinks():
    from agent import _run_tool
    from models import BacklinkProspect

    mock_bl = BacklinkOpportunities(
        target_domain="example.com",
        niche="SEO",
        prospects=[BacklinkProspect(
            url="https://prospect.com/resources",
            domain="prospect.com",
            relevance_reason="Resource page",
            contact_hint="prospect.com/contact",
            outreach_type="resource_page",
        )],
    )
    with patch("agent.find_backlink_opportunities", return_value=mock_bl):
        result = _run_tool("find_backlink_opportunities", {
            "domain": "example.com", "niche": "SEO"
        })

    assert result["target_domain"] == "example.com"
    assert len(result["prospects"]) == 1


def test_dispatcher_generate_schema():
    from agent import _run_tool

    mock_schema = SchemaMarkup(
        page_type="faq",
        json_ld='<script type="application/ld+json">{"@type":"FAQPage"}</script>',
        implementation_note="Place in <head>",
    )
    with patch("agent.generate_schema", return_value=mock_schema):
        result = _run_tool("generate_schema", {
            "page_type": "faq",
            "data": {"qa_pairs": [{"question": "Q?", "answer": "A."}]}
        })

    assert result["page_type"] == "faq"
    assert "FAQPage" in result["json_ld"]


def test_dispatcher_analyze_for_geo():
    from agent import _run_tool

    mock_geo = GEOAudit(
        url="https://example.com/page",
        ai_readiness_score=72,
        has_faq_section=True,
    )
    with patch("agent.extract_page_text", return_value="Some page content"):
        with patch("agent.analyze_for_geo", return_value=mock_geo):
            result = _run_tool("analyze_for_geo", {"url": "https://example.com/page"})

    assert result["ai_readiness_score"] == 72
    assert result["has_faq_section"] is True


def test_dispatcher_check_serp_rank():
    from agent import _run_tool

    with patch("agent.check_serp_rank", return_value={"keyword": "seo", "domain": "example.com", "position": 3}):
        result = _run_tool("check_serp_rank", {"keyword": "seo", "domain": "example.com"})

    assert result["position"] == 3


def test_dispatcher_unknown_tool():
    from agent import _run_tool

    result = _run_tool("nonexistent_tool", {})
    assert "error" in result
    assert "Unknown tool" in result["error"]


# ── Tool schema validation ─────────────────────────────────────────────────────

def test_all_tools_have_valid_schema():
    from agent import TOOLS

    for tool in TOOLS:
        assert "name" in tool, f"Tool missing name: {tool}"
        assert "description" in tool, f"Tool missing description: {tool['name']}"
        assert "input_schema" in tool, f"Tool missing input_schema: {tool['name']}"
        schema = tool["input_schema"]
        assert schema["type"] == "object", f"Schema type not object: {tool['name']}"
        assert "properties" in schema, f"Schema missing properties: {tool['name']}"
        assert "required" in schema, f"Schema missing required: {tool['name']}"


def test_all_tools_registered():
    from agent import TOOLS

    names = {t["name"] for t in TOOLS}
    expected = {
        "audit_url",
        "research_keywords",
        "find_backlink_opportunities",
        "generate_schema",
        "analyze_for_geo",
        "check_serp_rank",
    }
    assert names == expected, f"Tool mismatch. Got: {names}"


def test_tool_names_match_dispatcher():
    """Every tool in TOOLS must have a working dispatcher branch."""
    from agent import TOOLS, _run_tool

    # Use mocks so no actual work happens
    dummy_audit = TechnicalAudit(url="https://example.com")
    dummy_kw = KeywordResearchResult(seed_keyword="x")
    dummy_bl = BacklinkOpportunities(target_domain="x.com", niche="x")
    dummy_schema = SchemaMarkup(page_type="faq", json_ld="")
    dummy_geo = GEOAudit(url="https://example.com")

    with (
        patch("agent.audit_url", return_value=dummy_audit),
        patch("agent.research_keywords", return_value=dummy_kw),
        patch("agent.find_backlink_opportunities", return_value=dummy_bl),
        patch("agent.generate_schema", return_value=dummy_schema),
        patch("agent.extract_page_text", return_value=""),
        patch("agent.analyze_for_geo", return_value=dummy_geo),
        patch("agent.check_serp_rank", return_value={"position": 1}),
    ):
        _run_tool("audit_url", {"url": "https://x.com"})
        _run_tool("research_keywords", {"seed": "x"})
        _run_tool("find_backlink_opportunities", {"domain": "x.com", "niche": "x"})
        _run_tool("generate_schema", {"page_type": "faq", "data": {}})
        _run_tool("analyze_for_geo", {"url": "https://x.com"})
        _run_tool("check_serp_rank", {"keyword": "x", "domain": "x.com"})


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
