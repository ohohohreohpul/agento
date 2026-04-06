# Agento — AI SEO Agentic Tool

An AI-powered SEO agent built on **Claude Opus 4.6** that autonomously handles the full SEO stack:

| Category | Capabilities |
|----------|-------------|
| **Technical SEO** | Meta tags, headings, schema detection, images, links, HTTPS, word count, load time |
| **Keyword Research** | Google Autocomplete (free) + DataForSEO volume/difficulty/CPC (optional) |
| **Backlink Discovery** | Guest post targets, resource pages, outreach email templates + DataForSEO competitor backlinks |
| **Schema Generation** | Article, FAQ, HowTo, Product, LocalBusiness, Breadcrumb, WebSite (JSON-LD) |
| **GEO/AEO Optimisation** | AI readiness score (0–100) for ChatGPT, Perplexity, Google AI Overviews, Gemini |
| **llms.txt Generator** | AI crawler optimisation file + robots.txt AI bot audit |
| **Competitor Analysis** | Keyword gap, backlink gap, top competitor pages (DataForSEO) |
| **Google Search Console** | Real traffic data, quick-win opportunities, coverage issues |

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
python main.py llmstxt --url https://example.com
python main.py gsc --property https://example.com/
python main.py competitor --your-domain yourblog.com --competitor rival.com
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
| `llmstxt --url URL` | Generate llms.txt + audit AI bot access |
| `gsc --property URL` | Google Search Console performance + quick wins |
| `competitor --your-domain D --competitor C` | Full competitor gap analysis |

---

## API Keys

All commands work with only `ANTHROPIC_API_KEY`. Add these to `.env` for richer data:

| Key | What it unlocks |
|-----|----------------|
| `ANTHROPIC_API_KEY` | **Required** — Claude Opus 4.6 |
| `DATAFORSEO_LOGIN` + `DATAFORSEO_PASSWORD` | Keyword volume, difficulty, CPC; competitor keyword/backlink gaps |
| `SERPAPI_KEY` | Live SERP rank checking |
| `GSC_SERVICE_ACCOUNT_JSON` | Google Search Console real traffic data (path to service account JSON) |

**DataForSEO** offers pay-as-you-go — [sign up](https://dataforseo.com). At ~$0.001/request it's by far the most cost-effective SEO data API.

**Google Search Console** setup:
1. Create a GCP project → enable Search Console API
2. Create a Service Account → download JSON key
3. Set `GSC_SERVICE_ACCOUNT_JSON=/path/to/key.json` in `.env`
4. Grant the service account "Full User" access in GSC

---

## Architecture

```
main.py              CLI (click + rich) — 10 commands
agent.py             Claude Opus 4.6 orchestrator — streaming agentic loop
tools/
  web_audit.py       Technical SEO scraper (httpx + BeautifulSoup)
  keywords.py        Keyword research (Google Autocomplete + DataForSEO)
  backlinks.py       Link prospect finder (Google search + DataForSEO)
  schema.py          JSON-LD schema generators (7 types)
  geo_optimizer.py   GEO/AEO content scorer (9 Princeton/GT signals, 0–100)
  llms_txt.py        llms.txt generator + AI bot access auditor
  gsc.py             Google Search Console integration
  competitor.py      Competitor keyword/backlink/page gap analysis
models.py            Pydantic v2 data models
config.py            Environment config (.env)
tests/               Test suite
```

Claude uses **adaptive thinking** to reason through complex SEO problems before calling tools, and **tool use** to execute the right analysis steps in the right order — just like a senior SEO consultant would.

---

## Why GEO/AEO Matters in 2026

~31% of US searches now go through AI interfaces. AI referral traffic converts at **4.4× the rate** of organic traffic.

**2026 AI Search Benchmarks (used in Agento's GEO scorer):**

| Signal | Source | Impact |
|--------|--------|--------|
| FAQ section + FAQPage schema | GEO Tracker community | Highest single-item GEO lift |
| Direct answer in first paragraph | Princeton/Georgia Tech (2023) | 44.2% of LLM citations from top 30% of page |
| Statistics with source attribution | Princeton/Georgia Tech | Top-3 highest-impact tactic |
| Expert quotations | Princeton/Georgia Tech | Top-3 highest-impact tactic |
| Content freshness (≥ current year) | Conductor 2026 study | 3× more likely to be cited |
| Wikipedia-style structure | Conductor 2026 study | Wikipedia cited in 47.9% of ChatGPT results |
| Article + FAQPage JSON-LD schema | SiteUp.ai 2026 | Direct machine-readable metadata for AI engines |
| llms.txt deployed | llmstxt.org | Adopted by Stripe, Cloudflare, Vercel, 1,000+ sites |
| AI bots allowed in robots.txt | GEO community | GPTBot, ClaudeBot, PerplexityBot, Google-Extended |

**llms.txt** is the `robots.txt` for AI search engines — a structured markdown index at `yourdomain.com/llms.txt` that tells AI crawlers what to read and cite. Agento generates it automatically.

---

## Research Foundation

This tool was built on research from:
- **Princeton/Georgia Tech** — "GEO: Generative Engine Optimization" (Aggarwal et al., 2023): 9 proven tactics for 40% AI visibility lift
- **Conductor 2026** — AI referral traffic analysis across 13,770 domains
- **amplifying-ai/awesome-generative-engine-optimization** — community GEO tracker
- **DataForSEO** — SEO data APIs
- **ByteDance DeerFlow** — multi-agent research architecture patterns
- **CrewAI** — multi-agent role orchestration patterns
