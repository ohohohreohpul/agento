#!/usr/bin/env python3
"""
Agento — AI SEO Agentic Tool
CLI entry point.

Usage examples:
  python main.py chat
  python main.py audit --url https://example.com
  python main.py keywords --topic "python web scraping"
  python main.py backlinks --domain example.com --niche "software development"
  python main.py geo --url https://example.com/blog/my-post
  python main.py schema --type faq
"""
import sys

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from config import ANTHROPIC_API_KEY

console = Console()

# ── Guard: require API key ─────────────────────────────────────────────────────

def _check_api_key():
    if not ANTHROPIC_API_KEY:
        console.print(
            "[bold red]Error:[/] ANTHROPIC_API_KEY is not set.\n"
            "Copy [yellow].env.example[/] to [yellow].env[/] and add your key.",
            highlight=False,
        )
        sys.exit(1)


# ── Shared streaming renderer ──────────────────────────────────────────────────

def _stream_print(text: str):
    console.print(text, end="", markup=False, highlight=False)


def _run_agent(prompt: str):
    _check_api_key()
    from agent import AgentoAgent

    console.print(Panel(f"[bold cyan]Agento[/] › {prompt[:120]}", border_style="cyan"))

    full_response = []

    def on_chunk(chunk: str):
        full_response.append(chunk)
        console.print(chunk, end="", markup=False, highlight=False)

    agent = AgentoAgent(stream_callback=on_chunk)
    agent.run(prompt)
    console.print()   # newline after stream


# ── CLI commands ──────────────────────────────────────────────────────────────

@click.group()
def cli():
    """Agento — AI-powered SEO agent for technical audits, keyword research,
    backlink discovery, schema generation, and GEO/AEO optimisation."""
    pass


@cli.command()
def chat():
    """Interactive chat mode — describe any SEO task in plain English."""
    _check_api_key()
    from agent import AgentoAgent

    console.print(Panel(
        "[bold cyan]Agento Interactive Mode[/]\n"
        "Type your SEO request. Examples:\n"
        "  • Audit https://example.com for SEO issues\n"
        "  • Find backlink opportunities for myblog.com in the fitness niche\n"
        "  • Research keywords for 'content marketing'\n"
        "  • Generate FAQ schema for my article about Python\n"
        "  • Check GEO/AEO readiness of https://example.com/blog-post\n\n"
        "[dim]Type 'exit' or Ctrl+C to quit.[/]",
        border_style="cyan",
        title="Agento SEO Agent",
    ))

    agent = AgentoAgent(stream_callback=_stream_print)

    while True:
        try:
            user_input = console.input("\n[bold green]You »[/] ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Bye![/]")
            break
        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "q"):
            console.print("[dim]Bye![/]")
            break

        console.print("\n[bold cyan]Agento »[/]")
        agent.run(user_input)
        console.print()


@cli.command()
@click.option("--url", required=True, help="URL to audit")
def audit(url: str):
    """Run a full technical SEO audit on a URL."""
    _run_agent(
        f"Perform a comprehensive technical SEO audit on {url}. "
        "List all issues found, explain why each matters, and provide "
        "specific fixes ordered by impact. Also note what's already done well."
    )


@cli.command()
@click.option("--topic", required=True, help="Seed keyword / topic")
@click.option("--domain", default=None, help="Your domain (optional, for context)")
def keywords(topic: str, domain: str | None):
    """Research keyword opportunities for a topic."""
    domain_part = f" for the domain {domain}" if domain else ""
    _run_agent(
        f"Research keyword opportunities for '{topic}'{domain_part}. "
        "Identify the best primary keyword, 5 secondary keywords, and 10 long-tail / "
        "question keywords. For each, explain the search intent and content strategy."
    )


@cli.command()
@click.option("--domain", required=True, help="Your domain to build links for")
@click.option("--niche", required=True, help="Your industry / niche")
@click.option("--competitor", default=None, help="Competitor domain to analyse")
def backlinks(domain: str, niche: str, competitor: str | None):
    """Find backlink building opportunities."""
    competitor_part = f" Also analyse competitor backlinks from {competitor}." if competitor else ""
    _run_agent(
        f"Find backlink building opportunities for {domain} in the {niche} niche.{competitor_part} "
        "Group prospects by outreach type (guest post, resource page, mention). "
        "Provide a personalised outreach email template for the best opportunity type."
    )


@cli.command()
@click.option("--url", required=True, help="URL to analyse for GEO/AEO")
def geo(url: str):
    """Analyse a page for GEO/AEO (AI search engine) visibility."""
    _run_agent(
        f"Analyse {url} for GEO/AEO optimisation — how well it will be cited by "
        "AI search engines like ChatGPT, Perplexity, and Google AI Overviews. "
        "Provide the AI readiness score, top 3 critical fixes, and recommend the "
        "exact schema markup types to implement. Also suggest how to rewrite the "
        "page intro for maximum AI citation potential."
    )


@cli.command("schema")
@click.option("--type", "schema_type", required=True,
              type=click.Choice(["article", "faq", "howto", "local_business", "product", "breadcrumb", "website"]),
              help="Schema type to generate")
@click.option("--title", default="My Page Title", help="Page/article title")
@click.option("--url", default="https://example.com/page", help="Page URL")
@click.option("--author", default="Site Author", help="Author name (article only)")
def schema_cmd(schema_type: str, title: str, url: str, author: str):
    """Generate JSON-LD schema markup for a page."""
    context = f"title='{title}', url='{url}', author='{author}'"
    _run_agent(
        f"Generate a complete {schema_type} JSON-LD schema markup block. "
        f"Use these details: {context}. "
        "Show the complete <script> block ready to paste, then explain where on "
        "the page to place it and why this schema type helps with SEO and AI visibility."
    )


@cli.command()
@click.option("--url", required=True, help="URL to run full analysis on")
def full(url: str):
    """Run a complete SEO + GEO audit: technical, content, and AI visibility."""
    _run_agent(
        f"Run a complete SEO analysis on {url}. I need: "
        "1) Full technical SEO audit with all issues and fixes. "
        "2) GEO/AEO readiness score and top improvements for AI search visibility. "
        "3) Recommended schema markup types for this page. "
        "4) Keyword and content recommendations based on what you find. "
        "Prioritise everything by impact. Give me a clear action plan."
    )


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    cli()
