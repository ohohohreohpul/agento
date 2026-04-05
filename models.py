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
