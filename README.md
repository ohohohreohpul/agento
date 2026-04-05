# Agento — AI SEO Agentic Tool

An AI-powered SEO agent built on **Claude Opus 4.6** that autonomously handles:

- **Technical SEO audits** — meta tags, headings, schema, images, links, HTTPS, word count
- **Keyword research** — Google Autocomplete + DataForSEO (optional) for volume/difficulty
- **Backlink discovery** — guest post targets, resource pages, outreach email templates
- **Schema markup generation** — Article, FAQ, HowTo, Product, LocalBusiness, Breadcrumb, WebSite
- **GEO/AEO optimisation** — AI readiness scoring for ChatGPT, Perplexity & Google AI Overviews

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure API keys
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# 3. Run interactive chat mode
python main.py chat

# Or use specific commands:
python main.py audit --url https://example.com
python main.py keywords --topic "content marketing"
python main.py backlinks --domain example.com --niche "digital marketing"
python main.py geo --url https://example.com/blog/my-post
python main.py full --url https://example.com          # everything at once
python main.py schema --type faq --title "My Guide"
```

---

## Commands

| Command | What it does |
|---------|-------------|
| `chat` | Interactive mode — describe any SEO task in plain English |
| `audit --url URL` | Full technical SEO audit |
| `keywords --topic TOPIC` | Keyword research & suggestions |
| `backlinks --domain D --niche N` | Find link-building opportunities |
| `geo --url URL` | GEO/AEO readiness score + fixes for AI search |
| `schema --type TYPE` | Generate JSON-LD schema markup |
| `full --url URL` | Complete audit: technical + GEO + keywords |

---

## Optional API Keys

All commands work without extra API keys. Add these to `.env` for richer data:

| Key | What it unlocks |
|-----|----------------|
| `DATAFORSEO_LOGIN` + `DATAFORSEO_PASSWORD` | Keyword search volume, difficulty, CPC |
| `SERPAPI_KEY` | Live SERP rank checking |

DataForSEO offers pay-as-you-go pricing — [sign up here](https://dataforseo.com).

---

## Architecture

```
main.py            CLI (click + rich)
agent.py           Claude Opus 4.6 orchestrator — tool use agentic loop
tools/
  web_audit.py     Technical SEO scraper (httpx + BeautifulSoup)
  keywords.py      Keyword research (Google Autocomplete + DataForSEO)
  backlinks.py     Link prospect finder (Google search + DataForSEO)
  schema.py        JSON-LD schema generators
  geo_optimizer.py GEO/AEO content scorer
models.py          Pydantic data models
config.py          Environment config
```

Claude uses **adaptive thinking** to reason through complex SEO problems before calling tools, and **tool use** to execute the right analysis steps in the right order — just like a senior SEO consultant would.

---

## Why GEO/AEO Matters in 2026

~31% of US searches now go through AI interfaces (ChatGPT, Perplexity, Google AI Overviews). AI referral traffic converts at **4.4× the rate** of organic traffic. Agento's GEO optimizer scores your content against the signals AI engines use to decide what to cite:

- Direct answers in the intro
- FAQ / Q&A sections
- Structured data (JSON-LD)
- Author E-E-A-T signals
- Content freshness
- External citations
- Question-format headings
