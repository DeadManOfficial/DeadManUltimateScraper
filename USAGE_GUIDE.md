# DeadMan Ultimate Scraper - Usage Guide

## Table of Contents
1. [Quick Start](#quick-start)
2. [Installation](#installation)
3. [Usage Methods](#usage-methods)
4. [Dashboard](#dashboard)
5. [Configuration](#configuration)
6. [Advanced Usage](#advanced-usage)

---

## Quick Start

### Option 1: Docker (Recommended)
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f scraper

# Access dashboard
open http://localhost:3000
```

### Option 2: Python Direct
```bash
# Install dependencies
pip install -r requirements.txt

# Run a quick scrape
python -c "
import asyncio
from central_scraper import CentralScraper, ScrapeRequest

async def main():
    async with CentralScraper() as scraper:
        result = await scraper.scrape(ScrapeRequest(
            url='https://example.com',
            use_tor=False
        ))
        print(f'Success: {result.success}')
        print(f'Content: {result.content[:200]}...')

asyncio.run(main())
"
```

---

## Installation

### Prerequisites
- Python 3.10+
- Node.js 18+ (for dashboard)
- Docker & Docker Compose (optional)
- TOR (optional, for darknet)

### Step 1: Clone and Install
```bash
cd G:\Projects\DeadManUltimateScraper

# Python dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium firefox
```

### Step 2: Start TOR (Optional)
```bash
# Using Docker
docker run -d --name deadman-tor -p 9050:9050 dperson/torproxy

# Or use the built-in TOR manager
python -c "from deadman_scraper.fetch.tor_enhanced import TorManager; TorManager().start()"
```

### Step 3: Start Services (Full Stack)
```bash
# Start Elasticsearch + MongoDB
docker-compose up -d elasticsearch mongodb redis

# Start API server
cd server && npm install && npm start &

# Start dashboard
cd dashboard && npm install && npm start &
```

---

## Usage Methods

### Method 1: Python API (Most Powerful)

```python
import asyncio
from central_scraper import CentralScraper, ScrapeRequest
from deadman_scraper.core.scheduler import Priority

async def scrape_examples():
    async with CentralScraper() as scraper:

        # Basic scrape
        result = await scraper.scrape(ScrapeRequest(
            url="https://news.ycombinator.com"
        ))
        print(f"Fetched {len(result.content)} bytes")

        # Scrape with TOR
        result = await scraper.scrape(ScrapeRequest(
            url="http://example.onion",
            use_tor=True,
            priority=Priority.HIGH
        ))

        # Scrape with LLM analysis
        result = await scraper.scrape(ScrapeRequest(
            url="https://github.com/trending",
            use_llm=True,
            extract_strategy="auto"
        ))

        # Scrape with session hijacking (use existing Chrome cookies)
        result = await scraper.scrape(ScrapeRequest(
            url="https://authenticated-site.com",
            steal_session=True
        ))

asyncio.run(scrape_examples())
```

### Method 2: Batch Scraping

```python
import asyncio
from central_scraper import CentralScraper, ScrapeRequest

async def batch_scrape():
    urls = [
        "https://news.ycombinator.com",
        "https://reddit.com/r/netsec",
        "https://github.com/trending",
        "https://stackoverflow.com/questions"
    ]

    requests = [ScrapeRequest(url=url) for url in urls]

    async with CentralScraper() as scraper:
        async for result in scraper.scrape_batch(requests):
            print(f"[{result.status_code}] {result.url}")
            if result.success:
                print(f"  Content: {len(result.content)} bytes")
                print(f"  Layer: {result.fetch_layer}")

asyncio.run(batch_scrape())
```

### Method 3: Intelligence Gathering (Search + Scrape)

```python
import asyncio
from central_scraper import CentralScraper

async def gather_intel():
    async with CentralScraper() as scraper:
        # Search clearnet
        async for result in scraper.search_intelligence("CVE-2024", darkweb=False):
            print(f"Found: {result.url}")
            print(f"Content preview: {result.content[:100]}...")

        # Search darknet (requires TOR)
        async for result in scraper.search_intelligence("leaked credentials", darkweb=True):
            print(f"[ONION] {result.url}")

asyncio.run(gather_intel())
```

### Method 4: CLI Usage

```bash
# Using the CLI module
python -m cli.main scrape https://example.com

# With options
python -m cli.main scrape https://example.com --tor --llm --output json

# Deep scrape (recursive)
python -m cli.main deep https://example.com --depth 3 --keywords "security,exploit"
```

### Method 5: Armory Dashboard (Status Check)

```bash
# Check system status
python armory.py status

# Deploy to production
python armory.py deploy
```

---

## Dashboard

### Accessing the Dashboard
1. Start the API server: `cd server && npm start`
2. Start the dashboard: `cd dashboard && npm start`
3. Open http://localhost:3000

### Dashboard Features

#### Data Table
- **Infinite scroll** - Loads more as you scroll
- **Search** - Filter results in real-time
- **Click to hide** - Mark items as seen
- **Show All** - Toggle hidden items

#### Sentiment Charts
- **Score Chart** - Raw threat score over time
- **Comparative Chart** - Normalized sentiment
- **Average line** - Visual baseline

#### Keyword Pie Chart
- **Add/remove keywords** dynamically
- **Color-coded** frequency distribution
- **Hover** for details

#### Settings Modal
- **Cooldown period** - Time between scrape cycles
- **TOR toggle** - Enable/disable TOR proxy
- **Darkweb toggle** - Enable .onion scraping
- **LLM analysis** - Enable AI extraction
- **Keywords** - Manage search terms

### Real-Time Updates
The dashboard polls status every 15 seconds and receives WebSocket updates for new data.

---

## Configuration

### Main Config: `config/default.yaml`

```yaml
# Fetch settings
fetch:
  max_concurrent: 10
  request_timeout: 30
  layers:
    - curl_cffi      # TLS fingerprinting
    - camoufox      # Stealth browser
    - chromedriver  # Full browser
    - tor           # TOR fallback

# TOR settings
tor:
  enabled: true
  socks_port: 9050
  circuit_renew_interval: 300

# Stealth settings
stealth:
  inject_stealth: true
  spoof_canvas: true
  spoof_webgl: true
  simulate_human: true

# LLM settings
llm:
  primary: mistral
  fallback_chain:
    - mistral
    - groq
    - ollama

# Storage (NEW)
elasticsearch:
  hosts: ["http://localhost:9200"]
  index_name: deadman_scrapes

mongodb:
  uri: "mongodb://localhost:27017"
  database: deadman_scraper
```

### Environment Variables

```bash
# API Keys
export MISTRAL_API_KEY="your-key"
export GROQ_API_KEY="your-key"
export OPENROUTER_API_KEY="your-key"

# Services
export ELASTICSEARCH_HOST="http://localhost:9200"
export MONGODB_URI="mongodb://localhost:27017"
export TOR_PROXY="socks5h://127.0.0.1:9050"
```

---

## Advanced Usage

### Using Elasticsearch Storage

```python
from deadman_scraper.storage.elasticsearch import ElasticsearchStore

# Connect
es = ElasticsearchStore(hosts="http://localhost:9200")

# Index documents
es.bulk_index([
    {"url": "https://example.com", "title": "Example", "content": "..."},
    {"url": "https://test.com", "title": "Test", "content": "..."}
])

# Search
results = es.search("vulnerability exploit", size=100)
for doc in results:
    print(f"{doc['title']}: {doc['url']}")

# Paginated (for infinite scroll)
page_0 = es.search_paginated(page=0, page_size=10, query="bitcoin")
page_1 = es.search_paginated(page=1, page_size=10, query="bitcoin")

# Keyword frequency
counts = es.get_keyword_frequencies(["bitcoin", "ransomware", "exploit"])
```

### Using Sentiment Analysis

```python
from deadman_scraper.analytics.sentiment import SentimentAnalyzer, get_threat_score

# Analyze text
analyzer = SentimentAnalyzer()
result = analyzer.analyze("Selling stolen credit cards and fullz, bitcoin accepted")

print(f"Score: {result.score}")           # -23
print(f"Comparative: {result.comparative}") # -2.87
print(f"Keywords: {result.keyword_matches}") # ['stolen', 'credit cards', 'fullz', 'bitcoin']
print(f"Threat Level: {analyzer.get_threat_level(result.score)}")  # 'medium'

# Quick threat check
score, level = get_threat_score("ransomware attack on hospital")
print(f"Threat: {level} ({score})")  # Threat: medium (-7)
```

### Worker Deployment

```python
# Run as standalone worker
python -m deadman_scraper.worker

# Or in Docker
docker-compose up -d scraper
docker-compose logs -f scraper
```

---

## Troubleshooting

### TOR Connection Failed
```bash
# Check TOR is running
curl --socks5 localhost:9050 https://check.torproject.org/api/ip

# Restart TOR container
docker restart deadman-tor
```

### Elasticsearch Connection Failed
```bash
# Check Elasticsearch health
curl http://localhost:9200/_cluster/health

# Check index exists
curl http://localhost:9200/deadman_scrapes
```

### Dashboard Not Loading
```bash
# Check API server
curl http://localhost:8080/api/health

# Rebuild dashboard
cd dashboard && npm run build
```

---

## Security Notes

- **Never commit API keys** - Use environment variables
- **TOR for sensitive targets** - Always enable for darknet
- **Rate limiting** - Respect target site limits
- **Legal compliance** - Only scrape authorized targets

---

*DeadMan Ultimate Scraper - ALL FREE FOREVER*
