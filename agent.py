"""
Agento — AI SEO Orchestrator Agent.
Uses Claude Opus 4.6 with adaptive thinking + tool use to plan and execute
full SEO workflows: technical audits, keyword research, backlink discovery,
schema generation, GEO/AEO optimisation, competitor analysis, GSC data,
and llms.txt generation.
"""
from __future__ import annotations

import json
from typing import Any

import anthropic

from config import ANTHROPIC_API_KEY, MODEL
from models import (
    BacklinkOpportunities,
    CompetitorAnalysis,
    GEOAudit,
    GSCCoverageResult,
    GSCPerformanceResult,
    KeywordResearchResult,
    LLMsTxtResult,
    SchemaMarkup,
    TechnicalAudit,
)
from tools.backlinks import find_backlink_opportunities
from tools.competitor import analyze_competitor
from tools.geo_optimizer import analyze_for_geo
from tools.gsc import get_coverage_issues, get_search_performance
from tools.keywords import check_serp_rank, research_keywords
from tools.llms_txt import generate_llms_txt
from tools.schema import generate_schema
from tools.web_audit import audit_url, extract_page_text

# ── Tool definitions (Claude's schema) ───────────────────────────────────────

TOOLS: list[dict] = [
    {
        "name": "audit_url",
        "description": (
            "Perform a full technical SEO audit on a URL. "
            "Returns meta tags, headings, image alt coverage, internal/external links, "
            "structured data, word count, HTTPS status, and a list of issues and passes."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The full URL to audit (https://...)"}
            },
            "required": ["url"],
        },
    },
    {
        "name": "research_keywords",
        "description": (
            "Research keyword opportunities for a given topic/seed keyword. "
            "Returns keyword suggestions, question variants, and long-tail ideas. "
            "Includes search volume and difficulty when DataForSEO credentials are configured."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "seed": {"type": "string", "description": "The main topic or seed keyword"},
                "domain": {"type": "string", "description": "Optional: domain to check keyword fit for"},
            },
            "required": ["seed"],
        },
    },
    {
        "name": "find_backlink_opportunities",
        "description": (
            "Find link-building prospects for a domain in a specific niche. "
            "Returns guest-post targets, resource pages, and roundup opportunities "
            "along with contact hints and a ready-to-use outreach email template."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "domain": {"type": "string", "description": "Target domain to build links for (e.g. example.com)"},
                "niche": {"type": "string", "description": "Industry/topic niche (e.g. 'personal finance')"},
                "competitor_domain": {"type": "string", "description": "Optional: competitor domain to steal backlinks from"},
            },
            "required": ["domain", "niche"],
        },
    },
    {
        "name": "generate_schema",
        "description": (
            "Generate a ready-to-paste JSON-LD schema markup block for a page. "
            "Supported page_type values: article, faq, howto, local_business, product, breadcrumb, website."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "page_type": {
                    "type": "string",
                    "enum": ["article", "faq", "howto", "local_business", "product", "breadcrumb", "website"],
                    "description": "The type of schema markup to generate",
                },
                "data": {
                    "type": "object",
                    "description": (
                        "Fields for the schema. "
                        "article: headline, author_name, date_published, date_modified, url, [image_url, description]. "
                        "faq: qa_pairs=[{question, answer}]. "
                        "howto: name, description, steps=[str], [total_time]. "
                        "local_business: name, address, city, country, [phone, url, business_type]. "
                        "product: name, description, price, currency, [availability, image_url, sku]. "
                        "breadcrumb: items=[{name, url}]. "
                        "website: name, url, [search_url_template]."
                    ),
                },
            },
            "required": ["page_type", "data"],
        },
    },
    {
        "name": "analyze_for_geo",
        "description": (
            "Fetch a URL's content and analyse it for GEO/AEO readiness — how likely it is "
            "to be cited by AI search engines (ChatGPT, Perplexity, Google AI Overviews, Gemini). "
            "Returns an AI readiness score (0–100), Princeton/Georgia Tech tactic coverage, "
            "specific issues by severity, and actionable recommendations."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL to analyse for GEO/AEO optimisation"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "check_serp_rank",
        "description": (
            "Check what position a domain ranks at in Google for a given keyword. "
            "Requires SERPAPI_KEY to be configured; returns None position otherwise."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "keyword": {"type": "string", "description": "The keyword to check"},
                "domain": {"type": "string", "description": "The domain to check rank for"},
            },
            "required": ["keyword", "domain"],
        },
    },
    {
        "name": "generate_llms_txt",
        "description": (
            "Generate an llms.txt file for a website — a structured markdown index that helps "
            "AI search engines (ChatGPT, Perplexity, Gemini, Claude) discover and cite the site's "
            "best content. Also checks if the site already has an llms.txt, inspects robots.txt "
            "for blocked AI crawlers, and recommends fixes. "
            "Adopted by Stripe, Cloudflare, Vercel, and 1,000+ sites."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The website URL to generate llms.txt for (homepage)"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "get_search_performance",
        "description": (
            "Fetch real search performance data from Google Search Console: "
            "top keywords by clicks/impressions/CTR/position, top pages, and "
            "quick-win opportunities (positions 4–15 with high impressions but low CTR). "
            "Requires GSC_SERVICE_ACCOUNT_JSON to be configured."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "property_url": {
                    "type": "string",
                    "description": "GSC property URL (e.g. 'https://example.com/' or 'sc-domain:example.com')",
                },
                "days": {
                    "type": "integer",
                    "description": "Number of days to look back (default 28, max 90)",
                    "default": 28,
                },
                "page_filter": {
                    "type": "string",
                    "description": "Optional URL substring to filter results (e.g. '/blog/')",
                },
            },
            "required": ["property_url"],
        },
    },
    {
        "name": "analyze_competitor",
        "description": (
            "Run a full competitor gap analysis: find keywords the competitor ranks for "
            "that you don't (keyword gap), referring domains linking to them but not you "
            "(backlink gap), and their top organic pages. "
            "Requires DataForSEO for full data; falls back to Google search estimate without it."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "your_domain": {"type": "string", "description": "Your domain (e.g. 'yourblog.com')"},
                "competitor_domain": {"type": "string", "description": "Competitor domain to analyse (e.g. 'competitor.com')"},
            },
            "required": ["your_domain", "competitor_domain"],
        },
    },
]


# ── Tool dispatcher ───────────────────────────────────────────────────────────

def _run_tool(name: str, inputs: dict) -> Any:
    """Execute a tool by name and return a JSON-serialisable result."""
    if name == "audit_url":
        result: TechnicalAudit = audit_url(inputs["url"])
        return result.model_dump()

    if name == "research_keywords":
        result: KeywordResearchResult = research_keywords(
            seed=inputs["seed"],
            domain=inputs.get("domain"),
        )
        return result.model_dump()

    if name == "find_backlink_opportunities":
        result: BacklinkOpportunities = find_backlink_opportunities(
            domain=inputs["domain"],
            niche=inputs["niche"],
            competitor_domain=inputs.get("competitor_domain"),
        )
        return result.model_dump()

    if name == "generate_schema":
        result: SchemaMarkup = generate_schema(
            page_type=inputs["page_type"],
            data=inputs["data"],
        )
        return result.model_dump()

    if name == "analyze_for_geo":
        url = inputs["url"]
        page_text = extract_page_text(url)
        result: GEOAudit = analyze_for_geo(url=url, page_text=page_text)
        return result.model_dump()

    if name == "check_serp_rank":
        return check_serp_rank(
            keyword=inputs["keyword"],
            domain=inputs["domain"],
        )

    if name == "generate_llms_txt":
        result: LLMsTxtResult = generate_llms_txt(inputs["url"])
        return result.model_dump()

    if name == "get_search_performance":
        result: GSCPerformanceResult = get_search_performance(
            property_url=inputs["property_url"],
            days=inputs.get("days", 28),
            page_filter=inputs.get("page_filter"),
        )
        return result.model_dump()

    if name == "analyze_competitor":
        result: CompetitorAnalysis = analyze_competitor(
            your_domain=inputs["your_domain"],
            competitor_domain=inputs["competitor_domain"],
        )
        return result.model_dump()

    return {"error": f"Unknown tool: {name}"}


# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are Agento, an expert AI SEO strategist for 2026.

You have access to specialised tools for:
- Technical SEO auditing (audit_url)
- Keyword research and discovery (research_keywords)
- Backlink opportunity finding (find_backlink_opportunities)
- JSON-LD schema markup generation (generate_schema)
- GEO/AEO content optimisation for AI search visibility (analyze_for_geo)
- SERP rank checking (check_serp_rank)
- llms.txt generation for AI crawler optimisation (generate_llms_txt)
- Google Search Console performance data (get_search_performance)
- Competitor gap analysis — keywords, backlinks, top pages (analyze_competitor)

Your job is to:
1. Understand the user's SEO goal
2. Use the right tools — calling multiple tools when a thorough analysis is needed
3. Synthesise the data into clear, prioritised, actionable recommendations
4. Always explain the WHY behind each recommendation

When presenting results:
- Lead with the most critical issues first
- Group findings by category (Technical / Content / Backlinks / AI Visibility)
- Provide specific next steps the user can act on today
- When generating schema markup, always show the complete JSON-LD block
- When generating llms.txt, show the complete file content ready to deploy

Current context: April 2026.
- AI search (ChatGPT, Perplexity, Google AI Overviews, Gemini) accounts for ~31% of US searches
- ChatGPT drives 87.4% of AI referral traffic (Conductor, 13,770 domain study)
- Wikipedia cited in 47.9% of top ChatGPT results — encyclopaedic structure matters
- Content under 3 months old is 3x more likely to be cited by AI engines
- llms.txt adoption: 1,000+ sites including Stripe, Cloudflare, Vercel
- GEO/AEO optimisation is as important as traditional SEO — treat them as equals
"""


# ── Agent loop ────────────────────────────────────────────────────────────────

class AgentoAgent:
    def __init__(self, stream_callback=None):
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        self.stream_callback = stream_callback  # optional: called with each text chunk

    def run(self, user_message: str) -> str:
        """
        Run the full agentic loop for a user request.
        Returns the final text response from Claude.
        """
        messages: list[dict] = [{"role": "user", "content": user_message}]

        while True:
            with self.client.messages.stream(
                model=MODEL,
                max_tokens=8192,
                thinking={"type": "adaptive"},
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages,
            ) as stream:
                response = stream.get_final_message()

            # Collect text from this turn (excluding thinking blocks)
            text_output = ""
            for block in response.content:
                if block.type == "text":
                    text_output += block.text
                    if self.stream_callback:
                        self.stream_callback(block.text)

            # Done — no more tool calls
            if response.stop_reason == "end_turn":
                return text_output

            # Claude wants to call tools
            if response.stop_reason == "tool_use":
                tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

                # Append Claude's full response (incl. thinking blocks) to history
                messages.append({"role": "assistant", "content": response.content})

                # Execute all tool calls and collect results
                tool_results = []
                for block in tool_use_blocks:
                    if self.stream_callback:
                        self.stream_callback(f"\n[tool: {block.name}({json.dumps(block.input)[:80]}...)]\n")
                    result = _run_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result, default=str),
                    })

                messages.append({"role": "user", "content": tool_results})
                continue

            # Unexpected stop reason — bail out
            break

        return text_output
