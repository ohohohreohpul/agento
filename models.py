from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field




# ── Technical SEO Audit ────────────────────────────────────────────────────────

class MetaInfo(BaseModel):
    title: str = ""
    title_length: int = 0
    meta_description: str = ""
    meta_description_length: int = 0
    canonical: str = ""
    robots_meta: str = ""
    og_title: str = ""
    og_description: str = ""
    og_image: str = ""


class HeadingStructure(BaseModel):
    h1: list[str] = Field(default_factory=list)
    h2: list[str] = Field(default_factory=list)
    h3: list[str] = Field(default_factory=list)


class ImageInfo(BaseModel):
    src: str
    alt: str
    missing_alt: bool


class LinkInfo(BaseModel):
    internal_links: int = 0
    external_links: int = 0
    broken_link_candidates: list[str] = Field(default_factory=list)


class SchemaFound(BaseModel):
    types_found: list[str] = Field(default_factory=list)
    raw_schemas: list[str] = Field(default_factory=list)


class TechnicalAudit(BaseModel):
    url: str
    status_code: int = 0
    load_time_ms: float = 0.0
    page_size_bytes: int = 0
    meta: MetaInfo = Field(default_factory=MetaInfo)
    headings: HeadingStructure = Field(default_factory=HeadingStructure)
    images: list[ImageInfo] = Field(default_factory=list)
    images_missing_alt: int = 0
    links: LinkInfo = Field(default_factory=LinkInfo)
    schema_markup: SchemaFound = Field(default_factory=SchemaFound)
    word_count: int = 0
    has_viewport_meta: bool = False
    https: bool = False
    issues: list[str] = Field(default_factory=list)
    passes: list[str] = Field(default_factory=list)


# ── Keyword Research ───────────────────────────────────────────────────────────

class KeywordSuggestion(BaseModel):
    keyword: str
    search_volume: Optional[int] = None
    competition: Optional[str] = None   # low / medium / high
    cpc_usd: Optional[float] = None
    keyword_difficulty: Optional[int] = None


class KeywordResearchResult(BaseModel):
    seed_keyword: str
    domain: Optional[str] = None
    suggestions: list[KeywordSuggestion] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)
    long_tail: list[str] = Field(default_factory=list)
    source: str = "google_autocomplete"


# ── Backlinks ─────────────────────────────────────────────────────────────────

class BacklinkProspect(BaseModel):
    url: str
    domain: str
    relevance_reason: str
    contact_hint: str = ""
    outreach_type: str = ""   # guest_post / resource_page / broken_link / mention


class BacklinkOpportunities(BaseModel):
    target_domain: str
    niche: str
    prospects: list[BacklinkProspect] = Field(default_factory=list)
    outreach_template: str = ""


# ── Schema Markup ─────────────────────────────────────────────────────────────

class SchemaMarkup(BaseModel):
    page_type: str
    json_ld: str
    implementation_note: str = ""


# ── GEO / AEO Optimization ────────────────────────────────────────────────────

class GEOIssue(BaseModel):
    category: str       # structure / freshness / authority / citations / faq
    severity: str       # critical / warning / info
    description: str
    recommendation: str


class GEOAudit(BaseModel):
    url: str
    ai_readiness_score: int = 0   # 0–100
    issues: list[GEOIssue] = Field(default_factory=list)
    has_faq_section: bool = False
    has_direct_answers: bool = False
    has_schema_markup: bool = False
    has_author_info: bool = False
    content_freshness: str = ""
    recommended_schemas: list[str] = Field(default_factory=list)
    rewritten_intro: str = ""      # AI-suggested intro optimised for AI engines
    geo_context: str = ""          # Benchmark note explaining the score


# ── llms.txt Generation ───────────────────────────────────────────────────────

class LLMsTxtSection(BaseModel):
    title: str
    items: list[tuple[str, str]] = Field(default_factory=list)  # (title, url)


class LLMsTxtResult(BaseModel):
    url: str
    already_exists: bool = False
    existing_content: str = ""
    generated_content: str = ""
    sections: list[LLMsTxtSection] = Field(default_factory=list)
    blocked_ai_bots: list[str] = Field(default_factory=list)
    missing_ai_bot_rules: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


# ── Google Search Console ─────────────────────────────────────────────────────

class GSCKeywordRow(BaseModel):
    keyword: str
    clicks: int = 0
    impressions: int = 0
    ctr: float = 0.0       # percentage
    position: float = 0.0


class GSCPerformanceResult(BaseModel):
    property_url: str
    days: int = 28
    top_keywords: list[GSCKeywordRow] = Field(default_factory=list)
    top_pages: list[GSCKeywordRow] = Field(default_factory=list)
    quick_wins: list[GSCKeywordRow] = Field(default_factory=list)
    total_clicks: int = 0
    total_impressions: int = 0
    avg_ctr: float = 0.0
    avg_position: float = 0.0
    error: str = ""


class GSCCoverageResult(BaseModel):
    property_url: str
    submitted_urls: int = 0
    indexed_urls: int = 0
    coverage_note: str = ""
    error: str = ""


# ── Competitor Analysis ───────────────────────────────────────────────────────

class CompetitorKeywordGap(BaseModel):
    keyword: str
    competitor_position: int = 0
    your_position: Optional[int] = None
    search_volume: Optional[int] = None
    keyword_difficulty: Optional[int] = None
    opportunity: str = "medium"    # high / medium / low


class CompetitorBacklinkGap(BaseModel):
    referring_domain: str
    domain_rank: int = 0
    links_to_competitor: int = 0
    links_to_you: int = 0
    contact_hint: str = ""


class CompetitorPage(BaseModel):
    url: str
    estimated_traffic: int = 0
    top_keyword: str = ""
    keywords_count: int = 0


class CompetitorAnalysis(BaseModel):
    your_domain: str
    competitor_domain: str
    keyword_gaps: list[CompetitorKeywordGap] = Field(default_factory=list)
    backlink_gaps: list[CompetitorBacklinkGap] = Field(default_factory=list)
    competitor_top_pages: list[CompetitorPage] = Field(default_factory=list)
    data_source: str = "dataforseo"
    note: str = ""
