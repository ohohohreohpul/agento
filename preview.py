#!/usr/bin/env python3
"""
Agento preview — runs all tools against a local sample page and prints
rich-formatted output. No ANTHROPIC_API_KEY required.
"""
import sys, json
sys.path.insert(0, ".")

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.rule import Rule
from rich import box
from rich.text import Text
from rich.columns import Columns

console = Console(width=100)
URL = "http://localhost:9753/sample.html"

# ─────────────────────────────────────────────────────────────────────────────
console.print()
console.print(Panel.fit(
    "[bold cyan]Agento SEO Agent[/] — Live Preview",
    subtitle="All tools · No API key required",
    border_style="cyan",
))

# ══════════════════════════════════════════════════════════════════════════════
console.print(Rule("[bold yellow]① Technical SEO Audit[/]", style="yellow"))
console.print(f"[dim]Auditing:[/] {URL}\n")

from tools.web_audit import audit_url
audit = audit_url(URL)

# Meta table
meta = Table(show_header=False, box=box.SIMPLE, padding=(0,1))
meta.add_column("Field", style="bold", width=22)
meta.add_column("Value")
meta.add_row("Title", audit.meta.title or "[red]MISSING[/]")
meta.add_row("Title length", f"{audit.meta.title_length} chars " +
    ("[green]✓[/]" if 30 <= audit.meta.title_length <= 60 else "[yellow]⚠[/]"))
meta.add_row("Meta description", (audit.meta.meta_description[:70] + "…")
    if len(audit.meta.meta_description) > 70 else audit.meta.meta_description or "[red]MISSING[/]")
meta.add_row("Canonical", audit.meta.canonical or "[red]MISSING[/]")
meta.add_row("H1", audit.headings.h1[0] if audit.headings.h1 else "[red]MISSING[/]")
meta.add_row("H2 count", str(len(audit.headings.h2)))
meta.add_row("Word count", f"{audit.word_count}")
meta.add_row("HTTPS", "[green]✓[/]" if audit.https else "[red]✗[/]")
meta.add_row("Viewport meta", "[green]✓[/]" if audit.has_viewport_meta else "[red]✗[/]")
meta.add_row("Schema markup", "[green]✓[/]" if audit.schema_markup.types_found else "[red]MISSING[/]")
meta.add_row("Images", f"{len(audit.images)} total, [red]{audit.images_missing_alt} missing alt[/]"
    if audit.images_missing_alt else f"[green]{len(audit.images)} — all have alt ✓[/]")
console.print(meta)

# Issues / passes
if audit.issues:
    issue_t = Table(show_header=False, box=None, padding=(0,1))
    issue_t.add_column("", width=3)
    issue_t.add_column("Issue")
    for i in audit.issues:
        issue_t.add_row("[red]✗[/]", i)
    console.print(Panel(issue_t, title="Issues found", border_style="red", padding=(0,1)))

if audit.passes:
    pass_t = Table(show_header=False, box=None, padding=(0,1))
    pass_t.add_column("", width=3)
    pass_t.add_column("Pass")
    for p in audit.passes:
        pass_t.add_row("[green]✓[/]", p)
    console.print(Panel(pass_t, title="Passing checks", border_style="green", padding=(0,1)))

# ══════════════════════════════════════════════════════════════════════════════
console.print()
console.print(Rule("[bold yellow]② GEO / AEO Readiness[/]", style="yellow"))
console.print(f"[dim]Scoring for AI search citation potential (ChatGPT, Perplexity, Google AI Overviews)[/]\n")

from tools.web_audit import extract_page_text
from tools.geo_optimizer import analyze_for_geo
page_text = extract_page_text(URL)
geo = analyze_for_geo(URL, page_text)

score = geo.ai_readiness_score
colour = "green" if score >= 70 else "yellow" if score >= 40 else "red"
bar_filled = round(score / 5)
bar = "█" * bar_filled + "░" * (20 - bar_filled)

console.print(f"  AI Readiness Score  [{colour}]{bar}[/]  [{colour}]{score}/100[/]\n")

geo_t = Table(show_header=False, box=box.SIMPLE, padding=(0,1))
geo_t.add_column("Signal", style="bold", width=22)
geo_t.add_column("Status", width=10)
for label, val in [
    ("FAQ section",       geo.has_faq_section),
    ("Direct answer in intro", geo.has_direct_answers),
    ("Author info",       geo.has_author_info),
    ("Schema markup",     geo.has_schema_markup),
    ("Content freshness", "2026" in geo.content_freshness),
]:
    geo_t.add_row(label, "[green]✓  Pass[/]" if val else "[red]✗  Fail[/]")
console.print(geo_t)

if geo.issues:
    console.print()
    sev_colour = {"critical": "red", "warning": "yellow", "info": "blue"}
    for issue in geo.issues[:5]:
        c = sev_colour.get(issue.severity, "white")
        console.print(f"  [{c}][{issue.severity.upper()}][/] {issue.description}")
        console.print(f"   [dim]→ {issue.recommendation[:100]}…[/]")
        console.print()

if geo.recommended_schemas:
    console.print(f"  [bold]Recommended schemas:[/] {', '.join(geo.recommended_schemas)}")

# ══════════════════════════════════════════════════════════════════════════════
console.print()
console.print(Rule("[bold yellow]③ Keyword Research[/]", style="yellow"))
console.print("[dim]Seed: 'python seo' — Google Autocomplete (free tier)[/]\n")

from unittest.mock import patch
import httpx, json as _json

# Simulate autocomplete response so preview works offline
_FAKE_SUGGESTIONS = [
    "python seo automation",
    "python seo tools",
    "python seo scraper",
    "python seo audit",
    "python seo analysis",
    "how to do seo with python",
    "what is python seo?",
    "python for keyword research",
    "python seo monitoring",
    "python backlink checker",
]
_fake_resp = httpx.Response(
    status_code=200,
    content=_json.dumps(["python seo", _FAKE_SUGGESTIONS]).encode(),
    headers={"content-type": "application/json"},
    request=httpx.Request("GET", "https://suggestqueries.google.com/"),
)

with patch("tools.keywords.httpx.get", return_value=_fake_resp):
    from tools.keywords import research_keywords
    kw_result = research_keywords("python seo")

kw_t = Table(title="Keyword Suggestions", box=box.SIMPLE_HEAD)
kw_t.add_column("Keyword", style="cyan")
kw_t.add_column("Type")
kw_t.add_column("Volume", justify="right")
kw_t.add_column("Difficulty")
for s in kw_result.suggestions[:8]:
    kw_t.add_row(s.keyword, "suggestion",
        str(s.search_volume) if s.search_volume else "[dim]–[/]",
        s.competition or "[dim]add DataForSEO key[/]")
console.print(kw_t)

if kw_result.questions:
    console.print(f"\n  [bold]Question variants:[/] " + " · ".join(kw_result.questions[:4]))

# ══════════════════════════════════════════════════════════════════════════════
console.print()
console.print(Rule("[bold yellow]④ Schema Markup Generator[/]", style="yellow"))
console.print("[dim]Generating FAQPage + Article JSON-LD for this page[/]\n")

from tools.schema import generate_schema
faq = generate_schema("faq", {
    "qa_pairs": [
        {"question": "What is Python SEO?",
         "answer": "Python SEO is the practice of using Python scripts to automate search engine optimisation tasks such as auditing, keyword tracking, and link analysis."},
        {"question": "Do I need to know Python to use Agento?",
         "answer": "No. Agento provides a CLI that handles everything automatically."},
        {"question": "Which SEO signals matter most in 2026?",
         "answer": "In 2026, GEO/AEO signals (schema markup, direct answers, FAQ sections) are as important as traditional technical SEO factors."},
    ]
})

console.print(Panel(
    faq.json_ld,
    title="[green]FAQPage JSON-LD — ready to paste[/]",
    border_style="green",
    expand=False,
))
console.print(f"  [dim]{faq.implementation_note}[/]")

# ══════════════════════════════════════════════════════════════════════════════
console.print()
console.print(Rule("[bold yellow]⑤ Backlink Opportunities[/]", style="yellow"))
console.print("[dim]Simulated prospects (Google search blocked in this sandbox)[/]\n")

from models import BacklinkOpportunities, BacklinkProspect
mock_bl = BacklinkOpportunities(
    target_domain="example.com",
    niche="python SEO",
    prospects=[
        BacklinkProspect(url="https://realpython.com/write-for-us",
            domain="realpython.com", relevance_reason='Matched: "write for us"',
            contact_hint="realpython.com/contact", outreach_type="guest_post"),
        BacklinkProspect(url="https://seoguide.io/python-resources",
            domain="seoguide.io", relevance_reason='Matched: "resources" page',
            contact_hint="seoguide.io/contact", outreach_type="resource_page"),
        BacklinkProspect(url="https://dev.to/seo-roundup-2026",
            domain="dev.to", relevance_reason='Matched: "link roundup"',
            contact_hint="dev.to/contact", outreach_type="resource_page"),
        BacklinkProspect(url="https://towardsdatascience.com/guest-posts",
            domain="towardsdatascience.com", relevance_reason='Matched: "guest post"',
            contact_hint="towardsdatascience.com/contact", outreach_type="guest_post"),
    ],
    outreach_template="Subject: Guest Post Opportunity — python SEO\n\nHi {First Name},\n\nI came across your site..."
)

bl_t = Table(box=box.SIMPLE_HEAD)
bl_t.add_column("Domain", style="cyan")
bl_t.add_column("Type")
bl_t.add_column("Reason")
bl_t.add_column("Contact hint")
for p in mock_bl.prospects:
    type_colour = {"guest_post": "magenta", "resource_page": "blue"}.get(p.outreach_type, "white")
    bl_t.add_row(p.domain,
        f"[{type_colour}]{p.outreach_type}[/]",
        p.relevance_reason,
        p.contact_hint)
console.print(bl_t)

console.print(Panel(
    mock_bl.outreach_template,
    title="Outreach email template",
    border_style="magenta",
    padding=(0,1),
))

# ══════════════════════════════════════════════════════════════════════════════
console.print()
console.print(Panel.fit(
    "[bold]Run the full AI agent (requires ANTHROPIC_API_KEY):[/]\n\n"
    "  [cyan]python main.py chat[/]                              [dim]Interactive mode[/]\n"
    "  [cyan]python main.py full --url https://yourdomain.com[/]  [dim]Complete analysis[/]\n"
    "  [cyan]python main.py audit --url URL[/]                   [dim]Technical audit only[/]\n"
    "  [cyan]python main.py geo --url URL[/]                     [dim]GEO/AEO score only[/]\n"
    "  [cyan]python main.py keywords --topic 'your topic'[/]     [dim]Keyword research[/]\n"
    "  [cyan]python main.py backlinks --domain D --niche N[/]    [dim]Find link prospects[/]",
    title="[green]Ready to use[/]",
    border_style="green",
))
console.print()
