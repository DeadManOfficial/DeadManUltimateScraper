<p align="center">
  <img src="https://img.shields.io/badge/Version-2.0-black?style=for-the-badge&logo=github" alt="Version"/>
  <img src="https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License"/>
  <img src="https://img.shields.io/badge/Lines-20K+-orange?style=for-the-badge" alt="Lines"/>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/TOR-Enabled-purple?style=flat-square" alt="TOR"/>
  <img src="https://img.shields.io/badge/LLM-Integrated-blueviolet?style=flat-square" alt="LLM"/>
  <img src="https://img.shields.io/badge/Stealth-Anti--Detection-brightgreen?style=flat-square" alt="Stealth"/>
</p>

```
██████╗ ███████╗ █████╗ ██████╗ ███╗   ███╗ █████╗ ███╗   ██╗
██╔══██╗██╔════╝██╔══██╗██╔══██╗████╗ ████║██╔══██╗████╗  ██║
██║  ██║█████╗  ███████║██║  ██║██╔████╔██║███████║██╔██╗ ██║
██║  ██║██╔══╝  ██╔══██║██║  ██║██║╚██╔╝██║██╔══██║██║╚██╗██║
██████╔╝███████╗██║  ██║██████╔╝██║ ╚═╝ ██║██║  ██║██║ ╚████║
╚═════╝ ╚══════╝╚═╝  ╚═╝╚═════╝ ╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝

        ██╗   ██╗██╗  ████████╗██╗███╗   ███╗ █████╗ ████████╗███████╗
        ██║   ██║██║  ╚══██╔══╝██║████╗ ████║██╔══██╗╚══██╔══╝██╔════╝
        ██║   ██║██║     ██║   ██║██╔████╔██║███████║   ██║   █████╗
        ██║   ██║██║     ██║   ██║██║╚██╔╝██║██╔══██║   ██║   ██╔══╝
        ╚██████╔╝███████╗██║   ██║██║ ╚═╝ ██║██║  ██║   ██║   ███████╗
         ╚═════╝ ╚══════╝╚═╝   ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝   ╚═╝   ╚══════╝

                    ███████╗ ██████╗██████╗  █████╗ ██████╗ ███████╗██████╗
                    ██╔════╝██╔════╝██╔══██╗██╔══██╗██╔══██╗██╔════╝██╔══██╗
                    ███████╗██║     ██████╔╝███████║██████╔╝█████╗  ██████╔╝
                    ╚════██║██║     ██╔══██╗██╔══██║██╔═══╝ ██╔══╝  ██╔══██╗
                    ███████║╚██████╗██║  ██║██║  ██║██║     ███████╗██║  ██║
                    ╚══════╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚══════╝╚═╝  ╚═╝
```

<p align="center">
  <strong>AI-Powered Web Intelligence Engine</strong><br>
  <em>5-Layer Adaptive Stack • TOR Integration • Anti-Detection Suite</em>
</p>

---

## Overview

**DeadMan Ultimate Scraper** is an enterprise-grade web scraping framework with a 5-layer adaptive fetching system, built-in anti-detection, TOR routing, and AI-powered content analysis. Designed for intelligence gathering, research, and data extraction at scale.

### Philosophy

```
BUILD > BUY
```

### Core Principles

- **Adaptive Fetching** — Automatically escalates through layers until success
- **Stealth First** — Fingerprint masking, behavioral simulation, session management
- **AI-Enhanced** — LLM-powered relevance filtering and content extraction
- **Fault Tolerant** — Automatic retry, checkpoint recovery, graceful degradation

---

## Features

<table>
<tr>
<td width="50%">

### 5-Layer Fetch Stack
1. **JA4 TLS** — Fingerprint-matched requests
2. **Stealth Browser** — Playwright with injection
3. **Selenium UC** — Undetected ChromeDriver
4. **TOR Network** — Onion routing
5. **CAPTCHA Bypass** — Multi-solver integration

</td>
<td width="50%">

### Anti-Detection Suite
- Canvas/WebGL/Audio fingerprint noise
- Human-like mouse movements
- Typing cadence simulation
- Session cookie extraction
- Proxy rotation

</td>
</tr>
<tr>
<td>

### AI Integration
- Free LLM routing (Mistral, Groq, Cerebras)
- Relevance filtering
- Smart extraction strategies
- Token optimization (30-50% savings)

</td>
<td>

### Data Pipeline
- Multi-engine search aggregation
- Deduplication & scheduling
- Priority queuing
- MongoDB/Elasticsearch storage

</td>
</tr>
<tr>
<td>

### Dark Web Support
- TOR circuit management
- Onion crawling
- Media extraction
- OSINT collection

</td>
<td>

### Deployment Options
- Local execution
- Modal cloud deployment
- Docker containerization
- GitHub Actions automation

</td>
</tr>
</table>

---

## Architecture

```
deadman_scraper/
├── ai/                    # LLM routing & token optimization
│   ├── llm_router.py      # Free LLM provider routing
│   ├── relevance.py       # AI-powered filtering
│   └── token_optimizer/   # Cost reduction suite
├── core/                  # Engine orchestration
│   ├── engine.py          # Main coordinator
│   ├── scheduler.py       # Priority queue
│   └── config.py          # Configuration management
├── fetch/                 # 5-layer downloader
│   ├── downloader.py      # Adaptive fetcher
│   ├── tor_manager.py     # TOR circuit control
│   └── proxy_manager.py   # Proxy rotation
├── stealth/               # Anti-detection
│   ├── fingerprint.py     # Browser fingerprinting
│   ├── behavior.py        # Human simulation
│   └── session.py         # Cookie extraction
├── extract/               # Content extraction
│   ├── extractor.py       # Strategy pattern
│   └── url_extractor.py   # Link discovery
├── darkweb/               # Onion services
│   ├── crawler.py         # TOR crawler
│   └── media.py           # Media extraction
└── discovery/             # Search aggregation
    └── aggregator.py      # Multi-engine search
```

---

## Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/DeadManOfficial/DeadManUltimateScraper.git
cd DeadManUltimateScraper

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### Basic Usage

```python
from central_scraper import CentralScraper, ScrapeRequest

async with CentralScraper() as scraper:
    # Simple scrape
    result = await scraper.scrape(ScrapeRequest(
        url="https://example.com"
    ))
    print(result.content)

    # With TOR and session stealing
    result = await scraper.scrape(ScrapeRequest(
        url="https://protected-site.com",
        use_tor=True,
        steal_session=True,
        use_llm=True
    ))
```

### Intelligence Gathering

```python
async with CentralScraper() as scraper:
    # Multi-engine search + scrape
    async for result in scraper.search_intelligence(
        query="security vulnerabilities 2024",
        darkweb=False
    ):
        print(f"Found: {result.url}")
        print(f"Content: {result.content[:500]}")
```

### CLI Usage

```bash
# Single URL scrape
python central_scraper.py --url https://example.com

# Dark web crawl
python cli/main.py darkweb crawl --seed http://example.onion

# Intelligence mission
python armory.py --query "topic" --depth 3
```

---

## Configuration

### Environment Variables

```bash
# API Keys (optional - for LLM features)
OPENAI_API_KEY=sk-...
GROQ_API_KEY=gsk_...
MISTRAL_API_KEY=...

# TOR Configuration
TOR_SOCKS_PORT=9050
TOR_CONTROL_PORT=9051

# Proxy Settings
PROXY_LIST=/path/to/proxies.txt
```

### YAML Configuration

```yaml
# config/default.yaml
fetch:
  max_concurrent: 10
  timeout: 30
  retry_count: 3

tor:
  enabled: true
  circuit_timeout: 120

llm:
  provider: groq
  model: mixtral-8x7b-32768
```

---

## Fetch Layer Escalation

```
┌─────────────────────────────────────────────────────────────────┐
│                     REQUEST ARRIVES                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 1: JA4 TLS Request                                       │
│  ├── curl_cffi with browser fingerprint                         │
│  └── Success? → Return                                          │
└─────────────────────────────────────────────────────────────────┘
                              │ Fail
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 2: Stealth Playwright                                    │
│  ├── Fingerprint injection                                      │
│  ├── Canvas/WebGL noise                                         │
│  └── Success? → Return                                          │
└─────────────────────────────────────────────────────────────────┘
                              │ Fail
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 3: Undetected ChromeDriver                               │
│  ├── Selenium with UC patches                                   │
│  └── Success? → Return                                          │
└─────────────────────────────────────────────────────────────────┘
                              │ Fail
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 4: TOR Network                                           │
│  ├── Circuit rotation                                           │
│  ├── Exit node selection                                        │
│  └── Success? → Return                                          │
└─────────────────────────────────────────────────────────────────┘
                              │ Fail
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 5: CAPTCHA Bypass                                        │
│  ├── 2Captcha/Anti-Captcha                                      │
│  └── Human-in-the-loop fallback                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [USAGE_GUIDE.md](USAGE_GUIDE.md) | Detailed usage instructions |
| [DESIGN_SPECIFICATION.md](DESIGN_SPECIFICATION.md) | Architecture design |
| [STYLE_GUIDE.md](STYLE_GUIDE.md) | Code style guidelines |
| [docs/ULTIMATE_BOT_BYPASS_GUIDE.md](docs/ULTIMATE_BOT_BYPASS_GUIDE.md) | Anti-detection techniques |
| [docs/TOR_INTEGRATION_SOLUTIONS.md](docs/TOR_INTEGRATION_SOLUTIONS.md) | TOR setup & usage |
| [docs/DARKWEB_RESEARCH_PLAN.md](docs/DARKWEB_RESEARCH_PLAN.md) | Dark web methodology |

---

## Related Projects

| Project | Description |
|---------|-------------|
| [**BlackBox**](https://github.com/DeadManOfficial/BlackBox) | Security research platform |
| [**token-optimization**](https://github.com/DeadManOfficial/token-optimization) | Save 30-50% on API costs |
| [**mcp-auditor**](https://github.com/DeadManOfficial/mcp-auditor) | Security auditor for Claude |

---

## Disclaimer

> This tool is for authorized use only.

- Respect robots.txt and terms of service
- Obtain permission before scraping
- Use responsibly and ethically
- Follow applicable laws and regulations

---

## License

MIT License - See [LICENSE](LICENSE) for details.

---

<p align="center">
  <strong>DeadMan Toolkit v5.3</strong><br>
  <em>ALL FREE FOREVER</em><br><br>
  <a href="https://github.com/DeadManOfficial">
    <img src="https://img.shields.io/badge/Author-DeadManOfficial-black?style=for-the-badge&logo=github" alt="Author"/>
  </a>
</p>

<p align="center">
  <sub>BUILD > BUY</sub>
</p>
