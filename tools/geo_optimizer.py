"""
GEO / AEO (Generative Engine Optimization / Answer Engine Optimization) analyzer.
Scores content on how well it will be cited by AI search engines like ChatGPT,
Perplexity, and Google AI Overviews.
"""
from __future__ import annotations

import re

from models import GEOAudit, GEOIssue


# ── Signals ──────────────────────────────────────────────────────────────────

def _has_faq(text: str) -> bool:
    patterns = [
        r"\bfrequently asked questions\b",
        r"\bfaq\b",
        r"\bq&a\b",
        r"\bq:\s",
        r"\bcommon questions\b",
    ]
    low = text.lower()
    return any(re.search(p, low) for p in patterns)


def _has_direct_answer(text: str) -> bool:
    """Check if early content starts with a direct definition or answer."""
    first_500 = text[:500].lower()
    openers = ["is ", "are ", "refers to", "defined as", "means ", "involves "]
    sentences = re.split(r"[.!?]", first_500)
    for s in sentences[:4]:
        if any(o in s for o in openers):
            return True
    return False


def _has_author_info(text: str) -> bool:
    patterns = [r"\bby\s+[A-Z][a-z]+\b", r"\bauthor\b", r"\bwritten by\b", r"\bcontributor\b"]
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def _detect_year(text: str) -> str | None:
    match = re.search(r"\b(202[3-9]|2030)\b", text)
    return match.group() if match else None


def _count_external_citations(text: str) -> int:
    return len(re.findall(r"https?://\S+", text))


def _has_numbered_lists(text: str) -> bool:
    return bool(re.search(r"^\s*\d+[\.\)]\s+\S", text, re.MULTILINE))


def _has_bullet_lists(text: str) -> bool:
    return bool(re.search(r"^\s*[-*•]\s+\S", text, re.MULTILINE))


def _recommended_schemas(has_faq: bool, has_steps: bool, is_article: bool) -> list[str]:
    schemas = []
    if has_faq:
        schemas.append("FAQPage")
    if has_steps:
        schemas.append("HowTo")
    if is_article:
        schemas.append("Article")
    if not schemas:
        schemas.append("Article")
    return schemas


# ── Scorer ───────────────────────────────────────────────────────────────────

def analyze_for_geo(url: str, page_text: str) -> GEOAudit:
    """
    Analyse page text and return a GEO/AEO audit.
    page_text should be the clean visible body text of the page.
    """
    audit = GEOAudit(url=url)
    issues: list[GEOIssue] = []
    score = 0

    # ── 1. FAQ / Q&A ────────────────────────────────────────────────────────
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
                "People Also Ask queries for your topic. Use Q: / A: format or "
                "accordion headings. This is the single highest-impact GEO change."
            ),
        ))

    # ── 2. Direct answer in intro ────────────────────────────────────────────
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
                "as the featured answer. E.g., '[Topic] is X. It works by Y. "
                "The main benefit is Z.'"
            ),
        ))

    # ── 3. Author / E-E-A-T signals ─────────────────────────────────────────
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
                "higher for E-E-A-T (Experience, Expertise, Authoritativeness, Trust)."
            ),
        ))

    # ── 4. Freshness ─────────────────────────────────────────────────────────
    year = _detect_year(page_text)
    audit.content_freshness = f"Contains year reference: {year}" if year else "No year reference found"
    if year and int(year) >= 2025:
        score += 10
    else:
        issues.append(GEOIssue(
            category="freshness",
            severity="warning",
            description="Content may appear outdated to AI engines",
            recommendation=(
                "Update the article with the current year in the title and intro "
                "(e.g., 'Complete Guide [2026]'). AI engines heavily favour recently "
                "updated content. Also refresh statistics, examples, and references."
            ),
        ))

    # ── 5. Structured lists ──────────────────────────────────────────────────
    has_numbered = _has_numbered_lists(page_text)
    has_bullets = _has_bullet_lists(page_text)
    if has_numbered or has_bullets:
        score += 10
    else:
        issues.append(GEOIssue(
            category="structure",
            severity="info",
            description="No numbered or bulleted lists detected",
            recommendation=(
                "Use numbered steps and bullet lists for key points. "
                "AI engines preferentially extract structured lists as direct answers "
                "to 'how to' and 'what are the' type queries."
            ),
        ))

    # ── 6. External citations ────────────────────────────────────────────────
    citations = _count_external_citations(page_text)
    if citations >= 3:
        score += 10
    else:
        issues.append(GEOIssue(
            category="citations",
            severity="info",
            description=f"Only {citations} external citation(s) found",
            recommendation=(
                "Link to authoritative sources (research papers, official docs, "
                "government sites). AI engines favour content that cites credible "
                "external evidence — it signals information accuracy."
            ),
        ))

    # ── 7. Schema markup ────────────────────────────────────────────────────
    # (detected separately via web_audit; we check here by scanning for ld+json tag pattern)
    if "application/ld+json" in page_text:
        audit.has_schema_markup = True
        score += 15
    else:
        issues.append(GEOIssue(
            category="structure",
            severity="critical",
            description="No structured data (JSON-LD schema) found",
            recommendation=(
                "Add at minimum Article + FAQPage JSON-LD schema. This is machine-readable "
                "metadata that AI engines parse directly. Use the Agento schema generator "
                "to create the correct markup."
            ),
        ))

    # ── 8. Conversational subheadings ───────────────────────────────────────
    question_headings = len(re.findall(r"^#{1,3}\s+.+\?", page_text, re.MULTILINE))
    if question_headings >= 2:
        score += 10
    else:
        issues.append(GEOIssue(
            category="structure",
            severity="info",
            description="Few or no question-format subheadings detected",
            recommendation=(
                "Rewrite at least 3–5 H2/H3 headings as questions "
                "(e.g., 'What is X?' 'How does X work?'). "
                "These map directly to People Also Ask and AI conversational queries."
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
    return audit
