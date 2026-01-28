<p align="center">
  <img src="https://img.shields.io/badge/Version-2.0-black?style=for-the-badge" alt="Version"/>
  <img src="https://img.shields.io/badge/Python-3.11+-black?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/License-MIT-black?style=for-the-badge" alt="License"/>
</p>

```
██████  ██████   █████  ██████  ███    ███  █████  ███    ██
██   ██ ██      ██   ██ ██   ██ ████  ████ ██   ██ ████   ██
██   ██ █████   ███████ ██   ██ ██ ████ ██ ███████ ██ ██  ██
██   ██ ██      ██   ██ ██   ██ ██  ██  ██ ██   ██ ██  ██ ██
██████  ██████  ██   ██ ██████  ██      ██ ██   ██ ██   ████

        ██    ██ ██   ████████ ██ ███    ███  █████  ████████ ██████
        ██    ██ ██      ██    ██ ████  ████ ██   ██    ██    ██
        ██    ██ ██      ██    ██ ██ ████ ██ ███████    ██    █████
        ██    ██ ██      ██    ██ ██  ██  ██ ██   ██    ██    ██
         ██████  ██████  ██    ██ ██      ██ ██   ██    ██    ██████

        ███████  ██████ ██████   █████  ██████  ██████ ██████
        ██      ██      ██   ██ ██   ██ ██   ██ ██     ██   ██
        ███████ ██      ██████  ███████ ██████  █████  ██████
             ██ ██      ██   ██ ██   ██ ██      ██     ██   ██
        ███████  ██████ ██   ██ ██   ██ ██      ██████ ██   ██
```

<p align="center">
  <strong>DEADMAN // DEATH INCARNATE</strong>
</p>

---

## Overview

5-layer adaptive web scraper with TOR integration, anti-detection, and AI-powered analysis.

---

## Stack

| Layer | Tech |
|-------|------|
| 1 | JA4 TLS fingerprint matching |
| 2 | Stealth Playwright |
| 3 | Undetected ChromeDriver |
| 4 | TOR network |
| 5 | CAPTCHA bypass |

---

## Quick Start

```bash
# Docker (recommended)
docker compose up -d

# Manual
pip install -r requirements.txt
python central_scraper.py
```

```python
from central_scraper import CentralScraper, ScrapeRequest

async with CentralScraper() as scraper:
    result = await scraper.scrape(ScrapeRequest(
        url="https://example.com",
        use_tor=True
    ))
```

---

## Docker

```bash
docker compose up -d tor              # TOR only
docker compose up -d                  # TOR + Scraper
docker compose --profile storage up   # Full stack
```

---

## Structure

```
deadman_scraper/
├── ai/           # LLM routing, token optimization
├── core/         # Engine, scheduler, config
├── fetch/        # 5-layer downloader, TOR
├── stealth/      # Anti-detection
├── extract/      # Content extraction
├── darkweb/      # Onion crawling
└── discovery/    # Search aggregation
```

---

## Related

- [BlackBox](https://github.com/DeadManOfficial/BlackBox) - Security research platform
- [mcp-auditor](https://github.com/DeadManOfficial/mcp-auditor) - Security auditor for Claude
- [token-optimization](https://github.com/DeadManOfficial/token-optimization) - API cost reduction

---

<p align="center">
  <strong>DEADMAN // DEATH INCARNATE</strong><br>
  <sub>ALL FREE FOREVER</sub>
</p>
