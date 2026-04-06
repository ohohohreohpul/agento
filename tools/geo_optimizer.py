"""
GEO / AEO (Generative Engine Optimization / Answer Engine Optimization) analyzer.

Scores content on how well it will be cited by AI search engines: ChatGPT,
Perplexity, Google AI Overviews, Gemini, Claude, Copilot.

Signals based on:
- Princeton / Georgia Tech research (Aggarwal et al., 2023) — 40% visibility lift
- Conductor 2026 AI referral traffic study (13,770 domain dataset)
- GEO Tracker community benchmarks (amplifying-ai/awesome-generative-engine-optimization)
"""
from __future__ import annotations

import re
from urllib.parse import urlparse

from models import GEOAudit, GEOIssue


# ── Signal detectors ──────────────────────────────────────────────────────────

def _has_faq(text: str) -> bool:
    patterns = [
        r"\bfrequently asked questions\b",
        r"\bfaq\b",
        r"\bq&a\b",
        r"\bq:\s",
        r"\bcommon questions\b",
        r"\bpeople also ask\b",
    ]
    low = text.lower()
    return any(re.search(p, low) for p in patterns)


def _has_direct_answer(text: str) -> bool:
    """Check if the opening paragraph starts with a direct definition or answer."""
    first_500 = text[:500].lower()
    # Princeton research: 44.2% of LLM citations come from first 30% of page
    openers = ["is ", "are ", "refers to", "defined as", "means ", "involves ", "can be "]
    sentences = re.split(r"[.!?]", first_500)
    for s in sentences[:4]:
        if any(o in s for o in openers):
            return True
    return False


def _has_author_info(text: str) -> bool:
    patterns = [
        r"\bby\s+[A-Z][a-z]+\b",
        r"\bauthor\b",
        r"\bwritten by\b",
        r"\bcontributor\b",
        r"\breviewed by\b",       # medical/YMYL E-E-A-T
        r"\bfact[- ]check",
    ]
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def _detect_year(text: str) -> str | None:
    match = re.search(r"\b(202[4-9]|203\d)\b", text)
    return match.group() if match else None


def _count_external_citations(text: str) -> int:
    return len(re.findall(r"https?://\S+", text))


def _has_numbered_lists(text: str) -> bool:
    return bool(re.search(r"^\s*\d+[\.\)]\s+\S", text, re.MULTILINE))


def _has_bullet_lists(text: str) -> bool:
    return bool(re.search(r"^\s*[-*•]\s+\S", text, re.MULTILINE))


def _has_statistics(text: str) -> bool:
    """Princeton tactic #2: include statistics with source attribution."""
    stat_patterns = [
        r"\d+\.?\d*\s*%",                     # percentage
        r"\b\d+\s*(million|billion|thousand)\b",
        r"according to",
        r"research shows",
        r"study (found|shows|reveals)",
        r"survey (of|found|shows)",
        r"data (shows|suggests|indicates)",
    ]
    return any(re.search(p, text, re.IGNORECASE) for p in stat_patterns)


def _has_expert_quotes(text: str) -> bool:
    """Princeton tactic #3: include expert quotations."""
    patterns = [
        r'"[^"]{20,}"',                        # quoted text >= 20 chars
        r"according to [\w\s,]+said",
        r'says?\s+"',
        r"told\s+\w+\s+that",
        r"\bexpert\b",
        r"\bprofessor\b",
        r"\bresearcher\b",
    ]
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def _has_question_headings(text: str) -> int:
    """Count H2/H3 headings formatted as questions."""
    return len(re.findall(r"^#{1,3}\s+.+\?", text, re.MULTILINE))


def _has_wikipedia_style_structure(text: str) -> bool:
    """
    Wikipedia is cited in 47.9% of top ChatGPT results.
    Detect Wikipedia-like structure: clear definitions, sections, infobox-style data.
    """
    has_definition = bool(re.search(
        r"^[A-Z][^.]{10,80} (is|are|was|were|refers to) [^.]+\.",
        text, re.MULTILINE
    ))
    has_sections = len(re.findall(r"^#{1,3}\s+\S", text, re.MULTILINE)) >= 3
    return has_definition and has_sections


def _has_llms_txt_signal(text: str) -> bool:
    """Check if the page text mentions or links to llms.txt."""
    return bool(re.search(r"llms\.txt", text, re.IGNORECASE))


def _has_schema_markup(text: str) -> bool:
    return "application/ld+json" in text


def _recommended_schemas(has_faq: bool, has_steps: bool, is_article: bool) -> list[str]:
    schemas = []
    if has_faq:
        schemas.append("FAQPage")
    if has_steps:
        schemas.append("HowTo")
    if is_article:
        schemas.append("Article")
    schemas.append("BreadcrumbList")
    if not schemas:
        schemas.append("Article")
    return list(dict.fromkeys(schemas))   # deduplicate, preserve order


# ── Scorer ────────────────────────────────────────────────────────────────────

def analyze_for_geo(url: str, page_text: str) -> GEOAudit:
    """
    Analyse page text for GEO/AEO readiness and return a scored audit.

    Scoring breakdown (100 pts max):
      FAQ section                    20 pts  — single highest-impact GEO change
      Direct answer in intro         15 pts  — Princeton tactic #1
      Schema markup present          15 pts  — machine-readable for AI engines
      Author / E-E-A-T signals       10 pts  — Princeton tactic, trust signal
      Content freshness (≥2025 yr)   10 pts  — 3x citation boost
      Statistics & citations          8 pts  — Princeton tactic #2
      Expert quotes                   7 pts  — Princeton tactic #3
      Structured lists               10 pts  — extractability
      Question-format headings        5 pts  — People Also Ask mapping
    """
    audit = GEOAudit(url=url)
    issues: list[GEOIssue] = []
    score = 0

    # ── 1. FAQ / Q&A (20 pts) ────────────────────────────────────────────────
    audit.has_faq_section = _has_faq(page_text)
    if audit.has_faq_section:
        score += 20
        audit.recommended_schemas.append("FAQPage")
    else:
        issues.append(GEOIssue(
            category="structure",
            severity="warning",
            description="No FAQ section detected",
            recommendation=(
                "Add a dedicated FAQ section with 5–10 Q&A pairs targeting "
                "People Also Ask queries for your topic. Use 'Q:' / 'A:' format or "
                "accordion headings. This is the single highest-impact GEO change — "
                "FAQPage schema combined with real Q&A content directly feeds AI answer engines."
            ),
        ))

    # ── 2. Direct answer in intro (15 pts) ──────────────────────────────────
    audit.has_direct_answers = _has_direct_answer(page_text)
    if audit.has_direct_answers:
        score += 15
    else:
        issues.append(GEOIssue(
            category="structure",
            severity="critical",
            description="Intro does not open with a direct answer",
            recommendation=(
                "Rewrite the first paragraph to directly answer the primary question "
                "in 2–3 sentences. AI engines extract the first confident statement "
                "as the featured answer. Formula: '[Topic] is X. It works by Y. "
                "The main benefit is Z.' — Princeton research shows 44.2% of LLM "
                "citations come from the first 30% of the page."
            ),
        ))

    # ── 3. Schema markup (15 pts) ────────────────────────────────────────────
    audit.has_schema_markup = _has_schema_markup(page_text)
    if audit.has_schema_markup:
        score += 15
    else:
        issues.append(GEOIssue(
            category="structure",
            severity="critical",
            description="No structured data (JSON-LD schema) found",
            recommendation=(
                "Add at minimum Article + FAQPage JSON-LD schema. This is "
                "machine-readable metadata that AI engines parse directly to understand "
                "page content and author credibility. Use the Agento schema generator "
                "('generate_schema' tool) to create the correct markup instantly."
            ),
        ))

    # ── 4. Author / E-E-A-T (10 pts) ────────────────────────────────────────
    audit.has_author_info = _has_author_info(page_text)
    if audit.has_author_info:
        score += 10
    else:
        issues.append(GEOIssue(
            category="authority",
            severity="warning",
            description="No author attribution found",
            recommendation=(
                "Add a visible author byline with name, credentials, and a link to "
                "an author bio page. AI engines weight content with clear authorship "
                "higher for E-E-A-T (Experience, Expertise, Authoritativeness, Trust). "
                "Add Person schema markup for the author to further signal expertise."
            ),
        ))

    # ── 5. Freshness (10 pts) ────────────────────────────────────────────────
    year = _detect_year(page_text)
    audit.content_freshness = f"Year reference found: {year}" if year else "No year reference found"
    if year and int(year) >= 2025:
        score += 10
    else:
        issues.append(GEOIssue(
            category="freshness",
            severity="warning",
            description="Content may appear outdated to AI engines",
            recommendation=(
                "Update the article with the current year in the title and intro "
                "(e.g., 'Complete Guide [2026]'). AI engines are 3x more likely to cite "
                "content updated within the last 3 months. Also refresh statistics, "
                "examples, and references to current data."
            ),
        ))

    # ── 6. Statistics with attribution (8 pts) ───────────────────────────────
    has_stats = _has_statistics(page_text)
    if has_stats:
        score += 8
    else:
        issues.append(GEOIssue(
            category="citations",
            severity="info",
            description="No statistics or data citations detected",
            recommendation=(
                "Include specific statistics with source attribution "
                "(e.g., 'According to [Source], X% of...'). Princeton/Georgia Tech "
                "research confirmed this is one of the top-3 highest-impact GEO tactics, "
                "increasing AI citation probability significantly."
            ),
        ))

    # ── 7. Expert quotations (7 pts) ─────────────────────────────────────────
    has_quotes = _has_expert_quotes(page_text)
    if has_quotes:
        score += 7
    else:
        issues.append(GEOIssue(
            category="authority",
            severity="info",
            description="No expert quotes or attributed statements found",
            recommendation=(
                "Add 1–2 quotes from named experts, researchers, or industry authorities. "
                "Format: 'According to [Expert Name, Title], \"[quote].\"' "
                "This is Princeton tactic #3 — expert quotations signal credibility "
                "and increase the chance of AI engines citing your content."
            ),
        ))

    # ── 8. Structured lists (10 pts) ─────────────────────────────────────────
    has_numbered = _has_numbered_lists(page_text)
    has_bullets = _has_bullet_lists(page_text)
    if has_numbered or has_bullets:
        score += 10
        if has_numbered:
            audit.recommended_schemas.append("HowTo")
    else:
        issues.append(GEOIssue(
            category="structure",
            severity="info",
            description="No numbered or bulleted lists detected",
            recommendation=(
                "Use numbered steps and bullet lists for key points. "
                "AI engines preferentially extract structured lists as direct answers "
                "to 'how to' and 'what are the' type queries. Numbered steps also "
                "qualify for HowTo schema markup."
            ),
        ))

    # ── 9. Question-format headings (5 pts) ──────────────────────────────────
    question_headings = _has_question_headings(page_text)
    if question_headings >= 2:
        score += 5
    else:
        issues.append(GEOIssue(
            category="structure",
            severity="info",
            description=f"Only {question_headings} question-format heading(s) detected (need ≥ 2)",
            recommendation=(
                "Rewrite at least 3–5 H2/H3 headings as questions "
                "(e.g., 'What is X?', 'How does X work?', 'Why does X matter?'). "
                "These map directly to People Also Ask and AI conversational queries, "
                "dramatically increasing the chance of your content appearing as a "
                "direct answer in AI search results."
            ),
        ))

    # ── Bonus checks (informational, no score impact) ─────────────────────────

    # Wikipedia-style structure
    if not _has_wikipedia_style_structure(page_text):
        issues.append(GEOIssue(
            category="structure",
            severity="info",
            description="Content lacks Wikipedia-style definitional structure",
            recommendation=(
                "Wikipedia is cited in 47.9% of top ChatGPT results. Structure your "
                "key article as: (1) clear 1-sentence definition, (2) brief overview, "
                "(3) organised H2 sections covering all aspects of the topic. "
                "This 'encyclopaedic' structure is what AI engines extract for overviews."
            ),
        ))

    # External citations count
    citations = _count_external_citations(page_text)
    if citations < 3:
        issues.append(GEOIssue(
            category="citations",
            severity="info",
            description=f"Only {citations} external citation(s) found (aim for ≥ 3)",
            recommendation=(
                "Link to authoritative sources: research papers, official docs, "
                "government or academic sites (.gov/.edu). AI engines favour content "
                "that cites credible external evidence — it signals information accuracy "
                "and increases E-E-A-T score."
            ),
        ))

    # ── Recommended schemas ─────────────────────────────────────────────────
    audit.recommended_schemas = _recommended_schemas(
        has_faq=audit.has_faq_section,
        has_steps=has_numbered,
        is_article=True,
    )

    audit.ai_readiness_score = min(score, 100)
    audit.issues = issues

    # ── AI search context (2026 benchmarks) ──────────────────────────────────
    audit.geo_context = _geo_context_note(audit.ai_readiness_score)

    return audit


def _geo_context_note(score: int) -> str:
    """Return a contextual note based on the score benchmarks."""
    if score >= 80:
        return (
            f"Score {score}/100 — Excellent GEO readiness. Your content is well-positioned "
            "to be cited by AI search engines. ~31% of US searches now go through AI "
            "interfaces; at this score you're capturing that traffic."
        )
    if score >= 60:
        return (
            f"Score {score}/100 — Good GEO readiness with room to improve. "
            "Addressing the 'critical' issues above could push you into the top 20% "
            "of AI-cited content. Focus on FAQ section and direct-answer intro first."
        )
    if score >= 40:
        return (
            f"Score {score}/100 — Moderate GEO readiness. Your content ranks below "
            "average for AI citation probability. Implement the critical fixes (schema, "
            "direct answer intro) first — these alone could boost your score by 30+ points."
        )
    return (
        f"Score {score}/100 — Low GEO readiness. Your content is unlikely to be cited "
        "by ChatGPT, Perplexity, or Google AI Overviews in its current form. "
        "Start with: (1) add FAQPage schema, (2) rewrite intro with direct answer, "
        "(3) add author byline. These three changes have the highest ROI."
    )
